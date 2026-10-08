from backend.intent_router import classify_research_route
from backend.confidence import assess_confidence


def test_stress_test_is_framed_not_keyword_explanation():
    result = classify_research_route(
        "Stress-test this system. Part 1: Bayes calculation. Part 2: DDP/AMP reasoning. Part 3: sampling mechanics."
    )
    assert result["mode"] == "deep_research"
    assert result["framing"] is True
    assert len(result["parts"]) >= 3


def test_math_confidence_does_not_require_web_sources():
    result = assess_confidence("derive the gradient", {
        "intent": "MATHEMATICS", "response": "gradient", 
        "math_check": {"status": "passed"},
    })
    assert result["overall"]["percentage"] == 90
    assert result["evidence"]["sources_used"] == 0
