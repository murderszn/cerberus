# Cerberus × Nectar Cannibalization Plan

> Goal: turn Cerberus from a deterministic scanner CLI (`examine.py`) into a
> full-service Pollinations agent CLI like Nectar (`honey`), where the nine
> Cerberus check-agents (Sentinel, Gatekeeper, Vault, …) run independently
> by name — Grokbot-style — and can do local code updates or GitHub PRs.
>
> Status: **PLAN ONLY — no code has been moved yet.** This doc is the build
> order for when you say go. Proposed home for the runtime is a new
> `servers/` (or `agent/`) subtree inside this repo; see §5.

## 1. What exists today

### 1.1 Cerberus (this repo, `/Users/jahflyx/cerberus`)

- `examine.py` — stdlib-only deterministic scanner. Loads `checks.json`,
  evaluates a local dir or GitHub URL, emits `cerberus.report/2`. No LLM,
  no mutations, no server. This must keep working offline.
- `checks.json` — single source of truth. 59 checks grouped by 9 agents:
  `architect, auditor, conduit, gatekeeper, librarian, sentinel, shield,
  vault, watchtower`. Each check has an `agent` field + weight.
- `feeders/` — optional Phase-1 adapters (`gitleaks, osv-scanner, zizmor,
  scorecard, actionlint`) with `runner.py`, `normalize.py`, `registry.py`.
  Argv-only subprocesses, timeouts, allowlists, `.cerberusignore`.
- `alignment.py` — native ALIGNMENT review (agent-guidance / workflow policy).
- `agent.html` / `index.html` — browser scanner over GitHub API (public repos).
- `docs/agent-architecture.md` — explicitly marks WASM enclaves / per-agent
  runtimes as **roadmap, not shipped**. Real grouping = check catalog only.
- `tests/`, `scripts/build-checks.py`, `.github/workflows/` — CI + report gates.

### 1.2 Nectar (`/Users/jahflyx/nectar`, package `opencode_harness`)

Full LLM agent loop Nectar runs as `honey`:

- `opencode_harness/cli.py` — argparse CLI: interactive scrollback session
  (default), `honey "goal…"`, `login/logout/status`, `--tui`, provider flags
  (`--base-url`, `--model`, `--api-key`). Brand resolves from `argv[0]`.
- `opencode_harness/agent/loop.py` — multi-turn tool-evaluation loop, tool
  budget (`max_tool_rounds`, default 48), parallel-batch + tool-free wrap-up.
- `opencode_harness/agent/swarm.py` — subagent delegation: `coder,
  architect, auditor, pc_agent, researcher` with role-tailored prompts,
  restricted tool registries, concurrent map-reduce in isolated threads.
- `opencode_harness/agent/prompts.py`, `threads.py` — system prompts,
  branching / checkpoints.
- `opencode_harness/tools/` — `registry.py` + `files, edit, multiedit,
  search, symbols, bash, git (status/diff/log/branch), inspect, web,
  pathutil, safety, pc`. `build` vs `plan` (read-only) modes.
- `opencode_harness/provider/client.py` — OpenAI-compatible client. Default
  `https://gen.pollinations.ai/v1` (`kimi`, `deepseek`); also Ollama, LM
  Studio, vLLM/LiteLLM.
- `opencode_harness/auth/` — Pollinations Pollen BYOP device flow
  (`byop.py`, `login.py`, `store.py` → `credentials.json`).
- `config.py`, `session_store.py`, `logging_setup.py`, `mcp/manager.py`,
  `ui/` (Rich scrollback + Textual option), `models.py`,
  `models_catalog.py`.
- `pyproject.toml` — deps: `httpx, rich, prompt_toolkit, pyyaml,
  beautifulsoup4, textual, mcp`; entry points `honey, opencode-harness, ch`.

### 1.3 Reference: Grokbot (`~/.grokbot`, `~/.grok`)

Named-agent pattern to copy: invocable personas, per-session state, background
logging. Cerberus equivalent = `cerberus sentinel "…"` dispatches only that
persona with its tools + prompt.

## 2. Target vision

```
# scan stays deterministic (unchanged)
python3 examine.py <dir|github-url> --json out.json

# new: full agent (Nectar loop vendored in)
cerberus agent "harden auth in ./api"
cerberus sentinel "fix injection in server/auth.py"
cerberus vault "rotate exposed secret, open PR"
cerberus agent --plan "audit this repo"     # read-only
cerberus agent --pr --base main --title "…" "fix …"
```

- `cerberus scan` = today's `examine.py` path (stdlib-only, offline-capable).
- `cerberus <agent-name>` = that check-agent as an LLM persona, Grokbot-style,
  with a restricted toolbelt + its `checks.json` rules injected as policy.
- `cerberus agent` = orchestrator: fans out to named agents (Nectar `swarm.py`
  pattern), merges results, then either edits locally or opens a GitHub PR.

## 3. Cannibalization map (Nectar → Cerberus)

| Nectar module | Cerberus destination (proposed) | Action |
|---|---|---|
| `agent/loop.py` | `servers/agent/loop.py` | Lift nearly verbatim; keep budget + wrap-up; add Cerberus `OnStatus` for scan progress |
| `cli.py` | `servers/cli.py` (`cerberus` entry) | Lift parser structure; keep `scan` as legacy `examine.py` wrapper; add `<agent>` subcommands |
| `agent/swarm.py` | `servers/agent/cerberus_swarm.py` | Adapt: replace `coder/architect/auditor/pc_agent/researcher` roles with 9 Cerberus personas seeded from `checks.json` |
| `agent/prompts.py` | `servers/agent/personas/*.md` + builder | Keep builder; generate one system prompt per Cerberus agent from its checks (domain, responsibility, failure conditions) |
| `tools/registry.py`, `files/edit/multiedit/search/symbols/bash` | `servers/tools/` | Lift; keep `build`/`plan` modes; enforce workspace boundary by default |
| `tools/git.py` + `gh` PR helper (new) | `servers/tools/git.py`, `servers/tools/pr.py` | Lift git tools; add branch/commit/push + `gh pr create` wrapper (new, thin) |
| `tools/safety.py`, `pathutil.py` | `servers/tools/` | Lift; extend with `.cerberusignore` + secret-redaction from `feeders/normalize.py` |
| `provider/client.py`, `models*.py` | `servers/provider/` | Lift; default stays Pollinations; keep Ollama/LM Studio overrides |
| `auth/byop.py, login.py, store.py` | `servers/auth/` | Lift; rename config dir to `~/.cerberus/`; keep `login/logout/status` |
| `config.py`, `session_store.py`, `logging_setup.py` | `servers/` | Lift; add `agents:` + `policy:` sections (budgets, allowed tools per agent, PR defaults) |
| `mcp/manager.py` | `servers/mcp/` (optional, phase 4+) | Lift only if MCP servers needed; default off |
| `ui/` (Rich/Textual) | `servers/ui/` | Lift scrollback UI; reuse for `cerberus agent` interactive mode |
| `tools/pc.py`, `inspect.py` (pc automation) | Drop or gate | Exclude from default agent toolbelt; opt-in flag only (least need, most risk) |
| `tools/web.py` | Gate | Keep for `researcher/librarian` only, not default code-fix agents |

Do **not** move: `examine.py` core, `checks.json` schema, `feeders/` runners,
`cerberus.report/2` scoring. Those stay authoritative; the agent only reads
them and never deducts native points from LLM findings (same rule as feeders).

## 4. Named agents (Sentinel et al. as runnable personas)

- Source each persona from `checks.json`: all checks where `agent == X`
  become that persona's policy block (IDs, severities, failure conditions).
- Role → toolbelt sketch:
  - `sentinel` (backend/injection): read/edit/search/symbols/bash(pytest),
    git read-only by default.
  - `gatekeeper` (auth): same as sentinel + no secret exfiltration (safety deny).
  - `vault` (secrets): read/search/git + PR helper; never prints raw secrets
    (reuse feeder redaction).
  - `librarian` (deps): read + web (OSV lookup notes) + `osv-scanner` feeder passthrough.
  - `auditor/conduit/shield/watchtower/architect` — same pattern, one file per
    persona under `servers/agent/personas/`.
- Orchestrator (`cerberus agent`): classify goal → spawn 1–N personas via
  swarm map-reduce → dedup findings (reuse `feeders/normalize.py` fingerprint
  idea) → single patch set → verify (`examine.py --only …` + pytest) → PR.

## 5. Where it lives ("servers project folder")

There is **no `servers/` dir in Cerberus today** — so this plan proposes one
and nothing has been created yet:

```
cerberus/
  examine.py            # untouched deterministic engine
  checks.json           # untouched catalog
  feeders/              # untouched
  servers/              # NEW — all cannibalized Nectar runtime
    cli.py              # cerberus entry (scan | agent | <name>)
    agent/loop.py, cerberus_swarm.py, personas/
    tools/              # registry + files/edit/search/bash/git/pr/safety
    provider/ auth/     # Pollinations BYOP
    config.py, session_store.py
    ui/
  docs/nectar-cannibalization-plan.md  # this file
```

Alternative if you prefer flatter: `cerberus/agent/` instead of
`cerberus/servers/`. Decide at build start; the map in §3 is identical either
way. Keep `examine.py` importable stdlib-only — `servers/` deps (`httpx`,
`rich`, `prompt_toolkit`, …) must be optional so `--native-only` scans never
require them.

## 6. Phased build (with exit criteria)

- **Phase 0 — spike (½ day, no moves).** Run `honey` against a Cerberus clone;
  confirm Pollinations auth + loop + git tools work from inside this repo.
  Exit: notes on model choice + budget behavior.
- **Phase 1 — vendor (1 day).** Copy `opencode_harness/` → `servers/vendor/`
  (or `git subtree` / pip dep). Add `servers/cli.py` shim: `scan` delegates to
  `examine.py`; `agent` delegates to vendored loop. Exit: both subcommands run.
- **Phase 2 — core agent (2–3 days).** Wire config (`~/.cerberus/`),
  session store, provider, tool registry with workspace boundary + plan mode.
  Exit: `cerberus agent "list TODOs"` edits nothing, streams tool calls.
- **Phase 3 — named agents (2–3 days).** Build `cerberus_swarm.py` + 9 persona
  prompts from `checks.json`; `cerberus sentinel|vault|…` dispatch. Exit: each
  name runs with its restricted toolbelt; `--only` parity check vs scanner.
- **Phase 4 — local code tasks (2 days).** Enable edit/multiedit/bash + verify
  loop (`examine.py --only <agent>` + relevant pytest) + destructive-confirm.
  Exit: end-to-end local fix with tests green, no `servers/` dep needed for scan.
- **Phase 5 — GitHub PR tasks (2 days).** Branch-per-task, commit, push,
  `gh pr create` with scan report attached; reuse
  `docs/cerberus-github-action-template.md` CI. Exit: `cerberus vault --pr …`
  opens a real PR with `cerberus.report/2` JSON linked.
- **Phase 6 — hardening (ongoing).** Secret redaction, `.cerberusignore`
  enforcement in agent tools, per-agent budgets, audit log (Nectar session
  tail), `plan` default for Vault/Gatekeeper, MCP opt-in.

## 7. CLI sketch (to implement, not yet built)

```bash
cerberus scan ./api --json out.json --fail-under 80   # = examine.py today
cerberus agent "fix all high findings in ./api"
cerberus agent --plan "propose auth hardening"        # read-only
cerberus sentinel "fix SQLi in server/db.py" --pr --base main
cerberus vault --pr "remove hardcoded key, use env"
cerberus login | logout | status                      # Pollinations BYOP
```

## 8. Safety / non-goals for the merge

- `examine.py --native-only` must stay dependency-free and behavior-identical.
- Agent findings never mutate the native score (feeder rule applies to LLM too).
- Workspace boundary ON by default; `plan` mode for secrets/auth agents.
- Destructive bash + push/PR require explicit flags; every run logs tools +
  tokens (Nectar `logging_setup` + session tail).
- No WASM / sandbox rebuild — `agent-architecture.md` roadmap stays roadmap.

## 9. Verification

- Nectar suite: `pytest -q` inside vendored copy (must stay green).
- Cerberus suite: existing `tests/` + `scripts/test-scanner.mjs` (must stay green).
- New tests: persona-prompt generation from `checks.json`; swarm fan-out with
  stubbed provider; `plan`-mode mutation denial; PR-helper dry-run.
- Manual: `cerberus scan`, `cerberus agent --plan`, one named-agent local fix,
  one `--pr` dry-run before any real PR.

## 10. Build status (2026-09-06)

Phases 0–2 are implemented in the working tree (uncommitted):

- `servers/cli.py` — `cerberus` entry: `scan` (verbatim `examine.py`
  passthrough), `agent`/`orchestrator`, 9 named personas, bare one-shot,
  `login/logout/status/logs`, `--init`, `--plan`, `--swarm`, `--pr/--base/
  --title/--dry-run`, `-y`, `--max-rounds`. Flags work before or after the
  command; `scan` args are never rewritten.
- `servers/tools/inspect.py` + registry entries 16–18 (`file_tree`,
  `http_request`, `python_eval`); first two are PLAN-mode safe.
- `servers/ui/console.py` — minimal Rich scrollback UI; `cli.py` falls back
  to stdlib prints when rich is absent, and lazy-loads httpx/rich modules
  so `scan`/`status`/`--help` run dependency-free.
- `servers/requirements-agent.txt` — agent-only deps.
- `tests/test_servers_agent.py` — 13 unittest tests, stdlib-only for CI.
  Full suite: 80/80 green; `examine.py` + `checks.json` untouched.

Still open at that point: live model run (needs `cerberus login`),
MCP opt-in, commit + PR. (TUI landed same day — see §12.)

## 12. Ink TUI update (2026-09-06, same day)

- `servers/ui/tui.py` — full-screen Textual workbench (paper/ink theme):
  header / sidebar (task·files·changes·history) / workspace / `❯`
  composer (Enter submits, Shift+Enter newline) / dark footer. `cerberus`
  launches it by default on a TTY; `cerberus tui` forces it, `--classic`
  keeps the scrollback REPL. Ctrl+K palette, Shift+Tab mode toggle,
  Esc stop (cooperative `AgentLoop.request_cancel()`), `/scan` runs the
  real deterministic engine, `/save|/load` reuse the session store.
- `textual>=0.80` added to `servers/requirements-agent.txt`.
- `tests/test_servers_tui.py` — 8 headless pilot tests (skipped without
  textual). Verified: 8/8 ×3 runs, stdlib suite 108/108.
- Ink follow-ups: responsive narrow mode (<96 cols hides the sidebar for a
  top strip + compact composer/footer), dark theme via Ctrl+T (mostly
  black, in-memory toggle). 11/11 pilot ×3 runs, stdlib 111/111.

## 11. When you say go — first 5 commands

1. Decide `servers/` vs `agent/` dirname (§5).
2. Vendor Nectar (`cp -r ../nectar/opencode_harness servers/vendor` or subtree).
3. Add `servers/cli.py` + `cerberus` entry point; keep `examine.py` untouched.
4. Generate `servers/agent/personas/*.md` from `checks.json`.
5. Wire `login/status` + `agent --plan` end-to-end, then iterate phases §6.
