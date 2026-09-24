CREATE TABLE github_install_flows (
  state_hash TEXT PRIMARY KEY,
  github_id INTEGER NOT NULL REFERENCES accounts(github_id) ON DELETE CASCADE,
  expires_at INTEGER NOT NULL
);
CREATE INDEX github_install_flow_expiry ON github_install_flows(expires_at);

CREATE TABLE github_installations (
  installation_id INTEGER PRIMARY KEY,
  github_id INTEGER NOT NULL REFERENCES accounts(github_id) ON DELETE CASCADE,
  account_login TEXT NOT NULL,
  account_type TEXT NOT NULL,
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL
);
CREATE INDEX github_installation_owner ON github_installations(github_id);

CREATE TABLE installation_repositories (
  installation_id INTEGER NOT NULL REFERENCES github_installations(installation_id) ON DELETE CASCADE,
  repository_id INTEGER NOT NULL,
  owner TEXT NOT NULL,
  name TEXT NOT NULL,
  full_name TEXT NOT NULL,
  default_branch TEXT NOT NULL,
  private INTEGER NOT NULL DEFAULT 0,
  updated_at INTEGER NOT NULL,
  PRIMARY KEY (installation_id, repository_id)
);
CREATE UNIQUE INDEX installation_repository_name ON installation_repositories(owner, name, installation_id);

CREATE TABLE conversations (
  id TEXT PRIMARY KEY,
  github_id INTEGER NOT NULL REFERENCES accounts(github_id) ON DELETE CASCADE,
  repository_id INTEGER NOT NULL,
  installation_id INTEGER NOT NULL REFERENCES github_installations(installation_id) ON DELETE CASCADE,
  owner TEXT NOT NULL,
  repo TEXT NOT NULL,
  base_ref TEXT NOT NULL,
  base_sha TEXT NOT NULL,
  report_json TEXT NOT NULL,
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL
);
CREATE INDEX conversation_owner ON conversations(github_id, updated_at);

CREATE TABLE messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
  role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
  content TEXT NOT NULL,
  created_at INTEGER NOT NULL
);
CREATE INDEX conversation_messages ON messages(conversation_id, id);

CREATE TABLE change_sets (
  id TEXT PRIMARY KEY,
  conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
  github_id INTEGER NOT NULL REFERENCES accounts(github_id) ON DELETE CASCADE,
  repository_id INTEGER NOT NULL,
  title TEXT NOT NULL,
  body TEXT NOT NULL,
  base_sha TEXT NOT NULL,
  branch_name TEXT NOT NULL,
  changes_json TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('proposed', 'creating', 'opened', 'failed')),
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL
);
CREATE INDEX change_set_conversation ON change_sets(conversation_id, created_at);

CREATE TABLE pr_jobs (
  id TEXT PRIMARY KEY,
  change_set_id TEXT NOT NULL UNIQUE REFERENCES change_sets(id) ON DELETE CASCADE,
  github_id INTEGER NOT NULL REFERENCES accounts(github_id) ON DELETE CASCADE,
  status TEXT NOT NULL CHECK (status IN ('creating', 'opened', 'failed')),
  pr_number INTEGER,
  pr_url TEXT,
  error TEXT,
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL
);
