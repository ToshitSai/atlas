"""Expand seed prompts with DeepSeek Flash; no secrets are logged."""
from __future__ import annotations
import argparse, json, os, re, urllib.request
from pathlib import Path

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--input", default="data/distill_prompts.txt"); ap.add_argument("--output", default="data/distill_prompts_expanded.txt"); ap.add_argument("--dry-run", action="store_true"); a=ap.parse_args()
    prompts=[x.strip() for x in Path(a.input).read_text(encoding="utf-8").splitlines() if x.strip()]
    if a.dry_run: print(f"would expand {len(prompts)} prompts with deepseek-flash"); return 0
    key=os.environ.get("DEEPSEEK_API_KEY")
    if not key: print("DEEPSEEK_API_KEY is not configured"); return 1
    out=[]
    for prompt in prompts:
        body=json.dumps({"model":"deepseek-flash","temperature":.7,"messages":[{"role":"user","content":f"Return exactly four diverse research-assistant paraphrases, one per line, for: {prompt}"}]}).encode(); req=urllib.request.Request("https://api.deepseek.com/chat/completions",data=body,headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"},method="POST")
        with urllib.request.urlopen(req, timeout=60) as response: text=json.loads(response.read().decode())["choices"][0]["message"].get("content","")
        out.extend([x.strip(" -*\t") for x in text.splitlines() if len(x.strip()) > 20])
    seen=set(); Path(a.output).parent.mkdir(parents=True,exist_ok=True); Path(a.output).write_text("\n".join(x for x in out if not (re.sub(r"\W+"," ",x.lower()).strip() in seen or seen.add(re.sub(r"\W+"," ",x.lower()).strip())))+"\n",encoding="utf-8")
if __name__ == "__main__": raise SystemExit(main())
