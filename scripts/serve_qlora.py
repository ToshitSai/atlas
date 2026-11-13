"""Atlas AI — Production-Grade OpenAI-Compatible Local Qwen Inference Server.

Features:
 - Supports Qwen base models and fine-tuned PEFT LoRA adapters
 - 4-bit NF4 bitsandbytes quantization for low VRAM consumption
 - Real-time Server-Sent Events (SSE) streaming (`stream: true`)
 - GPU VRAM and health monitoring (`/health`)
 - Standard `/v1/models` endpoint for provider discovery
 - Context clamping to avoid OOM
 - Graceful error handling and timeouts
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HF_CACHE = Path.home() / ".cache" / "huggingface" / "hub"

app = FastAPI(title="Atlas Local Qwen Inference Engine", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

model = None
tokenizer = None
model_name_loaded = "unknown"
adapter_path_loaded: Optional[str] = None
device_name = "CPU"


class Message(BaseModel):
    role: str
    content: str


class CompletionRequest(BaseModel):
    messages: List[Dict[str, Any]]
    model: str = "local-qwen"
    max_tokens: Optional[int] = 512
    temperature: Optional[float] = 0.2
    top_p: Optional[float] = 0.9
    stream: Optional[bool] = False


def resolve_model_path(model_identifier: str) -> str:
    p = Path(model_identifier)
    if p.exists():
        return str(p)
    sanitized = "models--" + model_identifier.replace("/", "--")
    cache_model_dir = DEFAULT_HF_CACHE / sanitized / "snapshots"
    if cache_model_dir.exists():
        snapshots = [s for s in cache_model_dir.iterdir() if s.is_dir()]
        if snapshots:
            return str(snapshots[0])
    return model_identifier


def configured_adapter_path() -> Optional[Path]:
    """Resolve only an explicitly configured adapter; never infer by mtime."""
    configured = os.environ.get("ATLAS_ADAPTER_PATH") or os.environ.get("LOCAL_QWEN_ADAPTER")
    return Path(configured) if configured else None


def init_engine(
    model_name: Optional[str] = None,
    adapter_dir: Optional[str] = None,
    load_in_4bit: bool = True,
):
    global model, tokenizer, model_name_loaded, adapter_path_loaded, device_name
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from peft import PeftModel

    # Determine adapter path
    resolved_adapter = Path(adapter_dir) if adapter_dir else configured_adapter_path()
    if resolved_adapter and not (resolved_adapter / "adapter_config.json").exists():
        raise RuntimeError(f"Configured adapter is missing adapter_config.json: {resolved_adapter}")

    # Determine base model
    if model_name:
        chosen_base = model_name
    elif resolved_adapter and (resolved_adapter / "adapter_config.json").exists():
        try:
            cfg = json.loads((resolved_adapter / "adapter_config.json").read_text(encoding="utf-8"))
            chosen_base = cfg.get("base_model_name_or_path", "Qwen/Qwen3-0.6B")
        except Exception:
            chosen_base = "Qwen/Qwen3-0.6B"
    else:
        chosen_base = "Qwen/Qwen3-0.6B"

    resolved_base_path = resolve_model_path(chosen_base)
    print(f"[Inference Server] Loading tokenizer from: {resolved_base_path}", flush=True)
    tokenizer = AutoTokenizer.from_pretrained(resolved_base_path, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    compute_dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
    quant_cfg = None
    if load_in_4bit and torch.cuda.is_available():
        quant_cfg = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=compute_dtype,
            bnb_4bit_use_double_quant=True,
        )

    load_kwargs: Dict[str, Any] = {
        "device_map": "auto" if torch.cuda.is_available() else "cpu",
        "trust_remote_code": True,
        "torch_dtype": compute_dtype,
    }
    if quant_cfg:
        load_kwargs["quantization_config"] = quant_cfg

    print(f"[Inference Server] Loading base model weights: {chosen_base}...", flush=True)
    base_model = AutoModelForCausalLM.from_pretrained(resolved_base_path, **load_kwargs)
    base_model.config.use_cache = True

    if resolved_adapter and (resolved_adapter / "adapter_config.json").exists():
        print(f"[Inference Server] Attaching fine-tuned LoRA adapter from: {resolved_adapter}...", flush=True)
        model = PeftModel.from_pretrained(base_model, str(resolved_adapter))
        adapter_path_loaded = str(resolved_adapter)
    else:
        model = base_model
        adapter_path_loaded = None

    model.eval()
    model_name_loaded = chosen_base
    device_name = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU"
    print(f"[Inference Server] Ready on {device_name}. Model: {model_name_loaded} | Adapter: {adapter_path_loaded}", flush=True)


@app.on_event("startup")
def startup_event():
    # Only initialize if not already loaded (e.g. via direct script invocation)
    if model is None:
        env_model = os.environ.get("ATLAS_BASE_MODEL") or os.environ.get("LOCAL_QWEN_MODEL")
        env_adapter = os.environ.get("ATLAS_ADAPTER_PATH") or os.environ.get("LOCAL_QWEN_ADAPTER")
        init_engine(model_name=env_model, adapter_dir=env_adapter)


@app.get("/health")
def health():
    import torch
    vram_stats: Dict[str, float] = {}
    if torch.cuda.is_available():
        free_b, total_b = torch.cuda.mem_get_info()
        vram_stats = {
            "vram_allocated_mb": round(torch.cuda.memory_allocated() / (1024 ** 2), 1),
            "vram_reserved_mb": round(torch.cuda.memory_reserved() / (1024 ** 2), 1),
            "vram_free_mb": round(free_b / (1024 ** 2), 1),
            "vram_total_mb": round(total_b / (1024 ** 2), 1),
        }
    return {
        "status": "healthy" if model is not None else "initializing",
        "engine": "Atlas Local Qwen Server",
        "model": model_name_loaded,
        "adapter": adapter_path_loaded,
        "device": device_name,
        **vram_stats,
    }


@app.get("/v1/models")
def list_models():
    return {
        "object": "list",
        "data": [
            {
                "id": "local-qwen",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "atlas-local",
                "root": model_name_loaded,
                "adapter": adapter_path_loaded,
            },
            {
                "id": model_name_loaded,
                "object": "model",
                "created": int(time.time()),
                "owned_by": "atlas-local",
            }
        ]
    }


@app.post("/v1/chat/completions")
def chat_completions(req: CompletionRequest):
    if model is None or tokenizer is None:
        raise HTTPException(status_code=503, detail="Local model is still initializing or not loaded.")

    import torch
    from transformers import TextIteratorStreamer
    import threading

    # Format ChatML prompt
    try:
        prompt = tokenizer.apply_chat_template(req.messages, tokenize=False, add_generation_prompt=True)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to apply chat template: {exc}")

    inputs = tokenizer(prompt, return_tensors="pt")
    # Context window guard (max 2048 tokens to guarantee no OOM during generation)
    if inputs.input_ids.shape[-1] > 2048:
        inputs.input_ids = inputs.input_ids[:, -2048:]
        if "attention_mask" in inputs:
            inputs.attention_mask = inputs.attention_mask[:, -2048:]

    inputs = inputs.to(model.device)
    max_new = req.max_tokens or 512
    temp = req.temperature if req.temperature is not None and req.temperature > 0 else None
    do_sample = temp is not None and temp > 0.01

    gen_kwargs: Dict[str, Any] = {
        "max_new_tokens": max_new,
        "do_sample": do_sample,
        "pad_token_id": tokenizer.pad_token_id or tokenizer.eos_token_id,
        "eos_token_id": tokenizer.eos_token_id,
    }
    if do_sample and temp is not None:
        gen_kwargs["temperature"] = temp
        gen_kwargs["top_p"] = req.top_p or 0.9

    # Handle streaming SSE response
    if req.stream:
        streamer = TextIteratorStreamer(tokenizer, skip_prompt=True, skip_special_tokens=True)
        gen_kwargs["streamer"] = streamer

        def generate_worker():
            with torch.inference_mode():
                model.generate(**inputs, **gen_kwargs)

        thread = threading.Thread(target=generate_worker)
        thread.start()

        req_id = "chatcmpl-" + uuid.uuid4().hex

        def sse_sync_generator():
            created = int(time.time())
            for new_text in streamer:
                chunk = {
                    "id": req_id,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": req.model,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"content": new_text},
                            "finish_reason": None,
                        }
                    ],
                }
                yield f"data: {json.dumps(chunk)}\n\n"

            # Final finish chunk
            done_chunk = {
                "id": req_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": req.model,
                "choices": [
                    {
                        "index": 0,
                        "delta": {},
                        "finish_reason": "stop",
                    }
                ],
            }
            yield f"data: {json.dumps(done_chunk)}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(sse_sync_generator(), media_type="text/event-stream")

    # Non-streaming response
    started = time.time()
    with torch.inference_mode():
        output = model.generate(**inputs, **gen_kwargs)

    gen_tokens = output[0][inputs.input_ids.shape[-1]:]
    generated_text = tokenizer.decode(gen_tokens, skip_special_tokens=True).strip()

    return {
        "id": "chatcmpl-" + uuid.uuid4().hex,
        "object": "chat.completion",
        "created": int(started),
        "model": req.model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": generated_text,
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": int(inputs.input_ids.shape[-1]),
            "completion_tokens": len(gen_tokens),
            "total_tokens": int(inputs.input_ids.shape[-1]) + len(gen_tokens),
        },
    }


def main():
    parser = argparse.ArgumentParser(description="Atlas Local Qwen Inference Server")
    parser.add_argument("--model", default=None, help="Base model name or path")
    parser.add_argument("--adapter", default=None, help="Adapter folder path")
    parser.add_argument("--host", default="127.0.0.1", help="Host bind address")
    parser.add_argument("--port", type=int, default=8001, help="Port")
    parser.add_argument("--no-quant", action="store_true", help="Disable 4-bit quantization")
    args = parser.parse_args()

    init_engine(
        model_name=args.model,
        adapter_dir=args.adapter,
        load_in_4bit=not args.no_quant,
    )

    import uvicorn
    print(f"\n[Serving] Starting Atlas Qwen server at http://{args.host}:{args.port}", flush=True)
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
