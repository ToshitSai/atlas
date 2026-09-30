"""Run the held-out AI Scientist ML evaluation set against a live deployment.

This runner never reads SFT data.  It records raw responses, version metadata,
and conservative credibility flags for human/LLM-judge review.
"""
from __future__ import annotations

import argparse
import json
import re
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

RUBRICS = ("correctness", "completeness", "technical reasoning", "practical usefulness", "no fabricated claims")
UNSUPPORTED_COMPLETION = re.compile(r"\b(?:i (?:ran|searched|tested|measured|found)|we (?:ran|searched|tested|measured|found))\b", re.I)

def post(url: str, question: str) -> dict:
    payload = json.dumps({"message": question, "sessionId": "ml-eval"}).encode()
    req = urllib.request.Request(url.rstrip("/") + "/api/chat", data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=45) as response:
        return json.loads(response.read().decode())

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--eval-file", type=Path, required=True)
    parser.add_argument("--base-url", default="https://automl-scientist.vercel.app")
    parser.add_argument("--version", default="unknown")
    parser.add_argument("--out", type=Path, default=Path("eval_results"))
    args = parser.parse_args()
    cases = [json.loads(line) for line in args.eval_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    results = []
    for case in cases:
        started = time.monotonic()
        try:
            result = post(args.base_url, case["question"])
            answer = str(result.get("response", ""))
            # A completion claim is never auto-approved: a reviewer must verify
            # it against real runtime trace/source evidence.
            flags = ["possible_fabricated_completion"] if UNSUPPORTED_COMPLETION.search(answer) else []
            status = "critical_failure" if flags else "needs_rubric_review"
        except Exception as exc:
            answer, flags, status = "", [f"request_error: {exc}"], "critical_failure"
        results.append({"id": case["id"], "question": case["question"], "category": case.get("category"),
                        "rubric": case.get("rubric", list(RUBRICS)), "response": answer,
                        "latency_seconds": round(time.monotonic() - started, 3), "flags": flags, "status": status})
    report = {"timestamp": datetime.now(timezone.utc).isoformat(), "version": args.version,
              "base_url": args.base_url, "held_out_cases": len(results), "results": results}
    args.out.mkdir(parents=True, exist_ok=True)
    path = args.out / f"ml_eval_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(path)
    return 1 if any(r["status"] == "critical_failure" for r in results) else 0

if __name__ == "__main__":
    raise SystemExit(main())
