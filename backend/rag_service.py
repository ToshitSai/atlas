"""Atlas AI — Authoritative Production RAG Service Interface.

Provides a unified, consistent service interface for both document ingestion routes
and conversational retrieval. Handles multi-format extraction, chunking, embedding,
storage synchronization, citation synthesis, and knowledge graph persistence.
"""

from __future__ import annotations

import collections
import csv
import hashlib
import io
import json
import os
import re
import time
from typing import Any, Dict, List, Optional, Set, Tuple
import uuid

from backend.document_extractors import (
    ALL_SUPPORTED_EXTENSIONS,
    MAX_FILE_BYTES,
    clean_text,
    extract_document_or_image,
)
from backend.embedding_registry import (
    EmbeddingProfile,
    EmbeddingProviderUnavailableError,
    registry,
)
from backend.rag_storage import (
    RAGStorageBackend,
    get_rag_storage,
)

SUPPORTED_EXTENSIONS = ALL_SUPPORTED_EXTENSIONS


def safe_filename(name: str) -> str:
    name = os.path.basename((name or "").replace("\\", "/"))
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._")
    return name[:180] or "document"


def compute_file_sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def store_original_file(document_id: str, filename: str, content: bytes, owner_session: str) -> str:
    """Store the original uploaded document/image securely."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    storage_dir = os.path.join(base_dir, "data", "storage", safe_filename(owner_session))
    os.makedirs(storage_dir, exist_ok=True)
    target_path = os.path.join(storage_dir, f"{document_id}_{safe_filename(filename)}")
    with open(target_path, "wb") as f:
        f.write(content)
    return target_path


def delete_stored_file(document_id: str, owner_session: str) -> None:
    """Remove stored physical file from data/storage if present."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    storage_dir = os.path.join(base_dir, "data", "storage", safe_filename(owner_session))
    if os.path.exists(storage_dir):
        for f in os.listdir(storage_dir):
            if f.startswith(f"{document_id}_"):
                try:
                    os.remove(os.path.join(storage_dir, f))
                except Exception:
                    pass


def extract_document_text(filename: str, content: bytes, owner_session: Optional[str] = None) -> List[Dict[str, Any]]:
    """Safely extracts text and sections from all supported document and image formats."""
    sections, _ = extract_document_or_image(filename, content, owner_session=owner_session)
    return sections


# ============================================================================
# Smart Structure-Aware Chunking
# ============================================================================

def chunk_document_smart(
    sections: List[Dict[str, Any]],
    document_id: str,
    source_filename: str,
    chunk_size_chars: int = 1200,
    chunk_overlap_chars: int = 200,
) -> List[Dict[str, Any]]:
    """Chunks text while respecting heading, paragraph, and table boundaries."""
    chunks: List[Dict[str, Any]] = []
    chunk_idx = 0

    for sec in sections:
        page = sec.get("page")
        section_title = sec.get("section") or "General"
        raw_text = sec.get("text") or ""

        # Break text into paragraphs or logical blocks
        blocks = re.split(r"\n{2,}", raw_text)
        current_buf: List[str] = []
        current_len = 0

        for block in blocks:
            b_clean = block.strip()
            if not b_clean:
                continue

            m_h = re.match(r"^(#{1,4})\s+(.+)", b_clean)
            if m_h:
                section_title = m_h.group(2).strip()

            if current_len + len(b_clean) > chunk_size_chars and current_buf:
                chunk_text = "\n\n".join(current_buf).strip()
                chunks.append({
                    "chunk_id": f"{document_id}-{chunk_idx}",
                    "document_id": document_id,
                    "chunk_index": chunk_idx,
                    "page": page,
                    "section": section_title,
                    "source": source_filename,
                    "content": chunk_text,
                    "text": chunk_text,
                    "token_count": max(1, len(chunk_text) // 4)
                })
                chunk_idx += 1

                overlap_text = chunk_text[-chunk_overlap_chars:]
                current_buf = [overlap_text] if len(overlap_text) > 30 else []
                current_len = sum(len(x) for x in current_buf)

            current_buf.append(b_clean)
            current_len += len(b_clean)

        if current_buf:
            chunk_text = "\n\n".join(current_buf).strip()
            if chunk_text:
                chunks.append({
                    "chunk_id": f"{document_id}-{chunk_idx}",
                    "document_id": document_id,
                    "chunk_index": chunk_idx,
                    "page": page,
                    "section": section_title,
                    "source": source_filename,
                    "content": chunk_text,
                    "text": chunk_text,
                    "token_count": max(1, len(chunk_text) // 4)
                })
                chunk_idx += 1

    return chunks


def extract_kg_relations(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Extracts lightweight entity relationships from chunk headers and text."""
    edges: List[Dict[str, Any]] = []
    seen = set()
    relation_patterns = [
        r"([A-Z][a-zA-Z0-9_\s]{2,25})\s+(?:is defined as|is a|is an|refers to)\s+([A-Z][a-zA-Z0-9_\s]{2,35})",
        r"([A-Z][a-zA-Z0-9_\s]{2,25})\s+(?:uses|implements|supports|enables|depends on)\s+([A-Z][a-zA-Z0-9_\s]{2,35})",
        r"([A-Z][a-zA-Z0-9_\s]{2,25})\s+(?:consists of|contains|includes)\s+([A-Z][a-zA-Z0-9_\s]{2,35})"
    ]

    for chunk in chunks[:15]:
        txt = chunk.get("content", "")
        for pat in relation_patterns:
            matches = re.findall(pat, txt)
            for s, t in matches:
                s_c = s.strip()
                t_c = t.strip()
                if s_c.lower() == t_c.lower() or len(s_c) > 40 or len(t_c) > 40:
                    continue
                pair_key = (s_c.lower(), t_c.lower())
                if pair_key not in seen:
                    seen.add(pair_key)
                    edges.append({
                        "source": s_c,
                        "relation": "RELATES_TO",
                        "target": t_c,
                        "confidence": 0.85
                    })
                if len(edges) >= 20:
                    return edges
    return edges


# ============================================================================
# Main Service Interface
# ============================================================================

class RAGService:
    """Unified RAG service orchestrator."""

    def __init__(self, storage: Optional[RAGStorageBackend] = None):
        self._storage = storage

    @property
    def storage(self) -> RAGStorageBackend:
        if self._storage is None:
            self._storage = get_rag_storage()
        return self._storage

    def ingest_document(
        self,
        filename: str,
        content: bytes,
        owner_session: str,
        workflow: str = "knowledge_base"
    ) -> Dict[str, Any]:
        """Ingest, extract, chunk, embed, and store document or image with transactional consistency.
        
        Never displays a document as ready until extraction, chunking, and persistence succeed.
        """
        clean_name = safe_filename(filename)
        content_hash = compute_file_sha256(content)
        byte_size = len(content)
        doc_type = os.path.splitext(clean_name)[1].lstrip(".") or "document"
        doc_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{owner_session}:{content_hash}"))

        # 1. Multi-format extraction (documents + multimodal images)
        sections, extra_meta = extract_document_or_image(clean_name, content, owner_session=owner_session)

        # 2. Secure original file storage
        try:
            store_original_file(doc_id, clean_name, content, owner_session)
        except Exception as store_err:
            print(f"[RAG STORAGE WARNING] Failed to write original file: {store_err}")

        # 3. Structure-aware chunking
        chunks = chunk_document_smart(sections, doc_id, clean_name)
        if not chunks:
            raise ValueError("No extractable chunks found in document or image.")

        # 4. Real semantic vector generation
        profile = registry.resolve_default_profile()
        chunk_texts = [c["content"] for c in chunks]
        vectors = None
        try:
            vectors = registry.generate_embeddings(chunk_texts, profile=profile)
        except EmbeddingProviderUnavailableError as err:
            # When semantic provider is not configured, vectors remain None.
            # Lexical BM25 search will still index tokens honestly without fake vectors!
            print(f"[RAG Ingestion Notice] Semantic vectors omitted: {err}")
            vectors = None

        # 5. Extract knowledge graph edges
        kg_edges = extract_kg_relations(chunks)

        # 6. Atomic save into persistent storage (Postgres or SQLite)
        doc_record = self.storage.save_document(
            document_id=doc_id,
            filename=clean_name,
            content_hash=content_hash,
            byte_size=byte_size,
            doc_type=doc_type,
            owner_session=owner_session,
            chunks=chunks,
            vectors=vectors,
            embedding_profile=profile if vectors else None,
            kg_edges=kg_edges,
        )

        doc_record["is_image"] = extra_meta.get("is_image", False)
        doc_record["workflow"] = workflow
        if extra_meta.get("ocr_text"):
            doc_record["ocr_text"] = extra_meta["ocr_text"]
        if extra_meta.get("visual_description"):
            doc_record["visual_description"] = extra_meta["visual_description"]
        if extra_meta.get("image_type"):
            doc_record["image_type"] = extra_meta["image_type"]

        return doc_record

    def retrieve_context(
        self,
        query: str,
        owner_session: str,
        limit: int = 4,
        rag_mode: str = "auto"
    ) -> Dict[str, Any]:
        """Retrieve authoritative document evidence for a user query."""
        if rag_mode == "off":
            return {"active": False, "chunks": [], "context_text": "", "citations": []}

        # Check if this owner has any indexed documents
        user_docs = self.storage.list_documents(owner_session=owner_session)
        if not user_docs:
            return {"active": False, "chunks": [], "context_text": "", "citations": []}

        # Generate query vector if provider is available
        profile = registry.resolve_default_profile()
        query_vector = None
        try:
            vecs = registry.generate_embeddings([query], profile=profile)
            if vecs:
                query_vector = vecs[0]
        except EmbeddingProviderUnavailableError:
            query_vector = None

        # Execute hybrid search
        is_comparison = any(w in query.lower() for w in ("compare", "comparison", "contrast", "both", "all", "versus", "vs", "difference", "differences"))
        search_limit = max(limit * 2, len(user_docs) * 3) if is_comparison else limit
        hits = self.storage.hybrid_search(
            query_text=query,
            query_vector=query_vector,
            owner_session=owner_session,
            limit=search_limit
        )

        if not hits:
            return {"active": True, "chunks": [], "context_text": "", "citations": []}

        # Corrective RAG (CRAG) check: verify at least one query term or semantic overlap
        q_words = set(re.findall(r"\w{3,}", query.lower()))
        filtered_hits = []
        for h in hits:
            content_lower = h["content"].lower()
            overlap = any(w in content_lower for w in q_words)
            if overlap or h.get("dense_score", 0.0) > 0.30:
                filtered_hits.append(h)

        if not filtered_hits and rag_mode == "auto":
            # In auto mode, if retrieval confidence is low, don't force unrelated context
            return {"active": True, "chunks": [], "context_text": "", "citations": []}

        if is_comparison and len(user_docs) > 1:
            # Multi-document diversity: group hits by document_id so every document is represented
            doc_groups = collections.defaultdict(list)
            for h in (filtered_hits or hits):
                doc_groups[h.get("document_id")].append(h)
            diverse_hits = []
            for round_idx in range(4):
                for d_id, doc_hits in doc_groups.items():
                    if round_idx < len(doc_hits):
                        diverse_hits.append(doc_hits[round_idx])
            active_hits = diverse_hits if diverse_hits else (filtered_hits or hits[:limit])
        else:
            active_hits = (filtered_hits or hits)[:limit]

        # Format clean, isolated evidence blocks protecting against prompt injection
        evidence_blocks = []
        citations = []
        for idx, h in enumerate(active_hits, 1):
            source_file = h.get("source") or "document"
            page_info = f" (Page {h['page']})" if h.get("page") else ""
            section_info = f" [Section: {h['section']}]" if h.get("section") else ""
            evidence_blocks.append(
                f'<document_evidence id="{idx}" source="{source_file}{page_info}" section="{h.get("section") or "Text"}">\n'
                f'{h["content"]}\n'
                f'</document_evidence>'
            )
            citations.append({
                "id": str(idx),
                "title": f"{source_file}{page_info}{section_info}",
                "url": f"document://{h['document_id']}?chunk={h['chunk_index']}",
                "source": source_file,
                "page": h.get("page"),
                "snippet": h["content"][:240] + ("..." if len(h["content"]) > 240 else ""),
                "type": "document"
            })

        context_text = "\n\n".join(evidence_blocks)

        return {
            "active": True,
            "chunks": active_hits,
            "context_text": context_text,
            "citations": citations,
            "total_documents": len(user_docs)
        }

    def list_documents(self, owner_session: str) -> List[Dict[str, Any]]:
        return self.storage.list_documents(owner_session=owner_session)

    def get_document(self, document_id: str, owner_session: str) -> Optional[Dict[str, Any]]:
        return self.storage.get_document(document_id=document_id, owner_session=owner_session)

    def delete_document(self, document_id: str, owner_session: str) -> bool:
        delete_stored_file(document_id, owner_session)
        return self.storage.delete_document(document_id=document_id, owner_session=owner_session)

    def get_research_memory(self, owner_session: str, query: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        return self.storage.get_research_memory(owner_session=owner_session, query=query, limit=limit)

    def add_research_memory(
        self,
        owner_session: str,
        topic: str,
        finding: str,
        source_url: Optional[str] = None,
        confidence: float = 0.8,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        memory_id = str(uuid.uuid4())
        self.storage.save_research_memory(
            memory_id=memory_id,
            owner_session=owner_session,
            topic=topic,
            finding=finding,
            confidence=confidence,
            source_url=source_url,
            metadata=metadata
        )
        return memory_id

    def save_user_memory(
        self,
        owner_session: str,
        category: str,
        content: str,
        confidence: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None,
        memory_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        mem_id = memory_id or str(uuid.uuid4())
        return self.storage.save_user_memory(
            memory_id=mem_id,
            owner_session=owner_session,
            category=category,
            content=content,
            confidence=confidence,
            metadata=metadata or {},
        )

    def list_user_memories(
        self,
        owner_session: str,
        category: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        return self.storage.list_user_memories(owner_session=owner_session, category=category)

    def delete_user_memory(
        self,
        memory_id: str,
        owner_session: str,
    ) -> bool:
        return self.storage.delete_user_memory(memory_id=memory_id, owner_session=owner_session)


service = RAGService()
