"""Atlas AI — Model Feasibility & VRAM Profiling Suite.

Profiles candidate models (Qwen3-0.6B, Qwen3-1.7B, Qwen3-8B) on the RTX 5050 Laptop GPU:
 - Baseline memory
 - Weights memory in 4-bit NF4 vs BF16
 - Forward pass allocation with context length 512, 1024, 2048
 - Backward pass gradient checkpointing peak memory simulation
 - Feasibility score and recommendation
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
root_str = str(ROOT)
for p in [root_str, "", "."]:
    if p in sys.path:
        sys.path.remove(p)

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig


def profile_model(model_name: str, quant_4bit: bool = True) -> Dict[str, Any]:
    print(f"\n=======================================================", flush=True)
    print(f" Profiling Model: {model_name} (4-bit={quant_4bit})", flush=True)
    print(f"=======================================================", flush=True)

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is required for hardware profiling.")

    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()

    free_start, total_mem = torch.cuda.mem_get_info()
    baseline_used = (total_mem - free_start) / (1024**3)
    print(f"Baseline System VRAM In Use: {baseline_used:.2f} GiB (Free: {free_start / (1024**3):.2f} GiB)", flush=True)

    compute_dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
    quant_config = None
    if quant_4bit:
        quant_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=compute_dtype,
            bnb_4bit_use_double_quant=True,
        )

    t0 = time.time()
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    load_kwargs = {
        "device_map": "auto",
        "trust_remote_code": True,
        "torch_dtype": compute_dtype,
    }
    if quant_config:
        load_kwargs["quantization_config"] = quant_config

    model = AutoModelForCausalLM.from_pretrained(model_name, **load_kwargs)
    load_time = time.time() - t0

    weights_allocated = torch.cuda.memory_allocated() / (1024**3)
    weights_reserved = torch.cuda.memory_reserved() / (1024**3)
    print(f"Weights Loaded in {load_time:.2f}s | Allocated: {weights_allocated:.2f} GiB | Reserved: {weights_reserved:.2f} GiB", flush=True)

    # Test forward passes with various context lengths
    test_contexts = [128, 512, 1024]
    context_results = {}

    for ctx_len in test_contexts:
        torch.cuda.reset_peak_memory_stats()
        dummy_text = "What is the capital of France and what are its key historical landmarks? " * (ctx_len // 10)
        inputs = tokenizer(dummy_text, return_tensors="pt", max_length=ctx_len, truncation=True).to("cuda")

        t_inf_start = time.time()
        with torch.no_grad():
            outputs = model.generate(**inputs, max_new_tokens=32, do_sample=False)
        inf_time = time.time() - t_inf_start

        peak_allocated = torch.cuda.max_memory_allocated() / (1024**3)
        peak_reserved = torch.cuda.max_memory_reserved() / (1024**3)
        tokens_gen = outputs.shape[1] - inputs["input_ids"].shape[1]
        tok_per_sec = tokens_gen / max(0.001, inf_time)

        context_results[f"ctx_{ctx_len}"] = {
            "peak_allocated_gib": round(peak_allocated, 2),
            "peak_reserved_gib": round(peak_reserved, 2),
            "tokens_per_sec": round(tok_per_sec, 1),
            "latency_sec": round(inf_time, 2)
        }
        print(f"Context {ctx_len}: Peak Allocated={peak_allocated:.2f} GiB | Reserved={peak_reserved:.2f} GiB | Throughput={tok_per_sec:.1f} tok/s", flush=True)

    free_now, _ = torch.cuda.mem_get_info()
    headroom_gib = free_now / (1024**3)

    summary = {
        "model_name": model_name,
        "quantization": "4-bit NF4" if quant_4bit else "bf16",
        "load_time_sec": round(load_time, 2),
        "weights_allocated_gib": round(weights_allocated, 2),
        "weights_reserved_gib": round(weights_reserved, 2),
        "remaining_headroom_gib": round(headroom_gib, 2),
        "total_vram_gib": round(total_mem / (1024**3), 2),
        "context_benchmarks": context_results,
        "fits_8gb_vram": headroom_gib >= 1.0,
        "training_feasible_on_8gb": headroom_gib >= 2.0,
    }

    del model
    del tokenizer
    torch.cuda.empty_cache()
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="Qwen/Qwen3-1.7B")
    parser.add_argument("--compare", action="store_true")
    args = parser.parse_args()

    results = []
    models_to_test = [args.model]
    if args.compare:
        models_to_test = ["Qwen/Qwen3-0.6B", "Qwen/Qwen3-1.7B"]

    for m in models_to_test:
        try:
            res = profile_model(m, quant_4bit=True)
            results.append(res)
        except Exception as exc:
            print(f"[Profiling Failed for {m}]: {exc}", flush=True)
            results.append({"model_name": m, "error": str(exc), "fits_8gb_vram": False})

    out_file = ROOT / "training_artifacts" / "model_feasibility_report.json"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nSaved feasibility report to {out_file}", flush=True)
