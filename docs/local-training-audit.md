# Local Training Environment Audit — AI Scientist

Date: 2026-09-26 · Scope: §2 (GPU audit), §5 (feasibility), §20 (stop conditions) of the local-training directive.
Verifier: `scripts/verify_training_env.py` (rerunnable; writes `artifacts/training_env_report.json`). Latest run: **exit 0, all checks PASS**.

## 1. Hardware (measured, not assumed)

| Component | Measured value |
|---|---|
| GPU | NVIDIA GeForce RTX 5050 Laptop GPU, **8 GB VRAM** (8151 MiB; ~6.9 GiB free at idle) |
| GPU architecture | **Blackwell**, compute capability **12.0 → sm_120** |
| Driver | 617.14 (supports CUDA 12.8 runtime wheels) |
| CPU | Intel i7-13700HX, 16 cores / 24 threads |
| RAM | 15.7 GB total (~3.3 GB free at typical load — tight) |
| Disk | C: 396 GB free |

## 2. Software stack (installed in isolated venv — system Python untouched)

System Python is **3.14.4** and was deliberately **not modified** (directive §1). Python 3.12 was **not present on the machine**; per explicit user approval it was provisioned via `uv python install 3.12` (isolated, user-local, no PATH change).

| Item | Version | Notes |
|---|---|---|
| venv | `training_env/` on CPython **3.12.8** | gitignored; dedicated training interpreter |
| torch | **2.10.0+cu128** | CUDA 12.8 wheel; arch_list includes **sm_120** (Blackwell native) |
| transformers | 4.57.6 | |
| peft | 0.21.0 | LoRA/QLoRA adapters |
| trl | 0.29.1 | SFTTrainer |
| datasets | 4.8.5 | |
| accelerate | 1.15.0 | |
| bitsandbytes | 0.50.2 | NF4 4-bit (QLoRA) — **verified working on this GPU** |

Install notes: the 2.86 GB torch wheel required a resumable download (`curl -C -`) due to repeated connection resets; wheel SHA-256 is recorded in the PyTorch index metadata (`fbde8f6a…`). Pinning is version-bounded (not "latest of everything") per directive §3; exact pins live in `requirements-training.txt`.

## 3. Verification results (§2 — hard gates)

| Gate | Result |
|---|---|
| `torch.cuda.is_available()` | **True** |
| `torch.cuda.get_device_name(0)` | NVIDIA GeForce RTX 5050 Laptop GPU |
| `torch.version.cuda` | 12.8 |
| `torch.cuda.get_arch_list()` | sm_70 … sm_100, **sm_120** → RTX 5050 natively supported |
| Real GPU compute | fp32 512×512 matmul: max \|GPU−CPU\| error 4.8e-05 — **GPU actually computes** |
| bitsandbytes NF4 roundtrip (GPU) | mean abs err 0.073 — **4-bit quantization works** |
| bitsandbytes `Linear4bit` forward (GPU, bf16) | finite output — **QLoRA prerequisite met** |

## 4. Feasibility on 8 GB VRAM (§5)

Determinations below are reasoning from measured VRAM + verified tooling; the smoke test (§12 of the directive) will confirm experimentally before any real run.

| Method | Realistic target on 8 GB | Basis |
|---|---|---|
| **QLoRA (4-bit NF4)** | **1B–4B models comfortably; ~7–8B possible only with short sequences (≤1024), tiny LoRA rank, batch 1 + grad accum, gradient checkpointing** | 4-bit 7–8B weights ≈ 4–5 GB + LoRA params + optimizer + activations fits only marginally in ~6.9 usable GiB; 4B-class models leave real headroom |
| LoRA (bf16 weights) | ≤ 1.5B–2B models | bf16 8B weights alone = 16 GB → impossible; 2B ≈ 4 GB + overhead |
| Full fine-tuning | Not feasible | optimizer states (Adam ≈ 2× fp32 params) exceed 8 GB even at 1B |
| Inference (4-bit) | ≤ 7–8B at short context | fine for evaluation |

**Decision: QLoRA on a 1B–4B-class model.** Do NOT attempt an arbitrary 7B+ run without the measured smoke test passing (§20 stop condition).

## 5. Known constraints / risks

- **RAM pressure**: 15.7 GB total with ~3.3 GB free during normal desktop use — model downloads and dataset loading should stream and keep caches on disk (`HF_HOME=hf_cache/`, gitignored). Large-model training runs should be the only heavy process running.
- **Laptop thermals**: RTX 5050 Laptop is a 100 W part; long runs need power plugged in and ventilation. Expect throttling on sustained max-load runs.
- **Windows + bitsandbytes**: verified working here (0.50.2), but keep the minimal quantization test in CI/regression (`scripts/verify_training_env.py`) to catch stack upgrades that break it.
- **Python 3.14 is incompatible** with this stack today; all training commands must use `training_env/Scripts/python.exe`.

## 6. Stop conditions status (§20)

| Condition | Status |
|---|---|
| CUDA unavailable | ✅ cleared |
| Python compatibility fails | ✅ cleared (3.12.8 venv) |
| GPU architecture unsupported | ✅ cleared (sm_120 in build) |
| Insufficient VRAM | ⚠️ partial — QLoRA 1B–4B feasible; ≥7B only marginal (smoke test must confirm) |
| Dataset license unsuitable | pending (dataset audit, see training plan) |
| Training stack cannot be installed safely | ✅ cleared |
| Model cannot fit | depends on final base-model choice |

## 7. Current state of the application (for context)

- The served assistant remains API-backed (`backend/llm.py`: Mistral `mistral-tiny` locally; OpenAI/Gemini/Anthropic paths present). No local model is served yet — local training is a separate, isolated pipeline (`finetuning/`, `training_env/`).
- `finetuning/` was a deliberate stub (license gate real, trainer/benchmark raising `NotImplementedError`); the real trainer is being implemented under `finetuning/` without breaking the stub's tested contract.
- No instruction-level training data exists locally (`datasets/` = 3 small tabular CSVs used by the research flow; they must NOT be used for LLM training).
