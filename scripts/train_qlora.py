"""Memory-conscious QLoRA / LoRA SFT training pipeline for Qwen models.

Compatible with:
 - Windows 11 & Linux
 - NVIDIA RTX 5050 Laptop GPU (Blackwell sm_120) and modern CUDA
 - BitsAndBytes NF4 4-bit quantization with double quantization
 - HuggingFace Transformers, PEFT, TRL SFTTrainer
 - Offline local cache resolution for Qwen3-0.6B and Qwen3-8B
 - Checkpoint saving, resumption, telemetry logging, and adapter export
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import torch
except ImportError:
    torch = None

ROOT = Path(__file__).resolve().parents[1]
root_str = str(ROOT)
for p in [root_str, "", "."]:
    if p in sys.path:
        sys.path.remove(p)
DEFAULT_HF_CACHE = Path.home() / ".cache" / "huggingface" / "hub"


def resolve_model_path(model_identifier: str) -> str:
    """Resolve model identifier to local snapshot if present in cache, else return original."""
    p = Path(model_identifier)
    if p.exists():
        return str(p)

    # Check HF cache
    sanitized = "models--" + model_identifier.replace("/", "--")
    cache_model_dir = DEFAULT_HF_CACHE / sanitized / "snapshots"
    if cache_model_dir.exists():
        snapshots = [s for s in cache_model_dir.iterdir() if s.is_dir()]
        if snapshots:
            best_snap = snapshots[0]
            print(f"[Model Resolver] Found local cached snapshot: {best_snap}", flush=True)
            return str(best_snap)

    return model_identifier


def preflight_vram_check(torch_mod: Any, min_free_gib: float = 1.0) -> Dict[str, float]:
    """Check GPU availability and free VRAM."""
    if not torch_mod.cuda.is_available():
        raise RuntimeError("CUDA is unavailable. Please verify NVIDIA driver and PyTorch CUDA build.")

    free_b, total_b = torch_mod.cuda.mem_get_info()
    free_gib = free_b / (1024 ** 3)
    total_gib = total_b / (1024 ** 3)
    gpu_name = torch_mod.cuda.get_device_name(0)

    print(f"[Preflight] GPU: {gpu_name} | Total VRAM: {total_gib:.2f} GiB | Free VRAM: {free_gib:.2f} GiB", flush=True)

    if free_gib < min_free_gib:
        raise RuntimeError(
            f"Insufficient free VRAM ({free_gib:.2f} GiB free, minimum required is {min_free_gib:.1f} GiB). "
            "Please close GPU-intensive applications (e.g. browser hardware acceleration, games) and retry."
        )

    torch_mod.cuda.reset_peak_memory_stats()
    return {"total_gib": total_gib, "free_gib": free_gib}


def main() -> int:
    parser = argparse.ArgumentParser(description="Atlas Qwen QLoRA Training Pipeline")
    parser.add_argument("--config", default="configs/qlora_qwen3_8b.yaml", help="Path to config JSON/YAML")
    parser.add_argument("--model", default=None, help="Model name or snapshot path override")
    parser.add_argument("--train-file", default="data/processed/train.jsonl", help="Train dataset JSONL")
    parser.add_argument("--eval-file", default="data/processed/eval.jsonl", help="Eval dataset JSONL")
    parser.add_argument("--output-dir", default=None, help="Output directory override")
    parser.add_argument("--epochs", type=int, default=None, help="Number of epochs override")
    parser.add_argument("--max-steps", type=int, default=None, help="Maximum training steps override")
    parser.add_argument("--batch-size", type=int, default=None, help="Batch size override")
    parser.add_argument("--grad-accum", type=int, default=None, help="Gradient accumulation override")
    parser.add_argument("--lr", type=float, default=None, help="Learning rate override")
    parser.add_argument("--max-seq-len", type=int, default=None, help="Max sequence length override")
    parser.add_argument("--no-quant", action="store_true", help="Disable 4-bit quantization (e.g. for small models like 0.6B)")
    parser.add_argument("--smoke-test", action="store_true", help="Run rapid smoke test steps")
    parser.add_argument("--resume", default=None, help="Path to checkpoint to resume from")

    args = parser.parse_args()

    import torch
    from datasets import load_dataset
    from peft import LoraConfig, get_peft_model
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        BitsAndBytesConfig,
        TrainerCallback,
        TrainingArguments,
    )
    from trl import SFTTrainer

    # Load configuration
    cfg_path = Path(args.config)
    if not cfg_path.is_absolute():
        cfg_path = ROOT / cfg_path
    cfg: Dict[str, Any] = {}
    if cfg_path.exists():
        try:
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        except Exception:
            cfg = {}

    model_raw = args.model or cfg.get("model_name", "Qwen/Qwen3-1.7B")
    model_resolved = resolve_model_path(model_raw)

    raw_output_dir = args.output_dir or cfg.get("output_dir", f"training_artifacts/{Path(model_raw).name.lower()}-qlora")
    output_path = Path(raw_output_dir)
    if not output_path.is_absolute():
        output_path = ROOT / output_path
    output_dir = str(output_path)
    output_path.mkdir(parents=True, exist_ok=True)

    train_path = Path(args.train_file)
    if not train_path.is_absolute():
        train_path = ROOT / train_path

    eval_path = Path(args.eval_file)
    if not eval_path.is_absolute():
        eval_path = ROOT / eval_path

    max_seq_len = args.max_seq_len or cfg.get("max_seq_length", 1024)
    batch_size = args.batch_size or cfg.get("per_device_train_batch_size", 1)
    grad_accum = args.grad_accum or cfg.get("gradient_accumulation_steps", 4)
    num_epochs = args.epochs or cfg.get("num_train_epochs", 3)
    learning_rate = args.lr or cfg.get("learning_rate", 2e-4)
    lora_r = cfg.get("lora_r", 16)
    lora_alpha = cfg.get("lora_alpha", 32)
    lora_dropout = cfg.get("lora_dropout", 0.05)
    seed = cfg.get("seed", 42)

    smoke = args.smoke_test or bool(cfg.get("smoke_test", {}).get("enabled", False))
    max_steps = args.max_steps if args.max_steps is not None else (int(cfg.get("smoke_test", {}).get("max_steps", 20)) if smoke else -1)

    # Preflight
    if "0.6B" in model_raw or "0.5B" in model_raw:
        min_vram = 0.8
    elif "1.7B" in model_raw or "1.5B" in model_raw or "2B" in model_raw or "3B" in model_raw:
        min_vram = 2.0
    else:
        min_vram = 5.0
    vram_stats = preflight_vram_check(torch, min_free_gib=min_vram)

    print("\n--- Training Parameters ---", flush=True)
    print(f"Model: {model_raw} ({model_resolved})", flush=True)
    print(f"Output Directory: {output_dir}", flush=True)
    print(f"Max Sequence Length: {max_seq_len}", flush=True)
    print(f"Batch Size: {batch_size} | Grad Accum: {grad_accum} | Effective Batch: {batch_size * grad_accum}", flush=True)
    print(f"Epochs: {num_epochs} | Max Steps: {max_steps} | Learning Rate: {learning_rate}", flush=True)
    print(f"LoRA Rank (r): {lora_r} | Alpha: {lora_alpha} | Dropout: {lora_dropout}", flush=True)

    # Tokenizer
    tok = AutoTokenizer.from_pretrained(model_resolved, trust_remote_code=True)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token

    # Quantization Setup
    compute_dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
    quant_config = None
    if not args.no_quant:
        quant_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=compute_dtype,
            bnb_4bit_use_double_quant=True,
        )

    print("[Model] Loading model weights into memory...", flush=True)
    load_kwargs: Dict[str, Any] = {
        "device_map": "auto",
        "trust_remote_code": True,
        "torch_dtype": compute_dtype,
    }
    if quant_config:
        load_kwargs["quantization_config"] = quant_config

    model = AutoModelForCausalLM.from_pretrained(model_resolved, **load_kwargs)
    model.config.use_cache = False

    # Datasets
    print(f"[Data] Loading train from {train_path} and eval from {eval_path}...", flush=True)
    ds = load_dataset("json", data_files={"train": str(train_path), "eval": str(eval_path)})

    def format_chatml(example: Dict[str, Any]) -> Dict[str, str]:
        messages = example["messages"]
        formatted = tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)
        return {"text": formatted}

    ds = ds.map(format_chatml)
    print(f"[Data] Formatted {len(ds['train'])} train and {len(ds['eval'])} eval samples.", flush=True)

    # LoRA Config
    lora = LoraConfig(
        r=lora_r,
        lora_alpha=lora_alpha,
        lora_dropout=lora_dropout,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        task_type="CAUSAL_LM",
        bias="none",
    )

    # Telemetry Tracking Callback
    telemetry: Dict[str, Any] = {
        "losses": [],
        "initial_loss": None,
        "final_loss": None,
        "peak_vram_allocated_gib": 0.0,
        "peak_vram_reserved_gib": 0.0,
        "steps_completed": 0,
        "training_time_seconds": 0.0,
    }

    start_time = time.time()

    class TelemetryCallback(TrainerCallback):
        def on_log(self, _args, state, control, logs=None, **_kwargs):
            logs = logs or {}
            loss = logs.get("loss")
            if loss is not None:
                telemetry["losses"].append({"step": state.global_step, "loss": float(loss)})
                if telemetry["initial_loss"] is None:
                    telemetry["initial_loss"] = float(loss)
                telemetry["final_loss"] = float(loss)

            allocated = torch.cuda.max_memory_allocated() / (1024 ** 3)
            reserved = torch.cuda.max_memory_reserved() / (1024 ** 3)
            telemetry["peak_vram_allocated_gib"] = max(telemetry["peak_vram_allocated_gib"], allocated)
            telemetry["peak_vram_reserved_gib"] = max(telemetry["peak_vram_reserved_gib"], reserved)

            step_str = f"Step {state.global_step}" if state.global_step else "Step 0"
            loss_str = f"loss={loss:.4f}" if loss is not None else "loss=n/a"
            lr_str = f"lr={logs.get('learning_rate', 0):.2e}"
            print(f"[{step_str}] {loss_str} | {lr_str} | VRAM alloc={allocated:.2f} GiB | VRAM res={reserved:.2f} GiB", flush=True)

        def on_train_end(self, _args, state, control, **_kwargs):
            telemetry["steps_completed"] = state.global_step
            telemetry["training_time_seconds"] = round(time.time() - start_time, 2)

    # Training Arguments
    train_args = TrainingArguments(
        output_dir=output_dir,
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size,
        gradient_accumulation_steps=grad_accum,
        num_train_epochs=num_epochs,
        max_steps=max_steps,
        learning_rate=learning_rate,
        warmup_ratio=0.05,
        lr_scheduler_type="cosine",
        optim="paged_adamw_8bit" if quant_config else "adamw_torch",
        gradient_checkpointing=True,
        fp16=compute_dtype == torch.float16,
        bf16=compute_dtype == torch.bfloat16,
        eval_strategy="steps" if len(ds["eval"]) > 0 else "no",
        eval_steps=10 if smoke else 25,
        save_strategy="steps",
        save_steps=10 if smoke else 50,
        save_total_limit=2,
        logging_steps=1 if smoke else 5,
        report_to="none",
        seed=seed,
    )

    trainer = SFTTrainer(
        model=model,
        processing_class=tok,
        train_dataset=ds["train"],
        eval_dataset=ds["eval"],
        peft_config=lora,
        args=train_args,
        callbacks=[TelemetryCallback()],
    )

    print("\n[Training] Starting fine-tuning run...", flush=True)
    resume_checkpoint = args.resume or None
    train_result = trainer.train(resume_from_checkpoint=resume_checkpoint)

    # Save final model and tokenizer
    print(f"\n[Artifacts] Saving fine-tuned adapter to {output_dir}...", flush=True)
    trainer.save_model(output_dir)
    tok.save_pretrained(output_dir)

    # Save summary telemetry report
    summary = {
        "model": model_raw,
        "resolved_model_path": model_resolved,
        "train_samples": len(ds["train"]),
        "eval_samples": len(ds["eval"]),
        "parameters": {
            "max_seq_length": max_seq_len,
            "batch_size": batch_size,
            "gradient_accumulation_steps": grad_accum,
            "effective_batch_size": batch_size * grad_accum,
            "learning_rate": learning_rate,
            "lora_r": lora_r,
            "lora_alpha": lora_alpha,
            "quantization": "4-bit NF4 double quant" if quant_config else "none",
        },
        "telemetry": telemetry,
        "train_metrics": train_result.metrics,
    }

    summary_path = Path(output_dir) / "training_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"[Summary] Saved training summary to {summary_path}", flush=True)

    print("\n==========================================", flush=True)
    print("       FINE-TUNING COMPLETED SUCCESSFULLY", flush=True)
    print(f" Steps Completed: {telemetry['steps_completed']}", flush=True)
    if telemetry['initial_loss'] is not None and telemetry['final_loss'] is not None:
        print(f" Initial Loss: {telemetry['initial_loss']:.4f} -> Final Loss: {telemetry['final_loss']:.4f}", flush=True)
    print(f" Peak VRAM Allocated: {telemetry['peak_vram_allocated_gib']:.2f} GiB", flush=True)
    print(f" Peak VRAM Reserved:  {telemetry['peak_vram_reserved_gib']:.2f} GiB", flush=True)
    print(f" Training Wall Time:  {telemetry['training_time_seconds']}s", flush=True)
    print("==========================================\n", flush=True)

    return 0


if __name__ == "__main__":
    try:
        ret = main()
        sys.exit(ret)
    except SystemExit:
        raise
    except Exception as exc:
        if torch is not None and isinstance(exc, getattr(torch.cuda, "OutOfMemoryError", tuple())):
            print("\n[CRITICAL ERROR] CUDA out of memory during training.", file=sys.stderr)
            print("Remedy: Reduce batch_size to 1, reduce max_seq_length, or switch to a lighter model profile.", file=sys.stderr)
        else:
            print(f"\n[TRAINING FAILED] {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(1)
