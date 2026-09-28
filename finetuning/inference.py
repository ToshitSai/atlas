"""Local inference for base / LoRA-finetuned models (§18). Training venv only.

Loads a base model (optionally 4-bit) + adapter checkpoint, applies the base
model's OWN chat template (§10: never assume one format), and generates
answers. Requires CUDA; refuses to run on CPU so evals are never silently
different from the training device.
"""
from __future__ import annotations

import gc
from typing import Dict, List, Optional


def load_for_inference(base_model: str, adapter_path: Optional[str] = None,
                       load_in_4bit: bool = True):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA unavailable — inference must run on the GPU to match training conditions")
    quant_cfg = None
    if load_in_4bit:
        from transformers import BitsAndBytesConfig
        quant_cfg = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                                       bnb_4bit_compute_dtype=torch.bfloat16,
                                       bnb_4bit_use_double_quant=True)
    tok = AutoTokenizer.from_pretrained(base_model)
    model = AutoModelForCausalLM.from_pretrained(
        base_model, quantization_config=quant_cfg, device_map="cuda:0",
        attn_implementation="sdpa")
    if adapter_path:
        from peft import PeftModel
        model = PeftModel.from_pretrained(model, adapter_path)
    model.eval()
    return model, tok


def chat(model, tok, messages: List[Dict[str, str]], max_new_tokens: int = 256,
         temperature: float = 0.1) -> str:
    import torch
    # enable_thinking=False keeps Qwen3-family models in direct-answer mode;
    # for other tokenizers the kwarg is simply ignored as an unused var.
    prompt = tok.apply_chat_template(messages, tokenize=False,
                                     add_generation_prompt=True, enable_thinking=False)
    inputs = tok(prompt, return_tensors="pt", truncation=True, max_length=4096).to(model.device)
    gen_kwargs = dict(max_new_tokens=max_new_tokens,
                      pad_token_id=tok.pad_token_id or tok.eos_token_id)
    if temperature and temperature > 0:
        gen_kwargs.update(do_sample=True, temperature=max(temperature, 0.01))
    else:
        gen_kwargs.update(do_sample=False)
    with torch.no_grad():
        out = model.generate(**inputs, **gen_kwargs)
    text = tok.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
    return text.strip()


def unload(model) -> None:
    import torch
    del model
    gc.collect()
    torch.cuda.empty_cache()
