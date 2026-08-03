# The Cerberus Inspection — Target Scope (Roadmap)

> **Status: ROADMAP, not shipped.** This document is the long-run target scope for the
> Cerberus inspection — the full set of checks we intend to build out over time. It is
> **not** a record of what the product does today.
>
> **What actually ships today is 58 checks across the same nine agent domains, defined in
> `/checks.json`** — the single source of truth consumed by the web app, `examine.py`, and
> the generated docs at `documentation/checks.html` / `docs/scanner-checks.md`. If a check
> isn't in `checks.json`, it does not run, no matter what this document says.
>
> The check IDs and names below (S-01, G-01, …) are **not** the same IDs used by the
> shipped catalog — this document predates `checks.json` and its numbering was never
> reconciled to it. Treat everything below as directional scope for future work, not an
> implementation reference. For the real, currently-running checks, see
> `docs/scanner-checks.md` or `documentation/checks.html`.
>
> Shipped counts today, per agent (see `checks.json` for authoritative detail):
>
> | Agent | Shipped today | Target (this document) |
> |---|---|---|
> | SENTINEL | 11 | 17 |
> | GATEKEEPER | 6 | 17 |
> | VAULT | 8 | 17 |
> | CONDUIT | 5 | 17 |
> | WATCHTOWER | 8 | 17 |
> | LIBRARIAN | 6 | 17 |
> | SHIELD | 6 | 17 |
> | AUDITOR | 4 | 16 |
> | ARCHITECT | 5 | 16 |
> | **Total** | **59** | **151** |

This document outlines the long-term target scope for the Cerberus inspection. Each check
described below is a candidate for future implementation; none of the Pass/Fail criteria
below should be assumed to be evaluated by the current product.

## SENTINEL (Backend Code Review) - 17 Checks (target scope, see banner above)
| ID | Check Name | Severity | Description | Pass Criteria |
|---|---|---|---|---|
| S-01 | Hardcoded Secrets | Critical | Searches source code for plain-text API keys, tokens, and passwords. | Zero hardcoded secrets found in source. |
| S-02 | SQL Injection (Raw) | Critical | Detects string concatenation or raw string formatting in database queries. | Use of parameterized queries or strict ORM methods exclusively. |
| S-03 | Command Injection | Critical | Identifies unsafe execution of system commands using user input. | No unsafe OS command execution functions detected. |
| S-04 | Path Traversal | High | Checks if file read/write operations sanitize relative path inputs. | Input is strictly validated against directory traversal characters. |
| S-05 | Insecure Deserialization | High | Looks for deserialization of untrusted data (e.g., Python `pickle`, Java objects). | Use of safe serialization formats like JSON exclusively. |
| S-06 | Unvalidated Redirects | Medium | Detects HTTP redirects based on unvalidated user input. | Redirect URLs are strictly whitelisted or internally mapped. |
| S-07 | Verbose Error Handling | Medium | Checks if stack traces or internal errors are returned in HTTP responses. | Generic error messages returned in production environments. |
| S-08 | Weak Cryptography | High | Identifies the use of outdated algorithms (MD5, DES, SHA1). | Industry-standard algorithms (AES-256, SHA-256+) are used. |
| S-09 | IDOR in Controllers | High | Verifies that object access checks user ownership, not just ID presence. | Ownership verification logic is present for data access endpoints. |
| S-10 | Memory Leaks (Native) | Medium | Identifies unsafe memory handling in lower-level backend languages. | Use of safe memory constructs or automated garbage collection verification. |
| S-11 | Regex Denial of Service | Medium | Scans for complex regular expressions vulnerable to catastrophic backtracking. | Safe regex patterns or bounded regex execution time. |
| S-12 | Race Conditions | High | Analyzes state-changing endpoints for Time-of-Check to Time-of-Use flaws. | Use of database locks or atomic transactions for critical state changes. |
| S-13 | Improper File Uploads | High | Validates that file uploads restrict extensions and validate MIME types. | File uploads strictly enforce whitelisted types and maximum sizes. |
| S-14 | Unsafe Reflection | Medium | Detects dynamic instantiation or method invocation based on user input. | No unsafe reflection patterns found in codebase. |
| S-15 | Server-Side Request Forgery | High | Checks if the server fetches URLs provided by the user without validation. | Outbound requests use strict domain whitelists and block internal IPs. |
| S-16 | Business Logic Flaws | High | Heuristic analysis of unusual logic branching (e.g., skipping payment steps). | Critical business workflows enforce sequential state transitions. |
| S-17 | Code Complexity | Low | Flags functions with excessive cyclomatic complexity that hide bugs. | Cyclomatic complexity remains below acceptable threshold (e.g., <15). |

## GATEKEEPER (Auth & Access Control) - 17 Checks (target scope, see banner above)
| ID | Check Name | Severity | Description | Pass Criteria |
|---|---|---|---|---|
| G-01 | Weak Password Policy | High | Checks if the system allows short or common passwords. | Minimum 12 characters, complexity requirements enforced. |
| G-02 | MFA Absence | High | Verifies the capability to enable Multi-Factor Authentication. | MFA option is available and functional for user accounts. |
| G-03 | Insecure Session Tokens | Critical | Analyzes session token randomness and entropy. | Tokens are generated using cryptographically secure PRNGs. |
| G-04 | Session Expiration | Medium | Checks if sessions expire after a period of inactivity. | Absolute and idle session timeouts are enforced. |
| G-05 | Insecure Password Reset | High | Reviews password reset logic for predictable tokens or enumeration. | Reset tokens are long, random, and single-use with a short expiry. |
| G-06 | Broken RBAC | Critical | Verifies that lower-privileged users cannot access admin endpoints. | Role checks are enforced on all privileged routes. |
| G-07 | Brute Force Protection | High | Checks for rate limiting or account lockout on failed login attempts. | Account lockout or exponential backoff after X failed attempts. |
| G-08 | OAuth State Parameter | Medium | Verifies that OAuth flows use the `state` parameter to prevent CSRF. | `state` parameter is strictly validated during OAuth callbacks. |
| G-09 | JWT Weak Algorithms | High | Checks if JWTs accept the 'none' algorithm or use weak keys. | JWTs enforce RS256/HS256 and reject 'none'. |
| G-10 | JWT Expiration | Medium | Ensures JWTs have a short `exp` claim and proper refresh mechanisms. | JWTs expire quickly (e.g., <1 hour) and rely on secure refresh tokens. |
| G-11 | Concurrent Sessions | Low | Checks if an account can be logged in from multiple locations simultaneously. | Concurrent session limits or alerts are active. |
| G-12 | Credential Stuffing Risk | Medium | Analyzes if login endpoints are protected against credential stuffing bots. | CAPTCHA or behavioral analysis is present on auth endpoints. |
| G-13 | User Enumeration | Low | Verifies that login/reset errors do not confirm user existence. | Generic "If this email exists..." messages are used. |
| G-14 | Cleartext Password Trans | Critical | Checks if authentication happens over unencrypted channels. | All authentication endpoints strictly require HTTPS. |
| G-15 | Persistent Login Safety | Medium | Reviews "Remember Me" functionality for secure implementation. | Persistent tokens are distinct from session tokens and revocable. |
| G-16 | API Key Scoping | High | Checks if API keys can be generated with restricted scopes/permissions. | API keys support granular permissions and are not global by default. |
| G-17 | Admin Impersonation | High | Verifies that "login as user" admin features leave an audit trail. | Impersonation events are logged and temporary. |

## VAULT (Database Security) - 17 Checks (target scope, see banner above)
| ID | Check Name | Severity | Description | Pass Criteria |
|---|---|---|---|---|
| V-01 | Data at Rest Encryption | Critical | Ensures database volumes use AES-256 encryption. | Encryption at rest is enabled on all database instances. |
| V-02 | Password Hashing | Critical | Checks hashing algorithms used for storing credentials. | Bcrypt, Argon2, or PBKDF2 with appropriate work factors are used. |
| V-03 | PII Plaintext Storage | High | Scans for plaintext storage of SSNs, credit cards, or sensitive health data. | Sensitive PII is encrypted at the field level or tokenized. |
| V-04 | Exposed DB Ports | Critical | Verifies that database ports (e.g., 5432, 3306) are not publicly accessible. | Database is isolated in a private VPC/subnet. |
| V-05 | Automated Backups | High | Checks for the existence of automated, scheduled database backups. | Daily automated backups with minimum 30-day retention. |
| V-06 | Backup Encryption | High | Ensures that database backups are encrypted. | Backup files are encrypted using separate keys. |
| V-07 | Least Privilege (DB) | Medium | Verifies that the application connects to the DB using a restricted user. | App DB user cannot drop tables or access unrelated schemas. |
| V-08 | Transit Encryption | High | Ensures connections between the app and the database use TLS. | DB connection strings enforce SSL/TLS. |
| V-09 | Query Parameterization | Critical | Audits ORM configurations to ensure strict parameterization. | No raw query strings bypassing the ORM's parameterization. |
| V-10 | Data Masking (Non-Prod) | Medium | Checks if production data is masked when copied to staging. | Staging environments use anonymized or synthetic data. |
| V-11 | Audit Logging (DB) | Medium | Verifies that administrative database actions are logged. | DDL operations and failed auth attempts are logged. |
| V-12 | Unused Databases/Tables | Low | Identifies legacy schemas that expand the attack surface. | No deprecated or unused tables storing sensitive data. |
| V-13 | In-Memory Data Security | Medium | Checks if in-memory stores (Redis) require authentication. | Redis/Memcached instances require strong passwords and TLS. |
| V-14 | Secrets in DB | High | Detects storage of third-party API keys in plaintext within the DB. | Third-party secrets are encrypted in the database or stored in a KMS. |
| V-15 | Soft Deletion Safety | Medium | Ensures soft-deleted records are not accidentally exposed in API calls. | Global query scopes properly filter soft-deleted records. |
| V-16 | Multi-Tenant Isolation | High | Checks data isolation strategies in multi-tenant architectures (Row Level Security). | Tenant ID constraints are strictly enforced on all queries (e.g., RLS enabled). |
| V-17 | Backup Testing | Low | Checks documentation or mechanisms for periodic backup restoration tests. | Evidence of automated or manual backup restoration testing. |

## CONDUIT (API Security) - 17 Checks (target scope, see banner above)
| ID | Check Name | Severity | Description | Pass Criteria |
|---|---|---|---|---|
| C-01 | Permissive CORS | High | Detects CORS policies allowing `Access-Control-Allow-Origin: *` on authenticated APIs. | CORS specifically whitelists trusted domains. |
| C-02 | Global Rate Limiting | High | Verifies that all API endpoints are protected by rate limiting. | API gateway or middleware enforces requests-per-minute limits. |
| C-03 | Mass Assignment | High | Checks if API endpoints blindly accept and map JSON payloads to database models. | Strict DTOs or whitelisted parameters are used for model hydration. |
| C-04 | Missing Auth Headers | Critical | Identifies sensitive endpoints lacking authentication requirements. | All non-public endpoints require valid Authorization headers. |
| C-05 | Shadow APIs | Medium | Detects undocumented endpoints present in code but missing from specs. | All routable endpoints are documented and secured. |
| C-06 | Payload Size Limits | Medium | Verifies limits on incoming request body sizes to prevent DoS. | Maximum request size (e.g., 2MB) is enforced by the web server. |
| C-07 | GraphQL Introspection | Medium | Checks if GraphQL introspection is enabled in production. | Introspection is disabled in production environments. |
| C-08 | GraphQL Depth Limits | High | Verifies protections against deeply nested GraphQL queries. | Query depth and complexity limits are enforced. |
| C-09 | Webhook Verification | High | Checks if incoming webhooks validate signatures (e.g., from Stripe/GitHub). | Webhook handlers strictly verify cryptographic signatures before processing. |
| C-10 | Strict Content-Type | Medium | Ensures the API rejects unexpected Content-Types (e.g., XML when expecting JSON). | API strictly requires and parses `application/json`. |
| C-11 | API Versioning | Low | Checks for proper API versioning to prevent breaking security changes. | Endpoints are versioned (e.g., /v1/) to allow safe deprecation. |
| C-12 | Information Disclosure | Medium | Checks if APIs leak internal IDs or metadata in standard responses. | Responses expose only necessary data (UUIDs preferred over sequential IDs). |
| C-13 | Idempotency | Medium | Verifies that critical state-changing APIs (payments) are idempotent. | Idempotency keys are required and validated for critical POST requests. |
| C-14 | Caching Sensitive Data | High | Checks if APIs return `Cache-Control` headers for sensitive data. | Sensitive endpoints return `Cache-Control: no-store`. |
| C-15 | Unsafe Methods | Medium | Identifies the allowance of unnecessary HTTP methods (e.g., TRACE, TRACK). | Only required methods (GET, POST, PUT, DELETE, PATCH) are permitted. |
| C-16 | Pagination Security | Low | Checks if pagination endpoints can be abused to extract massive datasets. | Strict limits on `limit` or `per_page` parameters are enforced. |
| C-17 | REST Anti-patterns | Low | Identifies GET requests that modify state. | State modification strictly uses POST/PUT/DELETE. |

## WATCHTOWER (Infrastructure & Deploy) - 17 Checks (target scope, see banner above)
| ID | Check Name | Severity | Description | Pass Criteria |
|---|---|---|---|---|
| W-01 | HTTP Allowed | Critical | Checks if the infrastructure allows non-TLS HTTP traffic. | All HTTP traffic is forcefully redirected to HTTPS. |
| W-02 | Weak TLS Suites | High | Verifies TLS configuration against modern standards. | TLS 1.2+ is enforced; weak ciphers are disabled. |
| W-03 | Root Containers | High | Checks if Docker containers run as the root user. | Dockerfiles use `USER nonroot` or equivalent. |
| W-04 | CI/CD Secrets | Critical | Verifies that secrets are not hardcoded in CI/CD pipeline files. | GitHub Actions/GitLab CI use injected secrets managers. |
| W-05 | Security Headers | Medium | Checks for HSTS, X-Frame-Options, X-Content-Type-Options. | Standard security HTTP headers are present on all responses. |
| W-06 | Public Cloud Storage | Critical | Identifies S3 buckets or equivalent with public read/write access. | Storage buckets are private unless explicitly hosting public assets. |
| W-07 | Open Egress | Medium | Checks if servers can initiate outbound connections to any IP. | Egress traffic is restricted to known required endpoints. |
| W-08 | Unverified Images | Medium | Verifies that base Docker images come from trusted, signed registries. | Base images are pinned to specific SHAs and pulled from trusted sources. |
| W-09 | SSH Key Management | High | Checks infrastructure for shared SSH keys or password auth. | SSH access requires unique keys and password auth is disabled. |
| W-10 | Immutable Deployments | Low | Verifies that deployments do not modify running servers directly. | Deployments use immutable artifacts (containers/AMIs). |
| W-11 | WAF Presence | Medium | Checks if a Web Application Firewall is deployed in front of the app. | Traffic routes through a WAF (e.g., Cloudflare, AWS WAF). |
| W-12 | DDoS Protection | High | Verifies network-level protections against volumetric attacks. | Infrastructure leverages DDoS mitigation services. |
| W-13 | IaC Drift | Low | Checks if infrastructure as code matches the actual deployed state. | Terraform/Pulumi state matches reality with no manual overrides. |
| W-14 | Unused Open Ports | High | Scans infrastructure for open ports not required by the application. | Only port 80/443 (or specific app ports) are exposed to the internet. |
| W-15 | Orchestrator Dashboards | Critical | Checks if Kubernetes/Docker dashboards are exposed publicly. | Admin dashboards are inaccessible from the public internet. |
| W-16 | Metadata Service | High | Verifies that cloud instance metadata services (IMDSv2) require tokens. | IMDSv2 is enforced on AWS (or equivalent on GCP/Azure). |
| W-17 | Log Aggregation | Medium | Checks if infrastructure logs are securely centralized off-server. | Logs are shipped to a secure, centralized SIEM or logging platform. |

## LIBRARIAN (Dependencies & Supply Chain) - 17 Checks (target scope, see banner above)
| ID | Check Name | Severity | Description | Pass Criteria |
|---|---|---|---|---|
| L-01 | Known CVEs | Critical | Scans dependency trees for packages with known critical/high CVEs. | No dependencies with unpatched High/Critical CVEs. |
| L-02 | Outdated Packages | Medium | Identifies packages that have reached End-Of-Life (EOL). | All core dependencies are actively maintained. |
| L-03 | Missing Lock Files | High | Checks for the absence of `package-lock.json`, `yarn.lock`, etc. | Lock files are committed and enforced in CI/CD. |
| L-04 | Malicious Packages | Critical | Scans for known typosquatted or compromised packages. | No known malicious packages present in dependency tree. |
| L-05 | License Compliance | Medium | Identifies copyleft licenses (GPL) in closed-source commercial apps. | All dependencies use permissive licenses (MIT, Apache, BSD) or approved commercial licenses. |
| L-06 | Unpinned CI Tools | Medium | Checks if CI/CD pipelines use unpinned external actions (e.g., `uses: action@master`). | CI actions are pinned to specific commit SHAs. |
| L-07 | Vulnerable Base Images | High | Scans Docker base images for OS-level vulnerabilities. | Base images contain zero critical/high OS vulnerabilities. |
| L-08 | Automated Scanning | Low | Verifies the presence of automated Dependabot or Renovate setups. | Automated dependency vulnerability scanning is active. |
| L-09 | Unsafe Post-installs | High | Flags packages executing complex shell scripts during installation. | `ignore-scripts` is used or post-install scripts are heavily audited. |
| L-10 | Dependency Confusion | High | Checks configuration of private package registries for namespace hijacking risks. | Scoped packages correctly map strictly to private registries. |
| L-11 | Bloated Artifacts | Low | Identifies inclusion of unnecessary development dependencies in production builds. | Production builds strictly exclude `devDependencies`. |
| L-12 | Subresource Integrity | Medium | Verifies that CDN-hosted scripts use SRI hashes. | `<script>` tags for external domains include `integrity` attributes. |
| L-13 | Abandonware | Medium | Flags packages that haven't received updates in over 2 years. | Critical paths do not rely on abandoned libraries. |
| L-14 | Over-privileged Tokens | High | Checks if package registry tokens (NPM, PyPI) have overly broad scopes. | Registry tokens are strictly scoped to publish-only for specific packages. |
| L-15 | Secret Leaks in History | Medium | Scans git history for accidentally committed secrets that might be packaged. | Git history is free of leaked credentials. |
| L-16 | Build Reproducibility | Low | Checks if builds produce deterministic outputs. | Builds from the same commit produce identical artifacts. |
| L-17 | Third-party Scripts | High | Audits inclusion of analytics/marketing scripts for data exfiltration risks. | Third-party scripts are vetted and restricted by CSP. |

## SHIELD (Frontend Security) - 17 Checks (target scope, see banner above)
| ID | Check Name | Severity | Description | Pass Criteria |
|---|---|---|---|---|
| F-01 | XSS via React/Vue | High | Detects unsafe dynamic rendering (e.g., `dangerouslySetInnerHTML`). | Unsafe rendering functions are avoided or input is strictly sanitized. |
| F-02 | Missing CSP | High | Verifies the presence of a strong Content Security Policy. | CSP header restricts `script-src`, `style-src`, and `connect-src`. |
| F-03 | Missing CSRF Tokens | High | Checks if state-changing forms lack Anti-CSRF protection (if using cookies). | Valid CSRF tokens or `SameSite` cookies are implemented. |
| F-04 | Secrets in LocalStorage | High | Detects storage of JWTs or sensitive user data in local storage. | Sensitive tokens are stored in `HttpOnly` cookies. |
| F-05 | Env Vars in Client | Critical | Scans frontend build outputs for accidentally bundled backend secrets. | No backend API keys or database passwords present in client bundles. |
| F-06 | Insecure iFrames | Medium | Checks if the application can be framed by arbitrary domains (Clickjacking). | `X-Frame-Options: DENY` or CSP `frame-ancestors` is enforced. |
| F-07 | Open Redirects (Client) | Medium | Identifies JavaScript routers vulnerable to DOM-based open redirects. | Client-side redirects validate URLs against whitelists. |
| F-08 | PostMessage Flaws | High | Analyzes `window.postMessage` listeners for origin verification. | Message listeners strictly verify `event.origin`. |
| F-09 | Client-Side Auth Logic | High | Flags implementations relying on frontend code to enforce access control. | Frontend UI hiding is backed by strict backend authorization. |
| F-10 | Vulnerable DOM Sinks | Medium | Scans for writing untrusted data directly to `innerHTML` or `document.write`. | Safe DOM APIs (`textContent`, `innerText`) are used instead. |
| F-11 | Third-party Data Leaks | Medium | Checks if URLs contain sensitive tokens that leak to third-party analytics via `Referer`. | Sensitive data is passed via headers/body, not URL parameters. |
| F-12 | Tab Nabbing | Low | Verifies that external links use `rel="noopener noreferrer"`. | External `target="_blank"` links include secure `rel` attributes. |
| F-13 | Web Worker Security | Medium | Audits Web Workers for insecure data handling or DOM access attempts. | Workers handle data securely and validate incoming messages. |
| F-14 | Unsafe Eval | High | Scans frontend code for usage of `eval()` or `new Function()`. | Code execution from strings is strictly prohibited. |
| F-15 | PII in URLs | Medium | Checks if personal data (emails, names) are placed in route parameters. | PII is excluded from URL paths to prevent proxy/browser history leaks. |
| F-16 | Captcha Bypass | Medium | Verifies that client-side captcha checks are backed by server validation. | Server strictly validates captcha tokens before processing actions. |
| F-17 | Offline Storage Leak | Medium | Checks IndexedDB/WebSQL for unencrypted sensitive offline data. | Sensitive offline data is encrypted before storage. |

## AUDITOR (Compliance & Governance) - 16 Checks (target scope, see banner above)
| ID | Check Name | Severity | Description | Pass Criteria |
|---|---|---|---|---|
| A-01 | Action Audit Trails | High | Verifies that critical user and admin actions generate immutable logs. | All CUD (Create/Update/Delete) actions on critical data are logged. |
| A-02 | Log Retention | Medium | Checks if system logs are retained for appropriate compliance periods. | Logs are retained for at least 365 days (varies by framework). |
| A-03 | GDPR Right to Erasure | High | Verifies the technical capability to permanently delete a user's data. | Hard deletion or anonymization scripts exist for user accounts. |
| A-04 | Cookie Consent | Medium | Checks for technical enforcement of cookie banners prior to tracking. | Non-essential cookies are blocked until explicit user consent is given. |
| A-05 | Log Masking | High | Detects if passwords, tokens, or PII are written to application logs. | Logging frameworks filter or mask sensitive fields. |
| A-06 | Incident Response | Low | Checks for the existence of a documented Incident Response Plan. | IRP document exists in the repository/knowledge base. |
| A-07 | Separation of Duties | Medium | Verifies that developers don't have direct access to production databases. | Production access requires break-glass procedures or separate roles. |
| A-08 | HIPAA BAA Presence | High | Identifies if health data is handled without signed BAAs from vendors. | Third-party services processing health data have signed BAAs. |
| A-09 | Consent Tracking | Medium | Checks if user consent (e.g., terms acceptance) is timestamped and stored. | Terms of Service/Privacy Policy acceptance is logged with a timestamp. |
| A-10 | Data Portability | Low | Verifies the capability to export a user's data in a structured format. | Users can request or download an export of their data (JSON/CSV). |
| A-11 | Continuous Monitoring | Medium | Checks if vulnerability scanning is automated rather than point-in-time. | CI/CD pipelines include automated security gates. |
| A-12 | Terms of Service Link | Low | Ensures legal agreements are accessible from all user-facing interfaces. | Links to ToS and Privacy Policy are present in footers. |
| A-13 | DPA Execution | Medium | Verifies Data Processing Agreements with sub-processors (GDPR). | DPAs are documented for all third-party data processors. |
| A-14 | Age Verification | Medium | Checks for age gating mechanisms if the app targets minors (COPPA). | Age verification is implemented if applicable. |
| A-15 | Accessibility (A11y) | Low | Scans for basic accessibility compliance (WCAG) which limits legal liability. | Basic ARIA attributes and color contrasts meet WCAG AA standards. |
| A-16 | Vendor Security Review | Low | Checks for documentation assessing the security of third-party APIs used. | Third-party vendor security posture is documented and reviewed annually. |

## ARCHITECT (Scalability & Resilience) - 16 Checks (target scope, see banner above)
| ID | Check Name | Severity | Description | Pass Criteria |
|---|---|---|---|---|
| R-01 | Single Point of Failure | High | Identifies architectural bottlenecks (e.g., single unclustered database). | High Availability (HA) configurations are used for critical components. |
| R-02 | Unbounded Queues | Medium | Checks if message queues or memory buffers lack maximum size limits. | Memory and queue bounds are strictly defined to prevent OOM errors. |
| R-03 | Sync Long Tasks | High | Detects synchronous HTTP processing of tasks taking >5 seconds. | Heavy processing tasks (e.g., PDF generation) are offloaded to background workers. |
| R-04 | Missing Caching | Medium | Identifies high-traffic read-heavy endpoints lacking cache layers. | Redis/Memcached or CDN caching is implemented for static/heavy reads. |
| R-05 | Auto-scaling Config | Medium | Verifies that infrastructure can dynamically scale based on load. | Auto-scaling groups or serverless architectures are correctly configured. |
| R-06 | Load Balancer Health | Medium | Checks if load balancers use deep health checks instead of simple pings. | Health checks verify database connectivity, not just HTTP 200 on `/`. |
| R-07 | Graceful Degradation | Low | Analyzes if the app functions partially when a non-critical API fails. | Circuit breakers are implemented for third-party API dependencies. |
| R-08 | Database Connection Pools | High | Verifies that the application uses connection pooling to prevent DB exhaustion. | Connection poolers (e.g., PgBouncer) or framework pool limits are configured. |
| R-09 | N+1 Queries | Medium | Scans ORM usage for N+1 query problems that degrade performance under load. | Eager loading is utilized to prevent exponential query execution. |
| R-10 | Retry Storms | Medium | Checks if internal services use exponential backoff for retries. | Failed internal requests back off exponentially with jitter. |
| R-11 | Payload Compression | Low | Verifies that HTTP responses are compressed (gzip/brotli). | Compression is enabled on the web server or CDN. |
| R-12 | Hardcoded IP Addresses | Medium | Detects hardcoded internal or external IPs that break upon infrastructure changes. | Service discovery or DNS is used for internal routing. |
| R-13 | Alerting Thresholds | High | Checks if APM alerts exist for latency spikes or error rate increases. | Alerts are configured for CPU > 80%, Error Rate > 1%, etc. |
| R-14 | Timeout Configurations | High | Verifies that external API calls have strict timeouts. | All outbound HTTP requests enforce a timeout (e.g., <5s). |
| R-15 | Unbounded Pagination | High | Checks if API clients can request massive page sizes (e.g., `limit=100000`). | Hard upper bounds are enforced on all paginated queries. |
| R-16 | Disaster Recovery Plan | Medium | Checks for documentation detailing steps to rebuild the environment from scratch. | Infrastructure as Code is complete enough to enable rapid recreation. |

*Total Checks: 17 + 17 + 17 + 17 + 17 + 17 + 17 + 16 + 16 = 151.*
