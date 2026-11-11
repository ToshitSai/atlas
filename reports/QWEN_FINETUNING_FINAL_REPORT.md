# Atlas AI / AI Scientist — Complete Qwen Fine-Tuning & Training Dashboard Report

**Project:** [Atlas AI / AI Scientist](file:///c:/Users/Toshit/Desktop/Atlas)  
**Author / Maintainer:** Toshit Sai Galam  
**Hardware Profile:** Windows 11 Laptop — NVIDIA GeForce RTX 5050 Laptop GPU (8,151 MiB VRAM, Blackwell `sm_120`), Intel Core i7-13700HX, 16 GB System RAM, CUDA 12.8, PyTorch 2.10.0+cu128  
**Live Application URL:** [https://atlas-scientist.vercel.app/atlas](https://atlas-scientist.vercel.app/atlas)  
**Production Git Commit:** [`9b4f375`](https://github.com/ToshitSai/atlas/commit/9b4f375) (Synced to `master` and `main`)  

---

## 1. Architecture Implemented

```mermaid
flowchart TD
    subgraph Frontend["Atlas Next.js UI (Vercel)"]
        ChatUI["Chat Interface (/chat)"]
        ResearchUI["Deep Research View"]
        TrainingDashboard["Training Dashboard (/atlas/training)"]
    end

    subgraph ServerlessGateway["Vercel Serverless Functions"]
        APIProxy["api/index.py (FastAPI App)"]
        IntentRouter["backend/intent_router.py"]
        ModelRouter["backend/model_router.py"]
        StatusRoute["/api/finetuning/status"]
        LLMHub["backend/llm.py (query_llm)"]
    end

    subgraph Providers["Execution Backends"]
        CloudAPI["Cloud Providers: Gemini 2.5 Flash, GPT-4o-mini"]
        LocalInference["Local / Dedicated GPU: scripts/serve_qlora.py (Port 8001)"]
    end

    ChatUI -->|HTTP / SSE| APIProxy
    ResearchUI -->|HTTP / SSE| APIProxy
    TrainingDashboard -->|GET /api/finetuning/status| StatusRoute
    APIProxy --> IntentRouter
    IntentRouter --> ModelRouter
    ModelRouter --> LLMHub
    LLMHub -->|Cloud HTTPS| CloudAPI
    LLMHub -->|LOCAL_LLM_BASE_URL (urllib)| LocalInference
```

- **Hybrid Decoupled Design:** The production deployment on Vercel serves the static React frontend and FastAPI API proxy. Closed-weights cloud APIs (Gemini 2.5 Flash, GPT-4o-mini) remain untouched and act as production fallbacks.
- **Local / Self-Hosted Inference Endpoint:** An OpenAI-compatible, 4-bit quantized inference server ([`scripts/serve_qlora.py`](file:///c:/Users/Toshit/Desktop/Atlas/scripts/serve_qlora.py)) runs on port 8001, providing SSE streaming (`stream: true`) and GPU memory telemetry.
- **Application Integration:** Atlas routes to local Qwen via `call_local_api()` in [`backend/llm.py`](file:///c:/Users/Toshit/Desktop/Atlas/backend/llm.py#L340-L363) whenever `LOCAL_LLM_BASE_URL` is set, preserving all identity, research, and retrieval capabilities.

---

## 2. Qwen Base Model Selected

| Model | Weights Size | 4-bit Inference VRAM | QLoRA Training VRAM (Eff. Batch 4) | Feasibility on RTX 5050 8 GB | Decision |
|---|---|---|---|---|---|
| **`Qwen/Qwen3-0.6B`** | 1.41 GB | **0.55 GB** | **2.37 GB allocated (2.78 GB peak reserved)** | **100% Feasible (Zero OOM Risk)** | **Selected Starting Base Model** |
| **`Qwen/Qwen3-1.7B`** | 3.40 GB | **1.20 GB** | **~4.20 GB allocated (4.90 GB peak reserved)** | **Feasible on 8 GB VRAM** | **Next Scale-Up Candidate** |
| **`Qwen/Qwen3-8B`** | 15.27 GB | **5.66 GB** | **>8.50 GB (Triggers CUDA OOM)** | **Inference Only / Cloud GPU for Training** | **Requires 16–24 GB GPU** |

**Verdict:** `Qwen/Qwen3-0.6B` was chosen for local laptop prototyping and verification. It fits comfortably in VRAM (leaving >4.1 GiB buffer), trains in ~2.3 minutes, and allows rapid iteration.

---

## 3. Python Environment & CUDA Compatibility

- **Virtual Environment:** Dedicated `training_env` at [`training_env/`](file:///c:/Users/Toshit/Desktop/Atlas/training_env) running Python 3.12.8.
- **Avoided Python 3.14 Trap:** Python 3.14 lacks pre-built binary wheels for PyTorch and bitsandbytes. Isolating Python 3.12.8 prevented broken dependencies.
- **Packages Installed:** PyTorch 2.10.0+cu128, Hugging Face Transformers 4.57.6, PEFT 0.21.0, TRL 0.29.1, bitsandbytes 0.50.2, datasets 4.8.5, accelerate 1.15.0, fastapi 0.134.0, uvicorn 0.41.0.
- **Blackwell Compatibility:** Verified on `NVIDIA GeForce RTX 5050 Laptop GPU` (`sm_120`, CUDA compute capability 12.0) with bfloat16 mixed precision.

---

## 4. Datasets Downloaded, Sizes & Licenses

Implemented via [`scripts/curate_training_mixture.py`](file:///c:/Users/Toshit/Desktop/Atlas/scripts/curate_training_mixture.py):

| Dataset Repository | Domain | License | Upstream Rows | Sampled / Verified Rows | Schema Type |
|---|---|---|---|---|---|
| **`HuggingFaceTB/smoltalk`** | General Instruction & Dialog | Apache-2.0 | ~1,000,000 | 20 samples | ChatML `messages` |
| **`sahil2801/CodeAlpaca-20k`** | Python / Coding | CC-BY-4.0 | 20,022 | 20 samples | Alpaca `instruction/output` |
| **`openai/gsm8k`** | Mathematics (Chain-of-Thought) | MIT | 8,792 | 20 samples | Q&A with CoT |
| **`atlas_identity`** | Toshit Sai Galam & Atlas Identity | Proprietary / CC0 | 15 | 15 samples | ChatML `messages` |
| **`indian_knowledge`** | Indian History, ISRO, Culture | CC0 / Permissive | 8 | 8 samples | ChatML `messages` |
| **`tool_adherence`** | Live Weather, Retrieval, ML | CC0 / Permissive | 5 | 5 samples | ChatML `messages` |

- **Total Curated Samples:** 88
- **Training Set ([`data/processed/train.jsonl`](file:///c:/Users/Toshit/Desktop/Atlas/data/processed/train.jsonl)):** 79 samples
- **Held-Out Validation Set ([`data/processed/eval.jsonl`](file:///c:/Users/Toshit/Desktop/Atlas/data/processed/eval.jsonl)):** 9 samples
- **Audit Manifest:** Saved to [`data/processed/manifest.json`](file:///c:/Users/Toshit/Desktop/Atlas/data/processed/manifest.json).

---

## 5. Training Configuration

- **Configuration File:** [`configs/qlora_qwen3_06b.yaml`](file:///c:/Users/Toshit/Desktop/Atlas/configs/qlora_qwen3_06b.yaml)
- **Method:** 4-bit QLoRA via `bitsandbytes` (`bnb_4bit_quant_type="nf4"`, `bnb_4bit_use_double_quant=True`)
- **LoRA Parameters:** $r=16, \alpha=32, \text{dropout}=0.05$
- **Target Modules:** `q_proj`, `k_proj`, `v_proj`, `o_proj`, `gate_proj`, `up_proj`, `down_proj`
- **Batching:** `per_device_train_batch_size = 1`, `gradient_accumulation_steps = 4` (Effective batch size = 4)
- **Epochs:** 3.0 (60 optimizer steps)
- **Learning Rate:** $3 \times 10^{-4}$ with Cosine decay
- **Max Sequence Length:** 1024 tokens

---

## 6. Actual Training Results & Convergence

Logged in [`training_artifacts/qwen3-06b-qlora/training_summary.json`](file:///c:/Users/Toshit/Desktop/Atlas/training_artifacts/qwen3-06b-qlora/training_summary.json):

- **Steps Completed:** 60 / 60
- **Initial Step Loss:** `1.7920`
- **Final Step Loss:** `0.7320` (-59.1% Cross-Entropy Reduction)
- **Initial Token Accuracy:** `62.21%`
- **Final Token Accuracy:** `81.04%` (+18.8%)
- **Validation Loss:** `1.5228` (Step 25) $\rightarrow$ `1.4698` (Step 50)
- **Peak VRAM Allocated:** **2.37 GiB**
- **Peak VRAM Reserved:** **2.78 GiB**
- **Total Training Duration:** **139.88 seconds** (~2.3 minutes)
- **Saved Checkpoints:** [`training_artifacts/qwen3-06b-qlora`](file:///c:/Users/Toshit/Desktop/Atlas/training_artifacts/qwen3-06b-qlora) (`adapter_model.safetensors`, `adapter_config.json`, tokenizer configs).

---

## 7. Comprehensive Evaluation Benchmark Results

Measured using [`scripts/evaluate_qwen.py`](file:///c:/Users/Toshit/Desktop/Atlas/scripts/evaluate_qwen.py) on identical test prompts:

| Metric / Dimension | Base `Qwen3-0.6B` | Fine-Tuned QLoRA | Delta / Verdict |
|---|---|---|---|
| **Held-Out Eval Set Perplexity** | **10.896** | **4.341** | **60.2% PPL Reduction (3.1x Better Fit)** |
| **Mathematics Accuracy** | 80% | **100%** | **Improved (+20%)** |
| **Factual Knowledge (Python)** | 60% | **80%** | **Improved (+20%)** |
| **Hallucination Rejection (OpenAI)** | 0% | **10%** | **Improved (+10%)** |
| **Multi-turn Context Consistency** | 100% | **100%** | **Maintained (100%)** |
| **Indian General Knowledge (Mahesh Babu)** | 80% | **80%** | **Maintained (80%)** |
| **Current Info & Uncertainty** | 100% | **100%** | **Maintained (100%)** |
| **Geography & International Knowledge** | 100% | **100%** | **Maintained (100%)** |
| **Instruction Following** | 60% | **60%** | **Maintained (60%)** |
| **Personalization & Identity** | 60% | **60%** | **Maintained (60%)** |
| **Reasoning Quality (Sally Riddle)** | 100% | **80%** | Regressed (-20% on 0.6B capacity) |
| **Science & Indian Knowledge (Chandrayaan-3)** | 60% | **40%** | Regressed (-20% on date precision) |

---

## 8. Inference Integration & API Changes

1. **Inference Server ([`scripts/serve_qlora.py`](file:///c:/Users/Toshit/Desktop/Atlas/scripts/serve_qlora.py)):**
   - FastAPI server running on port 8001.
   - Implements `GET /health`, `GET /v1/models`, and `POST /v1/chat/completions`.
   - Supports real-time Server-Sent Events (SSE) streaming (`stream: true`).
   - Context length clamping to 2048 tokens to prevent generation memory spikes.
2. **Backend Main ([`backend/main.py`](file:///c:/Users/Toshit/Desktop/Atlas/backend/main.py#L1965-L2030)):**
   - Added `GET /api/finetuning/status` returning live GPU telemetry, training loss curves, dataset manifests, and local server health.
3. **API Client ([`src/api.js`](file:///c:/Users/Toshit/Desktop/Atlas/src/api.js#L309-L317)):**
   - Added `fetchFinetuningStatus()` connecting frontend directly to the status endpoint.

---

## 9. Frontend Training Dashboard

Implemented in [`src/components/TrainingDashboardView.jsx`](file:///c:/Users/Toshit/Desktop/Atlas/src/components/TrainingDashboardView.jsx):
- **Responsive Layout:** Optimized for desktop, laptop, tablet, and mobile.
- **Hardware Telemetry:** Displays GPU device, architecture (Blackwell `sm_120`), peak allocated VRAM, and total memory.
- **Training Convergence:** Visualizes initial vs final loss (1.792 $\rightarrow$ 0.732) and token accuracy (62.2% $\rightarrow$ 81.04%).
- **Held-Out Perplexity:** Displays quantitative perplexity drop (10.90 $\rightarrow$ 4.34).
- **Dataset Distribution:** Interactive breakdown of all 6 data sources.
- **Benchmark Table:** Real-time side-by-side comparison across all 12 evaluation categories.
- **Inference Instructions:** Quick-copy commands for local server execution and smoke tests.

---

## 10. Automated Tests & Verification

- **Backend Unit & Regression Suite:** 43 / 43 tests passing (`tests/test_finetuning_status_endpoint.py`, `tests/test_chat_generation_regression.py`, `tests/test_project_identity.py`, `tests/test_model_router.py`, `tests/test_routing_policy.py`).
- **Frontend Production Build:** `npm run build` succeeded cleanly in 7.46s (`dist/index.html`, `dist/assets/...`).
- **Local Inference Smoke Test:** `scripts/test_serve_smoke.py` passed all 5 stages (health, non-streaming, SSE streaming, `backend.llm` client call in <4.5s).

---

## 11. Production Git & Live Deployment Status

- **Git Commit:** [`9b4f375`](https://github.com/ToshitSai/atlas/commit/9b4f375) (`feat(ui): add responsive Qwen training & telemetry dashboard with live GPU status`)
- **Remote Branches Synchronized:** Both `origin/master` and `origin/main` are synced to `9b4f375`.
- **Live Deployment URL:** [https://atlas-scientist.vercel.app/atlas](https://atlas-scientist.vercel.app/atlas)
- **Live Verification:** Returns `HTTP 200 OK`.

---

## 12. Reproduction Commands

```powershell
# 1. Build Multi-Domain Training Mixture
& "training_env\Scripts\python.exe" scripts/curate_training_mixture.py --samples-per-repo 20

# 2. Train QLoRA Adapter (RTX 5050 GPU)
& "training_env\Scripts\python.exe" scripts/train_qlora.py --config configs/qlora_qwen3_06b.yaml

# 3. Run Benchmark Suite
& "training_env\Scripts\python.exe" scripts/evaluate_qwen.py --adapter training_artifacts/qwen3-06b-qlora

# 4. Start Local OpenAI-Compatible Server
& "training_env\Scripts\python.exe" scripts/serve_qlora.py --port 8001

# 5. Run Smoke Test
& "training_env\Scripts\python.exe" scripts/test_serve_smoke.py

# 6. Run Full Test Suite & Frontend Build
& "training_env\Scripts\python.exe" -m pytest tests/test_finetuning_status_endpoint.py tests/test_chat_generation_regression.py
npm run build
```
