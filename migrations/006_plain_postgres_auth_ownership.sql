-- Provider-neutral PostgreSQL ownership migration.
-- Review and run manually; the application never executes this file.
-- Supabase Auth remains the identity provider, but these tables use ordinary
-- PostgreSQL UUID ownership and backend-enforced authorization.

ALTER TABLE users ADD COLUMN IF NOT EXISTS external_id TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS users_external_id_unique ON users(external_id)
  WHERE external_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS conversations_user_updated
  ON conversations(user_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS messages_conversation_created
  ON messages(conversation_id, created_at);
CREATE INDEX IF NOT EXISTS research_projects_user_updated
  ON research_projects(user_id, updated_at DESC);

-- Existing rows are preserved. The backend maps the verified Supabase JWT
-- subject to users.external_id and filters all reads/writes by that owner.
