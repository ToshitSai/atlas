from backend import llm
from backend.intent_router import _general_answer, classify_intent


def test_effective_engine_label_reflects_configured_openai(monkeypatch):
    for env_name in ("OPENAI_API_KEY", "GEMINI_API_KEY", "ANTHROPIC_API_KEY", "MISTRAL_API_KEY"):
        monkeypatch.delenv(env_name, raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    assert llm.effective_provider_label("Heuristic / Rule-based") == "Auto (Openai configured)"
    assert llm.effective_provider_label("OpenAI GPT-4o") == "Openai (selected)"


def test_edge_input_routing_is_fast_and_safe():
    assert classify_intent("?") == "CASUAL_CHAT"
    assert classify_intent("   ") == "CASUAL_CHAT"
    # Non-English input is allowed through the normal answer path, never the
    # dataset/research router.
    assert classify_intent("नमस्ते, पाइथन क्या है?") == "EXPLANATION"


def test_offline_hindi_question_returns_without_llm_wait(monkeypatch):
    for env_name in ("OPENAI_API_KEY", "GEMINI_API_KEY", "ANTHROPIC_API_KEY", "MISTRAL_API_KEY"):
        monkeypatch.delenv(env_name, raising=False)
    answer = _general_answer("नमस्ते, पाइथन क्या है?", "पाइथन")
    assert "Python" in answer
    assert "प्रोग्रामिंग" in answer
