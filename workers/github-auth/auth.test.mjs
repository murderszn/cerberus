import { test } from 'node:test';
import assert from 'node:assert/strict';
import { DatabaseSync } from 'node:sqlite';
import { readFileSync } from 'node:fs';
import worker, { handle, digest } from './index.mjs';
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
      }; } };
    },
    async batch(statements) { sql.exec('BEGIN'); try { const results = []; for (const statement of statements) results.push(await statement.run()); sql.exec('COMMIT'); return results; } catch (e) { sql.exec('ROLLBACK'); throw e; } },
  };
  return { sql, env: { DB, APP_ORIGIN: origin, GITHUB_CLIENT_ID: 'client', GITHUB_CLIENT_SECRET: 'secret', ASSETS: { fetch: () => new Response('asset') } } };
}
const req = (path, options) => new Request(origin + path, options);
async function start(env) {
  const result = await handle(req('/auth/github/start'), env);
  assert.equal(result.status, 302);
  const location = new URL(result.headers.get('Location'));
  assert.equal(location.origin, 'https://github.com');
  assert.equal(location.searchParams.get('code_challenge_method'), 'S256');
  assert.equal(location.searchParams.get('scope'), 'read:user user:email');
  return { state: location.searchParams.get('state'), challenge: location.searchParams.get('code_challenge'), cookie: result.headers.get('Set-Cookie').split(';')[0] };
}
function mockGithub(flow, emails = [{ email: 'verified@example.com', verified: true, primary: true }]) {
  return async (url, options) => {
    if (url.endsWith('/access_token')) {
      assert.equal(await digest(options.body.get('code_verifier')), flow.challenge);
      assert.equal(options.body.get('client_secret'), 'secret');
      return Response.json({ access_token: 'github-secret-token' });
    }
    assert.equal(options.headers.Authorization, 'Bearer github-secret-token');
    return Response.json(url.endsWith('/user/emails') ? emails : { id: 42, login: 'octocat', email: 'unverified@example.com' });
  };
}
const callback = flow => req('/auth/github/callback?code=code&state=' + flow.state, { headers: { Cookie: flow.cookie } });
test('complete login, hashed cookie session, account upsert, replay rejection and logout', async () => {
  const { env, sql } = setup();
  const flow = await start(env);
  const result = await handle(callback(flow), env, mockGithub(flow));
  assert.equal(result.headers.get('Location'), '/agent.html?github_auth=connected');
  const cookies = result.headers.getSetCookie();
  const session = cookies.find(v => v.startsWith('__Host-cerberus-session='));
  assert.match(session, /HttpOnly; Secure; SameSite=Lax/);
  const cookie = session.split(';')[0];
  assert.notEqual(sql.prepare('SELECT token_hash FROM sessions').get().token_hash, cookie.split('=')[1]);
  assert.equal((await handle(callback(flow), env)).status, 400);
  const me = await handle(req('/auth/github/session', { headers: { Cookie: cookie } }), env);
  assert.deepEqual(await me.json(), { user: { id: 42, login: 'octocat', email: 'verified@example.com' } });
  const again = await start(env);
  await handle(callback(again), env, mockGithub(again));
  assert.equal(sql.prepare('SELECT count(*) AS n FROM accounts').get().n, 1);
  const logoutOptions = { method: 'POST', headers: { Cookie: cookie, Origin: origin, 'X-Cerberus-CSRF': '1' } };
  assert.equal((await handle(req('/auth/github/logout', logoutOptions), env)).status, 200);
  assert.deepEqual(await (await handle(req('/auth/github/session', { headers: { Cookie: cookie } }), env)).json(), { user: null });
});
test('state is bound to browser; expired flows cannot authenticate', async () => {
  const { env, sql } = setup(); const flow = await start(env);
  assert.equal((await handle(req('/auth/github/callback?code=x&state=' + flow.state, { headers: { Cookie: '__Host-cerberus-oauth=attacker' } }), env)).status, 400);
  assert.equal(sql.prepare('SELECT count(*) AS n FROM oauth_flows').get().n, 1);
  sql.exec('UPDATE oauth_flows SET expires_at = 0');
  assert.equal((await handle(callback(flow), env)).status, 400);
});
test('denial, upstream failure, and unverified primary email never create a session', async () => {
  for (const mode of ['denied', 'upstream', 'email']) {
    const { env, sql } = setup(); const flow = await start(env);
    const request = mode === 'denied' ? req('/auth/github/callback?error=access_denied&state=' + flow.state, { headers: { Cookie: flow.cookie } }) : callback(flow);
    const result = await handle(request, env, mode === 'upstream' ? async () => { throw Error('secret error'); } : mockGithub(flow, [{ primary: true, verified: false, email: 'bad@example.com' }]));
    assert.match(result.headers.get('Location'), /github_auth=(denied|failed)$/);
    assert.equal(sql.prepare('SELECT count(*) AS n FROM sessions').get().n, 0);
    assert.equal(sql.prepare('SELECT count(*) AS n FROM accounts').get().n, 0);
  }
});
test('logout requires exact origin and CSRF header; methods and origin fail closed', async () => {
  const { env } = setup();
  for (const headers of [{}, { Origin: 'https://evil.example', 'X-Cerberus-CSRF': '1' }, { Origin: origin }]) {
    assert.equal((await handle(req('/auth/github/logout', { method: 'POST', headers }), env)).status, 403);
  }
  assert.equal((await handle(req('/auth/github/logout'), env)).status, 405);
  assert.equal((await handle(new Request('https://evil.example/auth/github/start'), env)).status, 400);
  assert.equal((await handle(req('/auth/github/session'), {})).status, 503);
});
test('session expiry and scheduled cleanup; safe server errors and asset routing', async () => {
  const { env, sql } = setup(); const flow = await start(env);
  const result = await handle(callback(flow), env, mockGithub(flow));
  const cookie = result.headers.getSetCookie().find(v => v.startsWith('__Host-cerberus-session=')).split(';')[0];
  sql.exec('UPDATE sessions SET expires_at = 0');
  assert.deepEqual(await (await handle(req('/auth/github/session', { headers: { Cookie: cookie } }), env)).json(), { user: null });
  await worker.scheduled({}, env);
  assert.equal(sql.prepare('SELECT count(*) AS n FROM sessions').get().n, 0);
  assert.equal(await (await handle(req('/agent.html'), env)).text(), 'asset');
  env.DB.prepare = () => { throw Error('database secret'); };
  const failed = await worker.fetch(req('/auth/github/start'), env);
  assert.equal(failed.status, 503);
  assert.doesNotMatch(await failed.text(), /database secret/);
});
