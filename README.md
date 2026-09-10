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
  <a href="#agent-cli-workbench"><strong>Agent CLI</strong></a> &bull;
  <a href="#github-app--cloud-agent"><strong>GitHub App</strong></a> &bull;
  <a href="#the-10-agent-deployment"><strong>Meet the Swarm</strong></a> &bull;
  <a href="#architecture"><strong>Architecture</strong></a> &bull;
  <a href="#developer-guide"><strong>Developer Guide</strong></a>
</p>

---

## What is Cerberus?

**Cerberus** is an automated, zero-configuration security scanner and agent workbench designed for modern, rapid-deployment engineering teams. As developers leverage AI assistants to ship features in minutes, security reviews are frequently compromised. Cerberus replaces slow, costly human auditing with a high-rigor, collaborative **AI agent swarm** that validates code, infrastructure, and configuration against a comprehensive checks catalog — then helps you fix the findings.

The project spans three product surfaces:

1. **Deterministic Scanner** — a catalog-driven, zero-dependency engine that runs identically in the browser and on the CLI. No server, no build step, no signup.
2. **Agent CLI Workbench** — an interactive terminal (scrollback REPL or full-screen Ink TUI) that deploys nine named security-specialist personas against your codebase, with tool use, plan/accept-edits modes, session persistence, and swarm fan-out.
3. **GitHub App & Cloud Agent** — a Cloudflare Workers deployment with GitHub OAuth sign-in, GitHub App installation, scan-grounded conversations, AI-generated change sets with inline diffs, and one-click draft pull requests.

---

## Target Audience & Personas

Cerberus is built to serve three core workflows:

* 🚀 **The Vibe-Coding Founder**: You're building application logic at lightning speed with AI. Cerberus gives you a push-button, zero-setup audit to secure your platform, identify hidden vulnerabilities, and build immediate trust with your users.
* 📋 **The Compliance-Ready Lead**: You're preparing your startup for **SOC 2, HIPAA, or GDPR** audits. Cerberus provides a structured, scored report detailing infrastructure gaps and data security flaws.
* 🔍 **The Tech-Focused VC Partner**: You need to run technical due diligence on a target investment. Cerberus lets you rapidly inspect a repository's code quality, risk vectors, and dependency posture without configuring development environments.

---

## Key Features

- **Deterministic Security Scan**: Nine catalog-driven native agents score your repository from `0` to `100`. Every vulnerability is mapped to a concrete, verifiable failure condition — drastically reducing noise and false positives.
- **Unified Engine**: Both the web dashboard and CLI execute the same rules from [`checks.json`](checks.json), emitting matching `cerberus.report/2` reports.
- **Agent CLI Workbench**: Chat with an AI orchestrator or individual specialist personas. The agents can read files, search your workspace, edit code, run commands, browse the web, create PRs, and verify fixes with a scan — all within a permission-controlled tool loop.
- **GitHub App Cloud Agent**: Sign in with GitHub, install the Cerberus App on your repositories, start a scan-grounded conversation, and let the agent propose file-level changes. Review the diff, approve, and a draft PR is created on your repo — all from the browser.
- **Orchestration & External Feeders**: The CLI can add a native ALIGNMENT review and normalized findings from five specialized open-source scanners (Gitleaks, OSV-Scanner, Zizmor, OpenSSF Scorecard, actionlint).
- **Frictionless Integration**: Drop a repository URL in the browser, run it locally via a terminal, or gate pull requests in CI/CD using `--fail-under` and `--fail-on`.
- **GitHub Actions Template**: Copy [`.github/workflow-templates/cerberus-security-review.yml`](.github/workflow-templates/cerberus-security-review.yml) into another repository to run JSON, HTML, and SARIF reviews on pull requests and main-branch pushes. See the [deployment guide](docs/cerberus-github-action-template.md).
- **Hermes Voice Interface**: [`assistant-eyes.html`](assistant-eyes.html) is a browser-based voice assistant client with animated eye tracking, speech-to-text input, and text reply display — designed to bridge to a local Hermes agent instance over LAN.

---

## Running It

### npm launcher

If you already use Node.js, the published npm launcher can bootstrap and run the Python CLI:

```bash
npx cerberus-agent scan .
npx cerberus-agent agent "audit this repository"
```

The launcher requires Node.js 18+ and Python 3.10+. It installs the current agent runtime from this repository into the active Python environment, then forwards the command. The browser interface remains available at [Cerberus Agent](https://murderszn.github.io/cerberus/agent.html).

### 🌐 Web App (GitHub repositories only)

Open the [research homepage](index.html), then choose [Cerberus Agent](agent.html) in any modern browser, or serve the repository root using any static file server:

```bash
python3 -m http.server 8000
```

Then visit `http://localhost:8000/agent.html` and paste any public GitHub repository URL. The research homepage lives at `/`; existing `index.html#/scan/...` and `index.html#/report/...` links forward to the Agent page, preserving their targets.

> [!NOTE]
> Due to browser CORS policies, the web app can only fetch public repositories. To scan private repositories, input a GitHub **Personal Access Token (PAT)** in the provided web UI field, or use the CLI. With the GitHub App installed, authenticated users can scan private repositories through the cloud agent.

---

### 💻 CLI (`examine.py`) — Local Directories, Private Repos, and CI

Install the CLI (Python 3.10+) with the `cerberus` entry point:

```bash
pipx install "cerberus[agent] @ git+https://github.com/murderszn/cerberus.git"
cerberus scan <path-to-local-directory-or-github-url>
```

Scanner only, without the agent runtime: `pipx install git+https://github.com/murderszn/cerberus.git` — `cerberus scan` stays stdlib-only. From a checkout you can also run it with no installation step:

```bash
python3 examine.py <path-to-local-directory-or-github-url>
```

The default invocation runs the unchanged native checks plus ALIGNMENT, with external feeders disabled. Use `--native-only` for the exact native/offline path, or `--feeders auto` to discover all Phase 1 tools without installing anything automatically.

#### Scanner CLI Reference & Flags

| Flag | Argument | Description |
| :--- | :--- | :--- |
| `--json` | `path` | Write the complete, raw JSON report (matches the `cerberus.report/2` schema). |
| `--html` | `path` | Output a standalone, interactive HTML report. |
| `--sarif` | `path` | Generate SARIF format output to upload directly to GitHub Code Scanning. |
| `--fail-under` | `score` | Exit non-zero if the native Cerberus score is below the threshold (e.g. `80`). |
| `--fail-on` | `critical`, `high`, `medium`, or `low` | Exit non-zero if any failed check is at or above the severity (e.g. `--fail-on high` fails on high or critical, even at a passing score). |
| `--only` | `agents` | Restrict evaluation to a comma-separated list of agent IDs (e.g. `sentinel,vault`). |
| `--severity` | `level` | Filter terminal output to show only findings at or above `critical`, `high`, `medium`, or `low`. |
| `--quiet` | *None* | Suppress file listings and print only the final score and grade. |
| `--no-color` | *None* | Disable ANSI color output in the terminal. |
| `--feeders` | `auto` or tool list | Run detected feeders, or a comma-separated selection of `gitleaks`, `osv-scanner`, `zizmor`, `scorecard`, and `actionlint`. The default is `none`. |
| `--native-only` | *None* | Disable feeders and ALIGNMENT for an offline, legacy-compatible native scan. |
| `--feeder-timeout` | `seconds` | Set the timeout applied separately to each external scanner. |
| `--feeder-json` | `path` | Preserve feeder results, including bounded raw output where it is safe to retain it. |
| `--strict-feeders` | *None* | Treat unavailable, failed, timed-out, or malformed explicitly requested feeders as policy blockers. |

`--fail-under` continues to evaluate only the native Cerberus score. Feeder and ALIGNMENT findings never change that score. `--fail-on` is the severity companion: it fails on failed-check severity even when the score passes (e.g. CI uses `--fail-under 95 --fail-on high`). When orchestration is enabled, the report also includes a combined policy result: any critical finding or at least two high findings fails policy; missing optional tools are warnings; and tool failures become blockers only with `--strict-feeders`. In this release the policy result is report data, not a new implicit CLI exit condition, preserving existing automation behavior.

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

## Agent CLI Workbench

The `cerberus` entry point (installed via `pipx install "cerberus[agent] @ ..."`) provides an interactive agent runtime powered by Pollinations-compatible LLM providers. The deterministic scanner (`cerberus scan`) remains stdlib-only and never needs the agent dependencies.

### Subcommands

| Command | Description |
| :--- | :--- |
| `cerberus scan <args…>` | Passthrough to the deterministic engine. No login, no dependencies. |
| `cerberus agent [GOAL…]` | Orchestrator session with all 9 specialist personas available. |
| `cerberus <persona> [TASK…]` | Chat directly with one named specialist (e.g. `cerberus sentinel "fix the login bug"`). |
| `cerberus run "goal" [--format json]` | Headless one-shot execution (accepts stdin). |
| `cerberus model [name]` | List models or switch the persisted default. |
| `cerberus models` | Grouped model catalog table. |
| `cerberus init` | Scaffold `~/.cerberus/config.yaml` and a project `CERBERUS.md`. |
| `cerberus config show\|get\|set` | Inspect and edit the layered config. |
| `cerberus sessions list\|resume\|fork\|delete` | Manage saved conversation transcripts (`~/.cerberus/sessions/`). |
| `cerberus permissions allow\|ask\|deny` | Set tool permission tiers (global/project/session scopes). |
| `cerberus completions bash\|zsh\|fish` | Output shell completion scripts. |
| `cerberus login\|logout\|status\|logs` | Authenticate, check status, and view diagnostic logs. |

### Agent features

- **Plan & accept-edits modes**: Plan mode (default) is read-only; Shift-Tab toggles accept-edits live. `--yolo` starts in accept-edits.
- **Full-screen Ink workbench**: `--workbench` launches a Textual TUI with panels, scrollback, and inline diffs. Falls back to a classic scrollback REPL.
- **Swarm fan-out**: `--swarm` classifies a goal and delegates subtasks concurrently across the 9 personas with map-reduce coordination.
- **Tool safety**: Permission tiers (`allow|ask|deny`), workspace-boundary enforcement, `.cerberusignore` support, secret redaction, destructive-command approval gates, and bounded bash timeouts.
- **Tools available**: `read_file`, `edit_file`, `multi_edit_file`, `write_file`, `search_workspace`, `grep_search`, `list_symbols`, `list_directory`, `glob_files`, `file_tree`, `execute_bash_command`, `git_status`, `git_diff`, `git_log`, `git_branch`, `browse_web_content`, `http_request`, `python_diagnostics` (LSP), `mcp_invoke`, `create_pull_request`.
- **Layered config**: `global (~/.cerberus/config.yaml) < project (CERBERUS.md) < env < CLI flags`. Per-provider model maps with endpoint, key, and temperature overrides.
- **Session persistence**: Conversations are saved as JSONL transcripts and can be resumed, forked, or deleted.
- **Slash commands in REPL**: `/scan`, `/review`, `/undo`, `/model`, `/models`, `/approvals`, `/team`, `/compact`, `/add`, and more.
- **PR creation**: `--pr` opens a GitHub pull request from workspace changes after a run.
- **Streamlined output**: Long responses are auto-summarized into grouped digests; full text is available on request or with `-v`.

---

## GitHub App & Cloud Agent

The [`workers/github-auth/`](workers/github-auth/) directory contains a **Cloudflare Workers** deployment that powers the authenticated product backend:

- **GitHub OAuth sign-in** with PKCE, secure session cookies, and D1-backed account storage.
- **GitHub App installation** — users install the `cerberus-security-agent` App on their repositories, granting scoped `contents:write` and `pull_requests:write` permissions.
- **Scan-grounded conversations** — after a browser scan, authenticated users open a conversation pinned to an immutable commit SHA. The cloud agent has repository tools (`list_repository_paths`, `read_file`) and can inspect the codebase at the scanned commit.
- **Change set proposals** — the agent calls `propose_changes` to produce a reviewed file-level change set with diffs and rationale, stored server-side.
- **Draft PR creation** — users review the change set in the browser UI, approve it, and a draft PR is created on their repository via the GitHub App's installation token.
- **Webhook sync** — `installation` and `installation_repositories` events keep the repository list in sync.
- **Engineering intent tracking** — each conversation captures a concise engineering objective distilled by the agent.

The worker is configured in [`wrangler.jsonc`](workers/github-auth/wrangler.jsonc) with a D1 database, static asset serving, and a nightly cron.

---

## The 10-Agent Deployment

The native scan logic is divided among **9 deterministic security specialists**. Each owns a specific domain, evaluates a dedicated set of rules, and starts with a max weight. Failed checks subtract points from that agent's weight based on check severity (capped per check), and the specialist scores are summed to produce a final score from `0` to `100`.

In the web deployment, **CURATOR is agent 10**. It deploys alongside the specialists, waits on their evidence, and automatically asks the selected Pollinations model to synthesize their combined returns into a prioritized, user-facing brief. CURATOR is explicitly non-scoring: it cannot alter check states or the native 100-point result. Without a Pollinations connection, the nine specialists still complete and CURATOR is marked as awaiting connection.

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
| 🧠 **CURATOR** | AI Evidence Synthesis | Reviews the nine specialist returns and prioritizes the user brief | **Non-scoring** | Post-evidence curation |
| **Total** | | | **100** | **59 checks** |

The table above is the native score model and is unchanged. The CLI's additional **ALIGNMENT** agent examines repository instructions and operational surfaces used by coding agents—for example conflicting policy, destructive commands, secret-exposure directions, prompt-injection-like instructions, and risky workflow permissions. ALIGNMENT has its own score and grade and is not added to the 100 native points.

In the **Agent CLI**, the same nine specialist names are available as interactive personas. Each persona has a dedicated system prompt, domain-restricted tool set, and default mode (plan or build). The orchestrator can classify goals and fan out tasks to the relevant specialists concurrently using the swarm coordinator.

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

> **Master Architecture & Pitch Strategy**: For a comprehensive investor pitch and technology breakdown detailing the Cerberus Labs business model, Cerberus Agent runtime, GitHub App integration, and market strategy, see [**docs/architecture-map.md**](docs/architecture-map.md).

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


              ┌────────────────────────────────────────────────┐
              │            Agent CLI Workbench                 │
              │  Pollinations / OpenAI-compatible provider     │
              │  ┌─────────┐  ┌────────┐  ┌──────────────┐   │
              │  │  REPL   │  │Ink TUI │  │ Headless run │   │
              │  └────┬────┘  └───┬────┘  └──────┬───────┘   │
              │       └───────────┼───────────────┘           │
              │                   v                           │
              │          AgentLoop (tool loop)                │
              │          9 persona prompts                    │
              │          CerberusSwarm (fan-out)              │
              │          ToolRegistry (20+ tools)             │
              │          Session persistence                  │
              └────────────────────────────────────────────────┘

              ┌────────────────────────────────────────────────┐
              │       Cloudflare Workers (GitHub App)          │
              │  GitHub OAuth · D1 database · Webhooks         │
              │  Scan-grounded conversations · Change sets     │
              │  Draft PR creation · Installation sync         │
              └────────────────────────────────────────────────┘
```

- **[`checks.json`](checks.json)** remains the single source of truth for native checks and scoring. Feeder adapters and ALIGNMENT are additive CLI orchestration layers; they do not change the browser scanner or silently affect the native score.
- **[`assets/scanner.js`](assets/scanner.js)** reads the rules and evaluates them concurrently (up to 8 files at a time) against downloaded repository files.
- **[`examine.py`](examine.py)** parses the same rules and evaluates them locally.
- **[`alignment.py`](alignment.py)** performs bounded, read-only analysis of coding-agent policies, operational scripts, project metadata, and GitHub Actions workflows.
- **[`feeders/`](feeders/)** contains the fixed registry, safe subprocess runner, normalization utilities, and five Phase 1 adapters.
- **[`servers/`](servers/)** is the agent CLI runtime — entry point ([`cli.py`](servers/cli.py)), agent loop, swarm coordinator, 9 persona prompt files, 20+ tool implementations, Textual TUI, Rich console UI, config system, session store, auth/login, and provider client.
- **[`workers/github-auth/`](workers/github-auth/)** is the Cloudflare Workers backend — GitHub OAuth, App installation, scan-grounded conversations, change sets, draft PR creation, and webhook sync.
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

The test suite covers registry behavior, applicability, unavailable tools, timeouts, malformed output, exit codes, normalization, redaction, fingerprint stability, deduplication, report rendering, CLI modes, ALIGNMENT rules, workflow checks, scanner-checkout exclusion, agent loop behavior, swarm coordination, TUI markup, console output, slash commands, approval tiers, LSP/MCP stubs, and scan context.

### Current limitations

- Phase 1 implements only the five feeders listed above; it does not claim complete security coverage.
- External output formats can change between tool versions, so pin and validate versions before relying on CI policy.
- Gitleaks scans the working tree in this release, not Git history.
- Scorecard may require repository metadata, credentials, or network access that are unavailable in restricted environments.
- ALIGNMENT is contextual static analysis and can produce false positives in documentation, fixtures, or quoted unsafe examples.
- The combined policy result is report data. It does not implicitly replace the native `--fail-under` exit gate; `--strict-feeders` additionally fails on unavailable or failed requested feeders.
- The cloud agent runs over Pollinations and is subject to model availability and rate limits.

---

## Repository Structure

* [index.html](index.html) — The research homepage with three framed, full-bleed details from the Cerberus engraving and titles overlaid on the images.
* [agent.html](agent.html) — The browser scanner, progress view, interactive report, GitHub App integration, and scan-grounded conversation UI.
* [assistant-eyes.html](assistant-eyes.html) — Hermes voice assistant interface — animated eye tracking, speech-to-text input, configurable LAN bridge connection.
* [releases.html](releases.html) — Compact, stackable release list with collapsible install blocks and status badges.
* [shop.html](shop.html) — Pre-order reservation page (email only, $0 due today).
* [cerberus-classic.html](cerberus-classic.html) — The legacy static HTML scanner page.
* [cerberus-report.html](cerberus-report.html) — Sample standalone HTML report (dark/light mode, interactive).
* [examine.py](examine.py) — The Python CLI, native report builder, orchestration entry point, and JSON/HTML/SARIF renderer.
* [alignment.py](alignment.py) — Native repository and coding-agent alignment analyzer.
* [feeders/](feeders/) — Phase 1 external-tool adapters, registry, runner, and normalization contract.
* [servers/](servers/) — **Agent CLI runtime**: entry point (`cli.py`), commands, config system, session store, auth/login, provider client, agent loop, swarm coordinator, 9 persona prompts, 20+ tool implementations (file I/O, search, edit, bash, git, web, LSP, MCP, PR creation), and UI (Rich console, Textual TUI, narration, summarization).
* [workers/](workers/) — **Cloudflare Workers**: GitHub OAuth, App installation, D1-backed conversations, change sets, draft PR creation, webhook sync.
* [npm/](npm/) — `cerberus-agent` npm package — Node.js launcher that bootstraps the Python CLI.
* [checks.json](checks.json) — Native check catalog and scoring source of truth (59 checks across 9 agents).
* [pyproject.toml](pyproject.toml) — Python packaging with `cerberus` console entry point and `agent` extra.
* [logo.png](logo.png) — The official Cerberus Labs logo.
* [assets/](assets/) — Scanner scripts (`scanner.js`, `checks.js`), agent UI (`agent.js`, `agent.css`), the original engraving, social preview, shared `site.css`, concept art, and legacy-route forwarding (`home.js`).
* [documentation/](documentation/) — Static documentation site.
* [docs/](docs/) — Scanner catalog, examination specification, agent architecture, GitHub Actions guide, product documentation, roadmap, and compliance material.
* [scripts/](scripts/) — Check asset builders, documentation generation, and browser scanner integration harness.
* [tests/](tests/) — Native engine, feeder, ALIGNMENT, CLI mode, orchestration, agent loop, swarm, TUI, console, commands, approvals, LSP/MCP, SARIF, HTML, and safety tests.
* [.github/workflow-templates/cerberus-security-review.yml](.github/workflow-templates/cerberus-security-review.yml) — Pinned native-first CI review template with optional feeders.
* [HERMES_INTERFACE_SETUP_PROMPT.md](HERMES_INTERFACE_SETUP_PROMPT.md) — Setup instructions for the Hermes voice-interface HTTP bridge.
* [team.md](team.md) — Founding team roles, equity structure, and governance.

---

## Active Roles

- **Joshua Johnson** — CEO / CFO
- **Caleb Johnson** — COO
- **Elijah Johnson** — CTO
