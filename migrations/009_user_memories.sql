-- 009_user_memories.sql
-- Layer 2 Long-Term User Memory table for Atlas AI.
-- Non-destructive migration with session-isolated indexing.

CREATE TABLE IF NOT EXISTS user_memories (
    memory_id TEXT PRIMARY KEY,
    owner_session TEXT NOT NULL,
    category TEXT NOT NULL,
    content TEXT NOT NULL,
    confidence REAL NOT NULL DEFAULT 1.0,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_user_memories_owner ON user_memories(owner_session, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_user_memories_cat ON user_memories(owner_session, category);
