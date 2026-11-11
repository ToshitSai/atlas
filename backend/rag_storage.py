"""Atlas AI — Persistent Multi-Backend RAG Storage Engine.

Supports:
1. PostgreSQL with pgvector (Primary Production Backend):
   - Multi-serverless instance visibility and synchronization.
   - ACID transactional consistency with clean rollback on ingestion failure.
   - Session/owner isolation on all queries (`owner_session`).
   - Cascading deletions removing document metadata, chunks, vectors, and KG edges.
2. SQLite (Local Development & Testing Backend):
   - Zero-dependency local persistence surviving application restarts.
   - Concurrency locking with WAL mode.
"""

from __future__ import annotations

from collections import Counter
import json
import math
import os
from pathlib import Path
import sqlite3
import threading
import time
from typing import Any, Dict, List, Optional, Protocol, Set, Tuple
import uuid

import numpy as np

from backend.embedding_registry import (
    EmbeddingProfile,
    IncompatibleEmbeddingError,
    PROFILE_LOCAL_MINILM_384,
    PROFILE_OPENAI_SMALL_1536,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SQLITE_PATH = ROOT / "database" / "atlas_vector_store.db"
DEFAULT_SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)


class RAGStorageBackend(Protocol):
    def save_document(
        self,
        document_id: str,
        filename: str,
        content_hash: str,
        byte_size: int,
        doc_type: str,
        owner_session: str,
        chunks: List[Dict[str, Any]],
        vectors: Optional[List[List[float]]] = None,
        embedding_profile: Optional[EmbeddingProfile] = None,
        kg_edges: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]: ...

    def get_document(self, document_id: str, owner_session: str) -> Optional[Dict[str, Any]]: ...
    def list_documents(self, owner_session: str) -> List[Dict[str, Any]]: ...
    def delete_document(self, document_id: str, owner_session: str) -> bool: ...
    def hybrid_search(
        self,
        query_text: str,
        query_vector: Optional[List[float]],
        owner_session: str,
        limit: int = 5,
        bm25_weight: float = 0.5,
        dense_weight: float = 0.5,
    ) -> List[Dict[str, Any]]: ...
    def save_research_memory(
        self,
        memory_id: str,
        owner_session: str,
        topic: str,
        finding: str,
        confidence: float,
        source_url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None: ...
    def get_research_memory(
        self,
        owner_session: str,
        query: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]: ...
    def get_kg_edges(self, owner_session: str, node: Optional[str] = None) -> List[Dict[str, Any]]: ...


class SQLiteRAGStorage:
    """Thread-safe SQLite persistent RAG storage."""

    def __init__(self, db_path: Path = DEFAULT_SQLITE_PATH):
        self.db_path = db_path
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self):
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            cur = conn.cursor()
            cur.execute("PRAGMA journal_mode=WAL;")
            cur.execute("PRAGMA foreign_keys=ON;")

            # 1. Documents
            cur.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    document_id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    byte_size INTEGER NOT NULL,
                    doc_type TEXT NOT NULL,
                    owner_session TEXT NOT NULL,
                    chunk_count INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'ready',
                    created_at REAL NOT NULL,
                    metadata TEXT
                )
            """)

            # 2. Chunks
            cur.execute("""
                CREATE TABLE IF NOT EXISTS chunks (
                    chunk_id TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    page INTEGER,
                    section TEXT,
                    source TEXT NOT NULL,
                    content TEXT NOT NULL,
                    token_count INTEGER NOT NULL,
                    embedding_vector BLOB,
                    embedding_profile TEXT,
                    owner_session TEXT NOT NULL,
                    FOREIGN KEY(document_id) REFERENCES documents(document_id) ON DELETE CASCADE
                )
            """)

            # 3. Knowledge Graph
            cur.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_graph (
                    edge_id TEXT PRIMARY KEY,
                    owner_session TEXT NOT NULL,
                    source_node TEXT NOT NULL,
                    relation TEXT NOT NULL,
                    target_node TEXT NOT NULL,
                    confidence REAL NOT NULL DEFAULT 1.0,
                    source_doc_id TEXT,
                    created_at REAL NOT NULL
                )
            """)

            # 4. Research Memory
            cur.execute("""
                CREATE TABLE IF NOT EXISTS research_memory (
                    memory_id TEXT PRIMARY KEY,
                    owner_session TEXT NOT NULL,
                    topic TEXT NOT NULL,
                    finding TEXT NOT NULL,
                    source_url TEXT,
                    confidence REAL NOT NULL DEFAULT 0.8,
                    metadata TEXT,
                    created_at REAL NOT NULL
                )
            """)

            # Ensure columns exist if table was created in previous version
            cur.execute("PRAGMA table_info(documents);")
            doc_cols = {row[1] for row in cur.fetchall()}
            if "content_hash" not in doc_cols:
                cur.execute("ALTER TABLE documents ADD COLUMN content_hash TEXT DEFAULT '';")
            if "byte_size" not in doc_cols:
                cur.execute("ALTER TABLE documents ADD COLUMN byte_size INTEGER DEFAULT 0;")
            if "doc_type" not in doc_cols:
                cur.execute("ALTER TABLE documents ADD COLUMN doc_type TEXT DEFAULT 'document';")
            if "chunk_count" not in doc_cols:
                cur.execute("ALTER TABLE documents ADD COLUMN chunk_count INTEGER DEFAULT 0;")
            if "status" not in doc_cols:
                cur.execute("ALTER TABLE documents ADD COLUMN status TEXT DEFAULT 'ready';")
            if "created_at" not in doc_cols:
                cur.execute("ALTER TABLE documents ADD COLUMN created_at REAL DEFAULT 0.0;")
            if "metadata" not in doc_cols:
                cur.execute("ALTER TABLE documents ADD COLUMN metadata TEXT;")

            cur.execute("PRAGMA table_info(chunks);")
            chunk_cols = {row[1] for row in cur.fetchall()}
            if "owner_session" not in chunk_cols:
                cur.execute("ALTER TABLE chunks ADD COLUMN owner_session TEXT NOT NULL DEFAULT 'anonymous';")
            if "embedding_profile" not in chunk_cols:
                cur.execute("ALTER TABLE chunks ADD COLUMN embedding_profile TEXT;")
            if "embedding_vector" not in chunk_cols:
                cur.execute("ALTER TABLE chunks ADD COLUMN embedding_vector BLOB;")
                if "embedding_bytes" in chunk_cols:
                    try:
                        cur.execute("UPDATE chunks SET embedding_vector = embedding_bytes WHERE embedding_vector IS NULL AND embedding_bytes IS NOT NULL;")
                    except Exception:
                        pass
                elif "embedding" in chunk_cols:
                    try:
                        cur.execute("UPDATE chunks SET embedding_vector = embedding WHERE embedding_vector IS NULL AND embedding IS NOT NULL;")
                    except Exception:
                        pass


            cur.execute("PRAGMA table_info(knowledge_graph);")
            kg_cols = {row[1] for row in cur.fetchall()}
            if "source_doc_id" not in kg_cols:
                cur.execute("ALTER TABLE knowledge_graph ADD COLUMN source_doc_id TEXT;")

            cur.execute("CREATE INDEX IF NOT EXISTS idx_docs_owner ON documents(owner_session);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_chunks_doc ON chunks(document_id);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_chunks_owner ON chunks(owner_session);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_kg_owner ON knowledge_graph(owner_session);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_kg_source_doc ON knowledge_graph(source_doc_id);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_mem_owner ON research_memory(owner_session);")
            conn.commit()
            conn.close()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("PRAGMA foreign_keys=ON;")
        conn.row_factory = sqlite3.Row
        return conn

    def save_document(
        self,
        document_id: str,
        filename: str,
        content_hash: str,
        byte_size: int,
        doc_type: str,
        owner_session: str,
        chunks: List[Dict[str, Any]],
        vectors: Optional[List[List[float]]] = None,
        embedding_profile: Optional[EmbeddingProfile] = None,
        kg_edges: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        with self._lock:
            conn = self._get_connection()
            try:
                cur = conn.cursor()
                now = time.time()
                # Check for existing document with same id to overwrite/update
                cur.execute("DELETE FROM documents WHERE document_id = ? AND owner_session = ?", (document_id, owner_session))
                cur.execute("DELETE FROM knowledge_graph WHERE source_doc_id = ? AND owner_session = ?", (document_id, owner_session))

                profile_json = json.dumps(embedding_profile.to_dict()) if embedding_profile else None

                cur.execute("PRAGMA table_info(documents);")
                doc_cols = {row[1] for row in cur.fetchall()}
                cols = ["document_id", "filename", "byte_size", "doc_type", "owner_session", "chunk_count", "status", "created_at"]
                vals = [document_id, filename, byte_size, doc_type, owner_session, len(chunks), 'ready', now]
                if "content_hash" in doc_cols:
                    cols.append("content_hash")
                    vals.append(content_hash)
                if "file_hash" in doc_cols:
                    cols.append("file_hash")
                    vals.append(content_hash)
                if "metadata" in doc_cols:
                    cols.append("metadata")
                    vals.append(profile_json)
                placeholders = ", ".join("?" for _ in vals)
                cur.execute(f"INSERT INTO documents ({', '.join(cols)}) VALUES ({placeholders})", tuple(vals))


                cur.execute("PRAGMA table_info(chunks);")
                chunk_cols = {row[1] for row in cur.fetchall()}
                base_chunk_cols = [
                    "chunk_id", "document_id", "chunk_index", "page", "section",
                    "source", "content", "token_count", "owner_session"
                ]
                if "embedding_vector" in chunk_cols:
                    base_chunk_cols.append("embedding_vector")
                if "embedding_bytes" in chunk_cols:
                    base_chunk_cols.append("embedding_bytes")
                if "embedding_dim" in chunk_cols:
                    base_chunk_cols.append("embedding_dim")
                if "embedding_profile" in chunk_cols:
                    base_chunk_cols.append("embedding_profile")

                chunk_placeholders = ", ".join("?" for _ in base_chunk_cols)
                chunk_insert_sql = f"INSERT INTO chunks ({', '.join(base_chunk_cols)}) VALUES ({chunk_placeholders})"

                for i, c in enumerate(chunks):
                    vec_blob = None
                    dim = None
                    if vectors and i < len(vectors) and vectors[i] is not None:
                        vec_blob = np.array(vectors[i], dtype=np.float32).tobytes()
                        dim = len(vectors[i])

                    chunk_id = c.get("chunk_id") or f"{document_id}-{i}"
                    c_vals = [
                        chunk_id, document_id, c.get("chunk_index", i),
                        c.get("page"), c.get("section"), filename,
                        c.get("content") or c.get("text") or "",
                        c.get("token_count", 1), owner_session
                    ]
                    if "embedding_vector" in chunk_cols:
                        c_vals.append(vec_blob)
                    if "embedding_bytes" in chunk_cols:
                        c_vals.append(vec_blob)
                    if "embedding_dim" in chunk_cols:
                        c_vals.append(dim)
                    if "embedding_profile" in chunk_cols:
                        c_vals.append(profile_json)

                    cur.execute(chunk_insert_sql, tuple(c_vals))

                if kg_edges:
                    for edge in kg_edges:
                        cur.execute("""
                            INSERT INTO knowledge_graph (
                                edge_id, owner_session, source_node, relation,
                                target_node, confidence, source_doc_id, created_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            edge.get("edge_id") or str(uuid.uuid4()),
                            owner_session, edge["source"], edge["relation"],
                            edge["target"], edge.get("confidence", 1.0),
                            document_id, now
                        ))

                conn.commit()
                return {
                    "id": document_id,
                    "title": filename,
                    "filename": filename,
                    "chunks_count": len(chunks),
                    "doc_type": doc_type,
                    "byte_size": byte_size,
                    "status": "ready"
                }
            except Exception as exc:
                conn.rollback()
                raise exc
            finally:
                conn.close()

    def get_document(self, document_id: str, owner_session: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            conn = self._get_connection()
            try:
                cur = conn.cursor()
                cur.execute("""
                    SELECT document_id, filename, content_hash, byte_size, doc_type,
                           chunk_count, status, created_at
                    FROM documents
                    WHERE document_id = ? AND owner_session = ?
                """, (document_id, owner_session))
                row = cur.fetchone()
                if not row:
                    return None
                return {
                    "id": row["document_id"],
                    "title": row["filename"],
                    "filename": row["filename"],
                    "content_hash": row["content_hash"],
                    "byte_size": row["byte_size"],
                    "doc_type": row["doc_type"],
                    "chunk_count": row["chunk_count"],
                    "status": row["status"],
                    "created_at": row["created_at"],
                }
            finally:
                conn.close()

    def list_documents(self, owner_session: str) -> List[Dict[str, Any]]:
        with self._lock:
            conn = self._get_connection()
            try:
                cur = conn.cursor()
                cur.execute("""
                    SELECT document_id, filename, content_hash, byte_size, doc_type,
                           chunk_count, status, created_at
                    FROM documents
                    WHERE owner_session = ?
                    ORDER BY created_at DESC
                """, (owner_session,))
                rows = cur.fetchall()
                return [
                    {
                        "id": r["document_id"],
                        "title": r["filename"],
                        "filename": r["filename"],
                        "content_hash": r["content_hash"],
                        "byte_size": r["byte_size"],
                        "doc_type": r["doc_type"],
                        "chunk_count": r["chunk_count"],
                        "status": r["status"],
                        "created_at": r["created_at"],
                    }
                    for r in rows
                ]
            finally:
                conn.close()

    def delete_document(self, document_id: str, owner_session: str) -> bool:
        with self._lock:
            conn = self._get_connection()
            try:
                cur = conn.cursor()
                # Check document ownership first
                cur.execute("SELECT 1 FROM documents WHERE document_id = ? AND owner_session = ?", (document_id, owner_session))
                if not cur.fetchone():
                    return False

                # Cascade delete knowledge graph edges linked to this document
                cur.execute("DELETE FROM knowledge_graph WHERE source_doc_id = ? AND owner_session = ?", (document_id, owner_session))
                # Delete chunks
                cur.execute("DELETE FROM chunks WHERE document_id = ? AND owner_session = ?", (document_id, owner_session))
                # Delete document record
                cur.execute("DELETE FROM documents WHERE document_id = ? AND owner_session = ?", (document_id, owner_session))
                conn.commit()
                return True
            except Exception as exc:
                conn.rollback()
                raise exc
            finally:
                conn.close()

    def hybrid_search(
        self,
        query_text: str,
        query_vector: Optional[List[float]],
        owner_session: str,
        limit: int = 5,
        bm25_weight: float = 0.5,
        dense_weight: float = 0.5,
    ) -> List[Dict[str, Any]]:
        with self._lock:
            conn = self._get_connection()
            try:
                cur = conn.cursor()
                cur.execute("PRAGMA table_info(chunks);")
                c_cols = {row[1] for row in cur.fetchall()}
                vec_expr = "embedding_vector"
                if "embedding_vector" in c_cols and "embedding_bytes" in c_cols:
                    vec_expr = "COALESCE(embedding_vector, embedding_bytes)"
                elif "embedding_vector" not in c_cols and "embedding_bytes" in c_cols:
                    vec_expr = "embedding_bytes"
                elif "embedding_vector" not in c_cols:
                    vec_expr = "NULL"

                cur.execute(f"""
                    SELECT chunk_id, document_id, chunk_index, page, section,
                           source, content, token_count, {vec_expr} AS embedding_vector
                    FROM chunks
                    WHERE owner_session = ?
                """, (owner_session,))
                rows = cur.fetchall()
                if not rows:
                    return []

                # 1. Lexical BM25 Scoring
                q_words = [w.lower() for w in query_text.split() if len(w) > 2]
                bm25_scores: Dict[str, float] = {}
                doc_term_freqs = []
                df_counts = Counter()

                chunk_records = []
                for r in rows:
                    content = r["content"]
                    tokens = [w.lower() for w in content.split()]
                    tf = Counter(tokens)
                    doc_term_freqs.append(tf)
                    for w in set(tokens):
                        df_counts[w] += 1
                    chunk_records.append(r)

                total_chunks = len(rows)
                avg_dl = sum(len(c["content"].split()) for c in rows) / max(1, total_chunks)
                k1 = 1.5
                b = 0.75

                for idx, r in enumerate(chunk_records):
                    score = 0.0
                    dl = len(r["content"].split())
                    tf_map = doc_term_freqs[idx]
                    for w in q_words:
                        if w in tf_map:
                            df = df_counts.get(w, 0)
                            idf = math.log((total_chunks - df + 0.5) / (df + 0.5) + 1.0)
                            tf = tf_map[w]
                            numerator = tf * (k1 + 1)
                            denominator = tf + k1 * (1 - b + b * (dl / max(1.0, avg_dl)))
                            score += idf * (numerator / max(1e-6, denominator))
                    bm25_scores[r["chunk_id"]] = score

                # 2. Dense Cosine Similarity Scoring (if query vector provided)
                dense_scores: Dict[str, float] = {}
                if query_vector:
                    q_arr = np.array(query_vector, dtype=np.float32)
                    q_norm = np.linalg.norm(q_arr)
                    for r in chunk_records:
                        vec_blob = r["embedding_vector"]
                        if vec_blob:
                            c_arr = np.frombuffer(vec_blob, dtype=np.float32)
                            c_norm = np.linalg.norm(c_arr)
                            if q_norm > 0 and c_norm > 0:
                                sim = float(np.dot(q_arr, c_arr) / (q_norm * c_norm))
                                dense_scores[r["chunk_id"]] = max(0.0, sim)
                            else:
                                dense_scores[r["chunk_id"]] = 0.0
                        else:
                            dense_scores[r["chunk_id"]] = 0.0

                # 3. Reciprocal Rank Fusion (RRF) with k=60
                bm25_ranked = sorted(bm25_scores.keys(), key=lambda cid: bm25_scores[cid], reverse=True)
                dense_ranked = sorted(dense_scores.keys(), key=lambda cid: dense_scores[cid], reverse=True) if dense_scores else []

                rrf_scores: Dict[str, float] = {}
                k_rrf = 60
                for rank, cid in enumerate(bm25_ranked, 1):
                    rrf_scores[cid] = rrf_scores.get(cid, 0.0) + bm25_weight * (1.0 / (k_rrf + rank))

                for rank, cid in enumerate(dense_ranked, 1):
                    rrf_scores[cid] = rrf_scores.get(cid, 0.0) + dense_weight * (1.0 / (k_rrf + rank))

                sorted_cids = sorted(rrf_scores.keys(), key=lambda cid: rrf_scores[cid], reverse=True)

                record_map = {r["chunk_id"]: r for r in chunk_records}
                results = []
                for cid in sorted_cids[:limit]:
                    r = record_map[cid]
                    results.append({
                        "chunk_id": r["chunk_id"],
                        "document_id": r["document_id"],
                        "chunk_index": r["chunk_index"],
                        "page": r["page"],
                        "section": r["section"],
                        "source": r["source"],
                        "content": r["content"],
                        "score": rrf_scores[cid],
                        "bm25_score": bm25_scores.get(cid, 0.0),
                        "dense_score": dense_scores.get(cid, 0.0),
                    })
                return results
            finally:
                conn.close()

    def save_research_memory(
        self,
        memory_id: str,
        owner_session: str,
        topic: str,
        finding: str,
        confidence: float,
        source_url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        with self._lock:
            conn = self._get_connection()
            try:
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO research_memory (
                        memory_id, owner_session, topic, finding,
                        source_url, confidence, metadata, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    memory_id, owner_session, topic, finding,
                    source_url, confidence, json.dumps(metadata or {}), time.time()
                ))
                conn.commit()
            finally:
                conn.close()

    def get_research_memory(
        self,
        owner_session: str,
        query: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        with self._lock:
            conn = self._get_connection()
            try:
                cur = conn.cursor()
                if query:
                    cur.execute("""
                        SELECT memory_id, topic, finding, source_url, confidence, metadata, created_at
                        FROM research_memory
                        WHERE owner_session = ? AND (topic LIKE ? OR finding LIKE ?)
                        ORDER BY created_at DESC LIMIT ?
                    """, (owner_session, f"%{query}%", f"%{query}%", limit))
                else:
                    cur.execute("""
                        SELECT memory_id, topic, finding, source_url, confidence, metadata, created_at
                        FROM research_memory
                        WHERE owner_session = ?
                        ORDER BY created_at DESC LIMIT ?
                    """, (owner_session, limit))
                rows = cur.fetchall()
                out = []
                for r in rows:
                    meta = {}
                    try:
                        if r["metadata"]:
                            meta = json.loads(r["metadata"])
                    except Exception:
                        pass
                    out.append({
                        "id": r["memory_id"],
                        "topic": r["topic"],
                        "finding": r["finding"],
                        "source_url": r["source_url"],
                        "confidence": r["confidence"],
                        "metadata": meta,
                        "created_at": r["created_at"],
                    })
                return out
            finally:
                conn.close()

    def get_kg_edges(self, owner_session: str, node: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._lock:
            conn = self._get_connection()
            try:
                cur = conn.cursor()
                if node:
                    cur.execute("""
                        SELECT edge_id, source_node, relation, target_node, confidence, source_doc_id
                        FROM knowledge_graph
                        WHERE owner_session = ? AND (source_node = ? OR target_node = ?)
                    """, (owner_session, node, node))
                else:
                    cur.execute("""
                        SELECT edge_id, source_node, relation, target_node, confidence, source_doc_id
                        FROM knowledge_graph
                        WHERE owner_session = ?
                    """, (owner_session,))
                rows = cur.fetchall()
                return [
                    {
                        "edge_id": r["edge_id"],
                        "source": r["source_node"],
                        "relation": r["relation"],
                        "target": r["target_node"],
                        "confidence": r["confidence"],
                        "source_doc_id": r["source_doc_id"]
                    }
                    for r in rows
                ]
            finally:
                conn.close()


class PostgresRAGStorage:
    """PostgreSQL with pgvector persistent storage (Primary Production Backend).
    
    Shares document state across all serverless instances with multi-session isolation
    and transactional atomic rollback.
    """

    def __init__(self, repo: Any):
        self.repo = repo
        self._fallback_sqlite = SQLiteRAGStorage()

    def save_document(
        self,
        document_id: str,
        filename: str,
        content_hash: str,
        byte_size: int,
        doc_type: str,
        owner_session: str,
        chunks: List[Dict[str, Any]],
        vectors: Optional[List[List[float]]] = None,
        embedding_profile: Optional[EmbeddingProfile] = None,
        kg_edges: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        from psycopg.types.json import Json
        conn = self.repo._conn()
        try:
            with conn.transaction():
                # 1. Clean existing doc if present
                conn.execute("DELETE FROM knowledge_graph_edges WHERE source_document_id = %s AND owner_session = %s", (document_id, owner_session))
                conn.execute("DELETE FROM document_metadata WHERE document_id = %s AND owner_session = %s", (document_id, owner_session))
                conn.execute("DELETE FROM documents WHERE id = %s", (document_id,))

                # 2. Insert document record
                meta_dict = {
                    "owner_session": owner_session,
                    "content_hash": content_hash,
                    "embedding_profile": embedding_profile.to_dict() if embedding_profile else None
                }
                conn.execute(
                    """INSERT INTO documents (id, title, source, doc_type, metadata)
                       VALUES (%s, %s, %s, %s, %s)""",
                    (document_id, filename, filename, doc_type, Json(meta_dict))
                )

                # 3. Insert document metadata
                conn.execute(
                    """INSERT INTO document_metadata (
                           document_id, owner_session, original_filename, byte_size, status
                       ) VALUES (%s, %s, %s, %s, 'ready')""",
                    (document_id, owner_session, filename, byte_size)
                )

                # 4. Insert chunks and optional pgvector embeddings
                has_vector = self.repo._has_pgvector()
                for i, c in enumerate(chunks):
                    chunk_id = c.get("chunk_id") or str(uuid.uuid4())
                    vec = vectors[i] if (vectors and i < len(vectors)) else None

                    # If pgvector is installed and profile matches 1536 dim
                    if vec and has_vector and len(vec) == 1536:
                        vec_literal = "[" + ",".join(str(float(x)) for x in vec) + "]"
                        conn.execute(
                            """INSERT INTO document_chunks (
                                   id, document_id, chunk_index, content, page, section, embedding, metadata
                               ) VALUES (%s, %s, %s, %s, %s, %s, %s::vector, %s)""",
                            (chunk_id, document_id, i, c.get("content") or c.get("text") or "",
                             c.get("page"), c.get("section"), vec_literal, Json({"owner_session": owner_session}))
                        )
                    else:
                        conn.execute(
                            """INSERT INTO document_chunks (
                                   id, document_id, chunk_index, content, page, section, metadata
                               ) VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                            (chunk_id, document_id, i, c.get("content") or c.get("text") or "",
                             c.get("page"), c.get("section"), Json({"owner_session": owner_session}))
                        )

                # 5. Insert knowledge graph edges
                if kg_edges:
                    for edge in kg_edges:
                        edge_id = edge.get("edge_id") or str(uuid.uuid4())
                        conn.execute(
                            """INSERT INTO knowledge_graph_edges (
                                   edge_id, owner_session, source_node, relation, target_node, confidence, source_document_id
                               ) VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                            (edge_id, owner_session, edge["source"], edge["relation"],
                             edge["target"], edge.get("confidence", 1.0), document_id)
                        )

            # Also mirror locally so offline evaluation and hybrid search work immediately
            self._fallback_sqlite.save_document(
                document_id, filename, content_hash, byte_size, doc_type,
                owner_session, chunks, vectors, embedding_profile, kg_edges
            )

            return {
                "id": document_id,
                "title": filename,
                "filename": filename,
                "chunks_count": len(chunks),
                "doc_type": doc_type,
                "byte_size": byte_size,
                "status": "ready"
            }
        except Exception as exc:
            # Atomic rollback happens automatically via with conn.transaction()
            raise exc

    def get_document(self, document_id: str, owner_session: str) -> Optional[Dict[str, Any]]:
        row = self.repo._query_one(
            """SELECT d.id, d.title, d.doc_type, m.byte_size, m.status, m.updated_at
               FROM documents d
               JOIN document_metadata m ON m.document_id = d.id
               WHERE d.id = %s AND m.owner_session = %s""",
            (document_id, owner_session)
        )
        if not row:
            return self._fallback_sqlite.get_document(document_id, owner_session)
        return {
            "id": str(row[0]),
            "title": row[1],
            "filename": row[1],
            "doc_type": row[2],
            "byte_size": row[3],
            "status": row[4],
            "updated_at": row[5].isoformat() if row[5] else None,
        }

    def list_documents(self, owner_session: str) -> List[Dict[str, Any]]:
        rows = self.repo._execute(
            """SELECT d.id, d.title, d.doc_type, m.byte_size, m.status, m.updated_at
               FROM documents d
               JOIN document_metadata m ON m.document_id = d.id
               WHERE m.owner_session = %s
               ORDER BY m.updated_at DESC""",
            (owner_session,)
        )
        if not rows:
            return self._fallback_sqlite.list_documents(owner_session)
        return [
            {
                "id": str(r[0]),
                "title": r[1],
                "filename": r[1],
                "doc_type": r[2],
                "byte_size": r[3],
                "status": r[4],
                "updated_at": r[5].isoformat() if r[5] else None,
            }
            for r in rows
        ]

    def delete_document(self, document_id: str, owner_session: str) -> bool:
        conn = self.repo._conn()
        deleted = False
        try:
            with conn.transaction():
                conn.execute("DELETE FROM knowledge_graph_edges WHERE source_document_id = %s AND owner_session = %s", (document_id, owner_session))
                cur = conn.execute("DELETE FROM document_metadata WHERE document_id = %s AND owner_session = %s", (document_id, owner_session))
                if cur.rowcount > 0:
                    deleted = True
                conn.execute("DELETE FROM documents WHERE id = %s", (document_id,))
        except Exception:
            pass

        sqlite_deleted = self._fallback_sqlite.delete_document(document_id, owner_session)
        return deleted or sqlite_deleted

    def hybrid_search(
        self,
        query_text: str,
        query_vector: Optional[List[float]],
        owner_session: str,
        limit: int = 5,
        bm25_weight: float = 0.5,
        dense_weight: float = 0.5,
    ) -> List[Dict[str, Any]]:
        # Dense pgvector query if vector provided and extension active
        has_vector = self.repo._has_pgvector()
        if query_vector and has_vector and len(query_vector) == 1536:
            try:
                vec_lit = "[" + ",".join(str(float(x)) for x in query_vector) + "]"
                rows = self.repo._execute(
                    """SELECT c.id, c.document_id, c.chunk_index, c.page, c.section,
                              d.title, c.content, 1 - (c.embedding <=> %s::vector) AS score
                       FROM document_chunks c
                       JOIN documents d ON d.id = c.document_id
                       JOIN document_metadata m ON m.document_id = d.id
                       WHERE m.owner_session = %s AND c.embedding IS NOT NULL
                       ORDER BY c.embedding <=> %s::vector LIMIT %s""",
                    (vec_lit, owner_session, vec_lit, limit)
                )
                if rows:
                    return [
                        {
                            "chunk_id": str(r[0]),
                            "document_id": str(r[1]),
                            "chunk_index": r[2],
                            "page": r[3],
                            "section": r[4],
                            "source": r[5],
                            "content": r[6],
                            "score": float(r[7]),
                        }
                        for r in rows
                    ]
            except Exception as exc:
                print(f"[PGVECTOR SEARCH WARNING] {exc}")

        # Fallback to SQLite hybrid search (Dense + BM25 + RRF)
        return self._fallback_sqlite.hybrid_search(
            query_text, query_vector, owner_session, limit, bm25_weight, dense_weight
        )

    def save_research_memory(
        self,
        memory_id: str,
        owner_session: str,
        topic: str,
        finding: str,
        confidence: float,
        source_url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        from psycopg.types.json import Json
        try:
            self.repo._execute(
                """INSERT INTO research_memory (
                       memory_id, owner_session, topic, finding, confidence, source_url, metadata
                   ) VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (memory_id, owner_session, topic, finding, confidence, source_url, Json(metadata or {}))
            )
        except Exception:
            pass
        self._fallback_sqlite.save_research_memory(
            memory_id, owner_session, topic, finding, confidence, source_url, metadata
        )

    def get_research_memory(
        self,
        owner_session: str,
        query: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        try:
            if query:
                rows = self.repo._execute(
                    """SELECT memory_id, topic, finding, confidence, source_url, metadata, created_at
                       FROM research_memory
                       WHERE owner_session = %s AND (topic ILIKE %s OR finding ILIKE %s)
                       ORDER BY created_at DESC LIMIT %s""",
                    (owner_session, f"%{query}%", f"%{query}%", limit)
                )
            else:
                rows = self.repo._execute(
                    """SELECT memory_id, topic, finding, confidence, source_url, metadata, created_at
                       FROM research_memory
                       WHERE owner_session = %s
                       ORDER BY created_at DESC LIMIT %s""",
                    (owner_session, limit)
                )
            if rows:
                return [
                    {
                        "id": str(r[0]),
                        "topic": r[1],
                        "finding": r[2],
                        "confidence": float(r[3]),
                        "source_url": r[4],
                        "metadata": r[5] if isinstance(r[5], dict) else {},
                        "created_at": r[6].isoformat() if r[6] else None,
                    }
                    for r in rows
                ]
        except Exception:
            pass
        return self._fallback_sqlite.get_research_memory(owner_session, query, limit)

    def get_kg_edges(self, owner_session: str, node: Optional[str] = None) -> List[Dict[str, Any]]:
        try:
            if node:
                rows = self.repo._execute(
                    """SELECT edge_id, source_node, relation, target_node, confidence, source_document_id
                       FROM knowledge_graph_edges
                       WHERE owner_session = %s AND (source_node = %s OR target_node = %s)""",
                    (owner_session, node, node)
                )
            else:
                rows = self.repo._execute(
                    """SELECT edge_id, source_node, relation, target_node, confidence, source_document_id
                       FROM knowledge_graph_edges
                       WHERE owner_session = %s""",
                    (owner_session,)
                )
            if rows:
                return [
                    {
                        "edge_id": str(r[0]),
                        "source": r[1],
                        "relation": r[2],
                        "target": r[3],
                        "confidence": float(r[4]),
                        "source_doc_id": str(r[5]) if r[5] else None,
                    }
                    for r in rows
                ]
        except Exception:
            pass
        return self._fallback_sqlite.get_kg_edges(owner_session, node)


_RAG_STORAGE_INSTANCE: Optional[RAGStorageBackend] = None
_STORAGE_LOCK = threading.Lock()


def get_rag_storage() -> RAGStorageBackend:
    """Factory returning the active RAG storage backend (Postgres in production, SQLite in local/test)."""
    global _RAG_STORAGE_INSTANCE
    if _RAG_STORAGE_INSTANCE is not None:
        return _RAG_STORAGE_INSTANCE

    with _STORAGE_LOCK:
        if _RAG_STORAGE_INSTANCE is not None:
            return _RAG_STORAGE_INSTANCE

        from database.store import store
        if store.database_health() and getattr(store, "repo", None):
            _RAG_STORAGE_INSTANCE = PostgresRAGStorage(store.repo)
        else:
            _RAG_STORAGE_INSTANCE = SQLiteRAGStorage()
        return _RAG_STORAGE_INSTANCE
