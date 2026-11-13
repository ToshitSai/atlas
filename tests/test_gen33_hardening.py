"""
Atlas AI Gen-3.3 Comprehensive Hardening Test Suite
Covers:
- Test Group A: General Chat & Multi-Turn
- Test Group B: Provider Reliability & Circuit Breakers
- Test Group C: Multi-Document RAG (Orion & Neptune Test Suite)
- Test Group D: Database Diagnostics & Durability Truthfulness
- Test Group E: Persistent Memory (Layers 1, 2, 3)
- Test Group F: Security & Cross-Session Isolation
- Test Group G: Autonomous AI Scientist Workflow & Honest Metrics
"""

import pytest
import os
import sys
import uuid
import json
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
import backend.config
from backend.main import app
from database.store import store
import backend.llm as llm_mod
import backend.intent_router as intent_router_mod
from backend.rag_service import service as rag_svc
from backend.embedding_registry import registry as emb_reg
from backend import model_router


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def restore_live_llm():
    """Ensure live LLM is unpatched for tests requiring real provider execution."""
    old_query = llm_mod.query_llm
    old_configured = llm_mod.any_provider_configured
    import importlib
    importlib.reload(llm_mod)
    importlib.reload(intent_router_mod)
    yield
    llm_mod.query_llm = old_query
    llm_mod.any_provider_configured = old_configured


# ============================================================================
# Test Group A: General AI Chat & Multi-Turn
# ============================================================================

def test_group_a_general_chat_greetings_and_math(client):
    # 1. Greetings
    res_hi = client.post("/api/chat", json={"message": "hi", "stream": False})
    assert res_hi.status_code == 200
    assert "atlas" in res_hi.json()["response"].lower()

    # 2. Symbolic Math
    res_math = client.post("/api/chat", json={"message": "solve x + 7 = 19", "stream": False})
    assert res_math.status_code == 200
    assert "12" in res_math.json()["response"]
    assert res_math.json()["intent"] == "MATHEMATICS"

    # 3. Identity
    res_id = client.post("/api/chat", json={"message": "Who created you?", "stream": False})
    assert res_id.status_code == 200
    assert "toshit sai galam" in res_id.json()["response"].lower()


def test_group_a_bare_noun_disambiguation(restore_live_llm, client):
    # Bare noun "apple" must explain Apple Inc / apple topic, not identity
    res = client.post("/api/chat", json={"message": "apple", "stream": False})
    assert res.status_code == 200
    text = res.json()["response"].lower()
    assert "apple" in text
    assert "atlas is an intelligent" not in text[:60]


# ============================================================================
# Test Group B: Provider Reliability & Circuit Breaker
# ============================================================================

def test_group_b_provider_health_cooldown():
    # Record authentication failure (e.g. HTTP 401)
    model_router.health.record("mock_provider", False, "HTTP Error 401: Unauthorized")
    assert not model_router.health.is_available("mock_provider")
    
    # Snapshot reflects failure status
    snap = model_router.health.snapshot()
    assert "mock_provider" in snap
    assert snap["mock_provider"]["status"] == "authentication"
    assert snap["mock_provider"]["consecutive_failures"] >= 1

    # Record success -> immediately available again
    model_router.health.record("mock_provider", True)
    assert model_router.health.is_available("mock_provider")


def test_group_b_candidate_models_presence():
    candidates = llm_mod._gemini_candidate_models()
    assert len(candidates) >= 3
    assert "gemini-2.5-flash-lite" in candidates
    assert "gemini-flash-lite-latest" in candidates


# ============================================================================
# Test Group C: Multi-Document RAG (Orion & Neptune Test Suite)
# ============================================================================

DOC_ORION = """Project name: Orion.
Project code: ORION-9812.
Project manager: Dr. Elena.
Primary location: Mars.
Power system: Helios."""

DOC_NEPTUNE = """Project name: Neptune.
Project code: NEPTUNE-5521.
Project manager: Dr. Arjun.
Primary location: Titan.
Power system: Triton."""


def test_group_c_multi_document_rag_grounding_and_lifecycle():
    session_id = f"orion-neptune-test-{uuid.uuid4().hex[:8]}"

    # Ingest Document A (Orion)
    doc_a = rag_svc.ingest_document("project_orion.txt", DOC_ORION.encode("utf-8"), owner_session=session_id)
    assert doc_a["status"] == "ready"
    assert doc_a["chunks_count"] >= 1

    # Ingest Document B (Neptune)
    doc_b = rag_svc.ingest_document("project_neptune.txt", DOC_NEPTUNE.encode("utf-8"), owner_session=session_id)
    assert doc_b["status"] == "ready"
    assert doc_b["chunks_count"] >= 1

    # 1. Retrieve Orion's code
    r1 = rag_svc.retrieve_context("What is the project code for Orion?", owner_session=session_id)
    assert any("ORION-9812" in c["content"] for c in r1["chunks"])

    # 2. Retrieve Neptune's code
    r2 = rag_svc.retrieve_context("What is the project code for Neptune?", owner_session=session_id)
    assert any("NEPTUNE-5521" in c["content"] for c in r2["chunks"])

    # 3. Identify Orion's manager
    r3 = rag_svc.retrieve_context("Who is the project manager for Orion?", owner_session=session_id)
    assert any("Dr. Elena" in c["content"] for c in r3["chunks"])

    # 4. Identify Neptune's location
    r4 = rag_svc.retrieve_context("Where is Project Neptune located?", owner_session=session_id)
    assert any("Titan" in c["content"] for c in r4["chunks"])

    # 5. Multi-document query: Power system in both documents
    r5 = rag_svc.retrieve_context("What are the power systems of both projects?", owner_session=session_id, limit=4)
    chunks_text = " ".join(c["content"] for c in r5["chunks"])
    assert "Helios" in chunks_text
    assert "Triton" in chunks_text

    # 6. Paraphrased query
    r6 = rag_svc.retrieve_context("Who is directing the initiative situated on the red planet?", owner_session=session_id)
    assert any("Dr. Elena" in c["content"] or "Mars" in c["content"] for c in r6["chunks"])

    # 7. Absent information refusal test
    q_absent = "What is the total annual budget of Project Orion?"
    res_absent = intent_router_mod.handle_intent_message(
        message=q_absent,
        conversation_id=session_id,
        owner_session=session_id
    )
    ans_lower = res_absent["response"].lower()
    refusal_markers = ["does not contain", "not mentioned", "not provided", "not specified", "unspecified", "no information"]
    assert any(m in ans_lower for m in refusal_markers), f"Expected refusal without hallucination. Got: {res_absent['response']}"

    # 8. Document deletion lifecycle
    del_ok = rag_svc.delete_document(doc_a["id"], owner_session=session_id)
    assert del_ok is True

    # After deletion, Orion should no longer be listed
    active_docs = rag_svc.list_documents(owner_session=session_id)
    active_ids = [d["id"] for d in active_docs]
    assert doc_a["id"] not in active_ids
    assert doc_b["id"] in active_ids

    # Cleanup Document B
    rag_svc.delete_document(doc_b["id"], owner_session=session_id)


def test_group_c_section8_atlas_orion_and_neptune_suite():
    session_id = f"atlas-s8-test-{uuid.uuid4().hex[:8]}"

    doc_a_text = """Project: Atlas Orion
Verification code: ORION-8426
Location: Mars"""

    doc_b_text = """Project: Atlas Neptune
Verification code: NEPTUNE-5931
Location: Titan"""

    # Ingest Document A
    doc_a = rag_svc.ingest_document("atlas_orion.txt", doc_a_text.encode("utf-8"), owner_session=session_id)
    assert doc_a["status"] == "ready"

    # Ingest Document B
    doc_b = rag_svc.ingest_document("atlas_neptune.txt", doc_b_text.encode("utf-8"), owner_session=session_id)
    assert doc_b["status"] == "ready"

    # 1. What is Orion's verification code?
    r1 = intent_router_mod.handle_intent_message(
        message="What is Orion's verification code?",
        session_id=session_id,
        owner_session=session_id
    )
    assert "ORION-8426" in r1["response"] or "8426" in r1["response"]

    # 2. Where is Neptune located?
    r2 = intent_router_mod.handle_intent_message(
        message="Where is Neptune located?",
        session_id=session_id,
        owner_session=session_id
    )
    assert "Titan" in r2["response"]

    # 3. Compare the projects
    r3 = intent_router_mod.handle_intent_message(
        message="Compare the projects.",
        session_id=session_id,
        owner_session=session_id
    )
    ans3 = r3["response"]
    assert "Orion" in ans3 and "Neptune" in ans3

    # 4. What is Orion's annual budget? (Honest refusal)
    r4 = intent_router_mod.handle_intent_message(
        message="What is Orion's annual budget?",
        session_id=session_id,
        owner_session=session_id
    )
    ans4_lower = r4["response"].lower()
    refusal_markers = ["not mentioned", "not provided", "does not contain", "unspecified", "not specified", "no information"]
    assert any(m in ans4_lower for m in refusal_markers)

    # 5. Cascading deletion of one document
    del_ok = rag_svc.delete_document(doc_a["id"], owner_session=session_id)
    assert del_ok is True

    # 6. Verify deleted document is no longer retrievable
    remaining_docs = rag_svc.list_documents(owner_session=session_id)
    assert doc_a["id"] not in [d["id"] for d in remaining_docs]
    assert doc_b["id"] in [d["id"] for d in remaining_docs]

    # Cleanup
    rag_svc.delete_document(doc_b["id"], owner_session=session_id)


def test_group_c_cross_session_isolation():
    session_user1 = f"user1-{uuid.uuid4().hex[:8]}"
    session_user2 = f"user2-{uuid.uuid4().hex[:8]}"

    # User 1 ingests sensitive document
    doc1 = rag_svc.ingest_document(
        "secret_roadmap.txt",
        b"Secret Codename: PROJECT-ZEUS-99. Confidential launch date: October 2029.",
        owner_session=session_user1
    )

    # User 2 searches for secret codename -> MUST RETURN ZERO CHUNKS
    ret2 = rag_svc.retrieve_context("What is the secret codename?", owner_session=session_user2)
    assert len(ret2["chunks"]) == 0
    assert ret2["active"] is False

    # User 2 list documents -> MUST BE EMPTY
    docs2 = rag_svc.list_documents(owner_session=session_user2)
    assert len(docs2) == 0

    # User 2 attempts to delete User 1's document -> MUST FAIL
    del_attempt = rag_svc.delete_document(doc1["id"], owner_session=session_user2)
    assert del_attempt is False

    # Cleanup by User 1
    rag_svc.delete_document(doc1["id"], owner_session=session_user1)


# ============================================================================
# Test Group D: Database Diagnostics & Durability Truthfulness
# ============================================================================

def test_group_d_database_diagnostics_and_health_endpoints(client):
    # 1. /api/health
    res_h = client.get("/api/health")
    assert res_h.status_code == 200
    h_data = res_h.json()
    assert h_data["api"] is True
    assert set(h_data) <= {"status", "api", "database", "storage"}

    # 2. /api/ready
    res_r = client.get("/api/ready")
    assert res_r.status_code in (200, 503)
    r_data = res_r.json()
    assert "ready" in r_data
    assert "databaseType" in r_data

    # 3. /api/diagnostics
    res_d = client.get("/api/diagnostics")
    assert res_d.status_code == 200
    d_data = res_d.json()
    assert d_data["status"] == "ok"
    assert "subsystems" in d_data
    assert "database" in d_data["subsystems"]
    assert "ragEngine" in d_data["subsystems"]


def test_group_d_truthful_durability_metadata():
    session_id = f"test-durability-{uuid.uuid4().hex[:8]}"
    doc = rag_svc.ingest_document("test_durability.txt", b"Test durability content.", owner_session=session_id)
    
    # Must report truthful storage tier and durability
    assert "storage" in doc
    assert "durability" in doc
    assert doc["durability"] in ("durable", "ephemeral")
    
    rag_svc.delete_document(doc["id"], owner_session=session_id)


# ============================================================================
# Test Group E: Persistent Memory (Layers 1, 2, 3)
# ============================================================================

def test_group_e_user_memory_crud_and_isolation(client):
    session1 = f"session-mem-1-{uuid.uuid4().hex[:8]}"
    session2 = f"session-mem-2-{uuid.uuid4().hex[:8]}"

    # Save Layer 2 user memory for session 1
    m1 = rag_svc.save_user_memory(
        owner_session=session1,
        category="preference",
        content="User prefers Python code examples over JavaScript.",
        confidence=1.0,
        metadata={"source": "user_settings"}
    )
    assert m1["category"] == "preference"

    # List memory for session 1
    list1 = rag_svc.list_user_memories(owner_session=session1)
    assert len(list1) >= 1
    assert any("Python code" in m["content"] for m in list1)

    # Session 2 must see 0 memories (Strict session isolation)
    list2 = rag_svc.list_user_memories(owner_session=session2)
    assert len(list2) == 0

    # Delete memory
    del_ok = rag_svc.delete_user_memory(m1["memory_id"], owner_session=session1)
    assert del_ok is True
    assert len(rag_svc.list_user_memories(owner_session=session1)) == 0


def test_group_e_research_memory_crud():
    session_id = f"session-rmem-{uuid.uuid4().hex[:8]}"
    mem_id = rag_svc.add_research_memory(
        owner_session=session_id,
        topic="Transformer Optimization",
        finding="FlashAttention-2 achieves 2x speedup over standard attention without approximation.",
        source_url="https://arxiv.org/abs/2307.08691",
        confidence=0.95
    )
    assert mem_id is not None

    entries = rag_svc.get_research_memory(owner_session=session_id, query="FlashAttention")
    assert len(entries) >= 1
    assert "FlashAttention" in entries[0]["finding"]


# ============================================================================
# Test Group F: Security (SSRF & Filename Traversal)
# ============================================================================

def test_group_f_ssrf_protection():
    from backend.live_search import is_safe_external_url
    
    # Internal loopback / metadata / private ranges MUST BE REJECTED
    assert not is_safe_external_url("http://127.0.0.1:8000/api/keys")
    assert not is_safe_external_url("http://localhost:5432")
    assert not is_safe_external_url("http://169.254.169.254/latest/meta-data")
    assert not is_safe_external_url("http://10.0.0.1/admin")
    assert not is_safe_external_url("http://192.168.1.1/router")
    assert not is_safe_external_url("file:///etc/passwd")

    # Safe public domains MUST BE ALLOWED
    assert is_safe_external_url("https://en.wikipedia.org/wiki/Artificial_intelligence")


def test_group_f_filename_traversal():
    from backend.rag_service import safe_filename
    
    assert safe_filename("../../etc/passwd") == "passwd"
    assert safe_filename("..\\..\\windows\\system32\\cmd.exe") == "cmd.exe"
    assert ".." not in safe_filename("../sensitive.txt")


# ============================================================================
# Test Group G: Autonomous AI Scientist Workflow
# ============================================================================

def test_group_g_ai_scientist_pipeline_honesty():
    from backend.ai_scientist_pipeline import run_ai_scientist_pipeline, PipelineBudget
    from backend.step_trace import create_trace

    trace = create_trace("Trace for testing pipeline honesty")
    budget = PipelineBudget(
        max_llm_calls=4,
        max_tokens=3000,
        max_seconds=15.0,
        max_nodes=3,
        hypotheses=2,
        reflection_rounds=1
    )

    result = run_ai_scientist_pipeline(
        goal="Improve memory efficiency in distributed KV stores",
        trace=trace,
        budget=budget
    )

    assert result["status"] in ("ok", "budget_exhausted")
    assert "hypotheses" in result
    assert "what_was_not_done" in result
    # Must truthfully state no experiments or unverified code were executed
    assert any("No experiment" in s for s in result["what_was_not_done"])
