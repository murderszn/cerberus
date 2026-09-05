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

It operates entirely client-side with **no server, no build step, and no signup**:
- **The Web App ([index.html](index.html))** runs completely in your browser, analyzing public GitHub repositories using the GitHub API. It features real-time progress indicators, interactive check filters, history persistence, and shareable deep links.
- **The CLI ([examine.py](examine.py))** is a single Python 3 file with zero third-party dependencies, perfect for local directories, private repositories, and CI/CD pipelines.

Both interfaces consume the exact same unified check catalog, ensuring perfectly consistent results whether you scan from a terminal or a dashboard.

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

---

## Running It

### 🌐 Web App (GitHub repositories only)

Simply open [index.html](index.html) in any modern browser, or serve the repository root using any static file server:

```bash
python3 -m http.server 8000
```

Then visit `http://localhost:8000` and paste any public GitHub repository URL.

> [!NOTE]
> Due to browser CORS policies, the web app can only fetch public repositories. To scan private repositories, input a GitHub **Personal Access Token (PAT)** in the provided web UI field, or use the CLI.

---

### 💻 CLI (`examine.py`) — Local Directories, Private Repos, and CI

Run the scanner directly from your terminal. Since it is a raw Python 3 script, there is no installation step:

```bash
python3 examine.py <path-to-local-directory-or-github-url>
```

#### CLI Reference & Flags

| Flag | Argument | Description |
| :--- | :--- | :--- |
| `--json` | `path` | Write the complete, raw JSON report (matches the `cerberus.report/2` schema). |
| `--html` | `path` | Output a standalone, interactive HTML report. |
| `--sarif` | `path` | Generate SARIF format output to upload directly to GitHub Code Scanning. |
| `--fail-under` | `score` | Exit non-zero if the final score is below the threshold (e.g. `80`) — perfect for blocking failing PRs. |
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
# Exact legacy/offline behavior
python3 examine.py . --native-only

# Run every installed, applicable feeder; unavailable tools are warnings
python3 examine.py . --feeders auto --json report.json --feeder-json feeders.json

# Require selected tools to execute successfully
python3 examine.py . --feeders gitleaks,osv-scanner,zizmor --strict-feeders
```

Cerberus never downloads scanners during a scan. Install and version-pin them separately in your workstation or CI image. See the [GitHub Actions deployment guide](docs/cerberus-github-action-template.md) for the security and licensing notes.

#### Example: GitHub Actions CI/CD Integration

To run Cerberus on every pull request and upload findings directly to GitHub's Security tab:

```yaml
# .github/workflows/cerberus.yml
name: Cerberus Security Scan
on: [pull_request]

jobs:
  security-scan:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.x"

      - name: Run Cerberus Scanner
        run: python3 examine.py . --sarif cerberus.sarif --fail-under 80

      - name: Upload SARIF Report
        uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: cerberus.sarif
```

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
| [Gitleaks](https://github.com/gitleaks/gitleaks) | Secrets in files and, when configured, Git history | MIT |
| [OSV-Scanner](https://github.com/google/osv-scanner) | Known vulnerabilities in manifests, lockfiles, and SBOMs | Apache-2.0 |
| [Zizmor](https://github.com/woodruffw/zizmor) | GitHub Actions security weaknesses | MIT |
| [OpenSSF Scorecard](https://github.com/ossf/scorecard) | Repository supply-chain posture | Apache-2.0 |
| [actionlint](https://github.com/rhysd/actionlint) | GitHub Actions syntax and semantic errors | MIT |

Each adapter records tool provenance, normalizes severity, redacts possible secret values, and creates stable fingerprints for deduplication. `not_applicable` means the repository had no suitable input; `unavailable` means the executable was not installed; and `failed` covers timeout, invalid output, or another execution failure. Review upstream licenses yourself before redistributing scanner binaries.

### Grading Rubric
- **A**: $\ge$ 90
- **B**: $\ge$ 80
- **C**: $\ge$ 70
- **D**: $\ge$ 60
- **F**: $<$ 60

---

## Architecture

```
                 [ checks.json ] (Native Source of Truth)
                        │
         ┌──────────────┼──────────────┐
         ▼              ▼              ▼
   [ Web App ]     [ CLI Tool ]   [ Doc Generator ]
   (index.html)    (examine.py)   (generate-checks-docs.py)
         │              │              │
         ▼              ▼              ▼
    HTML Report    JSON/SARIF/HTML   documentation/checks.html
```

- **[`checks.json`](checks.json)** remains the single source of truth for native checks and scoring. Feeder adapters and ALIGNMENT are additive CLI orchestration layers; they do not change the browser scanner or silently affect the native score.
- **[`assets/scanner.js`](assets/scanner.js)** reads the rules and evaluates them concurrently (up to 8 files at a time) against downloaded repository files.
- **[`examine.py`](examine.py)** parses the same rules and evaluates them locally.
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

---

## Repository Structure

* [index.html](index.html) — The web dashboard scanner.
* [ceberus-classic.html](ceberus-classic.html) — The legacy static HTML scanner page.
* [examine.py](examine.py) — The Python CLI scanner.
* [checks.json](checks.json) — The unified check catalog rules engine.
* [logo.png](logo.png) — The official Cerberus Labs logo.
* [assets/](assets/) — Core JS assets including [`scanner.js`](assets/scanner.js) and [`checks.js`](assets/checks.js).
* [documentation/](documentation/) — Static documentation site.
* [docs/](docs/) — Additional specification docs (e.g. [`brand.md`](docs/brand.md), [`IMPROVEMENTS.md`](docs/IMPROVEMENTS.md), compliance guides).
* [scripts/](scripts/) — Internal developer tools, test runners, and doc generators.

---

## Active Roles

- **Joshua Johnson** — CEO / CFO
- **Caleb Johnson** — COO
- **Elijah Johnson** — CTO
