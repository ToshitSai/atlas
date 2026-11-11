"""Unit and Integration Tests for Atlas Advanced RAG Engine (Gen-3)."""

import os
import tempfile
import pytest
from pathlib import Path

from backend.advanced_rag import (
    AtlasVectorStore,
    ingest_document,
    crag_search,
    format_rag_citations,
    chunk_document_smart
)


def test_chunk_document_smart():
    text = (
        "# Introduction to Neural Networks\n\n"
        "Neural networks are computational models inspired by biological neural networks.\n"
        "They consist of interconnected neurons organized in layers.\n\n"
        "## Training Architecture\n\n"
        "```python\n"
        "def train_model(x, y):\n"
        "    return optimizer.step()\n"
        "```\n\n"
        "Backpropagation computes the gradient of the loss function with respect to weights.\n"
    )
    chunks = chunk_document_smart(text, chunk_size=200, chunk_overlap=40)
    assert len(chunks) >= 2
    assert any("Neural networks" in c["text"] for c in chunks)
    assert any("Backpropagation" in c["text"] or "train_model" in c["text"] for c in chunks)


def test_vector_store_in_memory_and_crud():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp_dir:
        db_path = Path(tmp_dir) / "test_rag.db"
        store = AtlasVectorStore(db_path=db_path)

        # Ingest document
        doc_id = store.add_document(
            title="Transformer Architecture",
            content="Attention is all you need. Transformers use self-attention mechanisms instead of RNNs.",
            doc_type="txt",
            owner_session="test-session-123",
            metadata={"author": "Vaswani et al."}
        )
        assert doc_id is not None

        # Verify listing
        docs = store.list_documents(owner_session="test-session-123")
        assert len(docs) == 1
        assert docs[0]["title"] == "Transformer Architecture"

        # Search
        results = store.hybrid_search("self-attention mechanisms", owner_session="test-session-123", top_k=2)
        assert len(results) > 0
        assert "Transformers" in results[0]["chunk"]["text"]

        # Formatted citations
        formatted = format_rag_citations(results)
        assert "Transformer Architecture" in formatted
        assert "Vaswani" in formatted

        # Knowledge Graph & Research Memory
        store.add_kg_triple("Transformer", "uses", "Self-Attention", source_doc_id=doc_id)
        kg_nodes = store.query_kg("Transformer")
        assert len(kg_nodes) == 1
        assert kg_nodes[0]["relation"] == "uses"
        assert kg_nodes[0]["target"] == "Self-Attention"

        store.add_research_memory(
            owner_session="test-session-123",
            topic="Attention",
            finding="Self-attention allows parallelization unlike RNN recurrence.",
            confidence=0.95
        )
        memories = store.get_research_memory(owner_session="test-session-123", query="parallelization")
        assert len(memories) == 1
        assert "parallelization" in memories[0]["finding"]

        # Delete document
        deleted = store.delete_document(doc_id, owner_session="test-session-123")
        assert deleted is True
        assert len(store.list_documents(owner_session="test-session-123")) == 0
        store.close()


def test_crag_search_grounding():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp_dir:
        db_path = Path(tmp_dir) / "test_crag.db"
        store = AtlasVectorStore(db_path=db_path)

        store.add_document(
            title="Atlas AI Specs",
            content="Atlas AI Gen-3 is developed by Toshit Sai Galam with high precision reasoning and local QLoRA inference on RTX 5050.",
            doc_type="txt",
            owner_session="session-456"
        )

        res = crag_search("Who created Atlas AI?", owner_session="session-456", vector_store=store)
        assert len(res) > 0
        assert "Toshit Sai Galam" in res[0]["chunk"]["text"]
        assert res[0].get("relevance_grade") in ("relevant", "ambiguous")
        store.close()
