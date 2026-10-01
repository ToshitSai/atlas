"""Application identity must override an underlying model's self-description."""
import pytest

from backend.project_identity import (
    classify_identity_query,
    get_public_project_info,
    handle_identity_response,
    sanitize_llm_identity_hallucinations,
)
from backend.intent_router import handle_intent_message

# Source-of-truth product name (config-driven; currently "Atlas"). Read from the
# application rather than hard-coded so this test protects the LIVE identity and
# tracks an intentional rebrand instead of pinning an obsolete string.
PRODUCT_NAME = get_public_project_info()["name"]


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
    # The self-description must use the configured product identity, never the
    # underlying model provider's name.
    assert PRODUCT_NAME in response
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


def test_identity_sanitizer_does_not_replace_an_unrelated_entity_answer():
    answer = "Mahesh Babu is an actor; Mistral is unrelated to this answer."
    assert sanitize_llm_identity_hallucinations(answer, "Who is Mahesh Babu?") == answer
