# TUI Overhaul Status

Updated: 2026-09-07

This document records the implementation state of the TUI overhaul work from
`tui-overhaul-steps.md`. The changes live in the parent Cerberus repository, not
only in the nested npm package.

## Current state

The scrollback REPL is now the default terminal experience. The full-screen
Textual workbench remains available with `--workbench` (and the explicit `tui`
command). The implementation has completed the planned interaction, output,
behavior, and permission changes at code level.

The browser analyst now uses Pollinations authentication. The site selector and
CLI catalog include current Pollinations IDs for OpenAI GPT-6 Astra/GPT-5.6,
Anthropic Opus/Sonnet/Haiku, Gemini 3.7/3.8 Flash, Kimi K3, and Qwen 3.8. The
live registry did not expose a Kimi K7 ID, so it is not advertised until an
exact Pollinations model ID is available.

## Completed checklist

- [x] Default entry path uses the scrollback REPL; `--workbench` opts into the full-screen UI.
- [x] Prompt Toolkit history persists at `~/.cerberus/history`.
- [x] Escape toggles single-line/multiline input and the prompt glyph changes accordingly.
- [x] Slash-command completion remains available; `@file` workspace completion was added.
- [x] Startup chrome is a compact three-line banner; operational details remain in `/status`.
- [x] A thinking spinner starts immediately after submission and stops on real activity.
- [x] Streamed assistant output renders through Rich Markdown and finishes in a Markdown panel.
- [x] Tool output is compact by default; `-v/--verbose` restores detailed tool arguments.
- [x] `write_file` and `edit_file` return unified diffs, rendered with Rich diff syntax.
- [x] Turn usage shows tokens, tool rounds, completion state, and known-model cost estimates.
- [x] Agent history auto-compacts at 80% of the configured `context_window` (128,000 default).
- [x] `@file`, `!command`, and normal composer routing are active in the REPL.
- [x] Permission prompts use the compact two-line format while preserving `y/a/N` behavior.
- [x] Provider retries cover rate limits, server failures, timeouts, and streaming failures with status messages.
- [x] Session exit prints token and tool-round totals.
- [x] Console colors use semantic Rich styles with Cerberus amber as the brand accent.
- [x] Permission tiers persist to the active global or project configuration; shell execution has an explicit tier.
- [x] Project permission loading recognizes `.cerberus/config.yaml` as well as the legacy project filename.

## Verification completed

The full unittest suite passed:

```text
Ran 255 tests
OK
```

The new regression coverage includes banner size, compact tool output, `@file`
completion, inline diffs, context-window loading, auto-compaction, model cost
lookups, and retry status behavior.

## Follow-up checklist

These are the remaining release-readiness checks rather than known blockers:

- [ ] Run a real interactive TTY smoke test for default REPL startup, Escape
      multiline mode, history recall, slash completion, and Ctrl+C summary.
- [ ] Run `cerberus --workbench "hello"` and confirm the workbench opens with
      the initial goal preloaded and submitted.
- [ ] Exercise a real streamed provider response containing Markdown and a code
      block; confirm the transient live view does not duplicate the final panel.
- [ ] Exercise an actual edit and write through the agent, including a large
      diff and a newly created file.
- [ ] Verify `/approvals execute_bash_command allow` and project-scoped changes
      survive a process restart.
- [ ] Validate retry behavior against a provider that returns 429 and a 5xx,
      including `Retry-After` handling and streaming retries.
- [ ] Reconfirm the model pricing table against current provider documentation
      before displaying dollar estimates in a release build.
- [ ] Review the complete worktree diff, separating these TUI changes from
      unrelated existing changes in the release pages, README, and changelog.
- [ ] Decide whether the untracked `cerberus.egg-info/` directory should be
      ignored or removed before commit.
- [ ] Update the user-facing CLI documentation with the new default and
      `--workbench` flag, then add a release note once the manual checks pass.
- [ ] Commit the implementation and this status document as a focused change.

## Main implementation files

- `servers/cli.py` — entry gating, REPL input, completion, spinners, summaries.
- `servers/ui/console.py` — banner, Markdown streaming, tool/diff rendering,
  usage, and permission prompt presentation.
- `servers/agent/loop.py` — streaming callback behavior, compaction, usage rounds.
- `servers/config.py` — context window and persistent permission configuration.
- `servers/provider/client.py` — retry and retry-status handling.
- `servers/tools/edit.py`, `servers/tools/files.py` — unified diff production.
- `servers/tools/registry.py` — shell permission gate.
- `servers/models_catalog.py` — optional cost estimation.
- `servers/ui/narrate.py` — compact tool verbs.
- `tests/test_tui_overhaul.py` — focused regression coverage.
