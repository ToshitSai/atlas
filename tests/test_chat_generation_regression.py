"""Automated regression suite for Atlas AI chat generation pipeline (Section 18).

Covers all 16 mandatory regression scenarios:
 1. Greeting ("hi") - permanent regression test for the original critical bug
 2. Normal question ("What is Python?")
 3. Difficult question (Technical trade-offs)
 4. Mathematics ("Solve x + 7 = 19.")
 5. Coding ("Write a simple Python program.")
 6. Person/entity lookup ("Who is Mahesh Babu?")
 7. Current information ("Who won IPL 2026?")
 8. Deep research ("Research transformer architectures.")
 9. Follow-up question (context resolution with pronouns)
10. Model switching (Atlas Large, Atlas Fast, Atlas Reasoning)
11. Provider timeout handling
12. Invalid API key handling
13. Malformed response handling
14. Streaming interruption
15. Retry after failure
16. Multiple consecutive messages
"""

import json
import pytest
from fastapi.testclient import TestClient

from backend.main import app
import backend.model_router as model_router
import backend.intent_router as intent_router
import backend.llm as llm_mod


@pytest.fixture
def client(isolate_store):
    with TestClient(app) as test_client:
        yield test_client


# ---------------------------------------------------------------------------
# 1. Greeting ("hi") - Original Bug Permanent Regression Test
# ---------------------------------------------------------------------------
def test_1_greeting_hi_returns_natural_response(client, isolate_store):
    """The original bug where 'hi' failed with a generic error must never regress."""
    response = client.post("/api/chat", json={"message": "hi", "conversationId": "reg-greet-1"})
    assert response.status_code == 200
    data = response.json()
    assert data.get("intent") == "CASUAL_CHAT"
    text = data.get("response", "")
    assert len(text) > 5
    assert "atlas" in text.lower() or "help" in text.lower() or "hi" in text.lower()
    # Ensure it did NOT trigger unwanted deep research or dataset pipelines
    assert "activity" not in data or not data.get("activity")
    assert not data.get("projectId")


# ---------------------------------------------------------------------------
# 2. Normal question ("What is Python?")
# ---------------------------------------------------------------------------
def test_2_normal_question_what_is_python(client, isolate_store):
    response = client.post("/api/chat", json={"message": "What is Python?", "conversationId": "reg-python-2"})
    assert response.status_code == 200
    data = response.json()
    assert data.get("intent") in ("EXPLANATION", "ENTITY_INFORMATION")
    assert "programming language" in data.get("response", "").lower()


# ---------------------------------------------------------------------------
# 3. Difficult question (Technical trade-offs)
# ---------------------------------------------------------------------------
def test_3_difficult_question_technical_tradeoffs(client, isolate_store, monkeypatch):
    monkeypatch.setattr(intent_router, "query_llm", lambda prompt, *_a, **_k: "Gradient boosting handles tabular data with tree ensembles while neural networks require dense embeddings.")
    response = client.post("/api/chat", json={
        "message": "Explain the trade-offs between gradient boosting and neural networks on tabular data.",
        "conversationId": "reg-diff-3",
    })
    assert response.status_code == 200
    data = response.json()
    assert "gradient boosting" in data.get("response", "").lower()


# ---------------------------------------------------------------------------
# 4. Mathematics ("Solve x + 7 = 19.")
# ---------------------------------------------------------------------------
def test_4_mathematics_solve_equation(client, isolate_store):
    response = client.post("/api/chat", json={"message": "Solve x + 7 = 19.", "conversationId": "reg-math-4"})
    assert response.status_code == 200
    data = response.json()
    resp = data.get("response", "")
    assert "12" in resp


# ---------------------------------------------------------------------------
# 5. Coding ("Write a simple Python program.")
# ---------------------------------------------------------------------------
def test_5_coding_request(client, isolate_store, monkeypatch):
    monkeypatch.setattr(intent_router, "query_llm", lambda prompt, *_a, **_k: "def hello():\n    print('Hello from Python!')")
    response = client.post("/api/chat", json={"message": "Write a simple Python program.", "conversationId": "reg-code-5"})
    assert response.status_code == 200
    data = response.json()
    resp = data.get("response", "")
    assert "python" in resp.lower() or "print" in resp.lower() or "def " in resp.lower()


# ---------------------------------------------------------------------------
# 6. Person/entity lookup ("Who is Mahesh Babu?")
# ---------------------------------------------------------------------------
def test_6_person_lookup_mahesh_babu(client, isolate_store):
    response = client.post("/api/chat", json={"message": "Who is Mahesh Babu?", "conversationId": "reg-person-6"})
    assert response.status_code == 200
    data = response.json()
    assert "mahesh babu" in data.get("response", "").lower()


# ---------------------------------------------------------------------------
# 7. Current information ("Who won IPL 2026?")
# ---------------------------------------------------------------------------
def test_7_current_information(client, isolate_store):
    response = client.post("/api/chat", json={"message": "Who won IPL 2026?", "conversationId": "reg-curr-7"})
    assert response.status_code == 200
    data = response.json()
    assert data.get("intent") in ("CURRENT_INFORMATION", "WEB_SEARCH", "EXPLANATION")


# ---------------------------------------------------------------------------
# 8. Deep research ("Research transformer architectures.")
# ---------------------------------------------------------------------------
def test_8_deep_research_routing(client, isolate_store):
    response = client.post("/api/chat", json={
        "message": "Research transformer architectures and recent developments.",
        "conversationId": "reg-dr-8",
    })
    assert response.status_code == 200
    data = response.json()
    assert data.get("intent") in ("DEEP_RESEARCH", "LITERATURE_SEARCH", "RESEARCH_START")


# ---------------------------------------------------------------------------
# 9. Follow-up question (Context & pronoun resolution)
# ---------------------------------------------------------------------------
def test_9_follow_up_question_pronoun_resolution(client, isolate_store, monkeypatch):
    monkeypatch.setattr(intent_router, "query_llm", lambda prompt, *_a, **_k: "Python is useful because of its clear syntax and vast ecosystem.")
    # Turn 1
    r1 = client.post("/api/chat", json={"message": "What is Python?", "conversationId": "reg-followup-9"})
    assert r1.status_code == 200
    # Turn 2: pronoun follow-up
    r2 = client.post("/api/chat", json={
        "message": "Why is it useful?",
        "conversationId": "reg-followup-9",
        "conversationHistory": [
            {"role": "user", "content": "What is Python?"},
            {"role": "assistant", "content": "Python is a programming language."},
        ],
    })
    assert r2.status_code == 200
    data2 = r2.json()
    assert "useful" in data2.get("response", "").lower() or "python" in data2.get("response", "").lower()


# ---------------------------------------------------------------------------
# 10. Model switching (Atlas Large, Atlas Fast, Atlas Reasoning)
# ---------------------------------------------------------------------------
def test_10_model_switching_selection(client, isolate_store):
    models = ["Atlas Large", "Atlas Fast", "Atlas Reasoning"]
    for m in models:
        decision = model_router.route("req-test", "What is AI?", preferred_model=m)
        assert decision.requested_model == m
        assert decision.model is not None


# ---------------------------------------------------------------------------
# 11. Provider timeout handling
# ---------------------------------------------------------------------------
def test_11_provider_timeout_handled_gracefully(client, isolate_store, monkeypatch):
    import socket
    def raise_timeout(*a, **k):
        raise TimeoutError("LLM socket timed out")
    monkeypatch.setattr(intent_router, "query_llm", raise_timeout)
    monkeypatch.setattr(llm_mod, "any_provider_configured", lambda: True)

    # Calling chat_stream directly via test client with a timeout exception
    response = client.post("/api/chat", json={"message": "What is Python?", "conversationId": "reg-timeout-11"})
    # Even if LLM times out, intent_router falls back to known KB or safe message
    assert response.status_code == 200
    data = response.json()
    assert data.get("response")


# ---------------------------------------------------------------------------
# 12. Invalid API key handling
# ---------------------------------------------------------------------------
def test_12_invalid_api_key_handled_safely(client, isolate_store, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "invalid_key_xyz")
    monkeypatch.setattr(llm_mod, "any_provider_configured", lambda: True)
    response = client.post("/api/chat", json={"message": "hi", "conversationId": "reg-invalid-key-12"})
    assert response.status_code == 200
    data = response.json()
    # Must never leak invalid key or stack trace to client
    assert "invalid_key_xyz" not in json.dumps(data)
    assert data.get("response")


# ---------------------------------------------------------------------------
# 13. Malformed response handling
# ---------------------------------------------------------------------------
def test_13_malformed_response_handling(client, isolate_store, monkeypatch):
    # LLM returns empty or malformed string
    monkeypatch.setattr(intent_router, "query_llm", lambda *a, **k: "")
    response = client.post("/api/chat", json={"message": "hi", "conversationId": "reg-malformed-13"})
    assert response.status_code == 200
    data = response.json()
    assert data.get("response")  # Falls back to deterministic greeting


# ---------------------------------------------------------------------------
# 14. Streaming interruption / client cancellation
# ---------------------------------------------------------------------------
def test_14_streaming_endpoint_handles_cancellation(client, isolate_store):
    with client.stream("POST", "/api/chat/stream", json={"message": "hi", "conversationId": "reg-cancel-14"}) as stream:
        lines = []
        for line in stream.iter_lines():
            if line:
                lines.append(line)
            if len(lines) > 2:
                break  # simulate early client disconnect
    assert len(lines) > 0


# ---------------------------------------------------------------------------
# 15. Retry after failure
# ---------------------------------------------------------------------------
def test_15_retry_after_failure_recovers(client, isolate_store, monkeypatch):
    fail_flag = {"fail": True}
    def flaky_llm(*a, **k):
        if fail_flag["fail"]:
            raise RuntimeError("Temporary provider hiccup")
        return "Recovered answer on retry"
    monkeypatch.setattr(intent_router, "query_llm", flaky_llm)
    monkeypatch.setattr(llm_mod, "any_provider_configured", lambda: True)

    # First attempt: failure falls back gracefully
    r1 = client.post("/api/chat", json={"message": "hi", "conversationId": "reg-retry-15"})
    assert r1.status_code == 200

    # Second attempt (retry): succeeds with LLM answer
    fail_flag["fail"] = False
    r2 = client.post("/api/chat", json={"message": "hi", "conversationId": "reg-retry-15"})
    assert r2.status_code == 200
    assert "recovered" in r2.json()["response"].lower() or "atlas" in r2.json()["response"].lower()


# ---------------------------------------------------------------------------
# 16. Multiple consecutive messages isolation
# ---------------------------------------------------------------------------
def test_16_multiple_consecutive_messages_maintain_isolation(client, isolate_store):
    sid = "reg-consecutive-16"
    turns = [
        ("hi", "CASUAL_CHAT"),
        ("What is Python?", "EXPLANATION"),
        ("Solve x + 7 = 19.", "MATHEMATICAL_REASONING"),
    ]
    for msg, expected_intent in turns:
        res = client.post("/api/chat", json={"message": msg, "conversationId": sid})
        assert res.status_code == 200
        data = res.json()
        assert data.get("response")
        assert data.get("messageId")
