# Cerberus Labs: Agent Architecture

> **Status: mostly roadmap.** §1 below (WASM enclaves, dynamic resource provisioning,
> cross-agent deduplication, network egress for CVE lookups) describes a **planned**
> architecture that is not what ships today. The real, shipped architecture is much
> simpler and is authoritative in `docs/IMPROVEMENTS.md`:
>
> - There is no orchestrator process, no sandboxed per-agent runtime, and no WASM.
> - "Agents" are a grouping in `/checks.json`: each check has an `agent` field, and
>   each agent has a `weight`. All 58 checks run as static pattern matches (regex over
>   fetched file content, or file-presence checks) in one pass — in the browser for the
>   web app, or in the CLI process for `examine.py`.
> - There is no cross-agent deduplication step. Each check independently resolves to
>   `pass` / `fail` / `not_applicable` / `skipped`.
> - The only network calls are to `api.github.com` (tree/metadata) and
>   `raw.githubusercontent.com` (file contents). There is no live CVE database lookup —
>   LIBRARIAN's known-vulnerable-version check is a regex against version ranges recorded
>   directly in `checks.json`.
> - Real scoring is per-agent weight minus per-hit deductions, not a flat `100 - Σ`
>   deduction — see §2.3 of `docs/IMPROVEMENTS.md` and `documentation/scoring.html`.
>
> The per-agent descriptions in §2 below (domain, responsibility, input/output) are
> accurate in *spirit* — that grouping is real — but the specific "WASM Runtime
> Configuration" lines are aspirational/roadmap flavor text, not real infrastructure.
> For the exact, currently-running checks per agent, see `docs/scanner-checks.md` or
> `documentation/checks.html`, both generated straight from `checks.json`.

Cerberus divides its check catalog into 9 discrete, specialized agent domains, mimicking the workflow of a cross-functional human red-teaming unit — even though every check runs as a single static pass over the same fetched files.

---

## 1. Roadmap architecture (not yet built)

The diagram and steps below describe a **future** orchestrated pipeline, not the current implementation. See the banner above for what's real today.

```
[Target Target URL / Repo] ──> [Orchestrator Pre-flight] ──> [Swarm WASM Spawn]
                                                                    │
┌───────────────────────────────────────────────────────────────────┘
│
├──> [SENTINEL] ──────┐
├──> [GATEKEEPER] ────┼──> [Raw Finding Streams] ──> [Deduplication & Severity Scoring] ──> [Final Score (0-100)]
├──> [VAULT] ─────────┤
└──> ... (all 9) ─────┘
```

1. **Pre-flight & Target Parsing**: Receives the target (GitHub repository URL or endpoint URL), identifies the stack (e.g., Node.js, Python, React, Docker), and flags relevant folders and configuration files.
2. **Dynamic Resource Provisioning**: Spawns isolated, sandboxed WebAssembly (WASM) enclaves. Each agent runs inside its own stateless runtime environment, restricted from internet egress (unless scanning external endpoints) and having read-only access to source code.
3. **Consensus & Deduplication**: Because agents scan overlapping files (e.g., `SENTINEL` looking at route controller logic and `GATEKEEPER` looking at route auth logic), the Orchestrator runs a deduplication heuristic to combine duplicate flags into single actionable reports.
4. **Scoring Logic (roadmap)**: A flat, non-weighted deduction matrix — this is **not** the
   shipped model. The shipped model is per-agent weighted deductions; see
   `docs/IMPROVEMENTS.md` §2.3 and `documentation/scoring.html`.
   - Base Score: `100` points.
   - **Critical Vulnerability**: `-5` points.
   - **High Vulnerability**: `-3` points.
   - **Medium Vulnerability**: `-1` points.
   - **Low Vulnerability**: `-0.2` points.
   - Minimum possible score is clamped at `0`.

---

## 2. Agent domains (real grouping, roadmap runtime detail)

The domain, responsibility, and input/output description for each agent below reflects
real check groupings in `checks.json`. The "WASM Runtime Configuration" line in each
entry is roadmap flavor text and does not describe real infrastructure.

### 2.1 SENTINEL (Backend Code Review)
* **Domain**: Static Code Analysis & Core Vulnerability Detection.
* **Responsibility**: Inspects server-side logic for unsafe execution paths, injection vectors, and weak cryptographic configurations.
* **WASM Runtime Configuration**: Low CPU limits, high memory limit. Code parser loaded with language-specific AST engines.
* **Input**: Backend source files (`.js`, `.py`, `.go`, `.rb`, `.java`), server configuration files.
* **Output**: JSON payload detailing vulnerability type, file path, line number range, snippet, and risk category.

### 2.2 GATEKEEPER (Auth & Access Control)
* **Domain**: Authentication, Authorization, and Session Security.
* **Responsibility**: Checks authorization guards, session tracking rules, OAuth configurations, and rate limits on login routes.
* **WASM Runtime Configuration**: Medium CPU/Memory limit. Focus on routing files, route controllers, and auth middleware.
* **Input**: Middleware modules, user session configurations, token creation rules.
* **Output**: Validation report on RBAC enforcement and session decay policies.

### 2.3 VAULT (Database Security)
* **Domain**: Persistence Security and Sensitive Data Protection.
* **Responsibility**: Audits database schemas, ORM configuration files, connection handlers, and data masking strategies.
* **WASM Runtime Configuration**: Focused read access on schema migrators and database configuration paths.
* **Input**: DB migration scripts, schema files, database connection profiles.
* **Output**: List of cleartext storage flags, missing encryption patterns, and privilege risks.

### 2.4 CONDUIT (API Security)
* **Domain**: API Contract Integrity and Request Validation.
* **Responsibility**: Evaluates API gateway settings, routing tables, input validation rules, and CORS configuration.
* **WASM Runtime Configuration**: Allowed local network access to verify internal Swagger/OpenAPI file integrity.
* **Input**: API spec files (Swagger, OpenAPI), routing declarations, request controllers.
* **Output**: Report on input validation coverage, rate-limiting rules, and CORS vulnerabilities.

### 2.5 WATCHTOWER (Infrastructure & Deploy)
* **Domain**: DevSecOps and Infrastructure as Code (IaC).
* **Responsibility**: Scans Dockerfiles, Kubernetes manifests, terraform files, and CI/CD pipelines for configuration drift.
* **WASM Runtime Configuration**: Read access to deployment directories and repository metadata.
* **Input**: Dockerfiles, `docker-compose.yml`, Kubernetes manifests, GitHub Actions YAML files.
* **Output**: Infrastructure compliance report detailing exposed ports and running context.

### 2.6 LIBRARIAN (Dependencies & Supply Chain)
* **Domain**: Third-Party Libraries and Software Bill of Materials (SBOM).
* **Responsibility**: Analyzes manifest files to cross-reference installed versions with global vulnerability databases.
* **WASM Runtime Configuration**: Read access to manifest lock files. Allowed egress to check CVE databases.
* **Input**: `package-lock.json`, `requirements.txt`, `go.sum`, `Cargo.lock`.
* **Output**: Dependency risk metrics listing CVE status and license compliance gaps.

### 2.7 SHIELD (Frontend Security)
* **Domain**: Client-Side Protection.
* **Responsibility**: Audits client-side scripts, HTML, and browser headers to prevent clickjacking, XSS, and local state leaks.
* **WASM Runtime Configuration**: Read access to HTML templates, static files, and Webpack configurations.
* **Input**: Web templates, single-page application index files, client router configs.
* **Output**: Frontend vulnerability matrix focusing on local storage and frame policies.

### 2.8 AUDITOR (Compliance & Governance)
* **Domain**: Logging, Auditing, and Regulatory Standards.
* **Responsibility**: Ensures appropriate logging structures, sanitizes logging payloads, and tracks SOC 2/HIPAA compliance readiness.
* **WASM Runtime Configuration**: Read access to logging setups and policy docs.
* **Input**: Logging configurations, data retention structures, policy texts.
* **Output**: Compliance gap details mapped to regulatory framework controls.

### 2.9 ARCHITECT (Scalability & Resilience)
* **Domain**: Fault Tolerance and Disaster Recovery.
* **Responsibility**: Audits failover setups, resource boundaries, error handling routes, and caching designs.
* **WASM Runtime Configuration**: Heavy analytical analysis of deployment manifests and networking routing plans.
* **Input**: System architectural specs, Docker/K8s limits, route configurations.
* **Output**: Resilience indicators showing failure points and recovery delays.

---

## 3. What's actually shipped, per agent

The "Input"/"Output"/"Responsibility" prose above is broader than what's implemented.
This is the real, current count from `/checks.json`, weight included:

| Agent | Real domain name | Weight | Checks shipped |
|---|---|---|---|
| SENTINEL | Code Analysis | 14 | 10 |
| VAULT | Data Security | 13 | 8 |
| GATEKEEPER | Access Control | 12 | 6 |
| LIBRARIAN | Dependencies | 12 | 6 |
| CONDUIT | Network & API | 11 | 5 |
| WATCHTOWER | Application Config | 11 | 8 |
| SHIELD | Client Security | 11 | 6 |
| AUDITOR | Logging & Monitoring | 8 | 4 |
| ARCHITECT | Infrastructure | 8 | 5 |
| **Total** |  | **100** | **58** |

For the exact check IDs, detectors, CWEs, and remediations, see `docs/scanner-checks.md`
or `documentation/checks.html` — both generated from `checks.json` by
`scripts/generate-checks-docs.py`.
