"""Run held-out confidence metadata checks; this is not a training input."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.confidence import assess_confidence

def main():
    rows = [json.loads(line) for line in (ROOT / "evaluation" / "confidence_holdout.jsonl").read_text(encoding="utf-8").splitlines() if line]
    # Deterministic fixture responses exercise the confidence layer without
    # treating a model's token scores as calibrated correctness probabilities.
    results = []
    for row in rows:
        intent = "EXPLANATION" if row["id"] in {"gd-definition", "overfitting"} else "RESEARCH_START" if "fraud" in row["question"].lower() or "model" in row["question"].lower() else "CURRENT_INFORMATION"
        meta = assess_confidence(row["question"], {"intent": intent, "response": "A substantive, evidence-limited answer."})
        results.append({"id": row["id"], "expected": row["expected_level"], "actual": meta["overall"]["level"], "match": row["expected_level"] == meta["overall"]["level"]})
    accuracy = sum(x["match"] for x in results) / len(results)
    print(json.dumps({"cases": results, "level_match_rate": accuracy, "calibration_metrics": "not computed: held-out correctness labels and model predictions are required"}, indent=2))

if __name__ == "__main__":
    main()
