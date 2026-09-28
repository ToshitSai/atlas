"""REAL QLoRA SFT trainer for the local training pipeline (§11).

Runs ONLY inside ``training_env/`` (torch/transformers/peft/trl imported
lazily). Refuses clearly instead of faking:

- no CUDA        -> RuntimeError (never silently trains on CPU, §13)
- OOM            -> raised as TrainingFailure with the allocation detail
- every run produces real, saveable artifacts + metrics

The stub ``finetuning.trainer.run_finetune`` (license gate +
NotImplementedError) is untouched; call ``train_sft`` here after the license
gate passes.
"""
from __future__ import annotations

import json
import os
import platform
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TrainingFailure(RuntimeError):
    """Raised when training cannot proceed honestly (OOM, no CUDA, bad data)."""


@dataclass
class TrainConfig:
    base_model: str = "Qwen/Qwen3-4B"
    dataset_dir: str = ""
    output_dir: str = os.path.join(_REPO_ROOT, "training_artifacts", "run")
    epochs: float = 1.0
    learning_rate: float = 2e-4
    per_device_batch_size: int = 1
    gradient_accumulation_steps: int = 16
    max_seq_len: int = 2048
    lora_r: int = 16
    lora_alpha: int = 32
    lora_dropout: float = 0.05
    load_in_4bit: bool = True
    logging_steps: int = 5
    save_steps: int = 50
    seed: int = 42
    max_steps: Optional[int] = None          # smoke tests: small positive int
    max_samples: Optional[int] = None        # smoke tests: tiny subsets
    resume_from_checkpoint: Optional[str] = None

    def to_dict(self) -> Dict:
        return {k: (v if not isinstance(v, tuple) else list(v))
                for k, v in self.__dict__.items()}


def _require_cuda() -> None:
    import torch
    if not torch.cuda.is_available():
        raise RuntimeError(
            "CUDA is not available — refusing to train on CPU (§13). Use the "
            "training_env venv on the RTX 5050 machine.")


def _pick_targets(model) -> List[str]:
    """All Linear module names present in the model, minus head/embed norms."""
    import torch.nn as nn
    names = set()
    for name, mod in model.named_modules():
        if isinstance(mod, nn.Linear):
            names.add(name.split(".")[-1])
    for banned in ("lm_head", "embed_tokens"):
        names.discard(banned)
    if not names:
        raise TrainingFailure("no Linear modules found for LoRA targets")
    return sorted(names)


def train_sft(cfg: TrainConfig) -> Dict:
    """Run QLoRA SFT. Returns a metrics dict; writes artifacts + manifest."""
    _require_cuda()
    if not os.path.isdir(cfg.dataset_dir):
        raise TrainingFailure(f"dataset_dir does not exist: {cfg.dataset_dir} "
                              "(build it first with finetuning.dataset_pipeline)")

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from trl import SFTTrainer, SFTConfig

    os.makedirs(cfg.output_dir, exist_ok=True)
    torch.manual_seed(cfg.seed)
    quant_cfg = None
    if cfg.load_in_4bit:
        from transformers import BitsAndBytesConfig
        quant_cfg = BitsAndBytesConfig(
            load_in_4bit=True, bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_use_double_quant=True)

    tok = AutoTokenizer.from_pretrained(cfg.base_model)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        cfg.base_model, quantization_config=quant_cfg,
        torch_dtype=torch.bfloat16 if not cfg.load_in_4bit else None,
        device_map="cuda:0", attn_implementation="sdpa")
    model.config.use_cache = False
    model = prepare_model_for_kbit_training(model)
    lora = LoraConfig(
        r=cfg.lora_r, lora_alpha=cfg.lora_alpha, lora_dropout=cfg.lora_dropout,
        bias="none", task_type="CAUSAL_LM", target_modules=_pick_targets(model))
    model = get_peft_model(model, lora)

    from finetuning.dataset_pipeline import load_split
    ds = load_split(cfg.dataset_dir, "train")
    if cfg.max_samples:
        ds = ds.select(range(min(cfg.max_samples, len(ds))))

    def format_example(batch):
        texts = []
        for msgs in batch["messages"]:
            texts.append(tok.apply_chat_template(
                msgs, tokenize=False, add_generation_prompt=False))
        return {"text": texts}

    ds = ds.map(format_example, batched=True, remove_columns=[c for c in ds.column_names if c != "category"])

    sft_args = SFTConfig(
        output_dir=cfg.output_dir,
        per_device_train_batch_size=cfg.per_device_batch_size,
        gradient_accumulation_steps=cfg.gradient_accumulation_steps,
        num_train_epochs=cfg.epochs,
        max_steps=cfg.max_steps if cfg.max_steps else -1,
        learning_rate=cfg.learning_rate,
        lr_scheduler_type="cosine",
        warmup_ratio=0.03,
        logging_steps=cfg.logging_steps,
        save_steps=cfg.save_steps,
        save_total_limit=2,
        bf16=True,
        max_length=cfg.max_seq_len,
        gradient_checkpointing=True,
        gradient_checkpointing_kwargs={"use_reentrant": False},
        packing=False,
        seed=cfg.seed,
        report_to=[],
        dataset_text_field="text",
    )

    t0 = time.time()
    trainer = SFTTrainer(model=model, args=sft_args, train_dataset=ds,
                         processing_class=tok)
    try:
        train_result = trainer.train(resume_from_checkpoint=cfg.resume_from_checkpoint)
    except torch.cuda.OutOfMemoryError as e:
        raise TrainingFailure(f"CUDA OOM during training: {e}. Reduce max_seq_len, "
                              "LoRA rank, or switch to a smaller base model.") from e
    duration = time.time() - t0
    # torch.cuda.max_memory_allocated() is cumulative peak — one read suffices (§13)
    peak_vram_mib = torch.cuda.max_memory_allocated() // 2**20

    trainer.save_model(os.path.join(cfg.output_dir, "adapter"))
    tok.save_pretrained(os.path.join(cfg.output_dir, "adapter"))

    metrics = {
        "base_model": cfg.base_model,
        "train_runtime_sec": round(duration, 1),
        "train_samples": len(ds),
        "train_loss_final": float(train_result.metrics.get("train_loss", float("nan"))),
        "peak_vram_mib": peak_vram_mib,
        "gpu": torch.cuda.get_device_name(0),
        "torch": torch.__version__,
        "python": platform.python_version(),
        "lora_config": {k: v for k, v in lora.to_dict().items() if k != "target_modules"},
        "lora_target_modules": _pick_targets(model),
        "train_config": cfg.to_dict(),
    }
    with open(os.path.join(cfg.output_dir, "train_metrics.json"), "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)
    return metrics
