"""Classification contract for normal, live-lookup, and deep-study modes."""
import pytest

from backend.intent_router import classify_research_route, handle_intent_message


@pytest.mark.parametrize("message,mode", [
    ("What is machine learning?", "normal"),
    ("Explain overfitting.", "normal"),
    ("What is precision and recall?", "normal"),
    ("What is Python?", "normal"),
    ("Write a binary search algorithm.", "normal"),
    ("What is a neural network?", "normal"),
    ("Calculate 25 * 37.", "normal"),
    ("Explain REST APIs.", "normal"),
    ("What is a database?", "normal"),
    ("Difference between SQL and NoSQL.", "normal"),
    ("What is today's NVIDIA stock price?", "web_search"),
    ("What are the latest Python releases?", "web_search"),
    ("What happened in today's AI news?", "web_search"),
    ("Improve fraud detection.", "deep_research"),
    ("Investigate methods for reducing false negatives in fraud detection.", "deep_research"),
    ("Compare recent fraud detection approaches using research papers.", "deep_research"),
    ("Find suitable datasets for fraud detection and evaluate candidate models.", "deep_research"),
    ("Design experiments to determine whether SMOTE improves fraud detection.", "deep_research"),
    ("Study recent techniques for transformer-based tabular classification.", "deep_research"),
    ("Find a research gap in automated ML.", "deep_research"),
    ("Reproduce a machine-learning research paper experimentally.", "deep_research"),
    ("Compare XGBoost, Random Forest and neural networks on a selected dataset.", "deep_research"),
    ("Research why my model performs poorly and design experiments to improve it.", "deep_research"),
    ("Conduct a full autonomous ML research cycle for fraud detection.", "deep_research"),
    ("What is the best ML algorithm?", "normal"),
    ("Best model for fraud detection?", "normal"),
    ("How can I improve my model?", "normal"),
    ("Research fraud detection.", "deep_research"),
])
def test_master_routing_matrix(message, mode):
    result = classify_research_route(message)
    assert set(result) == {"mode", "confidence", "reason", "requires_web", "requires_deep_research"}
    assert result["mode"] == mode
    assert 0 <= result["confidence"] <= 1
    assert result["requires_deep_research"] is (mode == "deep_research")


def test_deep_research_activity_contains_only_executed_stages(isolate_store, monkeypatch):
    import backend.deep_research as deep
    monkeypatch.setattr(deep, "run_deep_research", lambda goal: {
        "status": "ok", "report": "# Report\n\nEvidence-backed finding.",
        "sourceCount": 2, "subqueries": ["one", "two"],
    })
    result = handle_intent_message("Research this topic", session_id="deep-events")
    stages = [(event["stage"], event["status"]) for event in result["activity"]]
    assert result["intent"] == "DEEP_RESEARCH"
    assert ("UNDERSTANDING", "completed") in stages
    assert ("PLANNING", "completed") in stages
    assert ("LITERATURE_SEARCH", "completed") in stages
    assert ("REPORT", "completed") in stages
    assert ("COMPLETED", "completed") in stages
    assert not any(stage in {"BASELINE", "EVALUATION", "ERROR_ANALYSIS"} for stage, _ in stages)


def test_deep_research_failure_is_visible_not_fabricated(isolate_store, monkeypatch):
    import backend.deep_research as deep
    monkeypatch.setattr(deep, "run_deep_research", lambda goal: {
        "status": "no_sources", "report": "", "sourceCount": 0, "subqueries": ["one"],
    })
    result = handle_intent_message("Research this topic", session_id="deep-failure")
    assert any(event["stage"] == "LITERATURE_SEARCH" and event["status"] == "failed"
               for event in result["activity"])
    assert "won't pretend" in result["response"].lower()
