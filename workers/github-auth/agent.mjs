const enc = new TextEncoder();
const dec = new TextDecoder();
const epoch = () => Math.floor(Date.now() / 1000);
const json = (body, status = 200, headers = {}) => new Response(JSON.stringify(body), {
  status,
  headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff', ...headers },
});

function b64url(bytes) {
  const raw = typeof bytes === 'string' ? bytes : String.fromCharCode(...new Uint8Array(bytes));
  return btoa(raw).replaceAll('+', '-').replaceAll('/', '_').replaceAll('=', '');
}
function id(prefix = '') {
  return prefix + b64url(crypto.getRandomValues(new Uint8Array(18)));
}
async function sha256(value) {
  return b64url(await crypto.subtle.digest('SHA-256', enc.encode(value)));
}
function safePath(path) {
  const file = typeof path === 'string' ? path.split('/').pop().toLowerCase() : '';
  return typeof path === 'string' && path.length > 0 && path.length <= 240 &&
    !path.startsWith('/') && !path.includes('\\') && !path.split('/').includes('..') &&
    !path.startsWith('.git/') && path !== '.git' && !path.startsWith('.github/workflows/') &&
    !['package-lock.json', 'yarn.lock', 'pnpm-lock.yaml', 'poetry.lock', 'composer.lock'].includes(file);
}
function parsePem(pem) {
  const value = pem.replace(/\\n/g, '\n').replace(/-----[^-]+-----/g, '').replace(/\s/g, '');
  return Uint8Array.from(atob(value), c => c.charCodeAt(0));
}
export async function createAppJwt(env, at = epoch()) {
  if (!env.GITHUB_APP_ID || !env.GITHUB_APP_PRIVATE_KEY) throw new Error('GitHub App is not configured.');
  const key = await crypto.subtle.importKey('pkcs8', parsePem(env.GITHUB_APP_PRIVATE_KEY), { name: 'RSASSA-PKCS1-v1_5', hash: 'SHA-256' }, false, ['sign']);
  const head = b64url(JSON.stringify({ alg: 'RS256', typ: 'JWT' }));
  const payload = b64url(JSON.stringify({ iat: at - 60, exp: at + 540, iss: String(env.GITHUB_APP_ID) }));
  const input = head + '.' + payload;
  return input + '.' + b64url(await crypto.subtle.sign('RSASSA-PKCS1-v1_5', key, enc.encode(input)));
}
async function gh(env, path, options = {}, token) {
  const auth = token || await createAppJwt(env);
  const result = await fetch('https://api.github.com' + path, {
    ...options,
    headers: {
      Authorization: `Bearer ${auth}`,
      Accept: 'application/vnd.github+json',
      'Content-Type': 'application/json',
      'X-GitHub-Api-Version': '2022-11-28',
      'User-Agent': 'Cerberus',
      ...(options.headers || {}),
    },
  });
  const text = await result.text();
  const body = text ? JSON.parse(text) : {};
  if (!result.ok) {
    const error = new Error(body.message || `GitHub request failed (${result.status}).`);
    error.status = result.status;
    throw error;
  }
  return body;
}
async function installationToken(env, installationId, repo) {
  const requestBody = { permissions: { contents: 'write', pull_requests: 'write' } };
  if (repo) requestBody.repositories = [repo];
  const body = await gh(env, `/app/installations/${installationId}/access_tokens`, {
    method: 'POST',
    body: JSON.stringify(requestBody),
  });
  return body.token;
}
async function syncInstallation(env, installationId, githubId) {
  const installation = await gh(env, `/app/installations/${installationId}`);
  const token = await installationToken(env, installationId);
  const listing = await gh(env, '/installation/repositories?per_page=100', {}, token);
  const timestamp = epoch();
  await env.DB.prepare(`INSERT INTO github_installations (installation_id, github_id, account_login, account_type, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(installation_id) DO UPDATE SET github_id=excluded.github_id, account_login=excluded.account_login, account_type=excluded.account_type, updated_at=excluded.updated_at`)
    .bind(installationId, githubId, installation.account.login, installation.account.type, timestamp, timestamp).run();
  await env.DB.prepare('DELETE FROM installation_repositories WHERE installation_id = ?').bind(installationId).run();
  for (const repo of listing.repositories || []) {
    await env.DB.prepare(`INSERT INTO installation_repositories (installation_id, repository_id, owner, name, full_name, default_branch, private, updated_at)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?)`)
      .bind(installationId, repo.id, repo.owner.login, repo.name, repo.full_name, repo.default_branch, repo.private ? 1 : 0, timestamp).run();
  }
  return listing.repositories || [];
}
function requirePost(request, env) {
  if (request.method !== 'POST') return json({ error: 'Method not allowed.' }, 405, { Allow: 'POST' });
  if (request.headers.get('Origin') !== env.APP_ORIGIN || request.headers.get('X-Cerberus-CSRF') !== '1') return json({ error: 'Invalid request origin.' }, 403);
  return null;
}
async function readJson(request) {
  const type = request.headers.get('Content-Type') || '';
  if (!type.includes('application/json')) throw Object.assign(new Error('JSON body required.'), { status: 415 });
  return request.json();
}
async function repoForAccount(env, account, owner, repo) {
  return env.DB.prepare(`SELECT installation_repositories.*, github_installations.github_id FROM installation_repositories
    JOIN github_installations USING (installation_id)
    WHERE github_installations.github_id = ? AND lower(owner) = lower(?) AND lower(name) = lower(?)`)
    .bind(account.id, owner, repo).first();
}
async function ownedConversation(env, account, conversationId) {
  return env.DB.prepare('SELECT * FROM conversations WHERE id = ? AND github_id = ?').bind(conversationId, account.id).first();
}
function reportSummary(report) {
  const failures = [];
  for (const agent of report.agents || []) for (const check of agent.checks || []) {
    if (check.status !== 'fail') continue;
    failures.push({ agent: agent.name, id: check.id, name: check.name, severity: check.severity, summary: check.summary, risk: check.risk, findings: (check.findings || []).slice(0, 8) });
  }
  return { target: report.target, score: report.score, grade: report.grade, failures: failures.slice(0, 40) };
}
const toolDefinitions = [
  { type: 'function', function: { name: 'list_repository_paths', description: 'Find repository file paths at the pinned base commit.', parameters: { type: 'object', properties: { query: { type: 'string' } }, required: ['query'], additionalProperties: false } } },
  { type: 'function', function: { name: 'read_file', description: 'Read one UTF-8 repository file at the pinned base commit.', parameters: { type: 'object', properties: { path: { type: 'string' } }, required: ['path'], additionalProperties: false } } },
  { type: 'function', function: { name: 'propose_changes', description: 'Create the reviewed change set. Call only after inspecting every file being edited.', parameters: { type: 'object', properties: { title: { type: 'string' }, body: { type: 'string' }, changes: { type: 'array', maxItems: 10, items: { type: 'object', properties: { path: { type: 'string' }, content: { type: 'string' }, rationale: { type: 'string' } }, required: ['path', 'content', 'rationale'], additionalProperties: false } } }, required: ['title', 'body', 'changes'], additionalProperties: false } } },
  { type: 'function', function: { name: 'record_engineering_intent', description: 'Record one concise engineering objective distilled from the user requests in this conversation. Call once before the final response. Preserve concrete requirements and constraints; do not invent work.', parameters: { type: 'object', properties: { intent: { type: 'string', maxLength: 1600 } }, required: ['intent'], additionalProperties: false } } },
];
async function modelCall(env, key, model, messages, tools) {
  const result = await fetch('https://gen.pollinations.ai/v1/chat/completions', {
    method: 'POST',
    headers: { Authorization: `Bearer ${key}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({ model, stream: false, temperature: 0.2, messages, ...(tools ? { tools, tool_choice: 'auto' } : {}) }),
  });
  const body = await result.json();
  if (!result.ok) throw Object.assign(new Error(body.error?.message || body.error || body.message || `Pollinations failed (${result.status}).`), { status: 502 });
  return body.choices?.[0]?.message || {};
}

async function runAgent(env, account, conversation, prompt, model, suppliedKey) {
  const key = env.POLLINATIONS_API_KEY || suppliedKey;
  if (!key || !/^sk_|^pk_/.test(key)) throw Object.assign(new Error('Connect Pollinations or configure the server key.'), { status: 503 });
  const repo = await repoForAccount(env, account, conversation.owner, conversation.repo);
  if (!repo) throw Object.assign(new Error('Install the Cerberus GitHub App for this repository first.'), { status: 409 });
  const token = await installationToken(env, repo.installation_id, repo.name);
  const history = await env.DB.prepare('SELECT role, content FROM messages WHERE conversation_id = ? ORDER BY id DESC LIMIT 20').bind(conversation.id).all();
  const messages = [{ role: 'system', content: `You are Cerberus, a careful principal security engineer working on ${conversation.owner}/${conversation.repo} at immutable commit ${conversation.base_sha}. Use repository tools before claiming facts. Keep explanations direct. Before the final response, call record_engineering_intent once with a concise objective distilled from the recent user requests. When asked to implement changes, inspect each target file and call propose_changes with complete replacement text. Never edit .github/workflows, git metadata, binaries, generated files, lockfiles, or more than 10 files. A human reviews the change set and separately approves creation of a draft pull request. Scan context:\n${JSON.stringify(reportSummary(JSON.parse(conversation.report_json)))}` }];
  for (const item of (history.results || []).reverse()) messages.push({ role: item.role, content: item.content });
  let changeSet = null;
  let intent = '';
  const activity = [];
  const inspectedPaths = new Set();
  for (let round = 0; round < 8; round++) {
    const answer = await modelCall(env, key, model, messages, toolDefinitions);
    messages.push(answer);
    if (!answer.tool_calls?.length) return { content: String(answer.content || ''), changeSet, activity, intent };
    for (const call of answer.tool_calls) {
      let args;
      try { args = JSON.parse(call.function.arguments || '{}'); } catch { args = {}; }
      let output;
      if (call.function.name === 'list_repository_paths') {
        const tree = await gh(env, `/repos/${conversation.owner}/${conversation.repo}/git/trees/${conversation.base_sha}?recursive=1`, {}, token);
        const query = String(args.query || '').toLowerCase();
        output = (tree.tree || []).filter(x => x.type === 'blob' && x.path.toLowerCase().includes(query)).slice(0, 100).map(x => ({ path: x.path, size: x.size }));
      } else if (call.function.name === 'read_file') {
        if (!safePath(args.path)) output = { error: 'Path is not allowed.' };
        else {
          inspectedPaths.add(args.path);
          try {
            const file = await gh(env, `/repos/${conversation.owner}/${conversation.repo}/contents/${encodeURIComponent(args.path).replaceAll('%2F', '/')}?ref=${conversation.base_sha}`, {}, token);
            if (file.type !== 'file' || file.size > 180000 || !file.content) output = { error: 'Only UTF-8 text files up to 180 KB can be read.' };
            else output = { path: args.path, exists: true, content: dec.decode(Uint8Array.from(atob(file.content.replace(/\s/g, '')), c => c.charCodeAt(0))) };
          } catch (error) {
            if (error.status !== 404) throw error;
            output = { path: args.path, exists: false, content: '' };
          }
        }
      } else if (call.function.name === 'record_engineering_intent') {
        intent = String(args.intent || '').trim().slice(0, 1600);
        output = intent ? { accepted: true } : { error: 'Intent cannot be empty.' };
      } else if (call.function.name === 'propose_changes') {
        const changes = Array.isArray(args.changes) ? args.changes : [];
        if (!changes.length || changes.length > 10 || changes.reduce((n, x) => n + String(x.content || '').length, 0) > 700000 || changes.some(x => !safePath(x.path) || !inspectedPaths.has(x.path) || typeof x.content !== 'string' || x.content.length > 300000)) output = { error: 'Every changed path must be inspected and satisfy file, path, and size limits.' };
        else {
          const seen = new Set();
          if (changes.some(x => seen.has(x.path) || !seen.add(x.path))) output = { error: 'Each path may appear only once.' };
          else {
            const changeId = id('cs_');
            const stored = [];
            for (const change of changes) {
              let original = '';
              try {
                const file = await gh(env, `/repos/${conversation.owner}/${conversation.repo}/contents/${encodeURIComponent(change.path).replaceAll('%2F', '/')}?ref=${conversation.base_sha}`, {}, token);
                if (file.type === 'file' && file.content) original = dec.decode(Uint8Array.from(atob(file.content.replace(/\s/g, '')), c => c.charCodeAt(0)));
              } catch (error) { if (error.status !== 404) throw error; }
              stored.push({ path: change.path, original, content: change.content, rationale: String(change.rationale || '') });
            }
            const title = String(args.title || 'Cerberus security hardening').slice(0, 200);
            const body = String(args.body || '').slice(0, 12000);
            const branch = `cerberus/${changeId.slice(3, 13).toLowerCase()}`;
            await env.DB.prepare(`INSERT INTO change_sets (id, conversation_id, github_id, repository_id, title, body, base_sha, branch_name, changes_json, status, created_at, updated_at)
              VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'proposed', ?, ?)`)
              .bind(changeId, conversation.id, account.id, repo.repository_id, title, body, conversation.base_sha, branch, JSON.stringify(stored), epoch(), epoch()).run();
            changeSet = { id: changeId, title, body, branch_name: branch, base_sha: conversation.base_sha, status: 'proposed', changes: stored };
            output = { accepted: true, change_set_id: changeId, files: stored.map(x => x.path), note: 'The user must review this change set before a draft PR can be created.' };
          }
        }
      } else output = { error: 'Unknown tool.' };
      if (call.function.name !== 'record_engineering_intent') activity.push({ tool: call.function.name, detail: call.function.name === 'read_file' ? args.path : call.function.name === 'list_repository_paths' ? args.query : `${args.changes?.length || 0} files` });
      messages.push({ role: 'tool', tool_call_id: call.id, content: JSON.stringify(output) });
    }
  }
  throw Object.assign(new Error('The agent reached its repository tool limit.'), { status: 422 });
}
function publicChangeSet(row) {
  if (!row) return null;
  return { id: row.id, title: row.title, body: row.body, base_sha: row.base_sha, branch_name: row.branch_name, status: row.status, changes: JSON.parse(row.changes_json), pr_url: row.pr_url || null, pr_number: row.pr_number || null };
}
async function createDraftPr(env, account, row) {
  const prior = await env.DB.prepare('SELECT * FROM pr_jobs WHERE change_set_id = ? AND github_id = ?').bind(row.id, account.id).first();
  if (prior?.status === 'opened') return { url: prior.pr_url, number: prior.pr_number, draft: true, reused: true };
  const conversation = await ownedConversation(env, account, row.conversation_id);
  const repo = await repoForAccount(env, account, conversation.owner, conversation.repo);
  if (!repo || repo.repository_id !== row.repository_id) throw Object.assign(new Error('Repository installation is no longer available.'), { status: 409 });
  const token = await installationToken(env, repo.installation_id, repo.name);
  const branch = encodeURIComponent(conversation.base_ref.replace(/^refs\/heads\//, ''));
  const current = await gh(env, `/repos/${conversation.owner}/${conversation.repo}/git/ref/heads/${branch}`, {}, token);
  if (current.object.sha !== row.base_sha) throw Object.assign(new Error('The base branch moved after this change set was generated. Regenerate it against the latest commit.'), { status: 409 });
  const timestamp = epoch();
  const jobId = prior?.id || id('pr_');
  if (prior) await env.DB.prepare("UPDATE pr_jobs SET status='creating', error=NULL, updated_at=? WHERE id=?").bind(timestamp, jobId).run();
  else await env.DB.prepare("INSERT INTO pr_jobs (id, change_set_id, github_id, status, created_at, updated_at) VALUES (?, ?, ?, 'creating', ?, ?)").bind(jobId, row.id, account.id, timestamp, timestamp).run();
  try {
    const baseCommit = await gh(env, `/repos/${conversation.owner}/${conversation.repo}/git/commits/${row.base_sha}`, {}, token);
    const changes = JSON.parse(row.changes_json);
    const tree = await gh(env, `/repos/${conversation.owner}/${conversation.repo}/git/trees`, { method: 'POST', body: JSON.stringify({ base_tree: baseCommit.tree.sha, tree: changes.map(x => ({ path: x.path, mode: '100644', type: 'blob', content: x.content })) }) }, token);
    const commit = await gh(env, `/repos/${conversation.owner}/${conversation.repo}/git/commits`, { method: 'POST', body: JSON.stringify({ message: row.title, tree: tree.sha, parents: [row.base_sha] }) }, token);
    try { await gh(env, `/repos/${conversation.owner}/${conversation.repo}/git/refs`, { method: 'POST', body: JSON.stringify({ ref: `refs/heads/${row.branch_name}`, sha: commit.sha }) }, token); }
    catch (error) {
      if (error.status !== 422) throw error;
      const existing = await gh(env, `/repos/${conversation.owner}/${conversation.repo}/git/ref/heads/${encodeURIComponent(row.branch_name)}`, {}, token);
      if (existing.object.sha !== commit.sha) throw Object.assign(new Error('The proposed branch already exists with different content.'), { status: 409 });
    }
    let pr;
    try { pr = await gh(env, `/repos/${conversation.owner}/${conversation.repo}/pulls`, { method: 'POST', body: JSON.stringify({ title: row.title, body: row.body, head: row.branch_name, base: conversation.base_ref.replace(/^refs\/heads\//, ''), draft: true }) }, token); }
    catch (error) {
      if (error.status !== 422) throw error;
      const existing = await gh(env, `/repos/${conversation.owner}/${conversation.repo}/pulls?state=open&head=${encodeURIComponent(conversation.owner + ':' + row.branch_name)}`, {}, token);
      if (!existing[0]) throw error;
      pr = existing[0];
    }
    await env.DB.batch([
      env.DB.prepare("UPDATE pr_jobs SET status='opened', pr_number=?, pr_url=?, error=NULL, updated_at=? WHERE id=?").bind(pr.number, pr.html_url, epoch(), jobId),
      env.DB.prepare("UPDATE change_sets SET status='opened', updated_at=? WHERE id=?").bind(epoch(), row.id),
    ]);
    return { url: pr.html_url, number: pr.number, draft: true, reused: false };
  } catch (error) {
    await env.DB.batch([
      env.DB.prepare("UPDATE pr_jobs SET status='failed', error=?, updated_at=? WHERE id=?").bind(String(error.message || error).slice(0, 500), epoch(), jobId),
      env.DB.prepare("UPDATE change_sets SET status='failed', updated_at=? WHERE id=?").bind(epoch(), row.id),
    ]);
    throw error;
  }
}

export async function handleProductRoute(request, env, account) {
  const url = new URL(request.url);
  const path = url.pathname;
  if (path === '/github/status' && request.method === 'GET') {
    const owner = url.searchParams.get('owner'), repo = url.searchParams.get('repo');
    const installed = account && owner && repo ? await repoForAccount(env, account, owner, repo) : null;
    return json({ configured: Boolean(env.GITHUB_APP_ID && env.GITHUB_APP_SLUG && env.GITHUB_APP_PRIVATE_KEY), installed: Boolean(installed), repository: installed ? { owner: installed.owner, name: installed.name, default_branch: installed.default_branch } : null });
  }
  if (path === '/github/install/start') {
    const invalid = requirePost(request, env); if (invalid) return invalid;
    if (!account) return json({ error: 'Sign in with GitHub first.' }, 401);
    if (!env.GITHUB_APP_SLUG || !env.GITHUB_APP_ID || !env.GITHUB_APP_PRIVATE_KEY) return json({ error: 'GitHub repository access is not configured yet.' }, 503);
    const state = id();
    await env.DB.prepare('INSERT INTO github_install_flows (state_hash, github_id, expires_at) VALUES (?, ?, ?)').bind(await sha256(state), account.id, epoch() + 600).run();
    return json({ url: `https://github.com/apps/${encodeURIComponent(env.GITHUB_APP_SLUG)}/installations/new?state=${encodeURIComponent(state)}` });
  }
  if (path === '/github/install/callback' && request.method === 'GET') {
    if (!account) return new Response(null, { status: 302, headers: { Location: '/agent.html?github_install=signin' } });
    const state = url.searchParams.get('state'), installationId = Number(url.searchParams.get('installation_id'));
    if (!state || !Number.isSafeInteger(installationId)) return new Response(null, { status: 302, headers: { Location: '/agent.html?github_install=failed' } });
    const flow = await env.DB.prepare('DELETE FROM github_install_flows WHERE state_hash=? AND github_id=? AND expires_at>? RETURNING github_id').bind(await sha256(state), account.id, epoch()).first();
    if (!flow) return new Response(null, { status: 302, headers: { Location: '/agent.html?github_install=failed' } });
    await syncInstallation(env, installationId, account.id);
    return new Response(null, { status: 302, headers: { Location: '/agent.html?github_install=connected' } });
  }
  if (path === '/github/webhook' && request.method === 'POST') {
    if (!env.GITHUB_WEBHOOK_SECRET) return json({ error: 'Webhook is not configured.' }, 503);
    const raw = await request.text();
    const signature = request.headers.get('X-Hub-Signature-256') || '';
    const key = await crypto.subtle.importKey('raw', enc.encode(env.GITHUB_WEBHOOK_SECRET), { name: 'HMAC', hash: 'SHA-256' }, false, ['verify']);
    const provided = signature.startsWith('sha256=') ? signature.slice(7) : '';
    let bytes;
    try { bytes = Uint8Array.from(provided.match(/.{2}/g) || [], x => parseInt(x, 16)); } catch { bytes = new Uint8Array(); }
    if (bytes.length !== 32 || !await crypto.subtle.verify('HMAC', key, bytes, enc.encode(raw))) return json({ error: 'Invalid webhook signature.' }, 401);
    const event = request.headers.get('X-GitHub-Event');
    const payload = JSON.parse(raw);
    const installationId = payload.installation?.id;
    if (event === 'installation' && payload.action === 'deleted' && installationId) await env.DB.prepare('DELETE FROM github_installations WHERE installation_id=?').bind(installationId).run();
    else if ((event === 'installation' || event === 'installation_repositories') && installationId) {
      const row = await env.DB.prepare('SELECT github_id FROM github_installations WHERE installation_id=?').bind(installationId).first();
      if (row) await syncInstallation(env, installationId, row.github_id);
    }
    return json({ ok: true });
  }
  if (path === '/api/conversations' && request.method === 'POST') {
    const invalid = requirePost(request, env); if (invalid) return invalid;
    if (!account) return json({ error: 'Sign in with GitHub first.' }, 401);
    const body = await readJson(request), target = body.report?.target || {};
    if (!target.owner || !target.repo || !target.sha) return json({ error: 'The scan must include a repository and immutable commit SHA.' }, 400);
    const installed = await repoForAccount(env, account, target.owner, target.repo);
    if (!installed) return json({ error: 'Install the Cerberus GitHub App for this repository first.' }, 409);
    const conversationId = id('cv_'), timestamp = epoch();
    await env.DB.prepare(`INSERT INTO conversations (id, github_id, repository_id, installation_id, owner, repo, base_ref, base_sha, report_json, created_at, updated_at)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`)
      .bind(conversationId, account.id, installed.repository_id, installed.installation_id, installed.owner, installed.name, target.ref || installed.default_branch, target.sha, JSON.stringify(body.report), timestamp, timestamp).run();
    return json({ id: conversationId, repository: installed.full_name, base_sha: target.sha }, 201);
  }
  const messageMatch = path.match(/^\/api\/conversations\/([^/]+)\/messages$/);
  if (messageMatch) {
    const invalid = requirePost(request, env); if (invalid) return invalid;
    if (!account) return json({ error: 'Sign in with GitHub first.' }, 401);
    const conversation = await ownedConversation(env, account, messageMatch[1]);
    if (!conversation) return json({ error: 'Conversation not found.' }, 404);
    const body = await readJson(request), content = String(body.content || '').trim();
    if (!content || content.length > 12000) return json({ error: 'Message must be between 1 and 12,000 characters.' }, 400);
    await env.DB.prepare("INSERT INTO messages (conversation_id, role, content, created_at) VALUES (?, 'user', ?, ?)").bind(conversation.id, content, epoch()).run();
    const result = await runAgent(env, account, conversation, content, String(body.model || 'gpt-5.6-sol'), request.headers.get('X-Pollinations-Key'));
    await env.DB.prepare("INSERT INTO messages (conversation_id, role, content, created_at) VALUES (?, 'assistant', ?, ?)").bind(conversation.id, result.content, epoch()).run();
    await env.DB.prepare('UPDATE conversations SET updated_at=? WHERE id=?').bind(epoch(), conversation.id).run();
    return json(result);
  }
  const changeMatch = path.match(/^\/api\/change-sets\/([^/]+)$/);
  if (path === '/api/change-sets/history' && request.method === 'GET') {
    if (!account) return json({ error: 'Sign in with GitHub first.' }, 401);
    const url = new URL(request.url), owner = url.searchParams.get('owner'), repo = url.searchParams.get('repo');
    if (!owner || !repo) return json({ error: 'owner and repo are required.' }, 400);
    const rows = await env.DB.prepare(`SELECT cs.*, pj.pr_url, pj.pr_number FROM change_sets cs LEFT JOIN pr_jobs pj ON pj.change_set_id=cs.id WHERE cs.github_id=? AND cs.repository_id IN (SELECT repository_id FROM installation_repositories WHERE lower(owner)=lower(?) AND lower(name)=lower(?)) ORDER BY cs.created_at DESC LIMIT 12`).bind(account.id, owner, repo).all();
    return json({ items: (rows.results || []).map(publicChangeSet) });
  }
  if (path === '/api/change-sets/latest' && request.method === 'GET') {
    if (!account) return json({ error: 'Sign in with GitHub first.' }, 401);
    const owner = new URL(request.url).searchParams.get('owner');
    const repo = new URL(request.url).searchParams.get('repo');
    const sha = new URL(request.url).searchParams.get('sha');
    if (!owner || !repo || !sha) return json({ error: 'owner, repo, and sha are required.' }, 400);
    const row = await env.DB.prepare(`SELECT change_sets.*, pr_jobs.pr_url, pr_jobs.pr_number FROM change_sets LEFT JOIN pr_jobs ON pr_jobs.change_set_id=change_sets.id WHERE change_sets.github_id=? AND change_sets.base_sha=? AND change_sets.repository_id IN (SELECT repository_id FROM installation_repositories WHERE lower(owner)=lower(?) AND lower(name)=lower(?)) ORDER BY change_sets.created_at DESC LIMIT 1`).bind(account.id, sha, owner, repo).first();
    return json(row ? publicChangeSet(row) : null);
  }
  if (changeMatch && request.method === 'GET') {
    if (!account) return json({ error: 'Sign in with GitHub first.' }, 401);
    const row = await env.DB.prepare(`SELECT change_sets.*, pr_jobs.pr_url, pr_jobs.pr_number FROM change_sets LEFT JOIN pr_jobs ON pr_jobs.change_set_id=change_sets.id WHERE change_sets.id=? AND change_sets.github_id=?`).bind(changeMatch[1], account.id).first();
    return row ? json(publicChangeSet(row)) : json({ error: 'Change set not found.' }, 404);
  }
  const prMatch = path.match(/^\/api\/change-sets\/([^/]+)\/create-pr$/);
  if (prMatch) {
    const invalid = requirePost(request, env); if (invalid) return invalid;
    if (!account) return json({ error: 'Sign in with GitHub first.' }, 401);
    const body = await readJson(request);
    if (body.approved !== true) return json({ error: 'Review and approve the complete change set before creating a pull request.' }, 400);
    const row = await env.DB.prepare('SELECT * FROM change_sets WHERE id=? AND github_id=?').bind(prMatch[1], account.id).first();
    if (!row) return json({ error: 'Change set not found.' }, 404);
    return json(await createDraftPr(env, account, row));
  }
  return json({ error: 'Not found.' }, 404);
}

export const testables = { safePath, sha256, repoForAccount, reportSummary };
