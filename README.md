<h1 align="center">
  <img src="logo.png" alt="Cerberus Labs" width="200" /><br/>
  Cerberus
</h1>

<p align="center">
  <strong>HIGH-RIGOR REPO EXAMINATIONS &nbsp;|&nbsp; ZERO TRUST &nbsp;|&nbsp; AGENT ORCHESTRATED</strong>
</p>

<p align="center">
  <em>Rigorous, real-time security certification for vibe-coded and rapid-deployment applications.</em>
</p>

<p align="center">
  <a href="https://github.com/murderszn/cerberus/actions/workflows/ci.yml"><img src="https://github.com/murderszn/cerberus/actions/workflows/ci.yml/badge.svg" alt="CI Status"></a>
  <a href="https://github.com/murderszn/cerberus/stargazers"><img src="https://img.shields.io/github/stars/murderszn/cerberus" alt="GitHub Stars"></a>
  <a href="https://github.com/murderszn/cerberus/network"><img src="https://img.shields.io/github/forks/murderszn/cerberus" alt="GitHub Forks"></a>
  <a href="https://github.com/murderszn/cerberus/issues"><img src="https://img.shields.io/github/issues/murderszn/cerberus" alt="GitHub Issues"></a>
  <a href="https://github.com/murderszn/cerberus/blob/main/LICENSE"><img src="https://img.shields.io/github/license/murderszn/cerberus" alt="License"></a>
  <a href="https://pypi.org/project/cerberus/"><img src="https://img.shields.io/pypi/v/cerberus" alt="PyPI"></a>
  <a href="https://www.npmjs.com/package/cerberus-agent"><img src="https://img.shields.io/npm/v/cerberus-agent" alt="npm"></a>
</p>

---

## 🔍 What Is Cerberus?

**Cerberus** is an automated, zero-configuration security scanner and agent workbench built for modern engineering teams. As developers lean on AI assistants to ship features at speed, security reviews often fall behind. Cerberus replaces slow, costly human audits with a high-rigor **AI agent swarm** that validates code, infrastructure, and configuration against a comprehensive checks catalog — and helps you fix what's broken.

The project spans three product surfaces:

| Surface | Description |
|---------|-------------|
| **Deterministic Scanner** | Catalog-driven, zero-dependency engine that runs identically in the browser and CLI. No server, no build step, no signup. |
| **Agent CLI Workbench** | Interactive terminal (REPL or full-screen Ink TUI) deploying 9 security-specialist personas with tool use, plan/accept-edits modes, session persistence, and swarm fan-out. |
| **GitHub App & Cloud Agent** | Cloudflare Workers deployment with GitHub OAuth, scan-grounded conversations, AI-generated change sets with inline diffs, and one-click draft PRs. |

---

## 👥 Target Audience

| Persona | Need |
|---------|------|
| 🚀 **Vibe-Coding Founder** | Push-button, zero-setup audit to secure your platform and build user trust. |
| 📋 **Compliance Lead** | Structured, scored reports for **SOC 2, HIPAA, GDPR** audits. |
| 🔍 **VC Tech Partner** | Rapid technical due diligence on portfolio companies without configuring dev environments. |

---

## ✨ Key Features

- **Deterministic Security Scan** — Nine catalog-driven agents score your repo from `0` to `100`. Every finding maps to a concrete, verifiable condition.
- **Unified Engine** — Browser and CLI share the same rules from [`checks.json`](checks.json), producing identical `cerberus.report/2` reports.
- **Agent CLI Workbench** — Chat with an orchestrator or individual specialist personas that can read files, edit code, run commands, browse the web, and create PRs.
- **GitHub App Cloud Agent** — Sign in with GitHub, install the app, and let the agent propose file-level changes with reviewable diffs and draft PRs.
- **Orchestration & External Feeders** — Native ALIGNMENT review plus normalized findings from Gitleaks, OSV-Scanner, Zizmor, OpenSSF Scorecard, and actionlint.
- **CI/CD Integration** — Drop-in GitHub Actions template for JSON, HTML, and SARIF reviews on PRs and main-branch pushes.

---

## 🏃 Getting Started

### 🌐 Browser (Public Repos)

Open [Cerberus Agent](agent.html) in any modern browser, or serve the repo locally:

```bash
python3 -m http.server 8000
```

Then visit `http://localhost:8000/agent.html` and paste a public GitHub URL.

> **Note:** Due to CORS, the web app only scans public repos. Use a GitHub PAT for private repos, or the CLI.

### 💻 CLI (Local, Private, CI)

```bash
# Full installation with agent runtime
pipx install "cerberus[agent] @ git+https://github.com/murderszn/cerberus.git"
cerberus scan .

# Scanner only (stdlib, no dependencies)
pipx install git+https://github.com/murderszn/cerberus.git
cerberus scan . --native-only

# Or run directly from checkout
python3 examine.py .
```

### 📦 npm Launcher

```bash
npx cerberus-agent scan .
npx cerberus-agent agent "audit this repository"
```

---

## 📡 CLI Reference

| Command | Description |
| :--- | :--- |
| `cerberus scan <args>` | Run the deterministic security scan. |
| `cerberus agent [GOAL…]` | Orchestrator session with all 9 personas. |
| `cerberus <persona>` | Chat with a named specialist (e.g. `cerberus sentinel "fix the login bug"`). |
| `cerberus run "goal"` | Headless one-shot execution. |
| `cerberus model [name]` | List or switch the default model. |
| `cerberus init` | Scaffold config and project `CERBERUS.md`. |
| `cerberus sessions list\|resume\|fork\|delete` | Manage conversation transcripts. |
| `cerberus permissions allow\|ask\|deny` | Set tool permission tiers. |
| `cerberus login\|logout\|status` | Authenticate and check status. |

### Scanner Flags

| Flag | Description |
| :--- | :--- |
| `--json <path>` | Output raw JSON report. |
| `--html <path>` | Output standalone interactive HTML report. |
| `--sarif <path>` | Generate SARIF for GitHub Code Scanning. |
| `--fail-under <score>` | Exit non-zero if score is below threshold. |
| `--fail-on <level>` | Fail on severity level (`critical`, `high`, `medium`, `low`). |
| `--only <agents>` | Restrict evaluation to specific agents (e.g. `sentinel,vault`). |
| `--feeders auto` | Run all applicable external feeders. |
| `--native-only` | Offline scan with native checks only. |
| `--quiet` | Print only the final score and grade. |
| `--no-color` | Disable ANSI color output. |

---

## 🐝 The 10-Agent Swarm

Nine deterministic security specialists plus a non-scoring **CURATOR** that synthesizes their findings:

| Agent | Domain | Weight | Checks |
| :--- | :--- | :---: | :---: |
| 🛡️ **SENTINEL** | Code Analysis | **14** | 11 |
| 🔑 **VAULT** | Data Security | **13** | 8 |
| 🚪 **GATEKEEPER** | Access Control | **12** | 6 |
| 📦 **LIBRARIAN** | Dependencies | **12** | 6 |
| 📡 **CONDUIT** | Network & API | **11** | 5 |
| 🔭 **WATCHTOWER** | Application Config | **11** | 8 |
| 🖥️ **SHIELD** | Client Security | **11** | 6 |
| 📝 **AUDITOR** | Logging & Monitoring | **8** | 4 |
| 🏗️ **ARCHITECT** | Infrastructure | **8** | 5 |
| 🧠 **CURATOR** | AI Evidence Synthesis | *Non-scoring* | — |
| **Total** | | **100** | **59** |

**ALIGNMENT** is an additional agent that examines repository instructions and coding-agent operational surfaces (policy conflicts, destructive commands, prompt-injection risks, etc.). It has its own score and is not part of the native 100 points.

### 📦 External Feeders

| Feeder | Evidence | License |
| :--- | :--- | :--- |
| Gitleaks | Secrets in repository files | MIT |
| OSV-Scanner | Known vulnerabilities in deps | Apache-2.0 |
| Zizmor | GitHub Actions weaknesses | MIT |
| OpenSSF Scorecard | Supply-chain posture | Apache-2.0 |
| actionlint | GitHub Actions syntax errors | MIT |

### 📊 Grading

| Grade | Score |
| :--- | :--- |
| **A** | ≥ 90 |
| **B** | ≥ 80 |
| **C** | ≥ 70 |
| **D** | ≥ 60 |
| **F** | < 60 |

---

## 🏗️ Architecture

```
                  checks.json               checks.json
               (source of truth)            (source of truth)
                     /          \                /          \
                    v            v              v            v
             Browser scanner    CLI native scan
                                         |
               +-------------------------+-------------------------+
               |                                                   |
               v                                                   v
         ALIGNMENT analyzer                              Phase 1 Feeder Registry
                                         /    |    |    |    \
                               Gitleaks   OSV   Zizmor   Scorecard   actionlint
               |                                                   |
               +-------------------------+-------------------------+
                                         v
                               normalization + deduplication
                                         |
                                         v
                    cerberus.report/2 + HTML + SARIF + Feeder JSON
                    native score | alignment | feeders | policy

            ┌─────────────────────────────────────────┐
            │         Agent CLI Workbench              │
            │   REPL / Ink TUI / Headless Run          │
            │   9 Personas · Swarm Fan-out · 20+ Tools │
            └─────────────────────────────────────────┘

            ┌─────────────────────────────────────────┐
            │       Cloudflare Workers (GitHub App)    │
            │   OAuth · D1 · Conversations · PRs      │
            └─────────────────────────────────────────┘
```

---

## 📂 Repository Structure

```
cerberus/
├── examine.py                          # Python CLI, report builder, orchestration
├── alignment.py                        # Coding-agent alignment analyzer
├── checks.json                         # Native check catalog (59 checks)
├── pyproject.toml                      # Python packaging & dependencies
├── README.md                           # This file
├── SECURITY.md                         # Security policy
├── team.md                             # Founding team & governance
│
├── assets/                             # Web assets (scanner.js, agent.js, CSS)
├── documentation/                      # Static documentation site
├── docs/                               # Scanner catalog, specs, guides, roadmap
├── feeders/                            # External feeder adapters & registry
├── npm/                                # cerberus-agent npm launcher
├── scripts/                            # Build & documentation generators
├── servers/                            # Agent CLI runtime (CLI, agents, tools, TUI)
│   ├── cli.py                          # Entry point
│   ├── commands.py                     # Slash commands
│   ├── config.py                       # Layered configuration
│   ├── session_store.py                # Conversation persistence
│   ├── tools/                          # 20+ tool implementations
│   ├── ui/                             # Rich console & Textual TUI
│   └── provider/                       # LLM provider clients
├── tests/                              # Test suite (engine, feeders, agent, TUI, etc.)
├── workers/                            # Cloudflare Workers
│   └── github-auth/                    # GitHub OAuth & App backend
│
├── .github/workflow-templates/         # CI/CD template
├── .cerberusignore                     # Path exclusions
└── logo.png                            # Cerberus Labs logo
```

---

## 🛠️ Developer Guide

### Rebuilding Assets

```bash
# Compile checks.json → assets/checks.js for the browser
python3 scripts/build-checks.py

# Regenerate documentation
python3 scripts/generate-checks-docs.py
```

### Verification

```bash
python3 -m py_compile examine.py alignment.py feeders/*.py
python3 -m unittest discover -s tests -v
python3 scripts/build-checks.py
python3 scripts/generate-checks-docs.py
python3 examine.py . --native-only --json /tmp/report.json --no-color
git diff --check
```

### Adding a Feeder

1. Implement the adapter in `feeders/`
2. Declare executable name and argv builder
3. Add applicability detection
4. Normalize output (never retaining credentials)
5. Register in `feeders/registry.py`
6. Add fixtures and tests

Adapters must never invoke a shell, download binaries, or execute repository-provided commands.

---

## 🔒 Security Policy

Report security vulnerabilities **privately** rather than publicly:

- **[Private Security Advisory](https://github.com/murderszn/cerberus/security/advisories/new)**
- Email with `SECURITY` in the subject line

We aim to acknowledge within **2 business days** and ship a fix or mitigation plan within **30 days**.

See [SECURITY.md](SECURITY.md) for full details.

---

## 👥 The Team — Cerberus Labs

| Name | Role | Focus |
| :--- | :--- | :--- |
| **Joshua Johnson** | CEO / CFO | Strategy, capital, operations, financial governance |
| **Caleb Johnson** | COO | Swarm engineering, product delivery, orchestration |
| **Elijah Johnson** | CTO | Zero-trust runtimes, security protocols, core engine |

---

## 📜 License

[MIT](LICENSE) © Cerberus Labs

---

## 🤝 Contributing

1. Fork it
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 Acknowledgments

- [Gitleaks](https://github.com/gitleaks/gitleaks) — Secrets detection
- [OSV-Scanner](https://github.com/google/osv-scanner) — Vulnerability scanning
- [Zizmor](https://github.com/woodruffw/zizmor) — GitHub Actions auditing
- [OpenSSF Scorecard](https://github.com/ossf/scorecard) — Supply-chain security
- [actionlint](https://github.com/rhysd/actionlint) — Actions syntax checking
- [Pollinations](https://pollinations.ai) — LLM provider powering the agent runtime
- [Textual](https://textual.textualize.io) — TUI framework
- [Cloudflare Workers](https://workers.cloudflare.com) — Cloud backend

---

<p align="center">
  <em>Cerberus — Because your code should be <strong>trusted</strong>, not just <strong>trusted</strong>.</em>
</p>
