-- Supabase Auth ownership policies for Atlas application data.
-- REVIEW ONLY: this migration is intentionally not executed by the app.
-- Apply it manually after checking the existing production schema and data.

ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE research_projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE research_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE research_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE research_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE experiments ENABLE ROW LEVEL SECURITY;
ALTER TABLE hypotheses ENABLE ROW LEVEL SECURITY;
ALTER TABLE artifacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE reports ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS atlas_users_owner ON users;
CREATE POLICY atlas_users_owner ON users
  FOR ALL USING (id = auth.uid()) WITH CHECK (id = auth.uid());

DROP POLICY IF EXISTS atlas_conversations_owner ON conversations;
CREATE POLICY atlas_conversations_owner ON conversations
  FOR ALL USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());

DROP POLICY IF EXISTS atlas_messages_owner ON messages;
CREATE POLICY atlas_messages_owner ON messages
  FOR ALL
  USING (conversation_id IN (SELECT id FROM conversations WHERE user_id = auth.uid()))
  WITH CHECK (conversation_id IN (SELECT id FROM conversations WHERE user_id = auth.uid()));

DROP POLICY IF EXISTS atlas_projects_owner ON research_projects;
CREATE POLICY atlas_projects_owner ON research_projects
  FOR ALL USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());

DROP POLICY IF EXISTS atlas_sessions_owner ON research_sessions;
CREATE POLICY atlas_sessions_owner ON research_sessions
  FOR ALL USING (project_id IN (SELECT id FROM research_projects WHERE user_id = auth.uid()))
  WITH CHECK (project_id IN (SELECT id FROM research_projects WHERE user_id = auth.uid()));

DROP POLICY IF EXISTS atlas_events_owner ON research_events;
CREATE POLICY atlas_events_owner ON research_events
  FOR ALL USING (project_id IN (SELECT id FROM research_projects WHERE user_id = auth.uid()))
  WITH CHECK (project_id IN (SELECT id FROM research_projects WHERE user_id = auth.uid()));

DROP POLICY IF EXISTS atlas_sources_owner ON research_sources;
CREATE POLICY atlas_sources_owner ON research_sources
  FOR ALL USING (project_id IN (SELECT id FROM research_projects WHERE user_id = auth.uid()))
  WITH CHECK (project_id IN (SELECT id FROM research_projects WHERE user_id = auth.uid()));

DROP POLICY IF EXISTS atlas_experiments_owner ON experiments;
CREATE POLICY atlas_experiments_owner ON experiments
  FOR ALL USING (project_id IN (SELECT id FROM research_projects WHERE user_id = auth.uid()))
  WITH CHECK (project_id IN (SELECT id FROM research_projects WHERE user_id = auth.uid()));

DROP POLICY IF EXISTS atlas_hypotheses_owner ON hypotheses;
CREATE POLICY atlas_hypotheses_owner ON hypotheses
  FOR ALL USING (project_id IN (SELECT id FROM research_projects WHERE user_id = auth.uid()))
  WITH CHECK (project_id IN (SELECT id FROM research_projects WHERE user_id = auth.uid()));

DROP POLICY IF EXISTS atlas_artifacts_owner ON artifacts;
CREATE POLICY atlas_artifacts_owner ON artifacts
  FOR ALL USING (project_id IN (SELECT id FROM research_projects WHERE user_id = auth.uid()))
  WITH CHECK (project_id IN (SELECT id FROM research_projects WHERE user_id = auth.uid()));

DROP POLICY IF EXISTS atlas_reports_owner ON reports;
CREATE POLICY atlas_reports_owner ON reports
  FOR ALL USING (project_id IN (SELECT id FROM research_projects WHERE user_id = auth.uid()))
  WITH CHECK (project_id IN (SELECT id FROM research_projects WHERE user_id = auth.uid()));
