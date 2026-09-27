"""Application identity must override an underlying model's self-description."""
import pytest

from backend.project_identity import classify_identity_query, handle_identity_response
from backend.intent_router import handle_intent_message


@pytest.mark.parametrize("question", [
    "who is the founder of you",
    "Who created you?",
    "Who built this?",
    "Who made this AI?",
    "Who is behind AI Scientist?",
    "Who founded AI Scientist?",
])
def test_creator_variants_route_to_the_project_profile(question):
    assert classify_identity_query(question) == "CREATOR"
    response = handle_identity_response(question)["response"]
    assert "Toshit Sai Galam" in response
    assert "Mistral AI created" not in response
    assert "OpenAI created" not in response


def test_self_identity_is_application_not_model_provider():
    assert classify_identity_query("Who are you?") == "SELF"
    response = handle_identity_response("Who are you?")["response"]
    assert "AI Scientist" in response
    assert "Mistral" not in response


def test_model_power_is_distinct_and_never_guesses_provider(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("MISTRAL_API_KEY", raising=False)
    assert classify_identity_query("Are you powered by Mistral?") == "MODEL_POWER"
    response = handle_identity_response("What model powers you?")["response"]
    assert "exact configured underlying model information" in response


def test_router_intercepts_creator_before_any_llm(isolate_store, monkeypatch):
    import backend.intent_router as router
    monkeypatch.setattr(router, "query_llm", lambda *a, **k: pytest.fail("identity must not call LLM"))
    result = handle_intent_message("who is the founder of you", session_id="identity-regression")
    assert result["intent"] == "PROJECT_IDENTITY"
    assert "Toshit Sai Galam" in result["response"]
