# Cerberus Check Catalog

This document is generated directly from `checks.json` by `scripts/generate-checks-docs.py` — do not hand-edit it. `checks.json` is the single source of truth consumed by the web app, `examine.py`, and this page (see `docs/IMPROVEMENTS.md` §2.2/§6).

**Total: 59 checks across 9 agents, weighted to 100 points.**

Every check resolves to one of four states at scan time: `pass`, `fail`, `not_applicable` (precondition unmet, reason stated), or `skipped` (could not be evaluated, reason stated).

## Agent index

| Agent | Domain | Weight | Checks |
|---|---|---|---|
| SENTINEL | Code Analysis | 14 | 11 |
| GATEKEEPER | Access Control | 12 | 6 |
| VAULT | Data Security | 13 | 8 |
| CONDUIT | Network & API | 11 | 5 |
| WATCHTOWER | Application Config | 11 | 8 |
| LIBRARIAN | Dependencies | 12 | 6 |
| SHIELD | Client Security | 11 | 6 |
| AUDITOR | Logging & Monitoring | 8 | 4 |
| ARCHITECT | Infrastructure | 8 | 5 |
| **Total** |  | **100** | **59** |

## Summary table

| Agent | ID | Check | Severity | CWE |
|---|---|---|---|---|
| SENTINEL | S-01 | Hardcoded credential assignment | CRITICAL | CWE-798 |
| SENTINEL | S-02 | AWS access key ID in source | CRITICAL | CWE-798 |
| SENTINEL | S-03 | Private key material committed | CRITICAL | CWE-321 |
| SENTINEL | S-04 | SQL built by string concatenation | CRITICAL | CWE-89 |
| SENTINEL | S-05 | Shell execution with interpolated input | CRITICAL | CWE-78 |
| SENTINEL | S-06 | Dynamic code evaluation | HIGH | CWE-95 |
| SENTINEL | S-06P | Python exec() on a dynamic value | HIGH | CWE-95 |
| SENTINEL | S-07 | Unsafe deserialization | HIGH | CWE-502 |
| SENTINEL | S-08 | Non-cryptographic randomness for security values | MEDIUM | CWE-338 |
| SENTINEL | S-09 | Path traversal in file access | HIGH | CWE-22 |
| SENTINEL | S-10 | Server-side request forgery risk | HIGH | CWE-918 |
| GATEKEEPER | G-01 | Signature verification disabled | CRITICAL | CWE-347 |
| GATEKEEPER | G-02 | Weak password length policy | HIGH | CWE-521 |
| GATEKEEPER | G-03 | Endpoint opted out of authentication | MEDIUM | CWE-306 |
| GATEKEEPER | G-04 | Default or hardcoded admin credentials | CRITICAL | CWE-1392 |
| GATEKEEPER | G-05 | Session cookie missing security flags | HIGH | CWE-1004 |
| GATEKEEPER | G-06 | Authorization decided on the client | MEDIUM | CWE-602 |
| VAULT | V-01 | Broken hash used for passwords | HIGH | CWE-916 |
| VAULT | V-02 | Weak cipher mode or static IV | HIGH | CWE-327 |
| VAULT | V-03 | Sensitive value written to stdout | MEDIUM | CWE-532 |
| VAULT | V-04 | Environment file committed to the repository | CRITICAL | CWE-538 |
| VAULT | V-05 | Key or certificate file committed | CRITICAL | CWE-312 |
| VAULT | V-06 | Database dump or datastore committed | MEDIUM | CWE-538 |
| VAULT | V-07 | .gitignore does not cover secret files | MEDIUM | CWE-1230 |
| VAULT | V-08 | Bearer or provider token literal | CRITICAL | CWE-798 |
| CONDUIT | C-01 | Wildcard CORS origin | HIGH | CWE-942 |
| CONDUIT | C-02 | Wildcard CORS combined with credentials | CRITICAL | CWE-942 |
| CONDUIT | C-03 | TLS certificate validation disabled | HIGH | CWE-295 |
| CONDUIT | C-04 | Cleartext HTTP endpoint | MEDIUM | CWE-319 |
| CONDUIT | C-05 | Service bound to all interfaces | MEDIUM | CWE-1327 |
| WATCHTOWER | W-01 | Debug mode enabled | HIGH | CWE-489 |
| WATCHTOWER | W-02 | Container runs as root | HIGH | CWE-250 |
| WATCHTOWER | W-03 | Unpinned base image tag | MEDIUM | CWE-1104 |
| WATCHTOWER | W-04 | Privileged container or host namespace | HIGH | CWE-250 |
| WATCHTOWER | W-05 | Plaintext secret in CI workflow | HIGH | CWE-798 |
| WATCHTOWER | W-06 | No security disclosure policy | MEDIUM | CWE-1059 |
| WATCHTOWER | W-07 | No license file | LOW | N/A |
| WATCHTOWER | W-08 | Security headers not configured | MEDIUM | CWE-693 |
| LIBRARIAN | L-01 | Dependency lockfile missing | MEDIUM | CWE-1104 |
| LIBRARIAN | L-02 | Known-vulnerable dependency version | HIGH | CWE-1395 |
| LIBRARIAN | L-03 | Dependency sourced from a URL or git ref | MEDIUM | CWE-829 |
| LIBRARIAN | L-04 | No automated dependency updates | LOW | CWE-1104 |
| LIBRARIAN | L-05 | Remote script piped to a shell | HIGH | CWE-494 |
| LIBRARIAN | L-06 | Unpinned third-party GitHub Action | MEDIUM | CWE-829 |
| SHIELD | F-01 | Auth token stored in web storage | HIGH | CWE-922 |
| SHIELD | F-02 | Unsanitised HTML injection sink | HIGH | CWE-79 |
| SHIELD | F-03 | document.write or legacy DOM sink | MEDIUM | CWE-79 |
| SHIELD | F-04 | postMessage without origin validation | MEDIUM | CWE-346 |
| SHIELD | F-05 | target="_blank" without rel protection | LOW | CWE-1022 |
| SHIELD | F-06 | Secret embedded in client-side code | CRITICAL | CWE-798 |
| AUDITOR | A-01 | Credentials passed to the logger | HIGH | CWE-532 |
| AUDITOR | A-02 | Stack trace returned to the client | MEDIUM | CWE-209 |
| AUDITOR | A-03 | Debug output left in source | LOW | CWE-489 |
| AUDITOR | A-04 | No continuous integration pipeline | MEDIUM | N/A |
| ARCHITECT | R-01 | Hardcoded IP address | MEDIUM | CWE-1327 |
| ARCHITECT | R-02 | Security group open to the internet | CRITICAL | CWE-284 |
| ARCHITECT | R-03 | Publicly readable object storage | HIGH | CWE-732 |
| ARCHITECT | R-04 | No automated tests | MEDIUM | N/A |
| ARCHITECT | R-05 | Terraform state committed | CRITICAL | CWE-538 |

---

## Detailed checks

### SENTINEL — Code Analysis (11 checks, weight 14)

#### S-01: Hardcoded credential assignment
* **Severity**: `CRITICAL`
* **CWE**: CWE-798
* **Summary**: A secret-looking variable is assigned a long literal string directly in source.
* **Risk**: Anyone who can read the repository — including every fork, every CI log, and every future clone — holds a working credential. Git history keeps it even after the line is deleted.
* **Remediation**: Move the value into an environment variable or a secrets manager, rotate the exposed credential immediately, and purge it from git history with `git filter-repo`.
* **Suggested fix**:
  ```diff
  - API_KEY = "sk_live_9f2b1c8e4a7d0553"
  + import os
  + API_KEY = os.environ["API_KEY"]   # set in your secrets manager / .env (gitignored)
  ```

#### S-02: AWS access key ID in source
* **Severity**: `CRITICAL`
* **CWE**: CWE-798
* **Summary**: A literal matching the AWS access key ID format (AKIA/ASIA + 16 chars) appears in the repository.
* **Risk**: AWS key IDs are harvested from public GitHub within minutes by automated scrapers. Paired with a secret key this grants direct access to your cloud account.
* **Remediation**: Deactivate the key in IAM right now, then re-issue via IAM roles or AWS SSO instead of long-lived keys.
* **Suggested fix**:
  ```bash
  aws iam update-access-key --access-key-id AKIA... --status Inactive
  aws iam delete-access-key --access-key-id AKIA...
  ```

#### S-03: Private key material committed
* **Severity**: `CRITICAL`
* **CWE**: CWE-321
* **Summary**: A PEM private key block is embedded in a tracked file.
* **Risk**: A leaked private key lets an attacker impersonate your service, decrypt intercepted traffic, or sign artifacts as you.
* **Remediation**: Revoke and reissue the key pair, then load keys at runtime from a mounted secret or KMS — never from the repo.

#### S-04: SQL built by string concatenation
* **Severity**: `CRITICAL`
* **CWE**: CWE-89
* **Summary**: A SQL statement is assembled with f-strings, `+`, `%`, or `.format()` rather than bound parameters.
* **Risk**: Any user-controlled value reaching this query can rewrite it — reading other tenants' rows, dumping the user table, or dropping it.
* **Remediation**: Use parameter binding for every dynamic value. Only table/column names may be interpolated, and only from a fixed allow-list.
* **Suggested fix**:
  ```diff
  - cursor.execute(f"SELECT * FROM users WHERE email = '{email}'")
  + cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
  ```

#### S-05: Shell execution with interpolated input
* **Severity**: `CRITICAL`
* **CWE**: CWE-78
* **Summary**: An OS command is run through a shell with a dynamically built string, or with `shell=True`.
* **Risk**: A `;`, backtick, or `$()` in any interpolated value becomes arbitrary code execution on the host running the process.
* **Remediation**: Pass arguments as a list with `shell=False` (the default) and validate any value that reaches the argv.
* **Suggested fix**:
  ```diff
  - subprocess.run(f"git clone {repo_url}", shell=True)
  + subprocess.run(["git", "clone", repo_url], shell=False, check=True)
  ```

#### S-06: Dynamic code evaluation
* **Severity**: `HIGH`
* **CWE**: CWE-95
* **Summary**: `eval`, `exec`, `new Function`, or `setTimeout(string)` is called on a non-literal value.
* **Risk**: If the evaluated string is influenced by input, request data, or config fetched at runtime, it is remote code execution.
* **Remediation**: Replace with an explicit parser (`JSON.parse`, `ast.literal_eval`) or a dispatch table keyed by known-safe names.

#### S-06P: Python exec() on a dynamic value
* **Severity**: `HIGH`
* **CWE**: CWE-95
* **Summary**: Python's builtin `exec()` is called on a non-literal value.
* **Risk**: `exec` compiles and runs whatever string it is handed. If that string is influenced by input or remote config, it is remote code execution.
* **Remediation**: Use `ast.literal_eval` for data, or a dispatch dict keyed by known-safe names for behaviour.

#### S-07: Unsafe deserialization
* **Severity**: `HIGH`
* **CWE**: CWE-502
* **Summary**: Untrusted bytes are loaded through pickle, `yaml.load` without a safe loader, or Java/PHP native deserialization.
* **Risk**: These formats can instantiate arbitrary classes on load — a crafted payload runs code before your first line of validation.
* **Remediation**: Use `yaml.safe_load`, JSON, or a schema-validated format. Never unpickle data that crossed a trust boundary.
* **Suggested fix**:
  ```diff
  - config = yaml.load(untrusted_bytes)
  + config = yaml.safe_load(untrusted_bytes)
  ```

#### S-08: Non-cryptographic randomness for security values
* **Severity**: `MEDIUM`
* **CWE**: CWE-338
* **Summary**: `Math.random()` or `random.random()` is used near a token, password, nonce, or ID.
* **Risk**: These generators are predictable from a handful of outputs, so an attacker can forecast reset tokens or session identifiers.
* **Remediation**: Use `crypto.randomUUID()` / `crypto.randomBytes()` in Node, `secrets.token_urlsafe()` in Python.
* **Suggested fix**:
  ```diff
  - const token = Math.random().toString(36).slice(2);
  + const token = crypto.randomUUID();
  ```

#### S-09: Path traversal in file access
* **Severity**: `HIGH`
* **CWE**: CWE-22
* **Summary**: A filesystem path is built from request/user input without normalisation.
* **Risk**: `../../etc/passwd` style input reads or overwrites files outside the intended directory.
* **Remediation**: Resolve the path and assert it stays within a base directory before opening it.
* **Suggested fix**:
  ```python
  base = Path("/srv/uploads").resolve()
  target = (base / user_path).resolve()
  if not target.is_relative_to(base):
      raise PermissionError("path escapes upload root")
  ```

#### S-10: Server-side request forgery risk
* **Severity**: `HIGH`
* **CWE**: CWE-918
* **Summary**: An outbound HTTP request targets a URL taken from request input.
* **Risk**: An attacker can point the request at internal services or the cloud metadata endpoint (169.254.169.254) and read credentials.
* **Remediation**: Validate the destination against an allow-list of hosts and block link-local, loopback, and private ranges.

---

### GATEKEEPER — Access Control (6 checks, weight 12)

#### G-01: Signature verification disabled
* **Severity**: `CRITICAL`
* **CWE**: CWE-347
* **Summary**: JWT or token verification is switched off, or the `none` algorithm is accepted.
* **Risk**: Anyone can mint a token claiming to be any user, including an administrator. Authentication is effectively absent.
* **Remediation**: Always verify with an explicit algorithm allow-list (`algorithms=["RS256"]`) and never accept `none`.
* **Suggested fix**:
  ```diff
  - jwt.decode(token, options={"verify_signature": False})
  + jwt.decode(token, PUBLIC_KEY, algorithms=["RS256"], audience=API_AUDIENCE)
  ```

#### G-02: Weak password length policy
* **Severity**: `HIGH`
* **CWE**: CWE-521
* **Summary**: Password validation accepts fewer than 8 characters.
* **Risk**: Short passwords fall to offline cracking in seconds regardless of how well you hash them.
* **Remediation**: Require at least 12 characters and screen against a breached-password list (e.g. Have I Been Pwned range API).

#### G-03: Endpoint opted out of authentication
* **Severity**: `MEDIUM`
* **CWE**: CWE-306
* **Summary**: A route is explicitly marked as public via `AllowAny`, `@csrf_exempt`, `authenticate: false`, or similar.
* **Risk**: Each opt-out is an unauthenticated entry point. They accumulate silently and are rarely re-reviewed.
* **Remediation**: Default to deny. Keep an audited list of intentionally public routes and assert it in a test.

#### G-04: Default or hardcoded admin credentials
* **Severity**: `CRITICAL`
* **CWE**: CWE-1392
* **Summary**: An admin/root username is paired with a literal password in source or config.
* **Risk**: Default credentials are the single most reliable way into a self-hosted deployment; scanners try them first.
* **Remediation**: Generate the initial admin password at install time, force rotation on first login, and never ship a fallback.

#### G-05: Session cookie missing security flags
* **Severity**: `HIGH`
* **CWE**: CWE-1004
* **Summary**: A cookie is set with `httpOnly` or `secure` explicitly false, or a session cookie config omits both.
* **Risk**: Without `httpOnly` any XSS reads the session; without `secure` it leaks over plain HTTP on a hostile network.
* **Remediation**: Set `httpOnly: true`, `secure: true`, and `sameSite: 'lax'` (or `'strict'`) on every session cookie.
* **Suggested fix**:
  ```javascript
  res.cookie('sid', token, {
    httpOnly: true,
    secure: true,
    sameSite: 'lax',
    maxAge: 1000 * 60 * 60 * 8
  });
  ```

#### G-06: Authorization decided on the client
* **Severity**: `MEDIUM`
* **CWE**: CWE-602
* **Summary**: A role or admin flag is read from local/session storage or a decoded token without server verification.
* **Risk**: Anything the browser stores, the user edits. Client-side role checks are UI hints, not access control.
* **Remediation**: Re-check the caller's role server-side on every privileged request; treat client state as untrusted display data.

---

### VAULT — Data Security (8 checks, weight 13)

#### V-01: Broken hash used for passwords
* **Severity**: `HIGH`
* **CWE**: CWE-916
* **Summary**: MD5 or SHA-1 is applied to a password or credential value.
* **Risk**: Commodity GPUs test billions of MD5/SHA-1 candidates per second; a stolen table is cracked, not merely exposed.
* **Remediation**: Use Argon2id (preferred), bcrypt, or scrypt with tuned work factors, and re-hash on next successful login.
* **Suggested fix**:
  ```diff
  - digest = hashlib.md5(password.encode()).hexdigest()
  + from argon2 import PasswordHasher
  + digest = PasswordHasher().hash(password)
  ```

#### V-02: Weak cipher mode or static IV
* **Severity**: `HIGH`
* **CWE**: CWE-327
* **Summary**: ECB mode, DES/RC4, or a hardcoded initialisation vector is used for encryption.
* **Risk**: ECB leaks structure in ciphertext and a reused IV in CBC/CTR lets an attacker recover plaintext across messages.
* **Remediation**: Use AES-GCM or ChaCha20-Poly1305 with a fresh random nonce per message.

#### V-03: Sensitive value written to stdout
* **Severity**: `MEDIUM`
* **CWE**: CWE-532
* **Summary**: A print/console statement includes a password, token, SSN, or card field.
* **Risk**: Container stdout is shipped to log aggregators, retained for months, and readable by anyone with dashboard access.
* **Remediation**: Remove the statement or mask the value; add a redaction filter in the logging pipeline as a backstop.

#### V-04: Environment file committed to the repository
* **Severity**: `CRITICAL`
* **CWE**: CWE-538
* **Summary**: A real `.env` file (not `.env.example`) is tracked in git.
* **Risk**: Env files are where production credentials live. Committed once, they stay in history and in every clone forever.
* **Remediation**: `git rm --cached .env`, add it to `.gitignore`, rotate every value it contained, then scrub history.
* **Suggested fix**:
  ```bash
  git rm --cached .env
  echo '.env' >> .gitignore
  git commit -m 'chore: stop tracking .env'
  # then rotate every credential it held
  ```

#### V-05: Key or certificate file committed
* **Severity**: `CRITICAL`
* **CWE**: CWE-312
* **Summary**: A `.pem`, `.key`, `.p12`, `.pfx`, `.keystore`, or SSH private key file is tracked.
* **Risk**: Committed key material must be treated as compromised the moment it is pushed.
* **Remediation**: Revoke and reissue, then deliver keys through a secret mount or KMS at deploy time.

#### V-06: Database dump or datastore committed
* **Severity**: `MEDIUM`
* **CWE**: CWE-538
* **Summary**: A `.sqlite`, `.db`, or `.sql` dump file is tracked in the repository.
* **Risk**: Development databases routinely contain copies of real user records, and often password hashes.
* **Remediation**: Remove the file, gitignore the pattern, and seed local databases from a fixtures script instead.

#### V-07: .gitignore does not cover secret files
* **Severity**: `MEDIUM`
* **CWE**: CWE-1230
* **Summary**: The repository has a `.gitignore` but it does not exclude `.env` or key material.
* **Risk**: Without the ignore rule, the next `git add .` commits whatever credentials happen to be on disk.
* **Remediation**: Add the standard secret patterns to `.gitignore` before they get committed.
* **Suggested fix**:
  ```text
  # secrets
  .env
  .env.*
  !.env.example
  *.pem
  *.key
  *.p12
  credentials.json
  ```

#### V-08: Bearer or provider token literal
* **Severity**: `CRITICAL`
* **CWE**: CWE-798
* **Summary**: A recognisable provider token prefix (GitHub, Slack, Stripe, Google, OpenAI, Anthropic) appears as a literal.
* **Risk**: These are directly usable credentials with a known issuer, so exploitation needs no guesswork at all.
* **Remediation**: Revoke at the provider immediately, then load from the environment at runtime.

---

### CONDUIT — Network & API (5 checks, weight 11)

#### C-01: Wildcard CORS origin
* **Severity**: `HIGH`
* **CWE**: CWE-942
* **Summary**: `Access-Control-Allow-Origin` is set to `*`, or the CORS middleware allows all origins.
* **Risk**: Any website can call your API from a visitor's browser. On a cookie-authenticated API this is cross-origin data theft.
* **Remediation**: Enumerate trusted origins explicitly and reject everything else.
* **Suggested fix**:
  ```diff
  - app.use(cors({ origin: '*' }))
  + app.use(cors({ origin: ['https://app.example.com'], credentials: true }))
  ```

#### C-02: Wildcard CORS combined with credentials
* **Severity**: `CRITICAL`
* **CWE**: CWE-942
* **Summary**: Credentialed CORS is enabled alongside a permissive origin policy.
* **Risk**: Attacker-controlled pages can issue authenticated requests as the logged-in victim and read the responses.
* **Remediation**: Never combine `credentials: true` with a reflected or wildcard origin — pin to an explicit host list.

#### C-03: TLS certificate validation disabled
* **Severity**: `HIGH`
* **CWE**: CWE-295
* **Summary**: An HTTP client is configured with `verify=False`, `rejectUnauthorized: false`, or `InsecureSkipVerify`.
* **Risk**: TLS without certificate validation stops any active attacker on the path from being detected — HTTPS becomes decoration.
* **Remediation**: Keep validation on. For internal CAs, install the CA bundle rather than disabling the check.
* **Suggested fix**:
  ```diff
  - requests.get(url, verify=False)
  + requests.get(url, verify="/etc/ssl/certs/internal-ca.pem")
  ```

#### C-04: Cleartext HTTP endpoint
* **Severity**: `MEDIUM`
* **CWE**: CWE-319
* **Summary**: A non-local `http://` URL is used for an API or asset.
* **Risk**: Requests and any tokens they carry are readable and modifiable by anyone on the network path.
* **Remediation**: Switch to `https://` and add HSTS so downgrades are refused.

#### C-05: Service bound to all interfaces
* **Severity**: `MEDIUM`
* **CWE**: CWE-1327
* **Summary**: A server listens on `0.0.0.0` outside of a container entrypoint.
* **Risk**: Services intended for localhost become reachable from the network, and from the internet on a misconfigured host.
* **Remediation**: Bind to `127.0.0.1` and place a reverse proxy in front of anything that must be public.

---

### WATCHTOWER — Application Config (8 checks, weight 11)

#### W-01: Debug mode enabled
* **Severity**: `HIGH`
* **CWE**: CWE-489
* **Summary**: `DEBUG = True`, `app.run(debug=True)`, or an equivalent development flag is set in committed config.
* **Risk**: Debug handlers expose stack traces, settings, and — in Flask/Django — an interactive console that executes code.
* **Remediation**: Drive the flag from the environment and default it to off.
* **Suggested fix**:
  ```diff
  - DEBUG = True
  + DEBUG = os.environ.get("DEBUG", "").lower() == "true"   # off unless explicitly enabled
  ```

#### W-02: Container runs as root
* **Severity**: `HIGH`
* **CWE**: CWE-250
* **Summary**: A Dockerfile never drops privileges — no `USER` instruction, or it explicitly sets `USER root`.
* **Risk**: A process escape or a mounted host path gives the attacker root on the node instead of an unprivileged account.
* **Remediation**: Create a non-root user and switch to it before the entrypoint.
* **Suggested fix**:
  ```dockerfile
  RUN adduser --system --uid 10001 appuser
  USER appuser
  CMD ["node", "server.js"]
  ```

#### W-03: Unpinned base image tag
* **Severity**: `MEDIUM`
* **CWE**: CWE-1104
* **Summary**: A Dockerfile uses `:latest` or omits the tag entirely.
* **Risk**: Builds are not reproducible and a compromised or breaking upstream image ships straight to production.
* **Remediation**: Pin to a digest: `FROM node:20.11-alpine@sha256:...`.

#### W-04: Privileged container or host namespace
* **Severity**: `HIGH`
* **CWE**: CWE-250
* **Summary**: A compose or Kubernetes manifest requests `privileged: true`, `hostNetwork`, `hostPID`, or docker socket access.
* **Risk**: A privileged container is functionally root on the host; the docker socket is a full container escape.
* **Remediation**: Drop the privilege, add only the specific capabilities needed, and never mount `/var/run/docker.sock`.

#### W-05: Plaintext secret in CI workflow
* **Severity**: `HIGH`
* **CWE**: CWE-798
* **Summary**: A CI workflow sets a token or password to a literal value instead of referencing the secrets store.
* **Risk**: Workflow files are public on public repos, and the value is echoed into build logs on failure.
* **Remediation**: Reference `${{ secrets.NAME }}` (GitHub) or the equivalent masked variable in your CI provider.
* **Suggested fix**:
  ```diff
  - env:
  -   NPM_TOKEN: npm_9f2b1c8e4a7d0553aa11
  + env:
  +   NPM_TOKEN: ${{ secrets.NPM_TOKEN }}
  ```

#### W-06: No security disclosure policy
* **Severity**: `MEDIUM`
* **CWE**: CWE-1059
* **Summary**: The repository has no `SECURITY.md`.
* **Risk**: Researchers who find a flaw have no private channel, so issues get filed publicly — or sold.
* **Remediation**: Add `SECURITY.md` with a contact address, supported versions, and expected response time.
* **Suggested fix**:
  ```markdown
  # Security Policy
  
  ## Reporting a Vulnerability
  Email security@example.com. We acknowledge within 2 business days
  and aim to ship a fix within 30 days.
  
  ## Supported Versions
  | Version | Supported |
  |---------|-----------|
  | 2.x     | yes       |
  | < 2.0   | no        |
  ```

#### W-07: No license file
* **Severity**: `LOW`
* **Summary**: The repository does not declare a license.
* **Risk**: Without a license the code is all-rights-reserved by default, which blocks legitimate reuse and complicates audits.
* **Remediation**: Add a `LICENSE` file, or state the proprietary terms explicitly if the code is closed.

#### W-08: Security headers not configured
* **Severity**: `MEDIUM`
* **CWE**: CWE-693
* **Summary**: No Content-Security-Policy, HSTS, or X-Frame-Options configuration found anywhere in the repository.
* **Risk**: Missing CSP removes the main mitigation for XSS; missing frame protection allows clickjacking of authenticated views.
* **Remediation**: Add a security-headers middleware (helmet, django-csp, secure.py) or set them at the edge/CDN.
* **Suggested fix**:
  ```javascript
  import helmet from 'helmet';
  app.use(helmet({
    contentSecurityPolicy: { directives: { defaultSrc: ["'self'"] } },
    hsts: { maxAge: 31536000, includeSubDomains: true }
  }));
  ```

---

### LIBRARIAN — Dependencies (6 checks, weight 12)

#### L-01: Dependency lockfile missing
* **Severity**: `MEDIUM`
* **CWE**: CWE-1104
* **Summary**: A manifest declares dependencies but no lockfile pins the resolved versions.
* **Risk**: Every install can pull different transitive code. A hijacked patch release lands in production without a diff.
* **Remediation**: Commit the lockfile your package manager produces and install with `npm ci` / `pip install -r requirements.txt --require-hashes`.

#### L-02: Known-vulnerable dependency version
* **Severity**: `HIGH`
* **CWE**: CWE-1395
* **Summary**: A manifest pins a package version with a published CVE.
* **Risk**: Public advisories come with public exploits; these are the first things scanned for on an exposed service.
* **Remediation**: Upgrade to the patched release and enable automated dependency updates so this does not recur.

#### L-03: Dependency sourced from a URL or git ref
* **Severity**: `MEDIUM`
* **CWE**: CWE-829
* **Summary**: A dependency is installed from a git URL or tarball rather than a registry release.
* **Risk**: A moving branch reference means the code can change under you with no version bump and no audit trail.
* **Remediation**: Publish an internal registry package, or at minimum pin to an immutable commit SHA.

#### L-04: No automated dependency updates
* **Severity**: `LOW`
* **CWE**: CWE-1104
* **Summary**: No Dependabot or Renovate configuration is present.
* **Risk**: Patch lag is the dominant cause of exploited dependency CVEs; manual upgrades slip.
* **Remediation**: Add `.github/dependabot.yml` or a Renovate config so upgrade PRs open automatically.
* **Suggested fix**:
  ```yaml
  version: 2
  updates:
    - package-ecosystem: npm
      directory: "/"
      schedule: { interval: weekly }
      open-pull-requests-limit: 10
  ```

#### L-05: Remote script piped to a shell
* **Severity**: `HIGH`
* **CWE**: CWE-494
* **Summary**: A build or CI step pipes `curl`/`wget` output directly into `bash` or `sh`.
* **Risk**: The remote server decides what code runs on your builder, and can serve different content to you than to reviewers.
* **Remediation**: Download to a file, verify a pinned checksum or signature, then execute.
* **Suggested fix**:
  ```bash
  curl -fsSL -o install.sh https://example.com/install.sh
  echo "<known-sha256>  install.sh" | sha256sum -c -
  sh install.sh
  ```

#### L-06: Unpinned third-party GitHub Action
* **Severity**: `MEDIUM`
* **CWE**: CWE-829
* **Summary**: A workflow references a third-party action by branch or floating tag instead of a commit SHA.
* **Risk**: The action author — or anyone who compromises their account — can retroactively change what runs with your repo token.
* **Remediation**: Pin third-party actions to a full commit SHA and let Dependabot bump them.
* **Suggested fix**:
  ```diff
  - uses: some-org/deploy-action@main
  + uses: some-org/deploy-action@a1b2c3d4e5f60718293a4b5c6d7e8f9012345678  # v3.1.0
  ```

---

### SHIELD — Client Security (6 checks, weight 11)

#### F-01: Auth token stored in web storage
* **Severity**: `HIGH`
* **CWE**: CWE-922
* **Summary**: A JWT, session, or auth token is written to `localStorage` or `sessionStorage`.
* **Risk**: Web storage is readable by any script on the page, so a single XSS or a compromised npm package exfiltrates every session.
* **Remediation**: Keep the session in an `HttpOnly; Secure; SameSite` cookie so script cannot read it.
* **Suggested fix**:
  ```diff
  - localStorage.setItem('token', res.data.token);
  + // server sets: Set-Cookie: sid=...; HttpOnly; Secure; SameSite=Lax
  + // client sends credentials automatically:
  + fetch('/api/me', { credentials: 'include' });
  ```

#### F-02: Unsanitised HTML injection sink
* **Severity**: `HIGH`
* **CWE**: CWE-79
* **Summary**: `dangerouslySetInnerHTML`, `v-html`, `[innerHTML]`, or a direct `innerHTML =` assignment is used.
* **Risk**: If any part of that string is user-controlled it becomes stored XSS — session theft, keylogging, or account takeover.
* **Remediation**: Render as text, or sanitise with DOMPurify immediately before insertion.
* **Suggested fix**:
  ```diff
  - <div dangerouslySetInnerHTML={{ __html: comment.body }} />
  + import DOMPurify from 'dompurify';
  + <div dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(comment.body) }} />
  ```

#### F-03: document.write or legacy DOM sink
* **Severity**: `MEDIUM`
* **CWE**: CWE-79
* **Summary**: `document.write` is used, which parses its argument as HTML.
* **Risk**: It is an XSS sink, blocks the parser, and is ignored entirely in async script contexts.
* **Remediation**: Build nodes with `createElement`/`textContent` and append them.

#### F-04: postMessage without origin validation
* **Severity**: `MEDIUM`
* **CWE**: CWE-346
* **Summary**: A `message` listener does not check `event.origin`, or `postMessage` targets `*`.
* **Risk**: Any framing or opened window can send messages your handler trusts, or read messages you broadcast.
* **Remediation**: Compare `event.origin` against an exact expected origin and pass a specific target origin when sending.
* **Suggested fix**:
  ```javascript
  window.addEventListener('message', (e) => {
    if (e.origin !== 'https://trusted.example.com') return;
    handle(e.data);
  });
  ```

#### F-05: target="_blank" without rel protection
* **Severity**: `LOW`
* **CWE**: CWE-1022
* **Summary**: An anchor opens a new tab without `rel="noopener"`.
* **Risk**: In older browsers the opened page can redirect the original tab via `window.opener` — a credible phishing pivot.
* **Remediation**: Add `rel="noopener noreferrer"` to every `target="_blank"` link.

#### F-06: Secret embedded in client-side code
* **Severity**: `CRITICAL`
* **CWE**: CWE-798
* **Summary**: A credential literal appears in a file that ships to the browser.
* **Risk**: Anything in the bundle is public — view-source is all the attacker needs, regardless of build-time obfuscation.
* **Remediation**: Proxy the call through your backend and keep the credential server-side.

---

### AUDITOR — Logging & Monitoring (4 checks, weight 8)

#### A-01: Credentials passed to the logger
* **Severity**: `HIGH`
* **CWE**: CWE-532
* **Summary**: A structured log call includes a password, key, or secret field.
* **Risk**: Log aggregators have far broader access than production databases, and retain data long after rotation.
* **Remediation**: Redact sensitive keys in a log processor and pass identifiers, not credentials.
* **Suggested fix**:
  ```diff
  - logger.info("login attempt", { email, password });
  + logger.info("login attempt", { email, hasPassword: Boolean(password) });
  ```

#### A-02: Stack trace returned to the client
* **Severity**: `MEDIUM`
* **CWE**: CWE-209
* **Summary**: An error handler sends `err.stack`, `traceback`, or the raw exception in the HTTP response.
* **Risk**: Traces reveal file paths, framework versions, and query structure — the reconnaissance step of a real attack.
* **Remediation**: Return a generic message plus a correlation ID, and log the detail server-side.
* **Suggested fix**:
  ```diff
  - res.status(500).json({ error: err.stack });
  + const ref = crypto.randomUUID();
  + logger.error({ ref, err });
  + res.status(500).json({ error: 'Internal error', ref });
  ```

#### A-03: Debug output left in source
* **Severity**: `LOW`
* **CWE**: CWE-489
* **Summary**: `console.log`, bare `print`, or `debugger` statements remain in non-test source.
* **Risk**: Noisy logs bury real signals, and `debugger` halts execution in any browser with devtools open.
* **Remediation**: Route through a level-aware logger and enforce `no-console` / `no-debugger` in lint.

#### A-04: No continuous integration pipeline
* **Severity**: `MEDIUM`
* **Summary**: No CI configuration was found in the repository.
* **Risk**: Without automated checks, security linting and dependency audits depend on whoever remembers to run them.
* **Remediation**: Add a CI workflow that runs tests, a linter, and a dependency audit on every pull request.
* **Suggested fix**:
  ```yaml
  name: ci
  on: [push, pull_request]
  jobs:
    check:
      runs-on: ubuntu-latest
      steps:
        - uses: actions/checkout@v4
        - run: npm ci
        - run: npm test
        - run: npm audit --audit-level=high
  ```

---

### ARCHITECT — Infrastructure (5 checks, weight 8)

#### R-01: Hardcoded IP address
* **Severity**: `MEDIUM`
* **CWE**: CWE-1327
* **Summary**: A routable IPv4 literal is embedded in source or configuration.
* **Risk**: Infrastructure changes silently break the deployment, and the address discloses internal topology.
* **Remediation**: Resolve endpoints through DNS or service discovery and supply them as configuration.

#### R-02: Security group open to the internet
* **Severity**: `CRITICAL`
* **CWE**: CWE-284
* **Summary**: An infrastructure definition allows ingress from `0.0.0.0/0`.
* **Risk**: Databases and admin ports exposed this way are found by internet-wide scanners within hours of going live.
* **Remediation**: Restrict ingress to known CIDRs or a bastion/VPN security group; expose only 443 publicly.
* **Suggested fix**:
  ```diff
    ingress {
      from_port   = 5432
      to_port     = 5432
  -   cidr_blocks = ["0.0.0.0/0"]
  +   security_groups = [aws_security_group.app.id]
    }
  ```

#### R-03: Publicly readable object storage
* **Severity**: `HIGH`
* **CWE**: CWE-732
* **Summary**: A bucket or blob container is configured with a public-read ACL.
* **Risk**: Public buckets are the most common source of large-scale data exposure; they are indexed and enumerated continuously.
* **Remediation**: Block public access at the account level and serve objects through signed URLs or a CDN origin identity.

#### R-04: No automated tests
* **Severity**: `MEDIUM`
* **Summary**: No test directory or test files were found in the repository.
* **Risk**: Security fixes regress silently when nothing verifies the behaviour they depend on.
* **Remediation**: Add a test suite and wire it into CI, starting with the authentication and authorization paths.

#### R-05: Terraform state committed
* **Severity**: `CRITICAL`
* **CWE**: CWE-538
* **Summary**: A `.tfstate` file is tracked in the repository.
* **Risk**: Terraform state stores resource attributes in plaintext, routinely including database passwords and generated keys.
* **Remediation**: Move state to an encrypted remote backend (S3 + DynamoDB lock, Terraform Cloud) and gitignore `*.tfstate*`.
* **Suggested fix**:
  ```hcl
  terraform {
    backend "s3" {
      bucket         = "tf-state-prod"
      key            = "app/terraform.tfstate"
      encrypt        = true
      dynamodb_table = "tf-locks"
    }
  }
  ```

---
