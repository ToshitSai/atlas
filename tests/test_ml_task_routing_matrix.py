"""Regression matrix: questions never launch dataset discovery by accident."""
import pytest

from backend.intent_router import classify_intent, handle_intent_message


@pytest.mark.parametrize("message,expected", [
    # Questions and advice requests: always normal answer paths.
    ("how do I improve accuracy", "EXPLANATION"),
    ("How to improve sales", "EXPLANATION"),
    ("what is overfitting", "EXPLANATION"),
    ("why does my model overfit", "EXPLANATION"),
    ("explain how to detect fraud", "EXPLANATION"),
    ("what model should I use for churn", "EXPLANATION"),
    ("how can I predict house prices", "EXPLANATION"),
    ("why is fraud detection difficult", "EXPLANATION"),
    ("what is a dataset", "EXPLANATION"),
    ("explain precision and recall", "EXPLANATION"),
    ("how do I optimize a classifier", "EXPLANATION"),
    ("what features improve a sales forecast", "EXPLANATION"),
    # Unambiguous ML work or explicit dataset discovery.
    ("predict house prices", "RESEARCH_START"),
    ("build a churn model", "RESEARCH_START"),
    ("train a fraud detection model", "RESEARCH_START"),
    ("evaluate my classification model", "RESEARCH_START"),
    ("improve this model using my dataset", "RESEARCH_START"),
    ("detect fraudulent transactions", "RESEARCH_START"),
    ("forecast sales with a regression model", "RESEARCH_START"),
    ("classify spam emails", "RESEARCH_START"),
    ("find a dataset for fraud detection", "DATASET_RESEARCH"),
    ("search for churn datasets", "DATASET_RESEARCH"),
    ("recommend datasets for house price prediction", "DATASET_RESEARCH"),
    ("show me datasets about customer churn", "DATASET_RESEARCH"),
    # Borderline imperatives provide advice plus an opt-in offer.
    ("improve fraud detection", "RESEARCH_START"),
    ("optimize sales forecasting", "RESEARCH_START"),
    ("tune churn prediction", "EXPLANATION"),
    ("build fraud detection", "EXPLANATION"),
    # Greetings and ordinary general questions remain non-research.
    ("hello", "CASUAL_CHAT"),
    ("good morning", "CASUAL_CHAT"),
    ("what can you do", "CASUAL_CHAT"),
    ("What is Python?", "EXPLANATION"),
    ("write python code", "CODING"),
    ("solve 2 + 2", "MATHEMATICS"),
    # Follow-ups against an active project versus general follow-ups.
    ("why did the model perform poorly", "RESEARCH_FOLLOWUP"),
    ("show me the report", "REPORT_REQUEST"),
    ("try another approach", "RESEARCH_CONTROL"),
    ("how do I improve accuracy", "EXPLANATION"),
    ("what is overfitting", "EXPLANATION"),
    ("explain the dataset", "EXPLANATION"),
    ("why did the model perform poorly", "RESEARCH_FOLLOWUP"),
])
def test_routing_matrix(message, expected):
    active_project = "proj-routing" if expected in {"RESEARCH_FOLLOWUP", "REPORT_REQUEST", "RESEARCH_CONTROL"} else None
    assert classify_intent(message, active_project_id=active_project, session_id=f"matrix-{message}") == expected


def test_borderline_ml_request_answers_and_offers_dataset_search(isolate_store):
    response = handle_intent_message("improve sales", session_id="borderline-ml")
    assert response["intent"] == "EXPLANATION"
    assert response["action"] == "NONE"
    assert "Want me to search for datasets for this?" in response["response"]
    assert "I'll look for datasets" not in response["response"]
