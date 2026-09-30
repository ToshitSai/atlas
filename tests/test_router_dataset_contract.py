import json
from pathlib import Path

from backend.intent_router import classify_intent


DATA = Path(r"C:\Users\Toshit\Downloads\ai_scientist_ml_dataset_starter\ai_scientist_ml_dataset\ai_scientist_ml_router.jsonl")
EXPECTED = {"normal": "EXPLANATION", "web_search": "WEB_SEARCH", "deep_research": "DEEP_RESEARCH"}


def test_all_router_training_examples_match_authoritative_mode():
    cases = [json.loads(line) for line in DATA.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(cases) == 16
    assert [classify_intent(case["question"]) for case in cases] == [EXPECTED[case["mode"]] for case in cases]
