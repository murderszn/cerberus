import { test } from 'node:test';
import assert from 'node:assert/strict';
import { DatabaseSync } from 'node:sqlite';
import { readFileSync } from 'node:fs';
import { handleProductRoute, testables } from './agent.mjs';

const origin = 'https://cerberus.example';
function setup() {
  const sql = new DatabaseSync(':memory:');
  sql.exec(readFileSync(new URL('./migrations/0001_auth.sql', import.meta.url), 'utf8'));
  sql.exec(readFileSync(new URL('./migrations/0002_agent_github_app.sql', import.meta.url), 'utf8'));
  const DB = {
    prepare(query) {
      return { bind(...params) { return {
        run: async () => sql.prepare(query).run(...params),
        first: async () => sql.prepare(query).get(...params) || null,
        all: async () => ({ results: sql.prepare(query).all(...params) }),
      }; } };
    },
    async batch(statements) {
      sql.exec('BEGIN');
      try { const results = []; for (const statement of statements) results.push(await statement.run()); sql.exec('COMMIT'); return results; }
      catch (error) { sql.exec('ROLLBACK'); throw error; }
    },
  };
  sql.prepare('INSERT INTO accounts VALUES (?, ?, ?, ?)').run(42, 'octocat', 'octo@example.com', 1);
  sql.prepare('INSERT INTO github_installations VALUES (?, ?, ?, ?, ?, ?)').run(7, 42, 'octocat', 'User', 1, 1);
  sql.prepare('INSERT INTO installation_repositories VALUES (?, ?, ?, ?, ?, ?, ?, ?)').run(7, 99, 'octocat', 'demo', 'octocat/demo', 'main', 0, 1);
  return { sql, env: { DB, APP_ORIGIN: origin }, account: { id: 42, login: 'octocat' } };
}
const post = (path, body, headers = {}) => new Request(origin + path, { method: 'POST', headers: { Origin: origin, 'X-Cerberus-CSRF': '1', 'Content-Type': 'application/json', ...headers }, body: JSON.stringify(body) });

test('repository paths reject traversal, workflow edits, git metadata, and absolute paths', () => {
  for (const path of ['../secret', '/etc/passwd', '.git/config', '.github/workflows/release.yml', 'a\\b', 'package-lock.json']) assert.equal(testables.safePath(path), false, path);
  for (const path of ['src/app.js', '.github/dependabot.yml', 'README.md']) assert.equal(testables.safePath(path), true, path);
});

test('conversation creation is account-scoped and pinned to an immutable SHA', async () => {
  const { env, account, sql } = setup();
  const report = { target: { owner: 'octocat', repo: 'demo', ref: 'main', sha: 'a'.repeat(40) }, score: 72, grade: 'C', agents: [] };
  const response = await handleProductRoute(post('/api/conversations', { report }), env, account);
  assert.equal(response.status, 201);
  const body = await response.json();
  assert.match(body.id, /^cv_/);
  const row = sql.prepare('SELECT * FROM conversations').get();
  assert.equal(row.base_sha, 'a'.repeat(40));
  assert.equal(row.repository_id, 99);
  const outsider = await handleProductRoute(post('/api/conversations', { report }), env, { id: 43, login: 'other' });
  assert.equal(outsider.status, 409);
});

test('mutating routes require authentication, exact origin, CSRF, and explicit PR approval', async () => {
  const { env, account, sql } = setup();
  const report = { target: { owner: 'octocat', repo: 'demo', ref: 'main', sha: 'b'.repeat(40) }, agents: [] };
  assert.equal((await handleProductRoute(post('/api/conversations', { report }), env, null)).status, 401);
  const wrongOrigin = post('/api/conversations', { report }, { Origin: 'https://evil.example' });
  assert.equal((await handleProductRoute(wrongOrigin, env, account)).status, 403);
  sql.prepare(`INSERT INTO conversations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`).run('cv_x', 42, 99, 7, 'octocat', 'demo', 'main', 'b'.repeat(40), JSON.stringify(report), 1, 1);
  sql.prepare(`INSERT INTO change_sets VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`).run('cs_x', 'cv_x', 42, 99, 'Fix', 'Body', 'b'.repeat(40), 'cerberus/x', '[]', 'proposed', 1, 1);
  const denied = await handleProductRoute(post('/api/change-sets/cs_x/create-pr', { approved: false }), env, account);
  assert.equal(denied.status, 400);
  assert.match((await denied.json()).error, /approve/i);
});

test('GitHub App status reveals configuration and repo access without exposing secrets', async () => {
  const { env, account } = setup();
  Object.assign(env, { GITHUB_APP_ID: '1', GITHUB_APP_SLUG: 'cerberus', GITHUB_APP_PRIVATE_KEY: 'secret' });
  const response = await handleProductRoute(new Request(origin + '/github/status?owner=octocat&repo=demo'), env, account);
  assert.deepEqual(await response.json(), { configured: true, installed: true, repository: { owner: 'octocat', name: 'demo', default_branch: 'main' } });
});
