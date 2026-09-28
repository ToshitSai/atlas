# Training Environment — AI Scientist

How to operate the local training pipeline. Audit/feasibility findings: `docs/local-training-audit.md`. Method + data plan: `docs/training-plan.md`.

## Layout

| Path | Purpose | Committed? |
|---|---|---|
| `training_env/` | Dedicated venv, CPython **3.12.8** (system Python 3.14 untouched) | no (gitignored) |
| `requirements-training.txt` | Pinned, verified training stack + install procedure | yes |
| `scripts/verify_training_env.py` | Hard-gate environment verifier (CUDA, sm_120, GPU matmul, bitsandbytes NF4, stack imports) | yes |
| `scripts/smoke_test_training.py` | End-to-end pipeline smoke test (§12/§13) | yes |
| `finetuning/sft_trainer.py` | Real QLoRA SFT trainer (CUDA-gated, OOM → clear failure, checkpoints, resume, metrics) | yes |
| `finetuning/dataset_pipeline.py` | Multi-domain dataset builder: validate → dedupe → per-row license audit → 90/5/5 split → manifest | yes |
| `finetuning/inference.py` | Local inference (base or +adapter) using the tokenizer's own chat template | yes |
| `finetuning/evaluate.py` | Held-out eval battery + capability-gated before/after comparison | yes |
| `training_artifacts/`, `hf_cache/`, `models/` | Run outputs, HF download cache | no (gitignored) |

## Verified stack (2026-09-26)

Python 3.12.8 · torch **2.10.0+cu128** (arch_list includes **sm_120** Blackwell) · transformers 4.57.6 · peft 0.21.0 · trl 0.29.1 · datasets 4.8.5 · accelerate 1.15.0 · bitsandbytes 0.50.2 (NF4 verified on GPU). Hardware: RTX 5050 Laptop 8 GB, driver 617.14.

## Rules

1. **Never** run training with system `py` (3.14) — use `training_env/Scripts/python.exe` for everything in this doc.
2. Training **refuses to run without CUDA** (never silently on CPU) and raises a clear `TrainingFailure` on OOM instead of dying mid-run unexplained.
3. Repo quirk: the local `datasets/` package shadows HF `datasets` once the repo root hits `sys.path`. Scripts import HF `datasets` **first** (see `scripts/smoke_test_training.py` header). Keep that order in any new entry-point script.
4. Do not commit adapters/weights; artifacts stay under gitignored dirs.

## 1. Verify environment (run after any stack change)

```bash
training_env/Scripts/python.exe scripts/verify_training_env.py --json artifacts/training_env_report.json
```

Exit 0 required before any training. Re-runnable; never fabricates results.

## 2. Smoke test (pipeline proof — tiny model, tiny data, 5 steps)

```bash
training_env/Scripts/python.exe scripts/smoke_test_training.py
```

Proves: GPU used (peak VRAM reported), loss recorded, checkpoint written, adapter reloaded, inference works, eval battery runs. Latest: **PASS** — Qwen3-0.6B, peak 1315 MiB, final loss 3.46, answer to "What is 2 + 2?" = "2 + 2 = 4" (`artifacts/smoke_test_report.json`, `artifacts/smoke_eval.json`).

## 3. Build the training dataset (multi-domain, §4/§7/§9)

```python
# training_env venv
from finetuning.dataset_pipeline import build_dataset
manifest = build_dataset(
    categories={"general_instruction": 3000, "math": 2500, "coding": 2500,
                "reasoning": 2000},
    output_dir="training_artifacts/dataset_v1",
    benchmark_texts=[...],   # protected benchmark prompts → excluded by hash
)
```

Produces `train/ validation/ test/` + `manifest.json` (per-category stats, dedup rate, license values seen). Nemotron v2 is gated:auto — accept terms once with `HF_TOKEN` set (present in `.env`). Fraud is NOT a training domain; tabular research CSVs in `datasets/` are never used.

## 4. Baseline evaluation (BEFORE training, §14)

```python
from finetuning import inference, evaluate
model, tok = inference.load_for_inference("Qwen/Qwen3-4B")   # 4-bit
report = evaluate.run(model, tok, dataset_dir="training_artifacts/dataset_v1",
                      out_json="artifacts/eval_base.json", label="base")
inference.unload(model)
```

## 5. Train (QLoRA, §11)

```python
from finetuning.sft_trainer import TrainConfig, train_sft
metrics = train_sft(TrainConfig(
    base_model="Qwen/Qwen3-4B",
    dataset_dir="training_artifacts/dataset_v1",
    output_dir="training_artifacts/run_v1",
    epochs=1.0, max_seq_len=2048))
```

Interrupted runs resume with `resume_from_checkpoint="training_artifacts/run_v1/checkpoint-<n>"`. Expected 4B/4-bit footprint ≈ 2.5–3.5 GB weights + adapter/optimizer/activations — if OOM: lower `max_seq_len` → 1024, keep batch 1, raise `gradient_accumulation_steps`.

## 6. Evaluate after + gate (§17/§25/§26)

```python
model, tok = inference.load_for_inference("Qwen/Qwen3-4B",
                                          "training_artifacts/run_v1/adapter")
after = evaluate.run(model, tok, dataset_dir="training_artifacts/dataset_v1",
                     out_json="artifacts/eval_after_v1.json", label="after_v1")
from finetuning.evaluate import compare
verdict = compare(report, after)   # accept only if no significant regression
```

Accept the run only on held-out improvement + no significant capability regression + no hallucination-resistance degradation. A lower training loss alone is NOT success (§25).

## 7. Integration into the app (LATER, §19)

Only after a model passes gating: `MODEL_PROVIDER=local` + `MODEL_PATH` in `backend/llm.py`, as a fifth provider beside OpenAI/Gemini/Anthropic/Mistral — strict explicit-provider selection preserved, no silent fallback, existing API providers untouched. Identity stays "AI Scientist" (§29).
