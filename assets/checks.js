// GENERATED FILE — do not hand-edit.
// Produced by scripts/build-checks.py from checks.json.
// checks.json version: 2.0.0
window.CERBERUS_CHECKS = {
  "version": "2.0.0",
  "updated": "2026-08-02",
  "scoring": {
    "base": 100,
    "per_hit": {
      "critical": 4.0,
      "high": 2.0,
      "medium": 1.0,
      "low": 0.5
    },
    "default_hit_cap": 3
  },
  "agents": [
    {
      "id": "sentinel",
      "name": "SENTINEL",
      "domain": "Code Analysis",
      "weight": 14
    },
    {
      "id": "vault",
      "name": "VAULT",
      "domain": "Data Security",
      "weight": 13
    },
    {
      "id": "gatekeeper",
      "name": "GATEKEEPER",
      "domain": "Access Control",
      "weight": 12
    },
    {
      "id": "librarian",
      "name": "LIBRARIAN",
      "domain": "Dependencies",
      "weight": 12
    },
    {
      "id": "conduit",
      "name": "CONDUIT",
      "domain": "Network & API",
      "weight": 11
    },
    {
      "id": "watchtower",
      "name": "WATCHTOWER",
      "domain": "Application Config",
      "weight": 11
    },
    {
      "id": "shield",
      "name": "SHIELD",
      "domain": "Client Security",
      "weight": 11
    },
    {
      "id": "auditor",
      "name": "AUDITOR",
      "domain": "Logging & Monitoring",
      "weight": 8
    },
    {
      "id": "architect",
      "name": "ARCHITECT",
      "domain": "Infrastructure",
      "weight": 8
    }
  ],
  "source_globs": [
    "**/*.py",
    "**/*.js",
    "**/*.jsx",
    "**/*.ts",
    "**/*.tsx",
    "**/*.mjs",
    "**/*.cjs",
    "**/*.go",
    "**/*.java",
    "**/*.rb",
    "**/*.php",
    "**/*.cs",
    "**/*.rs",
    "**/*.kt",
    "**/*.swift",
    "**/*.scala",
    "**/*.sh",
    "**/*.bash",
    "**/*.json",
    "**/*.yml",
    "**/*.yaml",
    "**/*.toml",
    "**/*.ini",
    "**/*.cfg",
    "**/*.properties",
    "**/*.env*",
    "**/*.tf",
    "**/*.tfvars",
    "**/*.html",
    "**/*.vue",
    "**/*.svelte",
    "**/Dockerfile",
    "**/Dockerfile.*",
    "**/*.dockerfile",
    "**/Makefile",
    "**/*.gradle"
  ],
  "global_exclude": [
    "**/node_modules/**",
    "**/vendor/**",
    "**/.git/**",
    "**/dist/**",
    "**/build/**",
    "**/out/**",
    "**/target/**",
    "**/coverage/**",
    "**/.next/**",
    "**/.nuxt/**",
    "**/*.min.js",
    "**/*.min.css",
    "**/*.bundle.js",
    "**/*.map",
    "**/package-lock.json",
    "**/yarn.lock",
    "**/pnpm-lock.yaml",
    "**/poetry.lock",
    "**/Cargo.lock",
    "**/composer.lock",
    "**/Gemfile.lock",
    "**/go.sum",
    "**/*.snap",
    "**/__snapshots__/**",
    "**/migrations/**",
    "**/*.pb.go",
    "**/*_pb2.py",
    "**/.playwright-mcp/**",
    "**/__pycache__/**",
    "**/.venv/**",
    "**/venv/**",
    "**/.tox/**",
    "**/.cache/**",
    "**/.pytest_cache/**",
    "**/.mypy_cache/**",
    "**/.ruff_cache/**",
    "**/.idea/**",
    "**/.vscode/**",
    "**/*.lock",
    "**/.terraform/**",
    "**/site-packages/**"
  ],
  "test_paths": [
    "**/test/**",
    "**/tests/**",
    "**/spec/**",
    "**/__tests__/**",
    "**/testdata/**",
    "**/fixtures/**",
    "**/*.test.*",
    "**/*.spec.*",
    "**/test_*.py",
    "**/*_test.go",
    "**/examples/**",
    "**/example/**",
    "**/sample/**",
    "**/samples/**",
    "**/demo/**",
    "**/docs/**",
    "**/mock/**",
    "**/mocks/**",
    "**/*.md",
    "**/e2e/**",
    "**/playwright/**",
    "**/cypress/**",
    "**/*.e2e.*",
    "**/mock-server*",
    "**/__mocks__/**",
    "**/stories/**",
    "**/*.stories.*",
    "**/benchmark/**",
    "**/bench/**"
  ],
  "placeholder_pattern": "(?:example|sample|dummy|placeholder|your[-_]?|my[-_]?|test|fake|xxxx|1234567890|changeme|redacted|insert[-_]?|<[^>]*>|\\$\\{|\\{\\{|%s|process\\.env|os\\.environ|os\\.getenv|System\\.getenv|ENV\\[|config\\.|settings\\.|\\.\\.\\.)",
  "checks": [
    {
      "id": "S-01",
      "agent": "sentinel",
      "name": "Hardcoded credential assignment",
      "severity": "critical",
      "cwe": "CWE-798",
      "summary": "A secret-looking variable is assigned a long literal string directly in source.",
      "risk": "Anyone who can read the repository — including every fork, every CI log, and every future clone — holds a working credential. Git history keeps it even after the line is deleted.",
      "remediation": "Move the value into an environment variable or a secrets manager, rotate the exposed credential immediately, and purge it from git history with `git filter-repo`.",
      "fix": {
        "lang": "diff",
        "body": "- API_KEY = \"sk_live_9f2b1c8e4a7d0553\"\n+ import os\n+ API_KEY = os.environ[\"API_KEY\"]   # set in your secrets manager / .env (gitignored)"
      },
      "detector": {
        "kind": "content",
        "pattern": "(aws_access_key_id|aws_secret_access_key|api[_-]?key|apikey|secret[_-]?key|session[_-]?secret|jwt[_-]?secret|client[_-]?secret|private[_-]?token|auth[_-]?token|access[_-]?token|database[_-]?password|db[_-]?password|db[_-]?pass|slack[_-]?webhook|encryption[_-]?key)[\"']?\\s*[:=]\\s*[\"'][A-Za-z0-9_\\-+/=]{16,}[\"']",
        "flags": "i",
        "skip_if_placeholder": true,
        "exclude_tests": true,
        "scan_comments": true
      }
    },
    {
      "id": "S-02",
      "agent": "sentinel",
      "name": "AWS access key ID in source",
      "severity": "critical",
      "cwe": "CWE-798",
      "summary": "A literal matching the AWS access key ID format (AKIA/ASIA + 16 chars) appears in the repository.",
      "risk": "AWS key IDs are harvested from public GitHub within minutes by automated scrapers. Paired with a secret key this grants direct access to your cloud account.",
      "remediation": "Deactivate the key in IAM right now, then re-issue via IAM roles or AWS SSO instead of long-lived keys.",
      "fix": {
        "lang": "bash",
        "body": "aws iam update-access-key --access-key-id AKIA... --status Inactive\naws iam delete-access-key --access-key-id AKIA..."
      },
      "detector": {
        "kind": "content",
        "pattern": "\\b(AKIA|ASIA|AGPA|AIDA|AROA)[A-Z0-9]{16}\\b",
        "flags": "",
        "exclude_tests": true,
        "not_match": "AKIAIOSFODNN7EXAMPLE|EXAMPLE|example",
        "comment": "AKIAIOSFODNN7EXAMPLE is the key AWS itself uses throughout its own documentation; it appears in test fixtures constantly and is not a credential.",
        "scan_comments": true
      }
    },
    {
      "id": "S-03",
      "agent": "sentinel",
      "name": "Private key material committed",
      "severity": "critical",
      "cwe": "CWE-321",
      "summary": "A PEM private key block is embedded in a tracked file.",
      "risk": "A leaked private key lets an attacker impersonate your service, decrypt intercepted traffic, or sign artifacts as you.",
      "remediation": "Revoke and reissue the key pair, then load keys at runtime from a mounted secret or KMS — never from the repo.",
      "detector": {
        "kind": "content",
        "pattern": "-----BEGIN (RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY-----",
        "flags": "",
        "exclude_tests": false,
        "scan_comments": true
      }
    },
    {
      "id": "S-04",
      "agent": "sentinel",
      "name": "SQL built by string concatenation",
      "severity": "critical",
      "cwe": "CWE-89",
      "summary": "A SQL statement is assembled with f-strings, `+`, `%`, or `.format()` rather than bound parameters.",
      "risk": "Any user-controlled value reaching this query can rewrite it — reading other tenants' rows, dumping the user table, or dropping it.",
      "remediation": "Use parameter binding for every dynamic value. Only table/column names may be interpolated, and only from a fixed allow-list.",
      "fix": {
        "lang": "diff",
        "body": "- cursor.execute(f\"SELECT * FROM users WHERE email = '{email}'\")\n+ cursor.execute(\"SELECT * FROM users WHERE email = %s\", (email,))"
      },
      "detector": {
        "kind": "content",
        "pattern": "(execute|query|raw|exec)\\s*\\(\\s*f?[\"'`][^\"'`]*\\b(SELECT|INSERT|UPDATE|DELETE|DROP)\\b[^\"'`]*[\"'`]?\\s*(\\+|%\\s*[\\(\\w]|\\.format\\(|\\$\\{|\\{\\w)",
        "flags": "i",
        "exclude_tests": true
      }
    },
    {
      "id": "S-05",
      "agent": "sentinel",
      "name": "Shell execution with interpolated input",
      "severity": "critical",
      "cwe": "CWE-78",
      "summary": "An OS command is run through a shell with a dynamically built string, or with `shell=True`.",
      "risk": "A `;`, backtick, or `$()` in any interpolated value becomes arbitrary code execution on the host running the process.",
      "remediation": "Pass arguments as a list with `shell=False` (the default) and validate any value that reaches the argv.",
      "fix": {
        "lang": "diff",
        "body": "- subprocess.run(f\"git clone {repo_url}\", shell=True)\n+ subprocess.run([\"git\", \"clone\", repo_url], shell=False, check=True)"
      },
      "detector": {
        "kind": "content",
        "pattern": "(os\\.system|os\\.popen|subprocess\\.(run|call|Popen|check_output)|child_process\\.exec|execSync|shell_exec|passthru|system)\\s*\\(\\s*[f`\"'][^)]*(\\$\\{|\\{\\w|\\+\\s*\\w|%\\s*\\w)|shell\\s*[:=]\\s*(True|true)",
        "flags": "",
        "exclude_tests": true
      }
    },
    {
      "id": "S-06",
      "agent": "sentinel",
      "name": "Dynamic code evaluation",
      "severity": "high",
      "cwe": "CWE-95",
      "summary": "`eval`, `exec`, `new Function`, or `setTimeout(string)` is called on a non-literal value.",
      "risk": "If the evaluated string is influenced by input, request data, or config fetched at runtime, it is remote code execution.",
      "remediation": "Replace with an explicit parser (`JSON.parse`, `ast.literal_eval`) or a dispatch table keyed by known-safe names.",
      "detector": {
        "kind": "content",
        "pattern": "(^|[^.\\w$])eval\\s*\\(\\s*[^)\"'\\s][^)]*\\)|new\\s+Function\\s*\\(|setTimeout\\s*\\(\\s*[\"'`]",
        "flags": "",
        "exclude_tests": true,
        "comment": "The leading [^.\\w$] guard is load-bearing: without it this matched `regex.exec(s)`, the standard JS RegExp API, producing 46 false positives on a single repo. Python's builtin exec() is covered by S-06P.",
        "hit_cap": 3
      }
    },
    {
      "id": "S-06P",
      "agent": "sentinel",
      "name": "Python exec() on a dynamic value",
      "severity": "high",
      "cwe": "CWE-95",
      "summary": "Python's builtin `exec()` is called on a non-literal value.",
      "risk": "`exec` compiles and runs whatever string it is handed. If that string is influenced by input or remote config, it is remote code execution.",
      "remediation": "Use `ast.literal_eval` for data, or a dispatch dict keyed by known-safe names for behaviour.",
      "detector": {
        "kind": "content",
        "pattern": "(^|[^.\\w])exec\\s*\\(\\s*[^)\"'\\s][^)]*\\)",
        "flags": "",
        "include": [
          "**/*.py"
        ],
        "exclude_tests": true,
        "hit_cap": 3
      }
    },
    {
      "id": "S-07",
      "agent": "sentinel",
      "name": "Unsafe deserialization",
      "severity": "high",
      "cwe": "CWE-502",
      "summary": "Untrusted bytes are loaded through pickle, `yaml.load` without a safe loader, or Java/PHP native deserialization.",
      "risk": "These formats can instantiate arbitrary classes on load — a crafted payload runs code before your first line of validation.",
      "remediation": "Use `yaml.safe_load`, JSON, or a schema-validated format. Never unpickle data that crossed a trust boundary.",
      "fix": {
        "lang": "diff",
        "body": "- config = yaml.load(untrusted_bytes)\n+ config = yaml.safe_load(untrusted_bytes)"
      },
      "detector": {
        "kind": "content",
        "pattern": "pickle\\.loads?\\s*\\(|cPickle\\.loads?\\s*\\(|yaml\\.load\\s*\\([^)]*\\)(?!\\s*#\\s*safe)|marshal\\.loads\\s*\\(|unserialize\\s*\\(|readObject\\s*\\(",
        "flags": "",
        "exclude_tests": true,
        "not_match": "Loader\\s*=\\s*(yaml\\.)?(Safe|CSafe)Loader"
      }
    },
    {
      "id": "S-08",
      "agent": "sentinel",
      "name": "Non-cryptographic randomness for security values",
      "severity": "medium",
      "cwe": "CWE-338",
      "summary": "`Math.random()` or `random.random()` is used near a token, password, nonce, or ID.",
      "risk": "These generators are predictable from a handful of outputs, so an attacker can forecast reset tokens or session identifiers.",
      "remediation": "Use `crypto.randomUUID()` / `crypto.randomBytes()` in Node, `secrets.token_urlsafe()` in Python.",
      "fix": {
        "lang": "diff",
        "body": "- const token = Math.random().toString(36).slice(2);\n+ const token = crypto.randomUUID();"
      },
      "detector": {
        "kind": "content",
        "pattern": "(token|secret|password|passwd|nonce|salt|otp|session|reset|verif|api_?key)\\w*\\s*[:=][^\\n;]{0,80}(Math\\.random|random\\.random|random\\.randint|rand\\(\\)|mt_rand)",
        "flags": "i",
        "exclude_tests": true,
        "not_match": "RandomPassword|RandomBytes|randomUUID|SystemRandom|SecureRandom|crypto\\.|secrets\\.|pulumi|@random|randomSecure",
        "comment": "The case-insensitive flag made `random.random` match Pulumi's `random.RandomPassword`, a cryptographically secure generator — the exact opposite of the finding."
      }
    },
    {
      "id": "S-09",
      "agent": "sentinel",
      "name": "Path traversal in file access",
      "severity": "high",
      "cwe": "CWE-22",
      "summary": "A filesystem path is built from request/user input without normalisation.",
      "risk": "`../../etc/passwd` style input reads or overwrites files outside the intended directory.",
      "remediation": "Resolve the path and assert it stays within a base directory before opening it.",
      "fix": {
        "lang": "python",
        "body": "base = Path(\"/srv/uploads\").resolve()\ntarget = (base / user_path).resolve()\nif not target.is_relative_to(base):\n    raise PermissionError(\"path escapes upload root\")"
      },
      "detector": {
        "kind": "content",
        "pattern": "(open|readFile|readFileSync|sendFile|createReadStream|File|fopen)\\s*\\(\\s*[^)]{0,60}(req\\.(params|query|body)|request\\.(args|form|GET|POST)|params\\[|\\$_(GET|POST|REQUEST))",
        "flags": "",
        "exclude_tests": true
      }
    },
    {
      "id": "S-10",
      "agent": "sentinel",
      "name": "Server-side request forgery risk",
      "severity": "high",
      "cwe": "CWE-918",
      "summary": "An outbound HTTP request targets a URL taken from request input.",
      "risk": "An attacker can point the request at internal services or the cloud metadata endpoint (169.254.169.254) and read credentials.",
      "remediation": "Validate the destination against an allow-list of hosts and block link-local, loopback, and private ranges.",
      "detector": {
        "kind": "content",
        "pattern": "(requests\\.(get|post|put|head)|axios\\.(get|post)|fetch|urlopen|HttpClient|http\\.get)\\s*\\(\\s*[^)]{0,40}(req\\.(query|body|params)|request\\.(args|form|GET)|params\\[|\\$_(GET|POST))",
        "flags": "",
        "exclude_tests": true
      }
    },
    {
      "id": "G-01",
      "agent": "gatekeeper",
      "name": "Signature verification disabled",
      "severity": "critical",
      "cwe": "CWE-347",
      "summary": "JWT or token verification is switched off, or the `none` algorithm is accepted.",
      "risk": "Anyone can mint a token claiming to be any user, including an administrator. Authentication is effectively absent.",
      "remediation": "Always verify with an explicit algorithm allow-list (`algorithms=[\"RS256\"]`) and never accept `none`.",
      "fix": {
        "lang": "diff",
        "body": "- jwt.decode(token, options={\"verify_signature\": False})\n+ jwt.decode(token, PUBLIC_KEY, algorithms=[\"RS256\"], audience=API_AUDIENCE)"
      },
      "detector": {
        "kind": "content",
        "pattern": "algorithms?\\s*[:=]\\s*\\[?\\s*[\"']none[\"']|verify_signature[\"']?\\s*[:=]\\s*(False|false)|verify\\s*[:=]\\s*(False|false)|ignoreExpiration\\s*[:=]\\s*true",
        "flags": "",
        "exclude_tests": true
      }
    },
    {
      "id": "G-02",
      "agent": "gatekeeper",
      "name": "Weak password length policy",
      "severity": "high",
      "cwe": "CWE-521",
      "summary": "Password validation accepts fewer than 8 characters.",
      "risk": "Short passwords fall to offline cracking in seconds regardless of how well you hash them.",
      "remediation": "Require at least 12 characters and screen against a breached-password list (e.g. Have I Been Pwned range API).",
      "detector": {
        "kind": "content",
        "pattern": "password[^\\n]{0,60}(len\\(|\\.length|minLength|min_length|MinLength)\\s*[^\\n]{0,12}[<>=]{1,2}\\s*[1-7]\\b",
        "flags": "i",
        "exclude_tests": true
      }
    },
    {
      "id": "G-03",
      "agent": "gatekeeper",
      "name": "Endpoint opted out of authentication",
      "severity": "medium",
      "cwe": "CWE-306",
      "summary": "A route is explicitly marked as public via `AllowAny`, `@csrf_exempt`, `authenticate: false`, or similar.",
      "risk": "Each opt-out is an unauthenticated entry point. They accumulate silently and are rarely re-reviewed.",
      "remediation": "Default to deny. Keep an audited list of intentionally public routes and assert it in a test.",
      "detector": {
        "kind": "content",
        "pattern": "permission_classes\\s*=\\s*\\[?\\s*AllowAny|@csrf_exempt|authentication_classes\\s*=\\s*\\[\\s*\\]|auth\\s*[:=]\\s*(false|False)|requiresAuth\\s*[:=]\\s*false|AllowAnonymous",
        "flags": "",
        "exclude_tests": true,
        "exclude": [
          "**/script/**",
          "**/scripts/**",
          "**/build.*",
          "**/*.config.*"
        ]
      }
    },
    {
      "id": "G-04",
      "agent": "gatekeeper",
      "name": "Default or hardcoded admin credentials",
      "severity": "critical",
      "cwe": "CWE-1392",
      "summary": "An admin/root username is paired with a literal password in source or config.",
      "risk": "Default credentials are the single most reliable way into a self-hosted deployment; scanners try them first.",
      "remediation": "Generate the initial admin password at install time, force rotation on first login, and never ship a fallback.",
      "detector": {
        "kind": "content",
        "pattern": "(admin|root|superuser)[_-]?(password|passwd|pass|pwd)[\"']?\\s*[:=]\\s*[\"'][^\"'\\n]{3,}[\"']",
        "flags": "i",
        "skip_if_placeholder": true,
        "exclude_tests": true,
        "scan_comments": true
      }
    },
    {
      "id": "G-05",
      "agent": "gatekeeper",
      "name": "Session cookie missing security flags",
      "severity": "high",
      "cwe": "CWE-1004",
      "summary": "A cookie is set with `httpOnly` or `secure` explicitly false, or a session cookie config omits both.",
      "risk": "Without `httpOnly` any XSS reads the session; without `secure` it leaks over plain HTTP on a hostile network.",
      "remediation": "Set `httpOnly: true`, `secure: true`, and `sameSite: 'lax'` (or `'strict'`) on every session cookie.",
      "fix": {
        "lang": "javascript",
        "body": "res.cookie('sid', token, {\n  httpOnly: true,\n  secure: true,\n  sameSite: 'lax',\n  maxAge: 1000 * 60 * 60 * 8\n});"
      },
      "detector": {
        "kind": "content",
        "pattern": "(httpOnly|http_only|HttpOnly)\\s*[:=]\\s*(false|False)|(secure)\\s*[:=]\\s*(false|False)\\s*[,}]|SESSION_COOKIE_SECURE\\s*=\\s*False|CSRF_COOKIE_SECURE\\s*=\\s*False",
        "flags": "",
        "exclude_tests": true
      }
    },
    {
      "id": "G-06",
      "agent": "gatekeeper",
      "name": "Authorization decided on the client",
      "severity": "medium",
      "cwe": "CWE-602",
      "summary": "A role or admin flag is read from local/session storage or a decoded token without server verification.",
      "risk": "Anything the browser stores, the user edits. Client-side role checks are UI hints, not access control.",
      "remediation": "Re-check the caller's role server-side on every privileged request; treat client state as untrusted display data.",
      "detector": {
        "kind": "content",
        "pattern": "(localStorage|sessionStorage)\\.getItem\\s*\\(\\s*[\"'](role|isAdmin|is_admin|admin|permissions|scope)[\"']",
        "flags": "i",
        "exclude_tests": true
      }
    },
    {
      "id": "V-01",
      "agent": "vault",
      "name": "Broken hash used for passwords",
      "severity": "high",
      "cwe": "CWE-916",
      "summary": "MD5 or SHA-1 is applied to a password or credential value.",
      "risk": "Commodity GPUs test billions of MD5/SHA-1 candidates per second; a stolen table is cracked, not merely exposed.",
      "remediation": "Use Argon2id (preferred), bcrypt, or scrypt with tuned work factors, and re-hash on next successful login.",
      "fix": {
        "lang": "diff",
        "body": "- digest = hashlib.md5(password.encode()).hexdigest()\n+ from argon2 import PasswordHasher\n+ digest = PasswordHasher().hash(password)"
      },
      "detector": {
        "kind": "content",
        "pattern": "(md5|sha1)\\s*\\([^)\\n]{0,60}(pass|pwd|secret|credential|token)|(pass|pwd|password)\\w*[^\\n]{0,40}(hashlib\\.(md5|sha1)|createHash\\s*\\(\\s*[\"'](md5|sha1)[\"'])",
        "flags": "i",
        "exclude_tests": true
      }
    },
    {
      "id": "V-02",
      "agent": "vault",
      "name": "Weak cipher mode or static IV",
      "severity": "high",
      "cwe": "CWE-327",
      "summary": "ECB mode, DES/RC4, or a hardcoded initialisation vector is used for encryption.",
      "risk": "ECB leaks structure in ciphertext and a reused IV in CBC/CTR lets an attacker recover plaintext across messages.",
      "remediation": "Use AES-GCM or ChaCha20-Poly1305 with a fresh random nonce per message.",
      "detector": {
        "kind": "content",
        "pattern": "MODE_ECB|[\"']AES-\\d+-ECB[\"']|[\"']DES-|[\"']RC4[\"']|Cipher\\.getInstance\\s*\\(\\s*[\"'][^\"']*ECB|iv\\s*=\\s*[\"'][A-Za-z0-9+/=]{8,}[\"']",
        "flags": "i",
        "exclude_tests": true,
        "scan_comments": true
      }
    },
    {
      "id": "V-03",
      "agent": "vault",
      "name": "Sensitive value written to stdout",
      "severity": "medium",
      "cwe": "CWE-532",
      "summary": "A print/console statement includes a password, token, SSN, or card field.",
      "risk": "Container stdout is shipped to log aggregators, retained for months, and readable by anyone with dashboard access.",
      "remediation": "Remove the statement or mask the value; add a redaction filter in the logging pipeline as a backstop.",
      "detector": {
        "kind": "content",
        "pattern": "(print|console\\.(log|info|debug)|System\\.out\\.print\\w*|fmt\\.Print\\w*)\\s*\\([^)\\n]{0,80}(\\b(password|passwd|secret|ssn|social_security|credit_card|card_num|cvv|api_?key|private_key)s?\\b\\s*[,)}\\]]|\\$\\{[^}]{0,40}\\b(password|passwd|secret|ssn|credit_card|cvv|api_?key|private_key)\\b[^}]{0,20}\\})",
        "flags": "i",
        "exclude_tests": true,
        "comment": "Same prose-vs-value distinction as A-01. `console.log(\"Warning: SERVER_PASSWORD is not set\")` discloses nothing."
      }
    },
    {
      "id": "V-04",
      "agent": "vault",
      "name": "Environment file committed to the repository",
      "severity": "critical",
      "cwe": "CWE-538",
      "summary": "A real `.env` file (not `.env.example`) is tracked in git.",
      "risk": "Env files are where production credentials live. Committed once, they stay in history and in every clone forever.",
      "remediation": "`git rm --cached .env`, add it to `.gitignore`, rotate every value it contained, then scrub history.",
      "fix": {
        "lang": "bash",
        "body": "git rm --cached .env\necho '.env' >> .gitignore\ngit commit -m 'chore: stop tracking .env'\n# then rotate every credential it held"
      },
      "detector": {
        "kind": "path_forbidden",
        "paths": [
          "**/.env",
          "**/.env.local",
          "**/.env.production",
          "**/.env.prod",
          "**/.env.development"
        ],
        "exclude": [
          "**/.env.example",
          "**/.env.sample",
          "**/.env.template",
          "**/.env.dist"
        ]
      }
    },
    {
      "id": "V-05",
      "agent": "vault",
      "name": "Key or certificate file committed",
      "severity": "critical",
      "cwe": "CWE-312",
      "summary": "A `.pem`, `.key`, `.p12`, `.pfx`, `.keystore`, or SSH private key file is tracked.",
      "risk": "Committed key material must be treated as compromised the moment it is pushed.",
      "remediation": "Revoke and reissue, then deliver keys through a secret mount or KMS at deploy time.",
      "detector": {
        "kind": "path_forbidden",
        "paths": [
          "**/*.pem",
          "**/*.key",
          "**/*.p12",
          "**/*.pfx",
          "**/*.keystore",
          "**/*.jks",
          "**/id_rsa",
          "**/id_dsa",
          "**/id_ecdsa",
          "**/id_ed25519"
        ],
        "exclude": [
          "**/*.pub",
          "**/testdata/**",
          "**/fixtures/**",
          "**/*public*"
        ]
      }
    },
    {
      "id": "V-06",
      "agent": "vault",
      "name": "Database dump or datastore committed",
      "severity": "medium",
      "cwe": "CWE-538",
      "summary": "A `.sqlite`, `.db`, or `.sql` dump file is tracked in the repository.",
      "risk": "Development databases routinely contain copies of real user records, and often password hashes.",
      "remediation": "Remove the file, gitignore the pattern, and seed local databases from a fixtures script instead.",
      "detector": {
        "kind": "path_forbidden",
        "paths": [
          "**/*.sqlite",
          "**/*.sqlite3",
          "**/*.db",
          "**/dump.sql",
          "**/backup.sql",
          "**/*.bak"
        ],
        "exclude": [
          "**/testdata/**",
          "**/fixtures/**",
          "**/schema.sql",
          "**/migrations/**"
        ]
      }
    },
    {
      "id": "V-07",
      "agent": "vault",
      "name": ".gitignore does not cover secret files",
      "severity": "medium",
      "cwe": "CWE-1230",
      "summary": "The repository has a `.gitignore` but it does not exclude `.env` or key material.",
      "risk": "Without the ignore rule, the next `git add .` commits whatever credentials happen to be on disk.",
      "remediation": "Add the standard secret patterns to `.gitignore` before they get committed.",
      "fix": {
        "lang": "text",
        "body": "# secrets\n.env\n.env.*\n!.env.example\n*.pem\n*.key\n*.p12\ncredentials.json"
      },
      "applies_if": {
        "any_path": [
          "**/.gitignore"
        ]
      },
      "detector": {
        "kind": "content_required",
        "paths": [
          ".gitignore"
        ],
        "pattern": "^\\s*\\*?\\.?env|^\\s*\\*\\.pem|^\\s*\\*\\.key",
        "flags": "im"
      }
    },
    {
      "id": "V-08",
      "agent": "vault",
      "name": "Bearer or provider token literal",
      "severity": "critical",
      "cwe": "CWE-798",
      "summary": "A recognisable provider token prefix (GitHub, Slack, Stripe, Google, OpenAI, Anthropic) appears as a literal.",
      "risk": "These are directly usable credentials with a known issuer, so exploitation needs no guesswork at all.",
      "remediation": "Revoke at the provider immediately, then load from the environment at runtime.",
      "detector": {
        "kind": "content",
        "pattern": "\\b(gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{40,}|xox[baprs]-[A-Za-z0-9-]{10,}|sk-(live|proj|ant)?[-_]?[A-Za-z0-9]{20,}|rk_live_[A-Za-z0-9]{20,}|AIza[A-Za-z0-9_\\-]{35}|glpat-[A-Za-z0-9_\\-]{20})\\b",
        "flags": "",
        "exclude_tests": true,
        "skip_if_placeholder": true,
        "not_match": "EXAMPLE|example|dummy|fake|test|mock|recorded|redacted",
        "comment": "exclude_tests is on because HTTP-recording and provider test fixtures are overwhelmingly the source of hits here. Real secrets in shipped code are still caught; this trades a little recall for the precision the check needs to be believed at all.",
        "scan_comments": true
      }
    },
    {
      "id": "C-01",
      "agent": "conduit",
      "name": "Wildcard CORS origin",
      "severity": "high",
      "cwe": "CWE-942",
      "summary": "`Access-Control-Allow-Origin` is set to `*`, or the CORS middleware allows all origins.",
      "risk": "Any website can call your API from a visitor's browser. On a cookie-authenticated API this is cross-origin data theft.",
      "remediation": "Enumerate trusted origins explicitly and reject everything else.",
      "fix": {
        "lang": "diff",
        "body": "- app.use(cors({ origin: '*' }))\n+ app.use(cors({ origin: ['https://app.example.com'], credentials: true }))"
      },
      "detector": {
        "kind": "content",
        "pattern": "Access-Control-Allow-Origin[\"']?\\s*[:,]\\s*[\"']\\*[\"']|origins?\\s*[:=]\\s*[\\[\"']\\s*\\*|cors\\s*\\(\\s*\\)|CORS_ORIGIN_ALLOW_ALL\\s*=\\s*True",
        "flags": "i",
        "exclude_tests": true
      }
    },
    {
      "id": "C-02",
      "agent": "conduit",
      "name": "Wildcard CORS combined with credentials",
      "severity": "critical",
      "cwe": "CWE-942",
      "summary": "Credentialed CORS is enabled alongside a permissive origin policy.",
      "risk": "Attacker-controlled pages can issue authenticated requests as the logged-in victim and read the responses.",
      "remediation": "Never combine `credentials: true` with a reflected or wildcard origin — pin to an explicit host list.",
      "detector": {
        "kind": "content",
        "pattern": "credentials\\s*[:=]\\s*(true|True)[^}]{0,120}origin\\s*[:=]\\s*[\"'`]?(\\*|req\\.headers\\.origin)|origin\\s*[:=]\\s*[\"'`]?(\\*|req\\.headers\\.origin)[^}]{0,120}credentials\\s*[:=]\\s*(true|True)",
        "flags": "",
        "exclude_tests": true
      }
    },
    {
      "id": "C-03",
      "agent": "conduit",
      "name": "TLS certificate validation disabled",
      "severity": "high",
      "cwe": "CWE-295",
      "summary": "An HTTP client is configured with `verify=False`, `rejectUnauthorized: false`, or `InsecureSkipVerify`.",
      "risk": "TLS without certificate validation stops any active attacker on the path from being detected — HTTPS becomes decoration.",
      "remediation": "Keep validation on. For internal CAs, install the CA bundle rather than disabling the check.",
      "fix": {
        "lang": "diff",
        "body": "- requests.get(url, verify=False)\n+ requests.get(url, verify=\"/etc/ssl/certs/internal-ca.pem\")"
      },
      "detector": {
        "kind": "content",
        "pattern": "verify\\s*=\\s*False|rejectUnauthorized\\s*:\\s*false|InsecureSkipVerify\\s*:\\s*true|CURLOPT_SSL_VERIFYPEER\\s*,\\s*(0|false)|NODE_TLS_REJECT_UNAUTHORIZED\\s*=\\s*[\"']?0",
        "flags": "",
        "exclude_tests": true
      }
    },
    {
      "id": "C-04",
      "agent": "conduit",
      "name": "Cleartext HTTP endpoint",
      "severity": "medium",
      "cwe": "CWE-319",
      "summary": "A non-local `http://` URL is used for an API or asset.",
      "risk": "Requests and any tokens they carry are readable and modifiable by anyone on the network path.",
      "remediation": "Switch to `https://` and add HSTS so downgrades are refused.",
      "detector": {
        "kind": "content",
        "pattern": "[\"'`]http://(?!localhost|127\\.0\\.0\\.1|0\\.0\\.0\\.0|\\[::1\\]|host\\.docker|www\\.w3\\.org|schemas?\\.|xmlns|jsonschema|example\\.(com|org))[a-z0-9.-]+",
        "flags": "i",
        "exclude_tests": true,
        "hit_cap": 2,
        "not_match": "\\$schema|xmlns|json-schema\\.org|sitemaps\\.org|\\.dtd|<a\\s+href|purl\\.org|creativecommons\\.org|opengis\\.net|<!DOCTYPE|\\.internal\\b|\\.local\\b|tauri|\\.test\\b|\\.invalid\\b",
        "comment": "XML namespaces, JSON-Schema declarations, and outbound links in prose are identifiers or third-party content, not endpoints this codebase calls over cleartext. .internal/.local are non-routable names resolved inside a trusted network segment."
      }
    },
    {
      "id": "C-05",
      "agent": "conduit",
      "name": "Service bound to all interfaces",
      "severity": "medium",
      "cwe": "CWE-1327",
      "summary": "A server listens on `0.0.0.0` outside of a container entrypoint.",
      "risk": "Services intended for localhost become reachable from the network, and from the internet on a misconfigured host.",
      "remediation": "Bind to `127.0.0.1` and place a reverse proxy in front of anything that must be public.",
      "detector": {
        "kind": "content",
        "pattern": "(host|HOST|bind|listen|Addr)\\s*[:=]\\s*[\"']?0\\.0\\.0\\.0",
        "flags": "",
        "exclude_tests": true,
        "hit_cap": 2,
        "exclude": [
          "**/vite.config.*",
          "**/astro.config.*",
          "**/webpack.config.*",
          "**/next.config.*",
          "**/nuxt.config.*",
          "**/*.dev.*",
          "**/docker-compose*.yml",
          "**/Dockerfile*"
        ],
        "comment": "Dev-server configs bind 0.0.0.0 by design so the port is reachable from outside a container; that is not the misconfiguration this check is about."
      }
    },
    {
      "id": "W-01",
      "agent": "watchtower",
      "name": "Debug mode enabled",
      "severity": "high",
      "cwe": "CWE-489",
      "summary": "`DEBUG = True`, `app.run(debug=True)`, or an equivalent development flag is set in committed config.",
      "risk": "Debug handlers expose stack traces, settings, and — in Flask/Django — an interactive console that executes code.",
      "remediation": "Drive the flag from the environment and default it to off.",
      "fix": {
        "lang": "diff",
        "body": "- DEBUG = True\n+ DEBUG = os.environ.get(\"DEBUG\", \"\").lower() == \"true\"   # off unless explicitly enabled"
      },
      "detector": {
        "kind": "content",
        "pattern": "DEBUG\\s*=\\s*True|debug\\s*[:=]\\s*true|app\\.run\\s*\\([^)]*debug\\s*=\\s*True|FLASK_ENV\\s*=\\s*development",
        "flags": "",
        "exclude_tests": true
      }
    },
    {
      "id": "W-02",
      "agent": "watchtower",
      "name": "Container runs as root",
      "severity": "high",
      "cwe": "CWE-250",
      "summary": "A Dockerfile never drops privileges — no `USER` instruction, or it explicitly sets `USER root`.",
      "risk": "A process escape or a mounted host path gives the attacker root on the node instead of an unprivileged account.",
      "remediation": "Create a non-root user and switch to it before the entrypoint.",
      "fix": {
        "lang": "dockerfile",
        "body": "RUN adduser --system --uid 10001 appuser\nUSER appuser\nCMD [\"node\", \"server.js\"]"
      },
      "applies_if": {
        "any_path": [
          "**/Dockerfile",
          "**/Dockerfile.*",
          "**/*.dockerfile"
        ]
      },
      "detector": {
        "kind": "content_required",
        "paths": [
          "**/Dockerfile",
          "**/Dockerfile.*",
          "**/*.dockerfile"
        ],
        "pattern": "^\\s*USER\\s+(?!root\\s*$)\\S+",
        "flags": "im",
        "fail_message": "No non-root USER instruction found in this Dockerfile."
      }
    },
    {
      "id": "W-03",
      "agent": "watchtower",
      "name": "Unpinned base image tag",
      "severity": "medium",
      "cwe": "CWE-1104",
      "summary": "A Dockerfile uses `:latest` or omits the tag entirely.",
      "risk": "Builds are not reproducible and a compromised or breaking upstream image ships straight to production.",
      "remediation": "Pin to a digest: `FROM node:20.11-alpine@sha256:...`.",
      "applies_if": {
        "any_path": [
          "**/Dockerfile",
          "**/Dockerfile.*",
          "**/*.dockerfile"
        ]
      },
      "detector": {
        "kind": "content",
        "pattern": "^[ \\t]*FROM\\s+(?![^\\s]*\\$\\{)[^\\s:@]+([ \\t]|:latest)",
        "flags": "im",
        "include": [
          "**/Dockerfile",
          "**/Dockerfile.*",
          "**/*.dockerfile"
        ],
        "not_match": "\\$\\{|@sha256:",
        "hit_cap": 1,
        "comment": "hit_cap is 1 because multi-stage builds legitimately repeat FROM to reference earlier stages, which regex cannot distinguish from a registry image. Unpinned base images are one hygiene problem per Dockerfile, not one per line."
      }
    },
    {
      "id": "W-04",
      "agent": "watchtower",
      "name": "Privileged container or host namespace",
      "severity": "high",
      "cwe": "CWE-250",
      "summary": "A compose or Kubernetes manifest requests `privileged: true`, `hostNetwork`, `hostPID`, or docker socket access.",
      "risk": "A privileged container is functionally root on the host; the docker socket is a full container escape.",
      "remediation": "Drop the privilege, add only the specific capabilities needed, and never mount `/var/run/docker.sock`.",
      "detector": {
        "kind": "content",
        "pattern": "privileged\\s*:\\s*true|hostNetwork\\s*:\\s*true|hostPID\\s*:\\s*true|hostIPC\\s*:\\s*true|/var/run/docker\\.sock|allowPrivilegeEscalation\\s*:\\s*true",
        "flags": "",
        "include": [
          "**/*.yml",
          "**/*.yaml"
        ],
        "exclude_tests": true
      }
    },
    {
      "id": "W-05",
      "agent": "watchtower",
      "name": "Plaintext secret in CI workflow",
      "severity": "high",
      "cwe": "CWE-798",
      "summary": "A CI workflow sets a token or password to a literal value instead of referencing the secrets store.",
      "risk": "Workflow files are public on public repos, and the value is echoed into build logs on failure.",
      "remediation": "Reference `${{ secrets.NAME }}` (GitHub) or the equivalent masked variable in your CI provider.",
      "fix": {
        "lang": "diff",
        "body": "- env:\n-   NPM_TOKEN: npm_9f2b1c8e4a7d0553aa11\n+ env:\n+   NPM_TOKEN: ${{ secrets.NPM_TOKEN }}"
      },
      "detector": {
        "kind": "content",
        "pattern": "(token|password|secret|key|credential)\\s*:\\s*[\"']?[A-Za-z0-9_\\-+/=]{16,}[\"']?\\s*$",
        "flags": "im",
        "include": [
          "**/.github/workflows/*.yml",
          "**/.github/workflows/*.yaml",
          "**/.gitlab-ci.yml",
          "**/.circleci/config.yml"
        ],
        "skip_if_placeholder": true,
        "scan_comments": true
      }
    },
    {
      "id": "W-06",
      "agent": "watchtower",
      "name": "No security disclosure policy",
      "severity": "medium",
      "cwe": "CWE-1059",
      "summary": "The repository has no `SECURITY.md`.",
      "risk": "Researchers who find a flaw have no private channel, so issues get filed publicly — or sold.",
      "remediation": "Add `SECURITY.md` with a contact address, supported versions, and expected response time.",
      "fix": {
        "lang": "markdown",
        "body": "# Security Policy\n\n## Reporting a Vulnerability\nEmail security@example.com. We acknowledge within 2 business days\nand aim to ship a fix within 30 days.\n\n## Supported Versions\n| Version | Supported |\n|---------|-----------|\n| 2.x     | yes       |\n| < 2.0   | no        |"
      },
      "detector": {
        "kind": "path_required",
        "paths": [
          "SECURITY.md",
          ".github/SECURITY.md",
          "docs/SECURITY.md",
          "SECURITY.rst",
          "SECURITY.txt"
        ]
      }
    },
    {
      "id": "W-07",
      "agent": "watchtower",
      "name": "No license file",
      "severity": "low",
      "cwe": "N/A",
      "summary": "The repository does not declare a license.",
      "risk": "Without a license the code is all-rights-reserved by default, which blocks legitimate reuse and complicates audits.",
      "remediation": "Add a `LICENSE` file, or state the proprietary terms explicitly if the code is closed.",
      "detector": {
        "kind": "meta",
        "handler": "has_license"
      }
    },
    {
      "id": "W-08",
      "agent": "watchtower",
      "name": "Security headers not configured",
      "severity": "medium",
      "cwe": "CWE-693",
      "summary": "No Content-Security-Policy, HSTS, or X-Frame-Options configuration found anywhere in the repository.",
      "risk": "Missing CSP removes the main mitigation for XSS; missing frame protection allows clickjacking of authenticated views.",
      "remediation": "Add a security-headers middleware (helmet, django-csp, secure.py) or set them at the edge/CDN.",
      "fix": {
        "lang": "javascript",
        "body": "import helmet from 'helmet';\napp.use(helmet({\n  contentSecurityPolicy: { directives: { defaultSrc: [\"'self'\"] } },\n  hsts: { maxAge: 31536000, includeSubDomains: true }\n}));"
      },
      "applies_if": {
        "any_path": [
          "**/*.html",
          "**/*.js",
          "**/*.ts",
          "**/*.py",
          "**/*.rb",
          "**/*.go",
          "**/*.php"
        ]
      },
      "detector": {
        "kind": "content_required",
        "paths": [
          "**/*"
        ],
        "pattern": "Content-Security-Policy|contentSecurityPolicy|Strict-Transport-Security|X-Frame-Options|frame-ancestors|helmet\\(|secure_headers|SECURE_HSTS_SECONDS",
        "flags": "i",
        "fail_message": "No CSP, HSTS, or frame-protection configuration found in any scanned file."
      }
    },
    {
      "id": "L-01",
      "agent": "librarian",
      "name": "Dependency lockfile missing",
      "severity": "medium",
      "cwe": "CWE-1104",
      "summary": "A manifest declares dependencies but no lockfile pins the resolved versions.",
      "risk": "Every install can pull different transitive code. A hijacked patch release lands in production without a diff.",
      "remediation": "Commit the lockfile your package manager produces and install with `npm ci` / `pip install -r requirements.txt --require-hashes`.",
      "applies_if": {
        "any_path": [
          "package.json",
          "**/package.json",
          "requirements.txt",
          "**/requirements.txt",
          "Gemfile",
          "composer.json",
          "pyproject.toml"
        ]
      },
      "detector": {
        "kind": "path_required",
        "paths": [
          "package-lock.json",
          "yarn.lock",
          "pnpm-lock.yaml",
          "bun.lock",
          "bun.lockb",
          "deno.lock",
          "**/package-lock.json",
          "**/yarn.lock",
          "**/pnpm-lock.yaml",
          "**/bun.lock",
          "**/bun.lockb",
          "**/deno.lock",
          "poetry.lock",
          "Pipfile.lock",
          "requirements.lock",
          "Gemfile.lock",
          "composer.lock",
          "uv.lock",
          "pdm.lock",
          "pixi.lock",
          "Cargo.lock",
          "go.sum",
          "**/poetry.lock",
          "**/Gemfile.lock",
          "**/composer.lock",
          "**/uv.lock",
          "**/pdm.lock",
          "**/Cargo.lock",
          "**/go.sum"
        ]
      }
    },
    {
      "id": "L-02",
      "agent": "librarian",
      "name": "Known-vulnerable dependency version",
      "severity": "high",
      "cwe": "CWE-1395",
      "summary": "A manifest pins a package version with a published CVE.",
      "risk": "Public advisories come with public exploits; these are the first things scanned for on an exposed service.",
      "remediation": "Upgrade to the patched release and enable automated dependency updates so this does not recur.",
      "detector": {
        "kind": "content",
        "pattern": "[\"']?lodash[\"']?\\s*[\":= ]+[\\^~>=]*[\"']?4\\.(([0-9]|1[0-6])\\.|17\\.([0-9]|1[0-9]|20)\\b)|[\"']?minimist[\"']?\\s*[\":= ]+[\\^~>=]*[\"']?(0\\.|1\\.[01]\\.|1\\.2\\.[0-5]\\b)|[\"']?axios[\"']?\\s*[\":= ]+[\\^~>=]*[\"']?(0\\.|1\\.[0-5]\\.)|[\"']?jquery[\"']?\\s*[\":= ]+[\\^~>=]*[\"']?([12]\\.|3\\.[0-4]\\.)|[\"']?next[\"']?\\s*[\":= ]+[\\^~>=]*[\"']?(1[0-3]\\.|14\\.[01]\\.)|requests\\s*[=<>~]+\\s*2\\.([0-9]|1[0-9]|2[0-9]|30)\\.|django\\s*[=<>~]+\\s*([12]\\.|3\\.[01]\\.|4\\.[01]\\.)|flask\\s*[=<>~]+\\s*(0\\.|1\\.)|pyyaml\\s*[=<>~]+\\s*[0-4]\\.|log4j-core.{0,20}2\\.([0-9]|1[0-6])\\.",
        "flags": "i",
        "include": [
          "**/package.json",
          "**/requirements*.txt",
          "**/pyproject.toml",
          "**/Gemfile",
          "**/pom.xml",
          "**/build.gradle",
          "**/composer.json"
        ]
      }
    },
    {
      "id": "L-03",
      "agent": "librarian",
      "name": "Dependency sourced from a URL or git ref",
      "severity": "medium",
      "cwe": "CWE-829",
      "summary": "A dependency is installed from a git URL or tarball rather than a registry release.",
      "risk": "A moving branch reference means the code can change under you with no version bump and no audit trail.",
      "remediation": "Publish an internal registry package, or at minimum pin to an immutable commit SHA.",
      "detector": {
        "kind": "content",
        "pattern": "[\"'](git\\+(ssh|https?)://|github:|gitlab:|bitbucket:)[^\"']+[\"']|[\"']https?://[^\"']+\\.(tgz|tar\\.gz)[\"']|-e\\s+git\\+|@\\s*git\\+(ssh|https?)://",
        "flags": "",
        "include": [
          "**/package.json",
          "**/requirements*.txt",
          "**/Gemfile",
          "**/pyproject.toml"
        ],
        "not_match": "\\$schema|\"(repository|homepage|bugs|funding|author|docs|website)\"|\"url\"\\s*:",
        "comment": "Previously matched any https URL in package.json, so $schema declarations and the repository field registered as untrusted dependencies. Now only genuine git/tarball dependency specifiers match. A dependency is never keyed \"url\" — that is the repository/bugs metadata block."
      }
    },
    {
      "id": "L-04",
      "agent": "librarian",
      "name": "No automated dependency updates",
      "severity": "low",
      "cwe": "CWE-1104",
      "summary": "No Dependabot or Renovate configuration is present.",
      "risk": "Patch lag is the dominant cause of exploited dependency CVEs; manual upgrades slip.",
      "remediation": "Add `.github/dependabot.yml` or a Renovate config so upgrade PRs open automatically.",
      "fix": {
        "lang": "yaml",
        "body": "version: 2\nupdates:\n  - package-ecosystem: npm\n    directory: \"/\"\n    schedule: { interval: weekly }\n    open-pull-requests-limit: 10"
      },
      "applies_if": {
        "any_path": [
          "package.json",
          "**/package.json",
          "requirements.txt",
          "**/requirements.txt",
          "go.mod",
          "Gemfile",
          "pyproject.toml",
          "Cargo.toml"
        ]
      },
      "detector": {
        "kind": "path_required",
        "paths": [
          ".github/dependabot.yml",
          ".github/dependabot.yaml",
          "renovate.json",
          ".renovaterc",
          ".renovaterc.json",
          ".github/renovate.json"
        ]
      }
    },
    {
      "id": "L-05",
      "agent": "librarian",
      "name": "Remote script piped to a shell",
      "severity": "high",
      "cwe": "CWE-494",
      "summary": "A build or CI step pipes `curl`/`wget` output directly into `bash` or `sh`.",
      "risk": "The remote server decides what code runs on your builder, and can serve different content to you than to reviewers.",
      "remediation": "Download to a file, verify a pinned checksum or signature, then execute.",
      "fix": {
        "lang": "bash",
        "body": "curl -fsSL -o install.sh https://example.com/install.sh\necho \"<known-sha256>  install.sh\" | sha256sum -c -\nsh install.sh"
      },
      "detector": {
        "kind": "content",
        "pattern": "(curl|wget)[^\\n|]{0,120}\\|\\s*(sudo\\s+)?(ba)?sh",
        "flags": "",
        "exclude_tests": true,
        "exclude": [
          "**/*.md",
          "**/*.rst",
          "**/*.txt",
          "**/docs/**",
          "**/README*"
        ]
      }
    },
    {
      "id": "L-06",
      "agent": "librarian",
      "name": "Unpinned third-party GitHub Action",
      "severity": "medium",
      "cwe": "CWE-829",
      "summary": "A workflow references a third-party action by branch or floating tag instead of a commit SHA.",
      "risk": "The action author — or anyone who compromises their account — can retroactively change what runs with your repo token.",
      "remediation": "Pin third-party actions to a full commit SHA and let Dependabot bump them.",
      "fix": {
        "lang": "diff",
        "body": "- uses: some-org/deploy-action@main\n+ uses: some-org/deploy-action@a1b2c3d4e5f60718293a4b5c6d7e8f9012345678  # v3.1.0"
      },
      "applies_if": {
        "any_path": [
          "**/.github/workflows/*.yml",
          "**/.github/workflows/*.yaml"
        ]
      },
      "detector": {
        "kind": "content",
        "pattern": "uses\\s*:\\s*(?!actions/|github/|docker/)[\\w.-]+/[\\w.-]+@(main|master|v?\\d+(\\.\\d+)*)\\s*$",
        "flags": "im",
        "include": [
          "**/.github/workflows/*.yml",
          "**/.github/workflows/*.yaml"
        ]
      }
    },
    {
      "id": "F-01",
      "agent": "shield",
      "name": "Auth token stored in web storage",
      "severity": "high",
      "cwe": "CWE-922",
      "summary": "A JWT, session, or auth token is written to `localStorage` or `sessionStorage`.",
      "risk": "Web storage is readable by any script on the page, so a single XSS or a compromised npm package exfiltrates every session.",
      "remediation": "Keep the session in an `HttpOnly; Secure; SameSite` cookie so script cannot read it.",
      "fix": {
        "lang": "diff",
        "body": "- localStorage.setItem('token', res.data.token);\n+ // server sets: Set-Cookie: sid=...; HttpOnly; Secure; SameSite=Lax\n+ // client sends credentials automatically:\n+ fetch('/api/me', { credentials: 'include' });"
      },
      "detector": {
        "kind": "content",
        "pattern": "(localStorage|sessionStorage)\\.setItem\\s*\\(\\s*[\"'`][^\"'`]*(token|jwt|auth|session|credential|apikey|api_key)",
        "flags": "i",
        "exclude_tests": true
      }
    },
    {
      "id": "F-02",
      "agent": "shield",
      "name": "Unsanitised HTML injection sink",
      "severity": "high",
      "cwe": "CWE-79",
      "summary": "`dangerouslySetInnerHTML`, `v-html`, `[innerHTML]`, or a direct `innerHTML =` assignment is used.",
      "risk": "If any part of that string is user-controlled it becomes stored XSS — session theft, keylogging, or account takeover.",
      "remediation": "Render as text, or sanitise with DOMPurify immediately before insertion.",
      "fix": {
        "lang": "diff",
        "body": "- <div dangerouslySetInnerHTML={{ __html: comment.body }} />\n+ import DOMPurify from 'dompurify';\n+ <div dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(comment.body) }} />"
      },
      "detector": {
        "kind": "content",
        "pattern": "dangerouslySetInnerHTML|v-html|\\[innerHTML\\]|\\.innerHTML\\s*=|\\.outerHTML\\s*=|insertAdjacentHTML\\s*\\(",
        "flags": "",
        "exclude_tests": true,
        "not_match": "DOMPurify|sanitize|sanitise|escapeHtml|escapeHTML|htmlspecialchars|\\bescape\\(|\\besc\\(|textContent|\\.innerHTML\\s*=\\s*['\"`]{2}",
        "not_match_window": 8
      }
    },
    {
      "id": "F-03",
      "agent": "shield",
      "name": "document.write or legacy DOM sink",
      "severity": "medium",
      "cwe": "CWE-79",
      "summary": "`document.write` is used, which parses its argument as HTML.",
      "risk": "It is an XSS sink, blocks the parser, and is ignored entirely in async script contexts.",
      "remediation": "Build nodes with `createElement`/`textContent` and append them.",
      "detector": {
        "kind": "content",
        "pattern": "document\\.write(ln)?\\s*\\(",
        "flags": "",
        "exclude_tests": true
      }
    },
    {
      "id": "F-04",
      "agent": "shield",
      "name": "postMessage without origin validation",
      "severity": "medium",
      "cwe": "CWE-346",
      "summary": "A `message` listener does not check `event.origin`, or `postMessage` targets `*`.",
      "risk": "Any framing or opened window can send messages your handler trusts, or read messages you broadcast.",
      "remediation": "Compare `event.origin` against an exact expected origin and pass a specific target origin when sending.",
      "fix": {
        "lang": "javascript",
        "body": "window.addEventListener('message', (e) => {\n  if (e.origin !== 'https://trusted.example.com') return;\n  handle(e.data);\n});"
      },
      "detector": {
        "kind": "content",
        "pattern": "postMessage\\s*\\([^)]*,\\s*[\"'`]\\*[\"'`]\\s*\\)",
        "flags": "",
        "exclude_tests": true
      }
    },
    {
      "id": "F-05",
      "agent": "shield",
      "name": "target=\"_blank\" without rel protection",
      "severity": "low",
      "cwe": "CWE-1022",
      "summary": "An anchor opens a new tab without `rel=\"noopener\"`.",
      "risk": "In older browsers the opened page can redirect the original tab via `window.opener` — a credible phishing pivot.",
      "remediation": "Add `rel=\"noopener noreferrer\"` to every `target=\"_blank\"` link.",
      "detector": {
        "kind": "content",
        "pattern": "<a\\s[^>]*target\\s*=\\s*[\"']_blank[\"'][^>]*>",
        "flags": "i",
        "include": [
          "**/*.html",
          "**/*.jsx",
          "**/*.tsx",
          "**/*.vue",
          "**/*.svelte"
        ],
        "not_match": "noopener|noreferrer",
        "exclude_tests": true,
        "hit_cap": 2
      }
    },
    {
      "id": "F-06",
      "agent": "shield",
      "name": "Secret embedded in client-side code",
      "severity": "critical",
      "cwe": "CWE-798",
      "summary": "A credential literal appears in a file that ships to the browser.",
      "risk": "Anything in the bundle is public — view-source is all the attacker needs, regardless of build-time obfuscation.",
      "remediation": "Proxy the call through your backend and keep the credential server-side.",
      "detector": {
        "kind": "content",
        "pattern": "(api[_-]?key|secret|token|password|client[_-]?secret)\\s*[:=]\\s*[\"'][A-Za-z0-9_\\-+/=]{20,}[\"']",
        "flags": "i",
        "include": [
          "**/*.html",
          "**/*.jsx",
          "**/*.tsx",
          "**/*.vue",
          "**/*.svelte",
          "**/public/**/*.js",
          "**/static/**/*.js",
          "**/client/**/*.js",
          "**/src/**/*.js"
        ],
        "skip_if_placeholder": true,
        "exclude_tests": true,
        "scan_comments": true
      }
    },
    {
      "id": "A-01",
      "agent": "auditor",
      "name": "Credentials passed to the logger",
      "severity": "high",
      "cwe": "CWE-532",
      "summary": "A structured log call includes a password, key, or secret field.",
      "risk": "Log aggregators have far broader access than production databases, and retain data long after rotation.",
      "remediation": "Redact sensitive keys in a log processor and pass identifiers, not credentials.",
      "fix": {
        "lang": "diff",
        "body": "- logger.info(\"login attempt\", { email, password });\n+ logger.info(\"login attempt\", { email, hasPassword: Boolean(password) });"
      },
      "detector": {
        "kind": "content",
        "pattern": "(logger|log|logging)\\.(info|debug|warn|warning|error|trace)\\s*\\([^)\\n]{0,100}(\\b(password|passwd|secret|api_?key|token|credential)s?\\b\\s*[,)}\\]]|\\$\\{[^}]{0,40}\\b(password|passwd|secret|api_?key|token)\\b[^}]{0,20}\\})",
        "flags": "i",
        "exclude_tests": true,
        "comment": "Must match a credential being PASSED as a value, not prose mentioning one. The old pattern flagged log messages like `No credentials found for: x` and `Refresh token: present`, which leak nothing. Requiring a trailing delimiter or a ${} interpolation keeps `{ email, password }` while dropping the prose."
      }
    },
    {
      "id": "A-02",
      "agent": "auditor",
      "name": "Stack trace returned to the client",
      "severity": "medium",
      "cwe": "CWE-209",
      "summary": "An error handler sends `err.stack`, `traceback`, or the raw exception in the HTTP response.",
      "risk": "Traces reveal file paths, framework versions, and query structure — the reconnaissance step of a real attack.",
      "remediation": "Return a generic message plus a correlation ID, and log the detail server-side.",
      "fix": {
        "lang": "diff",
        "body": "- res.status(500).json({ error: err.stack });\n+ const ref = crypto.randomUUID();\n+ logger.error({ ref, err });\n+ res.status(500).json({ error: 'Internal error', ref });"
      },
      "detector": {
        "kind": "content",
        "pattern": "(res|response)\\.(send|json|write)\\s*\\([^)\\n]{0,80}(err\\.stack|error\\.stack|traceback|format_exc|getStackTrace|printStackTrace)",
        "flags": "i",
        "exclude_tests": true
      }
    },
    {
      "id": "A-03",
      "agent": "auditor",
      "name": "Debug output left in source",
      "severity": "low",
      "cwe": "CWE-489",
      "summary": "`console.log`, bare `print`, or `debugger` statements remain in non-test source.",
      "risk": "Noisy logs bury real signals, and `debugger` halts execution in any browser with devtools open.",
      "remediation": "Route through a level-aware logger and enforce `no-console` / `no-debugger` in lint.",
      "detector": {
        "kind": "content",
        "pattern": "^\\s*(console\\.log\\s*\\(|debugger\\s*;)",
        "flags": "m",
        "include": [
          "**/*.js",
          "**/*.jsx",
          "**/*.ts",
          "**/*.tsx",
          "**/*.vue",
          "**/*.svelte"
        ],
        "exclude_tests": true,
        "hit_cap": 2
      }
    },
    {
      "id": "A-04",
      "agent": "auditor",
      "name": "No continuous integration pipeline",
      "severity": "medium",
      "cwe": "N/A",
      "summary": "No CI configuration was found in the repository.",
      "risk": "Without automated checks, security linting and dependency audits depend on whoever remembers to run them.",
      "remediation": "Add a CI workflow that runs tests, a linter, and a dependency audit on every pull request.",
      "fix": {
        "lang": "yaml",
        "body": "name: ci\non: [push, pull_request]\njobs:\n  check:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n      - run: npm ci\n      - run: npm test\n      - run: npm audit --audit-level=high"
      },
      "detector": {
        "kind": "path_required",
        "paths": [
          ".github/workflows/*.yml",
          ".github/workflows/*.yaml",
          ".gitlab-ci.yml",
          ".circleci/config.yml",
          "Jenkinsfile",
          "azure-pipelines.yml",
          ".travis.yml",
          ".drone.yml"
        ]
      }
    },
    {
      "id": "R-01",
      "agent": "architect",
      "name": "Hardcoded IP address",
      "severity": "medium",
      "cwe": "CWE-1327",
      "summary": "A routable IPv4 literal is embedded in source or configuration.",
      "risk": "Infrastructure changes silently break the deployment, and the address discloses internal topology.",
      "remediation": "Resolve endpoints through DNS or service discovery and supply them as configuration.",
      "detector": {
        "kind": "content",
        "pattern": "\\b(?!0\\.0\\.0\\.0|127\\.0\\.0\\.1|255\\.255\\.255|1\\.0\\.0|0\\.1\\.0)((25[0-5]|2[0-4]\\d|1\\d\\d|[1-9]?\\d)\\.){3}(25[0-5]|2[0-4]\\d|1\\d\\d|[1-9]?\\d)\\b",
        "flags": "",
        "exclude_tests": true,
        "hit_cap": 3,
        "not_match": "version|Version|VERSION|\\d+\\.\\d+\\.\\d+\\.\\d+-|@|semver|Mozilla/|AppleWebKit|Chrome/|Safari/|user-?agent|<path|<svg| d=\"|viewBox|translate\\(|matrix\\(|192\\.0\\.2\\.|198\\.51\\.100\\.|203\\.0\\.113\\.|/32|/24|/16|/8\\b",
        "include": [
          "**/*.env*",
          "**/*.yml",
          "**/*.yaml",
          "**/*.toml",
          "**/*.ini",
          "**/*.cfg",
          "**/*.properties",
          "**/*.conf",
          "**/*.tf",
          "**/*.tfvars",
          "**/*.json",
          "**/config/**",
          "**/*config*"
        ],
        "comment": "Restricted to configuration files. In application source this matched SVG path coordinates, User-Agent version strings, and CIDR examples in comments — never an actual hardcoded endpoint. The reserved documentation ranges (RFC 5737) are excluded outright."
      }
    },
    {
      "id": "R-02",
      "agent": "architect",
      "name": "Security group open to the internet",
      "severity": "critical",
      "cwe": "CWE-284",
      "summary": "An infrastructure definition allows ingress from `0.0.0.0/0`.",
      "risk": "Databases and admin ports exposed this way are found by internet-wide scanners within hours of going live.",
      "remediation": "Restrict ingress to known CIDRs or a bastion/VPN security group; expose only 443 publicly.",
      "fix": {
        "lang": "diff",
        "body": "  ingress {\n    from_port   = 5432\n    to_port     = 5432\n-   cidr_blocks = [\"0.0.0.0/0\"]\n+   security_groups = [aws_security_group.app.id]\n  }"
      },
      "applies_if": {
        "any_path": [
          "**/*.tf",
          "**/*.tfvars",
          "**/cloudformation*.y*ml",
          "**/*.template.json"
        ]
      },
      "detector": {
        "kind": "content",
        "pattern": "0\\.0\\.0\\.0/0|::/0",
        "flags": "",
        "include": [
          "**/*.tf",
          "**/*.tfvars",
          "**/cloudformation*.yml",
          "**/cloudformation*.yaml",
          "**/*.template.json"
        ]
      }
    },
    {
      "id": "R-03",
      "agent": "architect",
      "name": "Publicly readable object storage",
      "severity": "high",
      "cwe": "CWE-732",
      "summary": "A bucket or blob container is configured with a public-read ACL.",
      "risk": "Public buckets are the most common source of large-scale data exposure; they are indexed and enumerated continuously.",
      "remediation": "Block public access at the account level and serve objects through signed URLs or a CDN origin identity.",
      "detector": {
        "kind": "content",
        "pattern": "acl\\s*=\\s*[\"'](public-read|public-read-write)[\"']|PublicAccessBlockConfiguration[^}]*false|\"Principal\"\\s*:\\s*\"\\*\"|allUsers",
        "flags": "",
        "include": [
          "**/*.tf",
          "**/*.yml",
          "**/*.yaml",
          "**/*.json"
        ],
        "exclude_tests": true
      }
    },
    {
      "id": "R-04",
      "agent": "architect",
      "name": "No automated tests",
      "severity": "medium",
      "cwe": "N/A",
      "summary": "No test directory or test files were found in the repository.",
      "risk": "Security fixes regress silently when nothing verifies the behaviour they depend on.",
      "remediation": "Add a test suite and wire it into CI, starting with the authentication and authorization paths.",
      "detector": {
        "kind": "path_required",
        "paths": [
          "test/**",
          "tests/**",
          "spec/**",
          "__tests__/**",
          "**/*_test.go",
          "**/test_*.py",
          "**/*.test.js",
          "**/*.test.ts",
          "**/*.spec.js",
          "**/*.spec.ts",
          "**/*Test.java",
          "src/test/**"
        ]
      }
    },
    {
      "id": "R-05",
      "agent": "architect",
      "name": "Terraform state committed",
      "severity": "critical",
      "cwe": "CWE-538",
      "summary": "A `.tfstate` file is tracked in the repository.",
      "risk": "Terraform state stores resource attributes in plaintext, routinely including database passwords and generated keys.",
      "remediation": "Move state to an encrypted remote backend (S3 + DynamoDB lock, Terraform Cloud) and gitignore `*.tfstate*`.",
      "fix": {
        "lang": "hcl",
        "body": "terraform {\n  backend \"s3\" {\n    bucket         = \"tf-state-prod\"\n    key            = \"app/terraform.tfstate\"\n    encrypt        = true\n    dynamodb_table = \"tf-locks\"\n  }\n}"
      },
      "detector": {
        "kind": "path_forbidden",
        "paths": [
          "**/*.tfstate",
          "**/*.tfstate.backup",
          "**/.terraform/**"
        ],
        "exclude": []
      }
    }
  ]
};
