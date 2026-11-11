import os
import sys
import pytest

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import backend.config
from backend.rag_service import service as rag_svc
from backend.intent_router import handle_intent_message
from backend import llm

FICTIONAL_DOC = """Atlas RAG Verification Code: ORBIT-7429.
The fictional research station is located on Europa.
Its chief scientist is Dr. Mira Sol.
Its emergency power system is named Aurora Core."""

TEST_SESSION = "test_gen32_europa_session"


def setup_module():
    """Ingest the Europa verification document for testing."""
    rag_svc.ingest_document(
        filename="europa_station.txt",
        content=FICTIONAL_DOC.encode("utf-8"),
        owner_session=TEST_SESSION,
    )


def teardown_module():
    """Clean up test documents."""
    docs = rag_svc.list_documents(owner_session=TEST_SESSION)
    for d in docs:
        rag_svc.delete_document(d["id"], owner_session=TEST_SESSION)


@pytest.fixture(autouse=True)
def unmock_llm_if_available():
    """Restore real LLM methods if GEMINI_API_KEY is configured in environment."""
    if os.environ.get("GEMINI_API_KEY"):
        import importlib
        import backend.llm as real_llm
        import backend.intent_router as intent_mod
        importlib.reload(real_llm)
        importlib.reload(intent_mod)


def test_what_is_apple_vs_apple():
    """Verify both 'what is apple' and 'apple' return valid explanations without failure."""
    from backend.intent_router import handle_intent_message
    res1 = handle_intent_message("what is apple", session_id=f"{TEST_SESSION}:c1")
    assert res1.get("response")
    assert "couldn't reach the AI service" not in res1["response"]
    assert "apple" in res1["response"].lower()

    res2 = handle_intent_message("apple", session_id=f"{TEST_SESSION}:c2")
    assert res2.get("response")
    assert "couldn't reach the AI service" not in res2["response"]
    assert "apple" in res2["response"].lower()


def test_rag_q1_verification_code():
    """Q1: What is the Atlas RAG verification code? -> ORBIT-7429 with citation."""
    res = handle_intent_message(
        "What is the Atlas RAG verification code?",
        session_id=f"{TEST_SESSION}:c3",
        owner_session=TEST_SESSION,
    )
    assert res.get("intent") == "DOCUMENT_ANALYSIS"
    resp = res.get("response", "")
    assert "ORBIT-7429" in resp
    assert len(res.get("sources", [])) > 0
    assert any("europa_station.txt" in s.get("title", "") or "europa_station.txt" in s.get("source", "") for s in res.get("sources", []))


def test_rag_q2_station_location():
    """Q2: Where is the fictional research station located? -> Europa with citation."""
    res = handle_intent_message(
        "Where is the fictional research station located?",
        session_id=f"{TEST_SESSION}:c4",
        owner_session=TEST_SESSION,
    )
    assert res.get("intent") == "DOCUMENT_ANALYSIS"
    resp = res.get("response", "")
    assert "Europa" in resp
    assert len(res.get("sources", [])) > 0


def test_rag_q3_chief_scientist():
    """Q3: Who is the chief scientist? -> Dr. Mira Sol with citation."""
    res = handle_intent_message(
        "Who is the chief scientist?",
        session_id=f"{TEST_SESSION}:c5",
        owner_session=TEST_SESSION,
    )
    assert res.get("intent") == "DOCUMENT_ANALYSIS"
    resp = res.get("response", "")
    assert "Mira Sol" in resp
    assert len(res.get("sources", [])) > 0


def test_rag_q4_emergency_power():
    """Q4: What is the emergency power system named? -> Aurora Core with citation."""
    res = handle_intent_message(
        "What is the emergency power system named?",
        session_id=f"{TEST_SESSION}:c6",
        owner_session=TEST_SESSION,
    )
    assert res.get("intent") == "DOCUMENT_ANALYSIS"
    resp = res.get("response", "")
    assert "Aurora Core" in resp
    assert len(res.get("sources", [])) > 0


def test_rag_q5_missing_info_no_hallucination():
    """Q5: What is the chief scientist's favorite food? -> Must state missing info, NO hallucination."""
    res = handle_intent_message(
        "What is the chief scientist's favorite food?",
        session_id=f"{TEST_SESSION}:c7",
        owner_session=TEST_SESSION,
    )
    assert res.get("intent") == "DOCUMENT_ANALYSIS"
    resp = res.get("response", "").lower()
    # Must explicitly state that the document does not contain this information
    missing_indicators = [
        "not contain", "does not mention", "no information", "not mentioned",
        "does not provide", "not stated", "cannot be found", "not specified"
    ]
    assert any(ind in resp for ind in missing_indicators), f"Expected missing-info disclosure but got: {res.get('response')}"


def test_casual_chat_and_math_not_hijacked_by_rag():
    """Casual chat and math queries must not be hijacked by RAG even with indexed docs."""
    res_hi = handle_intent_message("hi", session_id=f"{TEST_SESSION}:c8", owner_session=TEST_SESSION)
    assert res_hi.get("intent") == "CASUAL_CHAT"

    res_math = handle_intent_message("solve x + 7 = 19", session_id=f"{TEST_SESSION}:c9", owner_session=TEST_SESSION)
    assert res_math.get("intent") in ("MATHEMATICS", "EXPLANATION")
    assert "12" in res_math.get("response", "")
