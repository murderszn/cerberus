<p align="center">
  <img src="logo.png" alt="Cerberus Labs Logo" width="360" />
</p>

<h1 align="center">Cerberus</h1>

<p align="center">
  <a href="https://github.com/murderszn/cerberus/actions/workflows/ci.yml"><img src="https://github.com/murderszn/cerberus/actions/workflows/ci.yml/badge.svg" alt="CI Status"></a>
  <a href="https://github.com/murderszn/cerberus/stargazers"><img src="https://img.shields.io/github/stars/murderszn/cerberus" alt="GitHub stars"></a>
  <a href="https://github.com/murderszn/cerberus/network"><img src="https://img.shields.io/github/forks/murderszn/cerberus" alt="GitHub forks"></a>
  <a href="https://github.com/murderszn/cerberus/issues"><img src="https://img.shields.io/github/issues/murderszn/cerberus" alt="GitHub issues"></a>
  <a href="https://github.com/murderszn/cerberus/blob/main/LICENSE"><img src="https://img.shields.io/github/license/murderszn/cerberus" alt="License"></a>
</p>

<p align="center">
  <strong>HIGH-RIGOR REPO EXAMINATIONS | ZERO TRUST | AGENT ORCHESTRATED</strong><br>
  <em>Rigorous, real-time security certification for vibe-coded and rapid-deployment applications.</em>
</p>

<p align="center">
  <a href="#what-is-cerberus"><strong>About</strong></a> &bull;
  <a href="#running-it"><strong>Run a Scan</strong></a> &bull;
  <a href="#the-agent-swarm"><strong>Meet the Swarm</strong></a> &bull;
  <a href="#architecture"><strong>Architecture</strong></a> &bull;
  <a href="#developer-guide"><strong>Developer Guide</strong></a>
</p>

---

## What is Cerberus?

**Cerberus** is an automated, zero-configuration security scanner designed for modern, rapid-deployment engineering teams. As developers leverage AI assistants to ship features in minutes, security reviews are frequently compromised. Cerberus replaces slow, costly human auditing with a high-rigor, collaborative **AI agent swarm** that validates code, infrastructure, and configuration against a comprehensive checks catalog.

Its native scanner operates locally with **no server, no build step, and no signup**:
- **The Web App ([agent.html](agent.html))** runs completely in your browser, analyzing public GitHub repositories using the GitHub API. It features real-time progress indicators, interactive check filters, history persistence, and shareable deep links.
- **The CLI ([examine.py](examine.py))** uses Python 3 and the standard library for native checks, ALIGNMENT, orchestration, normalization, and reporting. Optional feeder executables are installed separately only when their specialized analysis is wanted.

Both interfaces consume the same native [`checks.json`](checks.json) catalog and preserve the same native scoring semantics. ALIGNMENT and external feeders are additive CLI capabilities and do not alter web scanner behavior.

---

## Target Audience & Personas

Cerberus is built to serve three core workflows:

* 🚀 **The Vibe-Coding Founder**: You're building application logic at lightning speed with AI. Cerberus gives you a push-button, zero-setup audit to secure your platform, identify hidden vulnerabilities, and build immediate trust with your users.
* 📋 **The Compliance-Ready Lead**: You're preparing your startup for **SOC 2, HIPAA, or GDPR** audits. Cerberus provides a structured, scored report detailing infrastructure gaps and data security flaws.
* 🔍 **The Tech-Focused VC Partner**: You need to run technical due diligence on a target investment. Cerberus lets you rapidly inspect a repository's code quality, risk vectors, and dependency posture without configuring development environments.

---

## Key Features

- **Security Orchestration**: Nine catalog-driven native agents remain the scoring engine, while the CLI can add a native ALIGNMENT review and normalized findings from specialized open-source scanners.
- **Deterministic Verification**: Every vulnerability is mapped to a concrete, verifiable failure condition. This drastically reduces the noise and false positives common in legacy static analysis.
- **Unified Engine**: Both the web dashboard and CLI execute the same rules from [`checks.json`](checks.json), emitting matching `cerberus.report/2` reports.
- **Frictionless Integration**: Drop a repository URL in the browser, run it locally via a terminal, or gate pull requests in CI/CD using `--fail-under`.
- **GitHub Actions Template**: Copy [`.github/workflow-templates/cerberus-security-review.yml`](.github/workflow-templates/cerberus-security-review.yml) into another repository to run JSON, HTML, and SARIF reviews on pull requests and main-branch pushes. See the [deployment guide](docs/cerberus-github-action-template.md).

### What the orchestration release adds

- Five allowlisted Phase 1 adapters: Gitleaks, OSV-Scanner, Zizmor, OpenSSF Scorecard, and actionlint.
- A native ALIGNMENT analyzer for unsafe, conflicting, or incomplete coding-agent guidance and workflow policy.
- Versioned normalized findings with source provenance, stable fingerprints, severity mapping, deduplication, and secret redaction.
- Independent native and ALIGNMENT scores plus a combined policy result with strict-feeder controls.
- Multi-producer JSON, HTML, and SARIF reports that still render when no feeder is installed.
- Safe execution boundaries: argv-only subprocesses, per-tool timeouts, bounded output, fixed executable allowlists, isolated filtered scan trees, and `.cerberusignore` support.

---

## Running It

### 🌐 Web App (GitHub repositories only)

Open the [research homepage](index.html), then choose [Cerberus Agent](agent.html) in any modern browser, or serve the repository root using any static file server:

```bash
python3 -m http.server 8000
```

Then visit `http://localhost:8000/agent.html` and paste any public GitHub repository URL. The research homepage lives at `/`; existing `index.html#/scan/...` and `index.html#/report/...` links forward to the Agent page, preserving their targets.

> [!NOTE]
> Due to browser CORS policies, the web app can only fetch public repositories. To scan private repositories, input a GitHub **Personal Access Token (PAT)** in the provided web UI field, or use the CLI.

---

### 💻 CLI (`examine.py`) — Local Directories, Private Repos, and CI

Run the scanner directly from your terminal. Since it is a raw Python 3 script, there is no installation step:

```bash
python3 examine.py <path-to-local-directory-or-github-url>
```

The default invocation runs the unchanged native checks plus ALIGNMENT, with external feeders disabled. Use `--native-only` for the exact native/offline path, or `--feeders auto` to discover all Phase 1 tools without installing anything automatically.

#### CLI Reference & Flags

| Flag | Argument | Description |
| :--- | :--- | :--- |
| `--json` | `path` | Write the complete, raw JSON report (matches the `cerberus.report/2` schema). |
| `--html` | `path` | Output a standalone, interactive HTML report. |
| `--sarif` | `path` | Generate SARIF format output to upload directly to GitHub Code Scanning. |
| `--fail-under` | `score` | Exit non-zero if the native Cerberus score is below the threshold (e.g. `80`). |
| `--only` | `agents` | Restrict evaluation to a comma-separated list of agent IDs (e.g. `sentinel,vault`). |
| `--severity` | `level` | Filter terminal output to show only findings at or above `critical`, `high`, `medium`, or `low`. |
| `--quiet` | *None* | Suppress file listings and print only the final score and grade. |
| `--no-color` | *None* | Disable ANSI color output in the terminal. |
| `--feeders` | `auto` or tool list | Run detected feeders, or a comma-separated selection of `gitleaks`, `osv-scanner`, `zizmor`, `scorecard`, and `actionlint`. The default is `none`. |
| `--native-only` | *None* | Disable feeders and ALIGNMENT for an offline, legacy-compatible native scan. |
| `--feeder-timeout` | `seconds` | Set the timeout applied separately to each external scanner. |
| `--feeder-json` | `path` | Preserve feeder results, including bounded raw output where it is safe to retain it. |
| `--strict-feeders` | *None* | Treat unavailable, failed, timed-out, or malformed explicitly requested feeders as policy blockers. |

`--fail-under` continues to evaluate only the native Cerberus score. Feeder and ALIGNMENT findings never change that score. When orchestration is enabled, the report also includes a combined policy result: any critical finding or at least two high findings fails policy; missing optional tools are warnings; and tool failures become blockers only with `--strict-feeders`. In this release the policy result is report data, not a new implicit CLI exit condition, preserving existing automation behavior.

Examples:

```bash
# Native/offline mode with legacy scoring semantics
python3 examine.py . --native-only

# Run every applicable feeder and write every supported report format
python3 examine.py . --feeders auto --json report.json --html report.html \
  --sarif report.sarif --feeder-json feeders.json

# Require selected tools to execute successfully
python3 examine.py . --feeders gitleaks,osv-scanner,zizmor --strict-feeders
```

Cerberus never downloads scanners during a scan. Install and version-pin them separately in your workstation or CI image. See the [GitHub Actions deployment guide](docs/cerberus-github-action-template.md) for the security and licensing notes.

#### GitHub Actions CI/CD integration

Use the reviewed template at [`.github/workflow-templates/cerberus-security-review.yml`](.github/workflow-templates/cerberus-security-review.yml). It:

- defaults to `native-only` so missing third-party tools cannot weaken the baseline;
- preserves the native `--fail-under` gate;
- supports manual `auto` and strict feeder modes;
- pins GitHub Actions and the Cerberus checkout to reviewed commit SHAs; and
- uploads normalized JSON, HTML, SARIF, and feeder artifacts.

The template never installs scanner binaries. Build a reviewed runner image with exact feeder versions if feeder execution is required in CI. `ref: main` is suitable only for experimentation, not production.

---

## The Agent Swarm

The scan logic is divided among **9 specialized security agents**. Each agent owns a specific domain, evaluates a dedicated set of rules, and starts with a max weight. Failed checks subtract points from that agent's weight based on check severity (capped per check), and the agent scores are summed to produce a final score from `0` to `100`.

| Agent | Domain | Target Focus | Weight | Active Checks |
| :--- | :--- | :--- | :---: | :---: |
| 🛡️ **SENTINEL** | Code Analysis | Vulnerable code patterns, injection points, unsafe functions | **14** | 11 checks |
| 🔑 **VAULT** | Data Security | Exposed secrets, unencrypted databases, hardcoded credentials | **13** | 8 checks |
| 🚪 **GATEKEEPER** | Access Control | Authentication, CORS misconfigurations, broken authorization | **12** | 6 checks |
| 📦 **LIBRARIAN** | Dependencies | Deprecated packages, lockfile presence, vulnerable versions | **12** | 6 checks |
| 📡 **CONDUIT** | Network & API | Cleartext communication, insecure HTTP methods, API keys | **11** | 5 checks |
| 🔭 **WATCHTOWER** | Application Config | Environment variables, debug flags, configuration safety | **11** | 8 checks |
| 🖥️ **SHIELD** | Client Security | XSS vectors, CSRF, insecure client-side session management | **11** | 6 checks |
| 📝 **AUDITOR** | Logging & Monitoring | Verbose logging, lack of audit trails, missing security contacts | **8** | 4 checks |
| 🏗️ **ARCHITECT** | Infrastructure | Dockerfile practices, IaC misconfigurations, root privileges | **8** | 5 checks |
| **Total** | | | **100** | **59 checks** |

The table above is the native score model and is unchanged. The CLI's additional **ALIGNMENT** agent examines repository instructions and operational surfaces used by coding agents—for example conflicting policy, destructive commands, secret-exposure directions, prompt-injection-like instructions, and risky workflow permissions. ALIGNMENT has its own score and grade and is not added to the 100 native points.

### External feeders

| Feeder | Specialized evidence | Upstream license |
| :--- | :--- | :--- |
| [Gitleaks](https://github.com/gitleaks/gitleaks) | Secrets in repository files (`--no-git`; history scanning is not enabled in Phase 1) | MIT |
| [OSV-Scanner](https://github.com/google/osv-scanner) | Known vulnerabilities in manifests, lockfiles, and SBOMs | Apache-2.0 |
| [Zizmor](https://github.com/woodruffw/zizmor) | GitHub Actions security weaknesses; invoked in offline mode | MIT |
| [OpenSSF Scorecard](https://github.com/ossf/scorecard) | Repository supply-chain posture | Apache-2.0 |
| [actionlint](https://github.com/rhysd/actionlint) | GitHub Actions syntax and semantic errors | MIT |

Each adapter records tool provenance, normalizes severity, redacts possible secret values, and creates stable fingerprints for deduplication. `not_applicable` means the repository had no suitable input; `unavailable` means the executable was not installed; and `failed` covers timeout, invalid output, or another execution failure. Review upstream licenses yourself before redistributing scanner binaries.

Applicability is evaluated before availability: OSV-Scanner requires a supported manifest, lockfile, or SBOM; Zizmor and actionlint require `.github/workflows/**/*.yml` or `.yaml`; Scorecard requires Git metadata or GitHub repository context; and Gitleaks requires repository files. Ignored paths and nested scanner checkouts are excluded before applicable feeders run.

### Grading Rubric
- **A**: $\ge$ 90
- **B**: $\ge$ 80
- **C**: $\ge$ 70
- **D**: $\ge$ 60
- **F**: $<$ 60

---

## Architecture

```text
                       checks.json
                  native source of truth
                     /             \
                    v               v
              Browser scanner    CLI native scan
                                      |
                   +------------------+------------------+
                   |                                     |
                   v                                     v
             ALIGNMENT analyzer                 Phase 1 feeder registry
                                                 /  /  |  \  \
                                      Gitleaks OSV Zizmor Scorecard actionlint
                   |                                     |
                   +------------------+------------------+
                                      v
                         normalization + deduplication
                                      |
                                      v
                cerberus.report/2 + HTML + SARIF + feeder JSON
                   native score | alignment | feeders | policy
```

- **[`checks.json`](checks.json)** remains the single source of truth for native checks and scoring. Feeder adapters and ALIGNMENT are additive CLI orchestration layers; they do not change the browser scanner or silently affect the native score.
- **[`assets/scanner.js`](assets/scanner.js)** reads the rules and evaluates them concurrently (up to 8 files at a time) against downloaded repository files.
- **[`examine.py`](examine.py)** parses the same rules and evaluates them locally.
- **[`alignment.py`](alignment.py)** performs bounded, read-only analysis of coding-agent policies, operational scripts, project metadata, and GitHub Actions workflows.
- **[`feeders/`](feeders/)** contains the fixed registry, safe subprocess runner, normalization utilities, and five Phase 1 adapters.
- **[`scripts/generate-checks-docs.py`](scripts/generate-checks-docs.py)** compiles the JSON catalog into customer-facing markdown files (`docs/scanner-checks.md`) and HTML sites (`documentation/checks.html`).

---

## Developer Guide

### Rebuilding Assets and Docs

If you add, remove, or modify checks in [`checks.json`](checks.json):

1. **Rebuild Web Assets**:
   Run the build script to compile the JSON catalog into `assets/checks.js` for browser consumption:
   ```bash
   python3 scripts/build-checks.py
   ```

2. **Regenerate Documentation**:
   Run the documentation generator to update the static HTML documentation site and local markdown reference:
   ```bash
   python3 scripts/generate-checks-docs.py
   ```

3. **Verify Locally**:
   Run the CLI scanner on the local repository to test your changes:
   ```bash
   python3 examine.py .
   ```

### Adding a feeder

Feeder integrations live under `feeders/`. Implement the shared adapter contract,
declare a fixed executable name and argv builder, add applicability detection,
normalize the tool's output without retaining credential values, and register the
adapter in `feeders/registry.py`. Adapters must never invoke a shell, download a
binary, or execute repository-provided commands. Add fixtures for applicable and
non-applicable repositories plus tests for unavailable tools, timeouts, non-zero
exits, malformed output, severity mapping, fingerprint stability, redaction, and
deduplication.

External results are best-effort translations of upstream formats. Tool versions
can add or rename rules, Scorecard checks may need GitHub/network context, history
scanning depends on available Git metadata, and heuristic ALIGNMENT findings need
human review. Use stable fingerprints and documented suppressions to manage false
positives; do not weaken native checks to hide feeder noise.

### Report compatibility

The top-level `schema`, `score`, `grade`, `counts`, and `agents` fields retain the
`cerberus.report/2` contract used by the web UI and existing automation. CLI
orchestration adds `native`, `alignment`, `feeders`, and `policy` sections. Each
tool result uses `cerberus.feeder/1`; the feeder collection uses
`cerberus.feeders/1`; and ALIGNMENT uses `cerberus.alignment/1`. SARIF keeps the
native Cerberus run first and adds separate runs for ALIGNMENT and each feeder so
source provenance is not lost.

```json
{
  "schema": "cerberus.report/2",
  "score": 100,
  "grade": "A",
  "native": { "score": 100, "grade": "A", "findings": [] },
  "alignment": { "schema": "cerberus.alignment/1", "score": 99, "grade": "A", "findings": [] },
  "feeders": {
    "schema": "cerberus.feeders/1",
    "summary": { "completed": 0, "not_applicable": 1, "unavailable": 4, "failed": 0 },
    "tools": [],
    "findings": []
  },
  "policy": { "passed": true, "blockers": [], "warnings": [] }
}
```

Each tool entry in `feeders.tools` uses `cerberus.feeder/1` and records its version, status, target, duration, normalized findings, sanitized raw evidence when practical, and structured errors. Secret-bearing Gitleaks fields and source snippets that may contain credentials are omitted rather than copied into reports.

### ALIGNMENT scope

ALIGNMENT checks supported instruction files such as `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `TEAM.md`, Cursor rules, Copilot instructions, `CONTRIBUTING.md`, `README.md`, and `SECURITY.md`. It also inspects package scripts, Makefiles and Justfiles, setup and shell scripts, and GitHub Actions workflows.

Its rules cover instruction conflicts, disabled validation or security controls, credential exposure, destructive Git operations, remote code piping, unsafe trust of issue or web content, hidden directives, missing policy/validation/secret guidance, documentation and stack mismatches, broad workflow permissions, unpinned actions, workflow expression injection, repository-boundary violations, and prompt-injection-like overrides. These are heuristic policy findings and should be reviewed in context.

### Development verification

```bash
python3 -m py_compile examine.py alignment.py feeders/*.py
python3 -m unittest discover -s tests -v
python3 scripts/build-checks.py
python3 scripts/generate-checks-docs.py
python3 examine.py . --native-only --json /tmp/cerberus-native.json --no-color
python3 examine.py . --feeders auto --json /tmp/cerberus-full.json --no-color
git diff --check
```

The test suite covers registry behavior, applicability, unavailable tools, timeouts, malformed output, exit codes, normalization, redaction, fingerprint stability, deduplication, report rendering, CLI modes, ALIGNMENT rules, workflow checks, and scanner-checkout exclusion.

### Current limitations

- Phase 1 implements only the five feeders listed above; it does not claim complete security coverage.
- External output formats can change between tool versions, so pin and validate versions before relying on CI policy.
- Gitleaks scans the working tree in this release, not Git history.
- Scorecard may require repository metadata, credentials, or network access that are unavailable in restricted environments.
- ALIGNMENT is contextual static analysis and can produce false positives in documentation, fixtures, or quoted unsafe examples.
- The combined policy result is report data. It does not implicitly replace the native `--fail-under` exit gate; `--strict-feeders` additionally fails on unavailable or failed requested feeders.

---

## Repository Structure

* [index.html](index.html) — The research homepage with three framed, full-bleed details from the Cerberus engraving and titles overlaid on the images.
* [agent.html](agent.html) — The browser scanner, progress view, and interactive report.
* [ceberus-classic.html](ceberus-classic.html) — The legacy static HTML scanner page.
* [examine.py](examine.py) — The Python CLI, native report builder, orchestration entry point, and JSON/HTML/SARIF renderer.
* [alignment.py](alignment.py) — Native repository and coding-agent alignment analyzer.
* [feeders/](feeders/) — Phase 1 external-tool adapters, registry, runner, and normalization contract.
* [checks.json](checks.json) — Native check catalog and scoring source of truth.
* [logo.png](logo.png) — The official Cerberus Labs logo.
* [assets/](assets/) — Scanner scripts, the original engraving, social preview, shared `site.css`, Agent styling in `agent-polish.css`, and legacy-route forwarding in `home.js`.
* [documentation/](documentation/) — Static documentation site.
* [docs/](docs/) — Scanner catalog, examination specification, GitHub Actions guide, product documentation, and compliance material.
* [scripts/](scripts/) — Check asset builders, documentation generation, and the browser scanner integration harness.
* [tests/](tests/) — Native engine, feeder, ALIGNMENT, CLI mode, orchestration, SARIF, HTML, and safety tests.
* [.github/workflow-templates/cerberus-security-review.yml](.github/workflow-templates/cerberus-security-review.yml) — Pinned native-first CI review template with optional feeders.

---

## Active Roles

- **Joshua Johnson** — CEO / CFO
- **Caleb Johnson** — COO
- **Elijah Johnson** — CTO
