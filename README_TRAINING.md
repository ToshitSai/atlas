# QLoRA training on Windows

This pipeline is designed for an 8 GB RTX 5050. It defaults to the Hugging Face `Qwen/Qwen3-8B` checkpoint (Qwen3 8B instruct/chat behavior is provided by its chat template); if that model does not fit, pass `--model deepseek-ai/DeepSeek-R1-Distill-Qwen-7B` and record that fallback in your experiment notes.

```powershell
uv venv training_env --python 3.12
uv pip install --python training_env/Scripts/python.exe --index-url https://download.pytorch.org/whl/cu128 "torch==2.10.0+cu128"
uv pip install --python training_env/Scripts/python.exe -r requirements-training.txt
training_env/Scripts/python.exe scripts/verify_training_env.py
training_env/Scripts/python.exe scripts/prepare_dataset.py
training_env/Scripts/python.exe scripts/prepare_dataset.py data/my_qa.jsonl
training_env/Scripts/python.exe scripts/train_qlora.py --config configs/qlora_qwen3_8b.yaml
training_env/Scripts/python.exe scripts/evaluate.py --config configs/qlora_qwen3_8b.yaml
training_env/Scripts/python.exe scripts/merge_and_save.py --config configs/qlora_qwen3_8b.yaml
```

## Smoke test first

Run the short validation before a full run:

```powershell
training_env\Scripts\python.exe scripts\prepare_dataset.py
training_env\Scripts\python.exe scripts\train_qlora.py --config configs\qlora_qwen3_8b.yaml --smoke-test
```

In a second terminal, monitor memory with `nvidia-smi -l 2`. The smoke test runs
30 configured steps, logs loss/learning rate and peak allocated/reserved VRAM
every 10 steps, writes a checkpoint, and prints `SMOKE TEST PASS` only when the
loss decreases, no exception/OOM occurs, and peak reserved memory stays below
7.2 GiB. It exits 1 and names the failed condition otherwise. Every training
run performs a 6 GiB free-VRAM preflight first. If any CUDA out-of-memory error
occurs, close GPU applications and switch to:

```powershell
training_env\Scripts\python.exe scripts\train_qlora.py --config configs\qlora_qwen3_8b_oomsafe.yaml --smoke-test
```

The OOM-safe config halves sequence length to 1024, uses rank 8, and doubles
accumulation to preserve the effective batch size. Use it for every retry after
an OOM; it is not selected silently.

Use `training_env/Scripts/python.exe` for every command. The config is JSON-compatible YAML so it can be read without adding a YAML dependency. The input format is JSONL with either `instruction`, `input`, `output` or `prompt`, `response`. `input` is optional. The preparation command makes a deterministic 90/10 split and writes `data/processed/train.jsonl` and `eval.jsonl`; omitting the input uses a small built-in sample.

Before training, run a dry import/GPU check:

```powershell
training_env/Scripts/python.exe -c "import torch, transformers, peft, trl, bitsandbytes; print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CUDA unavailable'); print(torch.cuda.mem_get_info() if torch.cuda.is_available() else '')"
```

If memory is insufficient, reduce `max_seq_length` to 1024 and keep batch size 1; increase accumulation to preserve the effective batch. Disable merge on an 8 GB card unless you have enough CPU RAM and disk. Gradient checkpointing is enabled by default. Blackwell/CUDA compatibility depends on the installed bitsandbytes build; use the verification script before starting.

The CUDA `torch==2.10.0+cu128` wheel is installed separately from the PyTorch index as shown above. No API keys or tokens are required by these scripts.

## Distillation dataset

Set `DEEPSEEK_API_KEY` in the environment (never commit it), optionally create
`data/distill_prompts.txt` with one prompt per line, then run:

```powershell
training_env\Scripts\python.exe scripts\distill.py --dry-run
training_env\Scripts\python.exe scripts\distill.py
training_env\Scripts\python.exe scripts\prepare_dataset.py data\raw\distilled_YYYYMMDD.jsonl
```

The distiller resumes an existing dated JSONL, retries with backoff, deduplicates
prompts, rate-limits calls, and stops at token or dollar caps. Reasoning is stored
separately and `prepare_dataset.py` embeds it as Qwen `<think>...</think>` blocks
by default; use `--no-reasoning` to omit it. Prompt expansion is optional:
`training_env\Scripts\python.exe scripts\expand_prompts.py --dry-run`, then run
it without `--dry-run` when the key is configured.

Using the supplied estimate of 1,800 output tokens per prompt and peak v4-pro
output pricing of $3.96 per million tokens: 2,000 × 1,800 = 3,600,000 output
tokens; 3.6 × $3.96 = **$14.26** output cost. Input tokens are additional and
depend on prompt length; off-peak pricing would be lower. The script's default
run cap is $25 and 8M output tokens.
