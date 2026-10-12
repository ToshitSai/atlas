"""Convert instruction JSONL into Qwen ChatML JSONL train/eval files."""
from __future__ import annotations
import argparse, json, random
from pathlib import Path

SAMPLE = [
    {"instruction": "Explain a scientific claim.", "input": "", "output": "State the claim, evidence, assumptions, and uncertainty."},
    {"prompt": "What is an experiment control?", "response": "A control is a comparison condition used to isolate the tested variable."},
    {"instruction": "Give one reproducible research practice.", "input": "", "output": "Record code, data versions, configuration, and random seeds."},
    {"instruction": "Explain a confidence interval.", "input": "", "output": "It describes a procedure that captures the parameter at a stated long-run rate."},
]

def row_to_messages(row: dict) -> dict:
    instruction = row.get("instruction", row.get("prompt", "")).strip()
    context = row.get("input", "").strip()
    response = row.get("output", row.get("response", "")).strip()
    if not instruction or not response:
        raise ValueError("each row needs instruction/prompt and output/response")
    user = instruction + ("\n\n" + context if context else "")
    return {"messages": [{"role": "user", "content": user}, {"role": "assistant", "content": response}]}

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("input", nargs="?", help="source JSONL; omitted uses built-in sample")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--eval-ratio", type=float, default=.1)
    args = ap.parse_args()
    rows = SAMPLE if not args.input else [json.loads(x) for x in Path(args.input).read_text(encoding="utf-8").splitlines() if x.strip()]
    data = [row_to_messages(r) for r in rows]
    random.Random(args.seed).shuffle(data)
    cut = max(1, int(len(data) * (1 - args.eval_ratio))) if len(data) > 1 else len(data)
    out = Path("data/processed"); out.mkdir(parents=True, exist_ok=True)
    for name, values in (("train.jsonl", data[:cut]), ("eval.jsonl", data[cut:] or data[-1:])):
        (out / name).write_text("".join(json.dumps(v, ensure_ascii=False) + "\n" for v in values), encoding="utf-8")
    print(f"wrote {len(data[:cut])} train and {len(data[cut:] or data[-1:])} eval rows to {out}")

if __name__ == "__main__": main()
