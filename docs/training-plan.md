# Training Plan — Local QLoRA Fine-Tuning for AI Scientist

Status: **PLAN — no training run has started.** Companion docs: `docs/local-training-audit.md` (measured hardware/stack audit), `docs/training-environment.md` (how to operate the environment).

## 1. Base model selection (§6)

Candidates verified against the live HF Hub API on 2026-09-26 (license / gating / context read from the Hub, not assumed):

| Model | Params | License | Gated | Context | Fit on 8 GB (QLoRA 4-bit) | Profile |
|---|---|---|---|---|---|---|
| **Qwen/Qwen3-4B** ✅ selected | ~4B | Apache-2.0 | no | 40,960 | ~2.3 GB weights + training overhead → **comfortable at seq 2048** | strong reasoning/math/code for its size, thinking + non-thinking modes, well-supported LoRA path in TRL/peft |
| Qwen/Qwen3-1.7B | ~1.7B | Apache-2.0 | no | 40,960 | very comfortable | smoke-test model + fallback if 4B does not fit |
| microsoft/Phi-4-mini-instruct | ~3.8B | MIT | no | 131,072 | comfortable | alternate base (long-context specialty) |
| meta-llama/Llama-3.2-3B-Instruct | ~3B | Llama license | **yes (401 without approval)** | 128k | comfortable | rejected for now: access friction, no capability edge at this size |

**Selected: `Qwen/Qwen3-4B`.** Rationale: the largest practical model that reliably fits this GPU with QLoRA (per `docs/local-training-audit.md` §4), permissive license (commercial-OK with attribution), strong small-model reasoning/math/code profile, open weights, no gating. **Smoke test runs on `Qwen3-1.7B` first** (§12); the 4B run only starts after the smoke test proves checkpoint/reload/inference and measured VRAM headroom. `finetuning/config.BASE_MODEL_CANDIDATES` (cloud-scale candidates) remains the roadmap if training is later moved to a rented GPU host.

## 2. Training method (§11, §21)

- **Method: QLoRA** (4-bit NF4 base + LoRA adapters r=16, α=32, dropout 0.05, targets = all attention + MLP projections) via peft + trl `SFTTrainer`.
- Sequence length 2048 (1.7B smoke test: 1024). Batch 1 + gradient accumulation 16. Gradient checkpointing ON. bf16 compute dtype.
- Full fine-tuning: **rejected** (optimizer state exceeds 8 GB even at 1B — see audit §4).
- Every hyperparameter, seed, dataset version, and LoRA config is recorded per run (§16 manifest); resume from checkpoints supported by Trainer out of the box.

## 3. Training data plan (§4, §7, §8, §9) — multi-domain, fraud is NOT the center

Primary corpus (license already audited in `finetuning/config.py`): **`nvidia/Nemotron-Post-Training-Dataset-v2`** — CC-BY-4.0, gated:auto (accept terms + `HF_TOKEN`, which is present in `.env`), per-row `license` field, splits `chat` / `math` / `code` / `stem`. Known gap (already documented in the repo): **no function/tool-calling subset**.

| Category (§6) | Source | License status | Notes |
|---|---|---|---|
| A General instruction | Nemotron `chat` | ✅ CC-BY-4.0 (audited 2026-09-22) | |
| B Reasoning | Nemotron `stem` (`reasoning` field) | ✅ CC-BY-4.0 | concise final answers; hidden CoT never shown to users (§8 of original directive) |
| C Math | Nemotron `math` | ✅ CC-BY-4.0 | runtime SymPy/Python verification stays a tool, not memorized |
| D Coding | Nemotron `code` | ✅ CC-BY-4.0 | |
| E Tool use | **Custom**: real traces from the project's sandbox/calculator (§7 anti-fake-tool-use rule) | n/a (self-produced) | assistant decides to call tool → real tool result → verified answer; no invented "I ran Python" |
| F Research | Custom: grounded answers with real citations from the project's literature search; abstention when sources are absent | n/a (self-produced) | no invented citations |
| G Multi-turn conversation | Nemotron `chat` multi-turn + custom reference-resolution examples ("what did I say earlier?") | ✅ + custom | |
| H Safety / uncertainty / false premise | Nemotron safety content + custom fictional-entity / false-premise sets | ✅ + custom | abstention without over-refusal |
| I Data analysis | Custom: small tabular Q&A with real executed pandas traces | n/a | |
| J Document Q&A | Custom: long-document excerpts + grounded Q/A | n/a | |

Supplementary public datasets (e.g., `HuggingFaceH4/no_robots`-class sets) are listed as **candidates only**: each gets a license record (source, URL, license, restrictions) verified at download time before inclusion — the tulu-3 audit in `finetuning/config.py` shows why (a CC-BY-NC component inside a permissive-tagged mixture). **No dataset enters training without a recorded license verdict from `finetuning/license_gate.py`.**

## 4. Data quality pipeline (§9)

`download → validate → normalize → dedupe (exact + near-dup hash) → drop corrupted/empty/contradictory → quality filter → chat-template formatting (actual tokenizer template, Qwen3) → split → manifest`.

- **Splits (§15): 90/5/5 train/validation/test, deduplicated BEFORE splitting; plus an external black-box benchmark that never touches training.** Benchmark questions (existing `scripts/repair_benchmark.py` set, and any new eval sets) are excluded from training data by hash matching.
- Domain distribution measured and reported per split → `docs/training-data-report.md` with the manifest (source, license, size, domain, language, dup rate).

## 5. Evaluation protocol (§14, §17, §25–§26, §37)

1. **Baseline first**: un-finetuned Qwen3-4B evaluated on the held-out test split + a small capability battery (general Q&A, reasoning, math, coding, instruction following, multi-part, hallucination probes, latency) → recorded in `docs/model-evaluation-before-after.md`.
2. **Train** (1.7B smoke → 4B real run), tracking loss + VRAM + throughput.
3. **Same benchmark after training** + held-out eval; capability-level comparison.
4. **Gating (§17/§26)**: accept the run only if held-out improves AND no capability regresses significantly AND hallucination resistance does not degrade. Otherwise reject and iterate — validation-loss drop alone is not success (§25).
5. Model identity stays **AI Scientist** (§29): the fine-tuned model serves only through the app's identity layer; `backend/project_identity.py` remains authoritative.

## 6. Integration (§19) — only after local inference works

Add `MODEL_PROVIDER=local` + `MODEL_PATH` to `backend/llm.py` as a fifth provider beside OpenAI/Gemini/Anthropic/Mistral, behind the existing strict explicit-provider selection (no silent fallback, no breaking change to API providers). Routing (§27): local model for easy/medium general requests; API models for hard reasoning until measured parity evidence exists.

## 7. Execution order (§40 chain, remaining steps)

1. smoke test (Qwen3-1.7B, tiny data, ~20 steps) → checkpoint/reload/inference + GPU-utilization proof (§12/§13)
2. dataset build + manifest + report (§9)
3. baseline eval of Qwen3-4B (§14)
4. real QLoRA run + monitoring (§11/§13/§16)
5. after-eval + capability gating (§17/§26) → accept/reject
6. local inference check (§18) → integration behind `MODEL_PROVIDER=local` (§19)
