CREATE TABLE accounts (
  github_id INTEGER PRIMARY KEY,
  login TEXT NOT NULL,
  email TEXT NOT NULL,
  updated_at INTEGER NOT NULL
);
CREATE TABLE oauth_flows (
  state_hash TEXT PRIMARY KEY,
  browser_hash TEXT NOT NULL,
  verifier TEXT NOT NULL,
  expires_at INTEGER NOT NULL
);
CREATE INDEX oauth_expiry ON oauth_flows(expires_at);
CREATE TABLE sessions (
  token_hash TEXT PRIMARY KEY,
  github_id INTEGER NOT NULL REFERENCES accounts(github_id) ON DELETE CASCADE,
  expires_at INTEGER NOT NULL
);
CREATE INDEX session_expiry ON sessions(expires_at);
