"""Memory-conscious QLoRA SFT training for Windows GPUs."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

def preflight(torch, cfg):
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is unavailable; install the cu128 torch build and verify the NVIDIA driver.")
    free, total = torch.cuda.mem_get_info(); free_gib, total_gib = free / 2**30, total / 2**30
    print(f"VRAM startup: total={total_gib:.2f} GiB free={free_gib:.2f} GiB", flush=True)
    minimum = float(cfg.get("smoke_test", {}).get("min_free_vram_gib", 6.0))
    if free_gib < minimum:
        raise RuntimeError(f"Only {free_gib:.2f} GiB VRAM is free (need {minimum:.1f} GiB). Close GPU-using apps such as browsers or Discord and retry.")
    torch.cuda.reset_peak_memory_stats()

def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--config", default="configs/qlora_qwen3_8b.yaml"); ap.add_argument("--model", default=None); ap.add_argument("--smoke-test", action="store_true"); args = ap.parse_args()
    import torch
    cfg = json.loads(Path(args.config).read_text(encoding="utf-8")); smoke = args.smoke_test or bool(cfg.get("smoke_test", {}).get("enabled", False))
    try:
        preflight(torch, cfg)
        from datasets import load_dataset
        from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, TrainingArguments, TrainerCallback
        from peft import LoraConfig
        from trl import SFTTrainer
        model_name = args.model or cfg["model_name"]
        compute = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
        bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=compute, bnb_4bit_use_double_quant=True)
        tok = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True); tok.pad_token = tok.pad_token or tok.eos_token
        model = AutoModelForCausalLM.from_pretrained(model_name, quantization_config=bnb, device_map="auto", trust_remote_code=True); model.config.use_cache = False
        ds = load_dataset("json", data_files={"train": "data/processed/train.jsonl", "eval": "data/processed/eval.jsonl"})
        ds = ds.map(lambda ex: {"text": tok.apply_chat_template(ex["messages"], tokenize=False, add_generation_prompt=False)})
        lora = LoraConfig(r=cfg["lora_r"], lora_alpha=cfg["lora_alpha"], lora_dropout=cfg["lora_dropout"], target_modules="all-linear", task_type="CAUSAL_LM")
        telemetry = {"first_loss": None, "last_loss": None, "checkpoint": False, "peak_reserved": 0.0}; interval = int(cfg.get("smoke_test", {}).get("log_every_steps", 10))
        class Telemetry(TrainerCallback):
            def on_log(self, _args, state, control, logs=None, **_kwargs):
                logs = logs or {}
                if "loss" in logs:
                    telemetry["first_loss"] = logs["loss"] if telemetry["first_loss"] is None else telemetry["first_loss"]; telemetry["last_loss"] = logs["loss"]
                if state.global_step and state.global_step % interval == 0:
                    reserved = torch.cuda.max_memory_reserved() / 2**30; telemetry["peak_reserved"] = max(telemetry["peak_reserved"], reserved)
                    print(f"step={state.global_step} loss={logs.get('loss', 'n/a')} lr={logs.get('learning_rate', 'n/a')} peak_allocated={torch.cuda.max_memory_allocated()/2**30:.2f}GiB peak_reserved={reserved:.2f}GiB", flush=True)
            def on_save(self, *_args, **_kwargs): telemetry["checkpoint"] = True
        output = cfg["output_dir"]
        train_args = TrainingArguments(output_dir=output, per_device_train_batch_size=cfg["per_device_train_batch_size"], per_device_eval_batch_size=cfg["per_device_eval_batch_size"], gradient_accumulation_steps=cfg["gradient_accumulation_steps"], num_train_epochs=cfg["num_train_epochs"], learning_rate=cfg["learning_rate"], warmup_ratio=cfg["warmup_ratio"], lr_scheduler_type="cosine", optim="paged_adamw_8bit", gradient_checkpointing=True, fp16=compute == torch.float16, bf16=compute == torch.bfloat16, eval_strategy="no" if smoke else "steps", save_strategy="steps", save_steps=interval, save_total_limit=2, max_steps=int(cfg.get("smoke_test", {}).get("max_steps", 30)) if smoke else -1, logging_steps=1 if smoke else 5, report_to="none", seed=cfg["seed"])
        trainer = SFTTrainer(model=model, processing_class=tok, train_dataset=ds["train"], eval_dataset=ds["eval"], peft_config=lora, args=train_args, dataset_text_field="text", max_seq_length=cfg["max_seq_length"], callbacks=[Telemetry()])
        trainer.train(); trainer.save_model(output); tok.save_pretrained(output); telemetry["checkpoint"] = telemetry["checkpoint"] or any(Path(output).glob("checkpoint-*"))
        if smoke:
            checks = {"loss decreased": telemetry["first_loss"] is not None and telemetry["last_loss"] < telemetry["first_loss"], "checkpoint written": telemetry["checkpoint"], "peak reserved under limit": telemetry["peak_reserved"] < float(cfg["smoke_test"].get("max_reserved_vram_gib", 7.2))}; failed = [k for k, v in checks.items() if not v]
            print("SMOKE TEST PASS" if not failed else "SMOKE TEST FAIL: " + ", ".join(failed), flush=True); return 0 if not failed else 1
        return 0
    except torch.cuda.OutOfMemoryError:
        torch.cuda.empty_cache(); print("CUDA out of memory. Retry with configs/qlora_qwen3_8b_oomsafe.yaml and rerun the VRAM pre-flight; close GPU-using apps first.", file=sys.stderr, flush=True); return 1
    except Exception as exc:
        print(f"TRAINING FAILED: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True); return 1

if __name__ == "__main__": raise SystemExit(main())
