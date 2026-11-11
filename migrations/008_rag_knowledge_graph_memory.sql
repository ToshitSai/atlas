-- 008_rag_knowledge_graph_memory.sql
-- Persistent Knowledge Graph and Research Memory tables for Atlas RAG.
-- Non-destructive migration; safely creates relational tables and indexes.

CREATE TABLE IF NOT EXISTS knowledge_graph_edges (
    edge_id TEXT PRIMARY KEY,
    owner_session TEXT NOT NULL,
    source_node TEXT NOT NULL,
    relation TEXT NOT NULL,
    target_node TEXT NOT NULL,
    confidence REAL NOT NULL DEFAULT 1.0,
    source_document_id TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_kg_edges_owner ON knowledge_graph_edges(owner_session);
CREATE INDEX IF NOT EXISTS idx_kg_edges_source_doc ON knowledge_graph_edges(source_document_id);
CREATE INDEX IF NOT EXISTS idx_kg_edges_nodes ON knowledge_graph_edges(source_node, target_node);

CREATE TABLE IF NOT EXISTS research_memory (
    memory_id TEXT PRIMARY KEY,
    owner_session TEXT NOT NULL,
    topic TEXT NOT NULL,
    finding TEXT NOT NULL,
    confidence REAL NOT NULL DEFAULT 0.8,
    source_url TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_research_memory_owner ON research_memory(owner_session, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_research_memory_topic ON research_memory(topic);
