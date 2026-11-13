"""Gen-3.3.10 Mandatory End-to-End Test Suite.

Tests:
TEST A — Previous README versus new resume (No stale document selection)
TEST B — Multiple current attachments (Fair multi-document evidence)
TEST C — Previous conversation context (Anaphora & follow-up context)
TEST D — Unrelated document isolation (Irrelevant files do not contaminate)
TEST E — Missing information handling (Honestly states missing, no hallucinations)
TEST F — Session isolation (Strict cross-session privacy)
"""

import os
import sys
import pytest

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import backend.config
from backend.rag_service import service as rag_svc
from backend.intent_router import handle_intent_message
from backend.resume_analyzer import (
    parse_resume_content, match_roles_for_resume,
    identify_skill_gaps, generate_resume_advice_markdown
)

README_CONTENT = """# React + Vite Application Template

This template provides a minimal setup to get React working in Vite with HMR and ESLint rules.

Currently, two official plugins are available:
- @vitejs/plugin-react uses Babel for Fast Refresh
- @vitejs/plugin-react-swc uses SWC for Fast Refresh

## Expanding the ESLint configuration
If you are developing a production application, we recommend updating the configuration.
""".encode("utf-8")

RESUME_CONTENT = """TOSHIT SAI GALAM
Email: toshit@example.com | GitHub: github.com/toshitsai | LinkedIn: linkedin.com/in/toshitsai

EDUCATION
Bachelor of Technology in Computer Science and Engineering
CGPA: 8.9 / 10.0 (2022 - 2026)

TECHNICAL SKILLS
- Programming Languages: Python, JavaScript, TypeScript, C++, SQL
- AI & Machine Learning: PyTorch, TensorFlow, Scikit-Learn, Transformers, Large Language Models (LLMs), RAG, Prompt Engineering, LangChain
- Web Development: React.js, Tailwind CSS, FastAPI, Node.js, REST APIs
- Databases & Cloud: PostgreSQL, SQLite, Redis, Git, Linux, Vercel

PROJECTS
1. Autonomous AI Research Agent:
Built an end-to-end autonomous research platform using Python, PyTorch, and FastAPI. Implemented hybrid RAG with BM25 and dense embeddings, real-time SSE streaming, and LLM fine-tuning via QLoRA.
2. GenAI Document Analyzer:
Created a multimodal document retrieval system with React frontend and LangChain backend. Integrated OCR and vector similarity search.

CERTIFICATIONS
- Anthropic Prompt Engineering Certification
- DeepLearning.AI Generative AI with Large Language Models
""".encode("utf-8")

CERTIFICATE_CONTENT = """CERTIFICATE OF ACCOMPLISHMENT
This is to certify that Toshit Sai Galam has successfully completed:
AI Fluency: AI Capabilities & Limitations
Issued by Anthropic & DeepLearning.AI
Topics: Prompt Engineering, LLM Alignment, Generative AI Evaluation
""".encode("utf-8")

SESSION_A = "test_gen3310_session_alpha"
SESSION_B = "test_gen3310_session_beta"


@pytest.fixture(autouse=True)
def cleanup():
    """Ensure clean test sessions before and after."""
    for sess in (SESSION_A, SESSION_B):
        try:
            docs = rag_svc.list_documents(owner_session=sess)
            for d in docs:
                rag_svc.delete_document(d["id"], owner_session=sess)
        except Exception:
            pass
    yield
    for sess in (SESSION_A, SESSION_B):
        try:
            docs = rag_svc.list_documents(owner_session=sess)
            for d in docs:
                rag_svc.delete_document(d["id"], owner_session=sess)
        except Exception:
            pass


def test_scenario_a_previous_readme_vs_new_resume():
    """TEST A: Previous README vs new resume.

    1. Upload README.md.
    2. Ask 'What is this?' -> Verify README is explained.
    3. Upload a new resume (TOSHIT_SAI_GALAM_RESUME.pdf).
    4. Ask 'Based on my resume what roles can I apply?'
    5. Verify that the resume is used and README is NOT cited!
    """
    # 1. Ingest README.md
    readme_doc = rag_svc.ingest_document(
        filename="README.md",
        content=README_CONTENT,
        owner_session=SESSION_A,
        workflow="chat_attachment"
    )

    # 2. Ask "What is this?" with README attachment
    res_step1 = handle_intent_message(
        "What is this?",
        session_id=SESSION_A,
        owner_session=SESSION_A,
        attachments=[{"document_id": readme_doc["id"], "filename": "README.md"}]
    )
    assert res_step1.get("response")
    assert "README" in str(res_step1.get("sources", [{}])[0].get("source", "")) or "README" in res_step1["response"]
    assert "React" in res_step1["response"] or "Vite" in res_step1["response"]

    # 3. Ingest Resume
    resume_doc = rag_svc.ingest_document(
        filename="TOSHIT_SAI_GALAM_RESUME.pdf",
        content=RESUME_CONTENT,
        owner_session=SESSION_A,
        workflow="chat_attachment"
    )

    # 4. Ask "Based on my resume what roles can I apply?" with Resume attachment
    res_step2 = handle_intent_message(
        "Based on my resume what roles can I apply?",
        session_id=SESSION_A,
        owner_session=SESSION_A,
        attachments=[{"document_id": resume_doc["id"], "filename": "TOSHIT_SAI_GALAM_RESUME.pdf"}],
        conversation_history=[
            {"role": "user", "content": "What is this?", "attachments": [{"document_id": readme_doc["id"], "filename": "README.md"}]},
            {"role": "assistant", "content": res_step1["response"]}
        ]
    )

    # 5. Verify Resume is used and README is NOT cited!
    resp_text = res_step2.get("response", "")
    sources = res_step2.get("sources", [])
    cited_files = [s.get("source") for s in sources if isinstance(s, dict)]

    # README must NOT be in cited sources
    assert "README.md" not in cited_files, f"Stale README.md was cited: {cited_files}"
    assert "TOSHIT_SAI_GALAM_RESUME.pdf" in cited_files, f"Resume was not cited: {cited_files}"

    # Response must analyze resume roles
    assert any(term in resp_text.lower() for term in ("generative ai", "ai/ml", "machine learning", "intern", "developer", "roles"))
    assert "does not contain resume information" not in resp_text.lower()
    assert "the provided document (readme.md) does not contain" not in resp_text.lower()

    # Diagnostics verification
    diag = res_step2.get("retrievalDiagnostics", {})
    assert diag.get("currentAttachmentsPrioritized") is True
    assert diag.get("priorityTier") == 1
    assert "TOSHIT_SAI_GALAM_RESUME.pdf" in diag.get("retrievedFilenames", [])
    assert "README.md" not in diag.get("retrievedFilenames", [])


def test_scenario_b_multiple_current_attachments():
    """TEST B: Multiple current attachments.

    Upload resume.pdf and certificate.pdf.
    Ask 'Which roles fit my resume and which certificates are relevant?'
    Verify both files are used appropriately.
    """
    resume_doc = rag_svc.ingest_document(
        filename="resume.pdf",
        content=RESUME_CONTENT,
        owner_session=SESSION_A,
        workflow="chat_attachment"
    )
    cert_doc = rag_svc.ingest_document(
        filename="certificates.pdf",
        content=CERTIFICATE_CONTENT,
        owner_session=SESSION_A,
        workflow="chat_attachment"
    )

    res = handle_intent_message(
        "Which roles fit my resume and which certificates are relevant?",
        session_id=SESSION_A,
        owner_session=SESSION_A,
        attachments=[
            {"document_id": resume_doc["id"], "filename": "resume.pdf"},
            {"document_id": cert_doc["id"], "filename": "certificates.pdf"}
        ]
    )

    sources = res.get("sources", [])
    cited_files = {s.get("source") for s in sources if isinstance(s, dict)}

    # Both documents must be represented
    assert "resume.pdf" in cited_files
    assert "certificates.pdf" in cited_files

    diag = res.get("retrievalDiagnostics", {})
    assert diag.get("priorityTier") == 1
    assert len(diag.get("retrievedDocumentIds", [])) >= 2


def test_scenario_c_previous_conversation_context():
    """TEST C: Previous conversation context.

    Turn 1: Ask about uploaded resume.
    Turn 2: Ask follow-up question without re-attaching.
    Verify previous document remains available and is used (Priority 2).
    """
    resume_doc = rag_svc.ingest_document(
        filename="TOSHIT_SAI_RESUME.pdf",
        content=RESUME_CONTENT,
        owner_session=SESSION_A,
        workflow="chat_attachment"
    )

    # Turn 1
    res1 = handle_intent_message(
        "Based on my resume what roles can I apply?",
        session_id=SESSION_A,
        owner_session=SESSION_A,
        attachments=[{"document_id": resume_doc["id"], "filename": "TOSHIT_SAI_RESUME.pdf"}]
    )

    # Turn 2: Follow-up without re-attaching
    res2 = handle_intent_message(
        "What are my key skills mentioned in it?",
        session_id=SESSION_A,
        owner_session=SESSION_A,
        conversation_history=[
            {"role": "user", "content": "Based on my resume what roles can I apply?", "attachments": [{"document_id": resume_doc["id"], "filename": "TOSHIT_SAI_RESUME.pdf"}]},
            {"role": "assistant", "content": res1.get("response", "")}
        ]
    )

    sources = res2.get("sources", [])
    cited_files = [s.get("source") for s in sources if isinstance(s, dict)]
    assert "TOSHIT_SAI_RESUME.pdf" in cited_files

    diag = res2.get("retrievalDiagnostics", {})
    assert diag.get("priorityTier") == 2
    assert diag.get("previousContextReused") is True


def test_scenario_d_unrelated_document_isolation():
    """TEST D: Unrelated document isolation.

    Upload an unrelated file (financial_report.txt).
    Then upload a resume and ask about it.
    Verify financial_report is NOT cited and does not contaminate the response.
    """
    unrelated_doc = rag_svc.ingest_document(
        filename="financial_report.txt",
        content="Q3 Revenue was $4.2M with EBITDA of 18%.".encode("utf-8"),
        owner_session=SESSION_A,
        workflow="knowledge_base"
    )
    resume_doc = rag_svc.ingest_document(
        filename="candidate_resume.pdf",
        content=RESUME_CONTENT,
        owner_session=SESSION_A,
        workflow="chat_attachment"
    )

    res = handle_intent_message(
        "Based on my resume what roles can I apply?",
        session_id=SESSION_A,
        owner_session=SESSION_A,
        attachments=[{"document_id": resume_doc["id"], "filename": "candidate_resume.pdf"}]
    )

    sources = res.get("sources", [])
    cited_files = [s.get("source") for s in sources if isinstance(s, dict)]
    assert "financial_report.txt" not in cited_files
    assert "candidate_resume.pdf" in cited_files


def test_scenario_e_missing_information():
    """TEST E: Missing information handling.

    Ask a question about something not in the resume (e.g. driving license or SAT score).
    Atlas must state the information is not present rather than inventing facts.
    """
    resume_doc = rag_svc.ingest_document(
        filename="candidate_resume.pdf",
        content=RESUME_CONTENT,
        owner_session=SESSION_A,
        workflow="chat_attachment"
    )

    res = handle_intent_message(
        "What is my driving license number?",
        session_id=SESSION_A,
        owner_session=SESSION_A,
        attachments=[{"document_id": resume_doc["id"], "filename": "candidate_resume.pdf"}]
    )

    resp_text = res.get("response", "").lower()
    assert any(term in resp_text for term in ("does not contain", "not mention", "no information", "not found"))
    assert "candidate_resume.pdf" in res.get("response", "")


def test_scenario_f_session_isolation():
    """TEST F: Session isolation.

    Upload resume in Session A.
    Query from Session B (different owner_session).
    Session B must NOT be able to retrieve Session A's documents!
    """
    rag_svc.ingest_document(
        filename="private_resume.pdf",
        content=RESUME_CONTENT,
        owner_session=SESSION_A,
        workflow="chat_attachment"
    )

    # Session B queries
    res_b = handle_intent_message(
        "What are my skills?",
        session_id=SESSION_B,
        owner_session=SESSION_B
    )

    sources_b = res_b.get("sources", [])
    cited_files_b = [s.get("source") for s in sources_b if isinstance(s, dict)]
    assert "private_resume.pdf" not in cited_files_b
    assert "private_resume.pdf" not in res_b.get("response", "")


def test_resume_analyzer_parsing_and_roles():
    """Unit test for the standalone resume analyzer module."""
    parsed = parse_resume_content(RESUME_CONTENT.decode("utf-8"), filename="TOSHIT_SAI_GALAM_RESUME.pdf")
    assert parsed["candidate_name"] == "Toshit Sai Galam"
    assert "Python" in parsed["skills"]["ai_ml"]
    assert "Pytorch" in parsed["skills"]["ai_ml"] or "PyTorch" in parsed["skills"]["ai_ml"]
    assert "React" in parsed["skills"]["frontend"] or "React.Js" in parsed["skills"]["frontend"]

    roles = match_roles_for_resume(parsed)
    assert len(roles) >= 2
    assert any("Generative AI" in r["title"] or "AI/ML" in r["title"] for r in roles)

    md = generate_resume_advice_markdown(parsed, query="what roles can I apply", source_filename="TOSHIT_SAI_GALAM_RESUME.pdf")
    assert "### 🎯 Roles that match your resume" in md
    assert "### ⭐ Best option to target first" in md
    assert "### 📈 Skills to improve" in md
    assert "### 🔗 Useful opportunities" in md
