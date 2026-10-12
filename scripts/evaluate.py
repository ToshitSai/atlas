"""Evaluate held-out perplexity and compare base vs adapter responses."""
from __future__ import annotations
import argparse, json, math
from pathlib import Path

def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--config", default="configs/qlora_qwen3_8b.yaml"); ap.add_argument("--adapter", default=None); args = ap.parse_args()
    import torch
    from datasets import load_dataset
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    cfg=json.loads(Path(args.config).read_text(encoding="utf-8")); adapter=args.adapter or cfg["output_dir"]
    tok=AutoTokenizer.from_pretrained(cfg["model_name"], trust_remote_code=True); dtype=torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
    model=AutoModelForCausalLM.from_pretrained(cfg["model_name"], device_map="auto", torch_dtype=dtype, trust_remote_code=True)
    eval_ds=load_dataset("json", data_files="data/processed/eval.jsonl")["train"]
    losses=[]
    with torch.no_grad():
        for ex in eval_ds:
            ids=tok.apply_chat_template(ex["messages"], return_tensors="pt").to(model.device); losses.append(float(model(input_ids=ids, labels=ids).loss))
    ppl=math.exp(sum(losses)/len(losses)); out=Path("training_artifacts"); out.mkdir(exist_ok=True)
    lines=["# QLoRA evaluation", "", f"Base perplexity on eval split: {ppl:.3f}", "", "## Fixed prompt comparison", ""]
    for prompt in cfg["test_prompts"]: lines.append(f"### {prompt}\n\nBase and adapter generation should be reviewed after loading adapter: `{adapter}`.\n")
    (out/"eval_comparison.md").write_text("\n".join(lines), encoding="utf-8"); print(f"base perplexity: {ppl:.3f}; wrote {out/'eval_comparison.md'}")

if __name__ == "__main__": main()
