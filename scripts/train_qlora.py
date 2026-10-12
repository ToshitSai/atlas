"""Memory-conscious QLoRA SFT training. Run with training_env/Scripts/python.exe."""
from __future__ import annotations
import argparse, json
from pathlib import Path

def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--config", default="configs/qlora_qwen3_8b.yaml"); ap.add_argument("--model", default=None); args = ap.parse_args()
    import torch
    from datasets import load_dataset
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, TrainingArguments
    from peft import LoraConfig
    from trl import SFTTrainer
    cfg = json.loads(Path(args.config).read_text(encoding="utf-8")); model_name = args.model or cfg["model_name"]
    compute = torch.bfloat16 if torch.cuda.is_available() and torch.cuda.is_bf16_supported() else torch.float16
    bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=compute, bnb_4bit_use_double_quant=True)
    tok = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True); tok.pad_token = tok.pad_token or tok.eos_token
    model = AutoModelForCausalLM.from_pretrained(model_name, quantization_config=bnb, device_map="auto", trust_remote_code=True)
    model.config.use_cache = False
    ds = load_dataset("json", data_files={"train": "data/processed/train.jsonl", "eval": "data/processed/eval.jsonl"})
    def text(ex): return {"text": tok.apply_chat_template(ex["messages"], tokenize=False, add_generation_prompt=False)}
    ds = ds.map(text)
    lora = LoraConfig(r=cfg["lora_r"], lora_alpha=cfg["lora_alpha"], lora_dropout=cfg["lora_dropout"], target_modules="all-linear", task_type="CAUSAL_LM")
    args_train = TrainingArguments(output_dir=cfg["output_dir"], per_device_train_batch_size=cfg["per_device_train_batch_size"], per_device_eval_batch_size=cfg["per_device_eval_batch_size"], gradient_accumulation_steps=cfg["gradient_accumulation_steps"], num_train_epochs=cfg["num_train_epochs"], learning_rate=cfg["learning_rate"], warmup_ratio=cfg["warmup_ratio"], lr_scheduler_type="cosine", optim="paged_adamw_8bit", gradient_checkpointing=True, fp16=compute == torch.float16, bf16=compute == torch.bfloat16, eval_strategy="steps", save_strategy="steps", logging_steps=5, report_to="none", seed=cfg["seed"])
    trainer = SFTTrainer(model=model, processing_class=tok, train_dataset=ds["train"], eval_dataset=ds["eval"], peft_config=lora, args=args_train, dataset_text_field="text", max_seq_length=cfg["max_seq_length"])
    trainer.train(); trainer.save_model(cfg["output_dir"]); tok.save_pretrained(cfg["output_dir"])

if __name__ == "__main__": main()
