"""Hermetic tests for capability planning and answer-quality metadata."""
import pytest

from backend.intelligence import (
    ambiguity_clarification,
    estimate_difficulty,
    execution_metadata,
    extract_entity_candidate,
)
from backend.intent_router import handle_intent_message


def test_difficulty_uses_structure_and_constraints_not_topic_keywords():
    hard = ("Design a scalable service. It must support multi-region failover, "
            "keep p95 below 50ms, comply with GDPR, and explain a safe rollout.")
    assert estimate_difficulty("What is Python?", "EXPLANATION") == "EASY"
    assert estimate_difficulty(hard, "REASONING") == "HARD"


def test_metadata_selects_tools_and_does_not_claim_code_was_run():
    meta = execution_metadata("Write a Python duplicate finder", {
        "intent": "CODING", "taskType": "coding", "response": "```python\npass\n```"})
    assert meta["selected_tools"] == ["code_generator", "sandbox"]
    assert meta["verification_status"] == "pending_execution"
    assert "prompt" not in meta and "chain" not in meta


def test_ambiguous_world_cup_asks_for_sport_and_year():
    assert "sport and year" in ambiguity_clarification("Who won the World Cup?")
    assert ambiguity_clarification("Who won the FIFA World Cup 2022?") is None


@pytest.mark.parametrize("question,entity", [
    ("Who is Mahesh Babu?", "Mahesh Babu"),
    ("Who is Virat Kohli?", "Virat Kohli"),
    ("Tell me about Sundar Pichai", "Sundar Pichai"),
    ("Who is Elon Musk?", "Elon Musk"),
    ("Who is A. R. Rahman?", "A. R. Rahman"),
    ("Who is Sachin Tendulkar?", "Sachin Tendulkar"),
    ("Who is Ratan Tata?", "Ratan Tata"),
    ("Who is Cristiano Ronaldo?", "Cristiano Ronaldo"),
    ("What is Tesla?", "Tesla"),
    ("What is React?", "React"),
    ("What is Hyderabad?", "Hyderabad"),
    ("What is Android?", "Android"),
    ("What is NASA?", "NASA"),
    ("What is the IPL?", "the IPL"),
])
def test_entity_candidate_extraction_is_generic(question, entity):
    assert extract_entity_candidate(question) == entity


def test_recognizable_person_uses_entity_information_and_search_fallback(monkeypatch, isolate_store):
    from backend import intent_router

    captured = []
    monkeypatch.setattr(intent_router, "query_llm", lambda prompt, *_a, **_k: captured.append(prompt) or "Mahesh Babu is an Indian actor known for Telugu cinema.")
    monkeypatch.setattr("backend.web_search.search_web", lambda query, limit=5: [{
        "title": "Official profile", "url": "https://example.test/profile",
        "snippet": "Actor and film producer.", "source": "Official",
    }])
    result = handle_intent_message("Who is Mahesh Babu?", session_id="entity-answer")
    assert result["intent"] == "ENTITY_INFORMATION"
    assert result["entity"] == "Mahesh Babu"
    assert result["entityType"] == "PERSON"
    assert result["searchUsed"] is True
    # A search result supplies a verifiable snippet, so it is rendered with its
    # source instead of the unverified model biography.
    assert "Actor and film producer" in result["response"]
    assert "Source: https://example.test/profile" in result["response"]
    # The model biography must not leak into the answer when search grounds it.
    assert captured == []


def test_unknown_entity_does_not_get_hallucinated_answer(monkeypatch, isolate_store):
    from backend import intent_router

    monkeypatch.setattr(intent_router, "query_llm", lambda *_a, **_k: None)
    monkeypatch.setattr("backend.web_search.search_web", lambda *_a, **_k: [])
    result = handle_intent_message("Who is XYZRandomPerson123?", session_id="unknown-person")
    assert result["intent"] == "ENTITY_INFORMATION"
    assert "can't reliably identify" in result["response"].lower()


def test_named_ambiguous_person_asks_clarification():
    assert "several notable people" in ambiguity_clarification("Who is John Smith?").lower()
    assert ambiguity_clarification("Who is Mahesh Babu?") is None


def test_router_attaches_intelligence_and_compact_memory(isolate_store):
    result = handle_intent_message("What is JavaScript?", session_id="intelligence-test")
    assert result["intelligence"]["task_type"]
    assert result["intelligence"]["difficulty"] == "EASY"
    summary = isolate_store.get_session("intelligence-test")["conversation_summary"]
    assert summary["turns_seen"] == 1


def test_router_returns_clarification_without_guessing(isolate_store):
    result = handle_intent_message("Who won the World Cup?", session_id="ambiguous-test")
    assert result["taskType"] == "clarification"
    assert "sport and year" in result["response"]
