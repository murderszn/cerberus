# Changelog

All notable changes to Cerberus are recorded here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning is
`major.minor.patch` with a `-beta` suffix while the agent CLI stabilises.

## [Unreleased]

### Fixed
- Engine: `path_forbidden` checks and `applies_if` preconditions now run on
  the non-excluded tree, so `global_exclude` and `.cerberusignore` actually
  suppress (vendored `.venv` content no longer fails the scanned repo, and a
  nested `package.json` inside `.venv` no longer triggers lockfile checks).
  Mirrored in the browser scanner (`assets/scanner.js`).
- CLI: removed `shell=True` from the Windows report-opener
  (`cmd /c start` via argv instead).
- Web: `agent.html` ships a hardened content-security policy — no
  `unsafe-inline`, no CDN script origin, loopback-only AI endpoints — with the
  page's script and styles extracted to `assets/agent.js` / `assets/agent.css`.
- Shop: checkout replaced with an honest pre-order reservation (email only,
  $0 due today, stored in-browser); removed the orders-paused dead end.
- Renamed `ceberus-classic.html` to `cerberus-classic.html`; removed the
  orphaned `terminal.html` web workbench.
- CI self-scan gate is now `--fail-under 95 --fail-on high` (was
  `--fail-under 80`, which passed with critical findings present).

### Changed
- Releases: redesigned `releases.html` from a single free-form article into a
  compact, stackable release list. Each `<article class="release">` now has an
  eyebrow + date row, inline title/version/status badge, 1–2 line summary,
  collapsible `<details>` for install & requirements, and a single row of
  links (npm / GitHub / Changelog / Docs). Cards stack with 2 px `--ink` top
  borders and numbered `note-index` (01, 02, …). Badge variants: filled
  (Beta), outline (Stable), muted (Superseded). Install block keeps the
  `5.5px 5.5px 0 var(--ink)` shadow. 680 px breakpoint collapses cleanly.
  Adding a new release = copy one `<article>` block.

### Added
- `examine.py --fail-on critical|high|medium|low`: exit non-zero on
  failed-check severity even at a passing score.
- Packaging: `pyproject.toml` with a `cerberus` console entry point and an
  `agent` extra (`pipx install "cerberus[agent] @ git+https://github.com/murderszn/cerberus.git"`).

## [1.0.0-beta] — 2026-09-05

First public beta of the agent CLI, layered on the unchanged deterministic
scanner (`examine.py`, stdlib-only).

### Added
- `cerberus scan` passthrough to the deterministic engine (no auth, no deps).
- `cerberus agent` orchestrator plus nine named specialist personas with
  team fan-out (`/team`), all running the same tool loop.
- Ink full-screen workbench (Textual) and classic REPL (`--classic`).
- Plan mode by default with ask-first approvals; Shift-Tab toggles
  accept-edits live.
- Layered config (`global < project < CERBERUS.md < env < CLI flags`),
  per-provider models (`model use`, latency check), token usage, saved
  sessions, `/review` hunk review and `/undo`.
- Headless `run --format json`, shell completions, opencode-style help.
- Permission tiers (`allow|ask|deny`) with global/project/session scopes.
- Read-only LSP wrappers and an opt-in MCP stub.
- Nine catalog-driven native agents (59 checks), ALIGNMENT analyzer, five
  Phase 1 feeder adapters, JSON/HTML/SARIF reports, GitHub Actions template.
