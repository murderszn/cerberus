# GitHub Connector

## Implemented: server-side account authentication

The browser uses these same-origin endpoints in `workers/github-auth/index.mjs`:

- `GET /auth/github/start`: random state, browser-bound HttpOnly flow cookie,
  ten-minute one-use D1 record, and S256 PKCE redirect to GitHub.
- `GET /auth/github/callback`: atomically consumes the state, exchanges the code
  with the server-held client secret and PKCE verifier, and fetches `/user` and
  `/user/emails`. A verified primary email is required. Accounts are keyed by
  GitHub's numeric ID, never by a mutable username or email.
- `GET /auth/github/session`: returns the signed-in account, or `user: null`.
- `POST /auth/github/logout`: requires the exact application Origin and a custom
  CSRF header, deletes the server session, and expires its cookie.

Sessions last seven days, use `__Host-` Secure/HttpOnly/SameSite=Lax cookies,
and are stored only as SHA-256 hashes. The OAuth token is used transiently for
identity; it is neither stored in D1 nor returned to the browser. Logout expires
Cerberus access; it does not revoke the GitHub OAuth application grant. Users
can revoke that grant in GitHub Settings → Applications.

The browser device flow was removed. Old device-flow credentials are cleared
on load. Manually entered scanning PATs remain separate. Account sign-in does
not increase scan API limits or grant private-repository access.

## Production setup (required before live sign-in works)

GitHub Pages cannot execute these endpoints. Serve the app and Worker on the
same HTTPS origin. This avoids cross-site session-cookie restrictions and CORS
configuration. The existing Pages deployment remains a static scanning app and
shows sign-in as unavailable. No client-ID-only browser configuration is needed.

1. Install the Cloudflare Wrangler CLI and authenticate with `wrangler login`.
2. From `workers/github-auth`, run `wrangler d1 create cerberus-accounts`.
   Put its returned database ID in `wrangler.jsonc`.
3. Choose the Worker HTTPS URL or custom domain. Set `APP_ORIGIN` to that exact
   origin (no trailing slash or path). Configure a custom domain in Cloudflare
   if using one. This app is served at the origin root.
4. Register a **GitHub OAuth App** in GitHub Settings → Developer settings:
   - Homepage: `https://YOUR-APP-ORIGIN/agent.html`
   - Authorization callback: `https://YOUR-APP-ORIGIN/auth/github/callback`
   - Device flow is not needed.
   Set `GITHUB_CLIENT_ID` in `wrangler.jsonc`. Store the secret using
   `wrangler secret put GITHUB_CLIENT_SECRET`; never place it in browser assets,
   committed files, or chat messages.
5. From the repository root run:

   ```sh
   node --test workers/github-auth/auth.test.mjs
   node workers/github-auth/build.mjs
   cd workers/github-auth
   wrangler d1 migrations apply cerberus-accounts --remote
   wrangler deploy
   ```

   The build copies only public website files to the ignored `public/` folder.
   Rebuild before each deployment. Do not point the asset directory at the repo
   root. The Worker has its own deployment; the Pages workflow does not deploy it.
6. Open `/agent.html` on the Worker origin, click Connect, authorize GitHub,
   confirm the displayed username, reload to check persistence, then Disconnect
   and reload to check logout. Check denied consent and a GitHub account without
   a verified primary email as well.

Do not call production ready until that real GitHub round trip succeeds. Local
automated tests use mocked GitHub responses and real SQLite queries; they do
not validate registered credentials or production Cloudflare configuration.

For local integration, apply migrations with `--local`, set local secrets in
ignored `workers/github-auth/.dev.vars`, and use `wrangler dev --local-protocol
https`. Match APP_ORIGIN and a separate test OAuth App callback to that HTTPS
local origin. Secure cookies require HTTPS.

## Account data and maintenance

The sign-in UI links to `documentation/privacy.html`. It discloses the stored
GitHub identity and verified primary email, session lifetime, and separate PAT
behavior. The scheduled Worker removes expired session and OAuth-flow rows
daily. Account records remain until deleted. To honor a verified account-deletion
request, delete the account by its numeric GitHub ID; the foreign key cascades
session deletion. For example, use the D1 console with a verified ID:

```sql
DELETE FROM accounts WHERE github_id = 123456;
```

Restrict D1 access to deployment operators. Worker observability is disabled to
avoid capturing callback URLs containing authorization codes; do not enable
request-URL logging for authentication callbacks without redaction.

## Implemented: repository agent and reviewed draft PRs

`workers/github-auth/agent.mjs` now provides the production repository path:

- `POST /github/install/start` and `GET /github/install/callback` bind a one-use,
  account-scoped GitHub App installation and its selected repositories.
- `POST /github/webhook` verifies the GitHub HMAC signature and synchronizes or
  removes installation records.
- `POST /api/conversations` pins a persistent agent session to the exact scanned
  commit. Messages and model responses are stored under the signed-in account.
- Repository tools list paths and read bounded text files at that pinned commit.
  A model cannot propose an edit until it has inspected the target path.
- Change sets contain complete before/after text for at most ten files. GitHub
  workflow files, git metadata, lockfiles, traversal paths, and oversized input
  are rejected.
- `POST /api/change-sets/:id/create-pr` requires explicit review approval, checks
  that the base branch has not moved, creates a deterministic branch and commit,
  and opens an idempotent draft pull request.

The Worker mints short-lived tokens scoped to one installation repository and
never stores or returns them. Configure the GitHub App with metadata read,
contents read/write, and pull requests read/write. Workflows permission is not
requested because workflow edits are excluded from this release.

Set `GITHUB_APP_ID` and `GITHUB_APP_SLUG` as Worker variables, then store
`GITHUB_APP_PRIVATE_KEY`, `GITHUB_WEBHOOK_SECRET`, and optionally a server-side
`POLLINATIONS_API_KEY` with `wrangler secret put`. The setup callback is
`https://YOUR-APP-ORIGIN/github/install/callback`; the webhook endpoint is
`https://YOUR-APP-ORIGIN/github/webhook`.

References:
- https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/authorizing-oauth-apps
- https://developers.cloudflare.com/workers/static-assets/binding/
- https://developers.cloudflare.com/d1/worker-api/prepared-statements/
- https://docs.github.com/en/apps/creating-github-apps/registering-a-github-app
- https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/authenticating-as-a-github-app-installation
