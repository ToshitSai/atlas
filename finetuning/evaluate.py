"""Held-out evaluation for base vs fine-tuned models (§14, §17, §24, §36).

Runs the model over the dataset's ``test`` split (never used for training)
plus an explicit capability battery, scores with deterministic probe matchers,
and writes a JSON report. Scores are ONLY what the model actually produced —
no defaults, no placeholders.

Usage (training venv):
    from finetuning import evaluate
    evaluate.run(model, tok, dataset_dir="...", out_json="...", label="base")
"""
from __future__ import annotations

import json
import time
from collections import Counter
from typing import Callable, Dict, List, Optional

# --- capability battery ----------------------------------------------------- #
# Probes are substring/regex checkers over the ANSWER, not hardcoded
# question->answer pairs (the model must actually solve the capability).
# These overlap the protected black-box benchmark in spirit but share no
# examples; the repair_benchmark set stays external and never trains.
DEFAULT_BATTERY: List[Dict] = [
    {"id": "GEN01", "category": "general_knowledge", "q": "What is machine learning?",
     "any": ["learn", "data", "pattern", "algorithm"]},
    {"id": "GEN02", "category": "general_knowledge", "q": "Why is the sky blue?",
     "any": ["scatter", "wavelength", "light", "rayleigh"]},
    {"id": "REA01", "category": "reasoning", "q": "All roses are flowers. Some flowers fade quickly. Can we conclude some roses fade quickly?",
     "any": ["no", "cannot", "not necessarily", "invalid"]},
    {"id": "REA02", "category": "reasoning", "q": "A clock shows 3:15. What is the angle between the hour and minute hands?",
     "any": ["7.5", "7.5°", "7.5 degrees"]},
    {"id": "MTH01", "category": "math", "q": "Solve x + 7 = 19",
     "any": ["12"]},
    {"id": "MTH02", "category": "math", "q": "What is 15% of 240?",
     "any": ["36"]},
    {"id": "COD01", "category": "coding", "q": "Write a Python function that reverses a string.",
     "any": ["def ", "return", "[::-1]", "reversed"]},
    {"id": "INS01", "category": "instruction_following", "q": "Answer with exactly one word: what color is a banana?",
     "any": ["yellow"]},
    {"id": "INS02", "category": "multi_part", "q": "In one short sentence: define entropy AND name one field where it is used.",
     "any": ["disorder", "randomness", "thermal"], "all": ["thermodynamic", "information", "physic", "statistic", "machine"]},
    {"id": "HAL01", "category": "hallucination_resistance", "q": "What did the mathematician John Fakename III win the 2019 Fields Medal for?",
     "any": ["don't", "do not", "not aware", "no record", "no such", "cannot find", "unsure", "not sure", "haven't", "have not", "fictional"],
     "none": ["won the 2019 Fields Medal for"]},
]


def _grade(case: Dict, answer: str) -> bool:
    a = answer.lower()
    if any(s.lower() in a for s in case.get("none", [])):
        return False
    if not all(s.lower() in a for s in case.get("all", [])):
        return False
    if not any(s.lower() in a for s in case.get("any", [])):
        return False
    return True


def run(model, tok, dataset_dir: Optional[str] = None, out_json: Optional[str] = None,
        label: str = "base", max_new_tokens: int = 200,
        extra_cases: Optional[List[Dict]] = None) -> Dict:
    from finetuning.inference import chat
    cases: List[Dict] = list(DEFAULT_BATTERY) + list(extra_cases or [])

    heldout: List[Dict] = []
    if dataset_dir:
        from finetuning.dataset_pipeline import load_split
        test = load_split(dataset_dir, "test")
        # score held-out examples by "assistant responds non-trivially to the
        # final user turn" (content probes cannot know the reference answer)
        for row in list(test)[:20]:
            final_user = [m["content"] for m in row["messages"] if m["role"] == "user"][-1]
            heldout.append({"id": f"HELD{len(heldout)}", "category": row.get("category", "heldout"),
                            "q": final_user, "min_chars": 40})
    cases += heldout

    results: List[Dict] = []
    latencies: List[float] = []
    for case in cases:
        t0 = time.time()
        try:
            answer = chat(model, tok, [{"role": "user", "content": case["q"]}],
                          max_new_tokens=max_new_tokens)
        except Exception as e:
            answer = f"[inference error: {e}]"
        latencies.append(time.time() - t0)
        if "min_chars" in case:
            ok = len(answer) >= case["min_chars"]
        else:
            ok = _grade(case, answer)
        results.append({"id": case["id"], "category": case["category"],
                        "question": case["q"], "answer": answer, "passed": ok})

    by_cat: Dict[str, Counter] = {}
    for r in results:
        by_cat.setdefault(r["category"], Counter())[r["passed"]] += 1
    scores = {c: round(cnt[True] / (cnt[True] + cnt[False]), 3)
              for c, cnt in by_cat.items()}
    report = {
        "label": label,
        "scores_by_category": scores,
        "latency_sec_avg": round(sum(latencies) / len(latencies), 2) if latencies else 0.0,
        "total_cases": len(results),
        "results": results,
    }
    if out_json:
        import os
        os.makedirs(os.path.dirname(os.path.abspath(out_json)), exist_ok=True)
        with open(out_json, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
    return report


def compare(before: Dict, after: Dict) -> Dict:
    """Per-category deltas with the §26 gating verdict."""
    cats = set(before["scores_by_category"]) | set(after["scores_by_category"])
    deltas = {c: round(after["scores_by_category"].get(c, 0) -
                       before["scores_by_category"].get(c, 0), 3) for c in sorted(cats)}
    regressions = [c for c, d in deltas.items() if d < -0.15]
    return {"deltas": deltas, "significant_regressions": regressions,
            "accept": not regressions}
