"""Current-product contract test (Atlas).

One high-level regression that protects the CURRENT product identity and flow
against an accidental return to the old "AI Scientist" / ResearchChatWorkspace
implementation. It walks the contract end to end:

    current branding
      -> current workspace shell
      -> normal question routing + answer
      -> deep-research question routing + research activity state
      -> web/current question routing
      -> identity interception (no provider self-identification)

Everything here is offline/hermetic: routing uses the deterministic classifier,
the LLM is stubbed by conftest, and network tools are neutralised by conftest, so
the deep-research path exercises its routing/activity contract without live calls.
"""
import re

import pytest

from backend.intent_router import classify_intent, handle_intent_message
from backend.project_identity import get_public_project_info, handle_identity_response

# Source-of-truth product name (config-driven). Read from the application so the
# contract tracks an intentional rebrand instead of pinning a literal string.
PRODUCT_NAME = get_public_project_info()["name"]

# Provider env vars deleted so identity assertions are deterministic regardless
# of a developer's .env (auto-loaded by backend.config) or earlier tests.
_PROVIDER_KEY_ENVS = ("OPENAI_API_KEY", "GEMINI_API_KEY", "ANTHROPIC_API_KEY", "MISTRAL_API_KEY")


# --------------------------------------------------------------------------- #
# 1. Current branding
# --------------------------------------------------------------------------- #
def test_product_identity_is_current_brand():
    assert PRODUCT_NAME == "Atlas"
    # The configured identity files and the served HTML title must agree.
    with open("index.html", encoding="utf-8") as f:
        html = f.read()
    assert re.search(r"<title>\s*Atlas\b", html), "index.html title must use the Atlas brand"


def test_self_identity_response_uses_current_brand():
    response = handle_identity_response("Who are you?")["response"]
    assert PRODUCT_NAME in response
    # Never self-identify as the underlying model provider.
    for provider in ("Mistral", "ChatGPT", "OpenAI", "Anthropic", "Gemini", "Claude"):
        assert provider not in response


# --------------------------------------------------------------------------- #
# 2. Current workspace shell (not the orphaned legacy component)
# --------------------------------------------------------------------------- #
def test_workspace_shell_is_the_atlas_view_set():
    with open("src/App.jsx", encoding="utf-8") as f:
        app = f.read()
    # The active answer surfaces are the Atlas views...
    assert "NormalAnswerView" in app and "ResearchWorkspaceView" in app
    # ...and the legacy cyan workspace must not be wired back into the shell.
    assert "ResearchChatWorkspace" not in app


def test_answer_views_are_label_free():
    """Role is conveyed visually (avatar/alignment/icon), not with literal
    'Question'/'Answer'/'You' field labels — the Claude/ChatGPT-style contract."""
    for path in ("src/components/NormalAnswerView.jsx", "src/components/ResearchWorkspaceView.jsx"):
        with open(path, encoding="utf-8") as f:
            src = f.read()
        # No standalone literal role-label headings rendered to the user.
        assert not re.search(r">\s*(Question|Answer)\s*<", src), f"{path} renders a literal role label"


# --------------------------------------------------------------------------- #
# 3. Normal question -> focused explanation
# --------------------------------------------------------------------------- #
def test_normal_question_routes_and_answers():
    assert classify_intent("What is overfitting?") == "EXPLANATION"
    assert classify_intent("Explain XGBoost.") == "EXPLANATION"

    res = handle_intent_message("What is overfitting?", session_id="contract-normal")
    assert res["intent"] == "EXPLANATION"
    assert res["action"] == "NONE"
    assert isinstance(res.get("response"), str) and res["response"].strip()
    # A normal answer must not silently escalate into a research offer.
    assert res.get("pendingAction") is None


# --------------------------------------------------------------------------- #
# 4. Deep-research question -> research routing + activity state
# --------------------------------------------------------------------------- #
def test_deep_research_question_routes_and_produces_research_state():
    assert classify_intent(
        "Investigate why my fraud model has low recall and design experiments to improve it."
    ) == "DEEP_RESEARCH"
    assert classify_intent("Do deep research on RAG.") == "DEEP_RESEARCH"

    res = handle_intent_message("Do deep research on RAG.", session_id="contract-deep")
    assert res["intent"] == "DEEP_RESEARCH"
    assert res["taskType"] == "deep_research"
    # The research routing decision that drives the workspace activity timeline.
    assert "researchRoute" in res
    assert isinstance(res.get("response"), str) and res["response"].strip()


def test_not_every_ml_question_is_deep_research():
    for normal in ("What is overfitting?", "Explain XGBoost.", "What is recall?"):
        assert classify_intent(normal) != "DEEP_RESEARCH"


# --------------------------------------------------------------------------- #
# 5. Web / current-information question -> web search
# --------------------------------------------------------------------------- #
def test_current_information_routes_to_web_search():
    assert classify_intent("What are the latest developments in RAG?") == "WEB_SEARCH"


# --------------------------------------------------------------------------- #
# 6. Identity interception (no provider self-identification)
# --------------------------------------------------------------------------- #
def test_identity_is_intercepted_without_provider_leak(monkeypatch):
    for key in _PROVIDER_KEY_ENVS:
        monkeypatch.delenv(key, raising=False)
    res = handle_intent_message("who created you", session_id="contract-identity")
    assert res["intent"] == "PROJECT_IDENTITY"
    response = res["response"]
    assert "Toshit Sai Galam" in response or PRODUCT_NAME in response
    for provider in ("Mistral AI", "OpenAI", "Anthropic", "Gemini", "DeepMind"):
        assert provider not in response
