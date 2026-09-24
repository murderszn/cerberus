import { handleProductRoute } from './agent.mjs';

const SESSION = '__Host-cerberus-session';
const FLOW = '__Host-cerberus-oauth';
const TTL = 7 * 86400;
const now = () => Math.floor(Date.now() / 1000);
const random = () => btoa(String.fromCharCode(...crypto.getRandomValues(new Uint8Array(32)))).replaceAll('+', '-').replaceAll('/', '_').replaceAll('=', '');
export async function digest(value) {
  return btoa(String.fromCharCode(...new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(value))))).replaceAll('+', '-').replaceAll('/', '_').replaceAll('=', '');
}
function cookie(request, name) {
  return (request.headers.get('Cookie') || '').split(';').map(v => v.trim()).find(v => v.startsWith(name + '='))?.slice(name.length + 1) || '';
}
const setCookie = (name, value, age) => `${name}=${value}; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=${age}`;
function response(body, status = 200, headers = {}) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store', 'Referrer-Policy': 'no-referrer', 'X-Content-Type-Options': 'nosniff', ...headers } });
}
function redirect(location, cookies = []) {
  const result = response(null, 302, { Location: location });
  for (const c of cookies) result.headers.append('Set-Cookie', c);
  return result;
}
async function getAccount(request, env) {
  const sid = cookie(request, SESSION);
  return sid ? env.DB.prepare('SELECT accounts.github_id AS id, accounts.login, accounts.email FROM sessions JOIN accounts USING (github_id) WHERE token_hash = ? AND expires_at > ?').bind(await digest(sid), now()).first() : null;
}
async function github(path, token, fetcher) {
  const result = await fetcher('https://api.github.com' + path, { headers: { Authorization: `Bearer ${token}`, Accept: 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28', 'User-Agent': 'Cerberus' } });
  if (!result.ok) throw new Error('GitHub profile request failed');
  return result.json();
}
export async function handle(request, env, fetcher = fetch) {
  const url = new URL(request.url);
  if (url.pathname.startsWith('/api/') || url.pathname.startsWith('/github/')) {
    if (!env.DB || !env.APP_ORIGIN) return response({ error: 'Cerberus accounts are not configured on this deployment.' }, 503);
    if (url.origin !== env.APP_ORIGIN || url.protocol !== 'https:') return response({ error: 'Invalid application origin.' }, 400);
    const account = url.pathname === '/github/webhook' ? null : await getAccount(request, env);
    return handleProductRoute(request, env, account);
  }
  if (!url.pathname.startsWith('/auth/')) return env.ASSETS.fetch(request);
  if (!env.DB || !env.GITHUB_CLIENT_ID || !env.GITHUB_CLIENT_SECRET || !env.APP_ORIGIN) return response({ error: 'GitHub sign-in is not configured on this deployment.' }, 503);
  if (url.origin !== env.APP_ORIGIN || url.protocol !== 'https:') return response({ error: 'Invalid authentication origin.' }, 400);
  const route = url.pathname;
  const expectedMethod = route === '/auth/github/logout' ? 'POST' : 'GET';
  if (request.method !== expectedMethod) return response({ error: 'Method not allowed.' }, 405, { Allow: expectedMethod });
  const db = env.DB;
  const callback = env.APP_ORIGIN + '/auth/github/callback';
  if (route === '/auth/github/start') {
    const state = random(), browser = random(), verifier = random();
    await db.prepare('INSERT INTO oauth_flows (state_hash, browser_hash, verifier, expires_at) VALUES (?, ?, ?, ?)').bind(await digest(state), await digest(browser), verifier, now() + 600).run();
    const authorize = new URL('https://github.com/login/oauth/authorize');
    authorize.search = new URLSearchParams({ client_id: env.GITHUB_CLIENT_ID, redirect_uri: callback, scope: 'read:user user:email', state, code_challenge: await digest(verifier), code_challenge_method: 'S256' }).toString();
    return redirect(authorize.href, [setCookie(FLOW, browser, 600)]);
  }
  if (route === '/auth/github/callback') {
    const state = url.searchParams.get('state'), browser = cookie(request, FLOW);
    if (!state || !browser) return response({ error: 'Invalid or expired sign-in. Please start again.' }, 400);
    // Consume atomically: neither concurrent callbacks nor replay may reuse a flow.
    const flow = await db.prepare('DELETE FROM oauth_flows WHERE state_hash = ? AND browser_hash = ? AND expires_at > ? RETURNING verifier').bind(await digest(state), await digest(browser), now()).first();
    if (!flow) return response({ error: 'Invalid or expired sign-in. Please start again.' }, 400);
    const cleared = setCookie(FLOW, '', 0);
    if (url.searchParams.has('error') || !url.searchParams.get('code')) return redirect('/agent.html?github_auth=denied', [cleared]);
    try {
      const exchange = await fetcher('https://github.com/login/oauth/access_token', { method: 'POST', headers: { Accept: 'application/json', 'Content-Type': 'application/x-www-form-urlencoded' }, body: new URLSearchParams({ client_id: env.GITHUB_CLIENT_ID, client_secret: env.GITHUB_CLIENT_SECRET, code: url.searchParams.get('code'), redirect_uri: callback, code_verifier: flow.verifier }) });
      const token = await exchange.json();
      if (!exchange.ok || !token.access_token || token.error) throw new Error('Exchange failed');
      const [user, emails] = await Promise.all([github('/user', token.access_token, fetcher), github('/user/emails', token.access_token, fetcher)]);
      const email = Array.isArray(emails) && emails.find(e => e.primary === true && e.verified === true && typeof e.email === 'string');
      if (!Number.isSafeInteger(user.id) || !user.login || !email) throw new Error('Verified primary email required');
      const session = random();
      const oldSession = cookie(request, SESSION);
      await db.batch([
        db.prepare('INSERT INTO accounts (github_id, login, email, updated_at) VALUES (?, ?, ?, ?) ON CONFLICT(github_id) DO UPDATE SET login = excluded.login, email = excluded.email, updated_at = excluded.updated_at').bind(user.id, user.login, email.email, now()),
        db.prepare('DELETE FROM sessions WHERE token_hash = ?').bind(await digest(oldSession)),
        db.prepare('INSERT INTO sessions (token_hash, github_id, expires_at) VALUES (?, ?, ?)').bind(await digest(session), user.id, now() + TTL),
      ]);
      // The OAuth access token is used only for identity and is never persisted or returned.
      return redirect('/agent.html?github_auth=connected', [cleared, setCookie(SESSION, session, TTL)]);
    } catch {
      return redirect('/agent.html?github_auth=failed', [cleared]);
    }
  }
  if (route === '/auth/github/session') {
    const account = await getAccount(request, env);
    return response({ user: account || null });
  }
  if (route === '/auth/github/logout') {
    if (request.headers.get('Origin') !== env.APP_ORIGIN || request.headers.get('X-Cerberus-CSRF') !== '1') return response({ error: 'Invalid logout origin.' }, 403);
    await db.prepare('DELETE FROM sessions WHERE token_hash = ?').bind(await digest(cookie(request, SESSION))).run();
    return response({ user: null }, 200, { 'Set-Cookie': setCookie(SESSION, '', 0) });
  }
  return response({ error: 'Not found.' }, 404);
}
export default {
  async fetch(request, env) {
    try { return await handle(request, env); }
    catch (error) { return response({ error: error?.status ? error.message : 'Cerberus is temporarily unavailable. Please try again.' }, error?.status || 503); }
  },
  async scheduled(event, env) {
    await env.DB.batch([
      env.DB.prepare('DELETE FROM oauth_flows WHERE expires_at <= ?').bind(now()),
      env.DB.prepare('DELETE FROM sessions WHERE expires_at <= ?').bind(now()),
      env.DB.prepare('DELETE FROM github_install_flows WHERE expires_at <= ?').bind(now()),
    ]);
  },
};
