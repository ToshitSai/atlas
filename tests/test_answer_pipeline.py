from backend.answer_pipeline import (
    build_context,
    classify_mode,
    normalize_question,
    structured_response,
    validate_response,
)


def test_normalization_preserves_meaning_without_prompt_injection():
    assert normalize_question("  Explain   XGBoost pls\n") == "Explain XGBoost pls"
    assert normalize_question("hi") == "hi"


def test_context_boundaries_keep_new_chat_isolated():
    context = build_context("hi", [{"role": "user", "content": "Explain CLIP"}])
    assert context["current_message"] == "hi"
    assert context["conversation_history"][0]["content"] == "Explain CLIP"
    fresh = build_context("hi")
    assert fresh["conversation_history"] == []
    assert fresh["research_context"] == {}
    assert fresh["tool_results"] == []


def test_modes_match_canonical_examples():
    assert classify_mode("Hi", {"mode": "normal"}) == "NORMAL"
    assert classify_mode("What is overfitting?", {"mode": "normal"}) == "NORMAL"
    assert classify_mode("What are the latest RAG papers?", {"mode": "web_search"}) == "WEB_SEARCH"
    assert classify_mode("Investigate why fraud detection recall is poor", {"mode": "deep_research"}) == "DEEP_RESEARCH"
    assert classify_mode("Compare XGBoost and Random Forest experimentally", {"mode": "normal"}) == "EXPERIMENT"


def test_structured_response_preserves_legacy_response_and_contract():
    result = structured_response(
        {"response": "Paris", "sources": []},
        question="What is the capital of France?",
        mode="NORMAL",
    )
    assert result["response"] == "Paris"
    assert result["answer"] == "Paris"
    assert result["mode"] == "NORMAL"
    assert result["validated"] is True
    assert result["citations"] == []


def test_stale_previous_answer_is_rejected_explicitly():
    try:
        validate_response(
            "old answer",
            question="new question",
            history=[{"role": "assistant", "content": "old answer"}],
        )
    except ValueError as exc:
        assert "stale" in str(exc)
    else:
        raise AssertionError("stale response was accepted")


def test_hi_never_uses_landing_copy_as_assistant_response():
    from backend.intent_router import handle_intent_message

    result = handle_intent_message("hi", session_id="render-regression-hi")
    assert result["response"]
    assert "Ready when you are. What should we investigate?" not in result["response"]


def test_llm_definition_is_grounded_and_not_provider_dependent():
    from backend.intent_router import handle_intent_message

    result = handle_intent_message("what is LLM", session_id="answer-regression-llm")
    answer = result["response"].lower()
    assert "large language model" in answer
    assert "neural network" in answer
    assert "predict" in answer or "generate" in answer

