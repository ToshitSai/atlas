-- =============================================================================
-- 005_supabase_rls.sql — Enable Row Level Security (RLS) for Supabase Auth
--
-- Restricts reading, inserting, updating, and deleting to data owned by the
-- authenticated Supabase user (auth.uid()). Service role / admin backend bypasses
-- RLS automatically.
-- =============================================================================

-- Enable Row Level Security on user tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversation_context ENABLE ROW LEVEL SECURITY;
ALTER TABLE memories ENABLE ROW LEVEL SECURITY;
ALTER TABLE research_projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE research_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE research_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE research_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE datasets ENABLE ROW LEVEL SECURITY;
ALTER TABLE experiments ENABLE ROW LEVEL SECURITY;
ALTER TABLE hypotheses ENABLE ROW LEVEL SECURITY;
ALTER TABLE artifacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE project_payloads ENABLE ROW LEVEL SECURITY;

-- --------------------------------------------------------------------- users
DROP POLICY IF EXISTS users_owner_policy ON users;
CREATE POLICY users_owner_policy ON users
    FOR ALL
    USING (id = auth.uid() OR external_id = auth.uid()::text)
    WITH CHECK (id = auth.uid() OR external_id = auth.uid()::text);

-- ------------------------------------------------------------- conversations
DROP POLICY IF EXISTS conversations_owner_policy ON conversations;
CREATE POLICY conversations_owner_policy ON conversations
    FOR ALL
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

-- ------------------------------------------------------------------ messages
DROP POLICY IF EXISTS messages_owner_policy ON messages;
CREATE POLICY messages_owner_policy ON messages
    FOR ALL
    USING (conversation_id IN (SELECT id FROM conversations WHERE user_id = auth.uid()))
    WITH CHECK (conversation_id IN (SELECT id FROM conversations WHERE user_id = auth.uid()));

-- ------------------------------------------------------- conversation_context
DROP POLICY IF EXISTS conversation_context_owner_policy ON conversation_context;
CREATE POLICY conversation_context_owner_policy ON conversation_context
    FOR ALL
    USING (conversation_id IN (SELECT id FROM conversations WHERE user_id = auth.uid()))
    WITH CHECK (conversation_id IN (SELECT id FROM conversations WHERE user_id = auth.uid()));

-- ------------------------------------------------------------------ memories
DROP POLICY IF EXISTS memories_owner_policy ON memories;
CREATE POLICY memories_owner_policy ON memories
    FOR ALL
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

-- ----------------------------------------------------------- research_projects
DROP POLICY IF EXISTS research_projects_owner_policy ON research_projects;
CREATE POLICY research_projects_owner_policy ON research_projects
    FOR ALL
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

-- ---------------------------------------------------------- research_sessions
DROP POLICY IF EXISTS research_sessions_owner_policy ON research_sessions;
CREATE POLICY research_sessions_owner_policy ON research_sessions
    FOR ALL
    USING (project_id IN (SELECT id FROM research_projects WHERE user_id = auth.uid()))
    WITH CHECK (project_id IN (SELECT id FROM research_projects WHERE user_id = auth.uid()));

-- ------------------------------------------------------------- research_events
DROP POLICY IF EXISTS research_events_owner_policy ON research_events;
CREATE POLICY research_events_owner_policy ON research_events
    FOR ALL
    USING (project_id IN (SELECT id FROM research_projects WHERE user_id = auth.uid()))
    WITH CHECK (project_id IN (SELECT id FROM research_projects WHERE user_id = auth.uid()));

-- ------------------------------------------------------------ research_sources
DROP POLICY IF EXISTS research_sources_owner_policy ON research_sources;
CREATE POLICY research_sources_owner_policy ON research_sources
    FOR ALL
    USING (project_id IN (SELECT id FROM research_projects WHERE user_id = auth.uid()))
    WITH CHECK (project_id IN (SELECT id FROM research_projects WHERE user_id = auth.uid()));

-- ------------------------------------------------------------------- datasets
DROP POLICY IF EXISTS datasets_owner_policy ON datasets;
CREATE POLICY datasets_owner_policy ON datasets
    FOR ALL
    USING (project_id IN (SELECT id FROM research_projects WHERE user_id = auth.uid()))
    WITH CHECK (project_id IN (SELECT id FROM research_projects WHERE user_id = auth.uid()));

-- ----------------------------------------------------------------- experiments
DROP POLICY IF EXISTS experiments_owner_policy ON experiments;
CREATE POLICY experiments_owner_policy ON experiments
    FOR ALL
    USING (project_id IN (SELECT id FROM research_projects WHERE user_id = auth.uid()))
    WITH CHECK (project_id IN (SELECT id FROM research_projects WHERE user_id = auth.uid()));

-- ----------------------------------------------------------------- hypotheses
DROP POLICY IF EXISTS hypotheses_owner_policy ON hypotheses;
CREATE POLICY hypotheses_owner_policy ON hypotheses
    FOR ALL
    USING (project_id IN (SELECT id FROM research_projects WHERE user_id = auth.uid()))
    WITH CHECK (project_id IN (SELECT id FROM research_projects WHERE user_id = auth.uid()));

-- ------------------------------------------------------------------ artifacts
DROP POLICY IF EXISTS artifacts_owner_policy ON artifacts;
CREATE POLICY artifacts_owner_policy ON artifacts
    FOR ALL
    USING (project_id IN (SELECT id FROM research_projects WHERE user_id = auth.uid()))
    WITH CHECK (project_id IN (SELECT id FROM research_projects WHERE user_id = auth.uid()));

-- -------------------------------------------------------------------- reports
DROP POLICY IF EXISTS reports_owner_policy ON reports;
CREATE POLICY reports_owner_policy ON reports
    FOR ALL
    USING (project_id IN (SELECT id FROM research_projects WHERE user_id = auth.uid()))
    WITH CHECK (project_id IN (SELECT id FROM research_projects WHERE user_id = auth.uid()));

-- ----------------------------------------------------------------- documents
DROP POLICY IF EXISTS documents_owner_policy ON documents;
CREATE POLICY documents_owner_policy ON documents
    FOR ALL
    USING (user_id = auth.uid() OR project_id IN (SELECT id FROM research_projects WHERE user_id = auth.uid()))
    WITH CHECK (user_id = auth.uid() OR project_id IN (SELECT id FROM research_projects WHERE user_id = auth.uid()));

-- ---------------------------------------------------------- project_payloads
DROP POLICY IF EXISTS project_payloads_owner_policy ON project_payloads;
CREATE POLICY project_payloads_owner_policy ON project_payloads
    FOR ALL
    USING (project_id IN (SELECT id FROM research_projects WHERE user_id = auth.uid()))
    WITH CHECK (project_id IN (SELECT id FROM research_projects WHERE user_id = auth.uid()));

-- Record migration execution
INSERT INTO schema_migrations (migration)
VALUES ('005_supabase_rls.sql')
ON CONFLICT (migration) DO NOTHING;
