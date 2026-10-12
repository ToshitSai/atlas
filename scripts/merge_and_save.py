"""Merge a PEFT adapter into base weights and save safetensors."""
from __future__ import annotations
import argparse, json
from pathlib import Path

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--config", default="configs/qlora_qwen3_8b.yaml"); ap.add_argument("--adapter", default=None); ap.add_argument("--output", default="training_artifacts/merged"); a=ap.parse_args()
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import PeftModel
    c=json.loads(Path(a.config).read_text(encoding="utf-8")); adapter=a.adapter or c["output_dir"]
    base=AutoModelForCausalLM.from_pretrained(c["model_name"], torch_dtype="auto", device_map="auto", trust_remote_code=True)
    merged=PeftModel.from_pretrained(base, adapter).merge_and_unload(); Path(a.output).mkdir(parents=True, exist_ok=True); merged.save_pretrained(a.output, safe_serialization=True); AutoTokenizer.from_pretrained(adapter).save_pretrained(a.output); print(f"saved {a.output}")
if __name__ == "__main__": main()
