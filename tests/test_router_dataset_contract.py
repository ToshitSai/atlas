import json
from pathlib import Path

import pytest

from backend.intent_router import classify_intent


DATA = Path(r"C:\Users\Toshit\Downloads\ai_scientist_ml_dataset_starter\ai_scientist_ml_dataset\ai_scientist_ml_router.jsonl")
EXPECTED = {"normal": "EXPLANATION", "web_search": "WEB_SEARCH", "deep_research": "DEEP_RESEARCH"}

# This contract is validated against an external, human-labelled router dataset
# that is not versioned in the repo. When it is absent the test cannot execute and
# is SKIPPED (truthfully reported), not failed. The offline routing contract is
# covered independently by test_intent_router / test_atlas_product_contract.
pytestmark = pytest.mark.skipif(
    not DATA.exists(),
    reason=f"SKIPPED — external router dataset unavailable at {DATA}",
)


def test_all_router_training_examples_match_authoritative_mode():
    cases = [json.loads(line) for line in DATA.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(cases) == 16
    assert [classify_intent(case["question"]) for case in cases] == [EXPECTED[case["mode"]] for case in cases]
