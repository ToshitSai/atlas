-- RAG document metadata and embedding storage. Non-destructive migration.
-- Run after 001_initial_schema.sql and 003_pgvector.sql.
CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE IF NOT EXISTS document_metadata (
    document_id UUID PRIMARY KEY REFERENCES documents(id) ON DELETE CASCADE,
    owner_session TEXT,
    storage_key TEXT,
    storage_provider TEXT NOT NULL DEFAULT 'vercel_blob',
    original_filename TEXT NOT NULL,
    byte_size BIGINT NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'uploaded',
    failure_reason TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS document_embeddings (
    chunk_id UUID PRIMARY KEY REFERENCES document_chunks(id) ON DELETE CASCADE,
    embedding_model TEXT NOT NULL,
    dimensions INTEGER NOT NULL,
    embedding vector(1536) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_document_metadata_owner ON document_metadata(owner_session, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_document_metadata_status ON document_metadata(status);
