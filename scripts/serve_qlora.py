"""Loopback-only OpenAI-compatible server for the local Qwen3-8B model."""
from __future__ import annotations
import os, time, uuid
from pathlib import Path
from fastapi import FastAPI
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = Path(os.environ.get("QWEN3_MODEL_PATH", Path.home() / ".cache" / "huggingface" / "hub" / "models--Qwen--Qwen3-8B" / "snapshots" / "b968826d9c46dd6066d109eabc6255188de91218"))
app = FastAPI(title="Atlas Local Qwen")
model = tokenizer = None

class CompletionRequest(BaseModel):
    messages: list[dict]
    max_tokens: int = 512
    temperature: float = 0.2
    model: str = "local-qwen3-8b"

@app.on_event("startup")
def load_model():
    global model, tokenizer
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    adapter = next((p for p in (ROOT / "training_artifacts").glob("**/adapter_config.json")), None)
    tokenizer = AutoTokenizer.from_pretrained(str(SNAPSHOT), trust_remote_code=True)
    compute = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
    quant = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=compute, bnb_4bit_use_double_quant=True)
    model = AutoModelForCausalLM.from_pretrained(str(SNAPSHOT), quantization_config=quant, device_map="auto", trust_remote_code=True)
    if adapter:
        from peft import PeftModel
        model = PeftModel.from_pretrained(model, str(adapter.parent))
        print("Atlas local Qwen server: base+adapter", flush=True)
    else:
        print("Atlas local Qwen server: base-only", flush=True)
    print("Start command: training_env\\Scripts\\python.exe scripts\\serve_qlora.py", flush=True)

@app.get("/health")
def health():
    return {"status": "ok", "model": "local-qwen3-8b"}

@app.post("/v1/chat/completions")
def completions(req: CompletionRequest):
    import torch
    prompt = tokenizer.apply_chat_template(req.messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    started = time.time()
    with torch.inference_mode():
        output = model.generate(**inputs, max_new_tokens=req.max_tokens, temperature=max(req.temperature, 0.01), do_sample=req.temperature > 0)
    text = tokenizer.decode(output[0][inputs.input_ids.shape[-1]:], skip_special_tokens=True)
    return {"id": "local-" + uuid.uuid4().hex, "object": "chat.completion", "created": int(started), "model": req.model, "choices": [{"index": 0, "message": {"role": "assistant", "content": text}, "finish_reason": "stop"}]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8001)
