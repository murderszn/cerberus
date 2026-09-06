"""
Shared slash-command helpers for the classic REPL and the Ink workbench.

Kept stdlib-only (plus servers.models) so both UIs share one implementation
and unit tests never need Textual, rich, or network access.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from servers.models import Message

MAX_ADD_FILES = 5
MAX_ADD_BYTES = 32 * 1024
COMPACT_KEEP_TAIL = 10


def pick_model(config: Any, arg: str) -> tuple[str | None, str]:
    """Resolve a /model argument against the catalog.

    Returns (picked_model_or_None, human_message). None means "no change"
    (empty arg shows the active model, bad index warns).
    """
    from servers.models_catalog import build_catalog, find_by_index, find_by_name

    catalog = build_catalog(
        current=config.provider.model, configured=config.provider.models
    )
    if not arg.strip():
        return None, (
            f"Active model: {config.provider.model}  "
            "(/models to browse, /model <number|name> to switch)"
        )
    picked: str | None = None
    if arg.strip().isdigit():
        picked = find_by_index(catalog, int(arg.strip()))
        if picked is None:
            return None, f"No model #{arg.strip()}  (try /models)"
    if picked is None:
        picked = find_by_name(catalog, arg) or arg.strip()
    return picked, f"Switched model → {picked}"


def catalog_lines(config: Any) -> list[str]:
    """Numbered model rows for `cerberus model` with no argument."""
    from servers.models_catalog import build_catalog

    catalog = build_catalog(
        current=config.provider.model, configured=config.provider.models
    )
    lines = ["Models — `cerberus model <number|name>` to switch:"]
    for row in catalog:
        mark = "●" if row.is_current else " "
        lines.append(f"[{row.index}] {mark} {row.model}  ({row.section})")
    return lines


def compact_history(messages: list[Message], keep_tail: int = COMPACT_KEEP_TAIL) -> str:
    """Drop middle history, keeping a leading system prompt + recent tail."""
    if len(messages) <= keep_tail + 1:
        return f"History already compact ({len(messages)} messages, nothing dropped)."
    head: list[Message] = []
    rest = messages
    if messages and messages[0].role == "system":
        head = [messages[0]]
        rest = messages[1:]
    kept = rest[-keep_tail:]
    dropped = len(rest) - len(kept)
    messages[:] = [*head, *kept]
    return f"Compacted history: dropped {dropped} older messages, kept {len(messages)}."


def attach_files(messages: list[Message], workspace: Path, spec: str) -> str:
    """Read workspace files into the conversation (opencode-style /add)."""
    names = [p for p in spec.replace(",", " ").split() if p.strip()]
    if not names:
        return "Usage: /add <file…> — paths relative to the workspace."
    if len(names) > MAX_ADD_FILES:
        return f"Too many files (max {MAX_ADD_FILES}); attach fewer at once."
    ws = workspace.expanduser().resolve()
    chunks: list[str] = []
    skipped: list[str] = []
    for name in names:
        try:
            path = (ws / name).resolve()
        except OSError:
            skipped.append(f"{name} (unresolvable)")
            continue
        try:
            path.relative_to(ws)
        except ValueError:
            skipped.append(f"{name} (outside workspace)")
            continue
        if not path.is_file():
            skipped.append(f"{name} (not a file)")
            continue
        try:
            raw = path.read_bytes()[: MAX_ADD_BYTES + 1]
        except OSError as exc:
            skipped.append(f"{name} ({exc})")
            continue
        if b"\0" in raw[:8192]:
            skipped.append(f"{name} (binary, skipped)")
            continue
        body = raw[:MAX_ADD_BYTES].decode("utf-8", errors="replace")
        if len(raw) > MAX_ADD_BYTES:
            body += "\n…(truncated at 32 KiB)"
        try:
            rel = str(path.relative_to(ws))
        except ValueError:
            rel = str(path)
        chunks.append(f"### {rel}\n```\n{body}\n```")
    if not chunks:
        detail = "; ".join(skipped) if skipped else "no files given"
        return f"Nothing attached: {detail}."
    messages.append(
        Message(
            role="user",
            content=(
                "Context attached via /add — use it for the next request:\n\n"
                + "\n\n".join(chunks)
            ),
        )
    )
    note = f" ({'; '.join(skipped)})" if skipped else ""
    return f"Attached {len(chunks)} file(s) to the conversation.{note}"


def workspace_diff_summary(workspace: Path, max_lines: int = 80) -> str:
    """git status + diff for the workspace (opencode-style /diff)."""
    ws = workspace.expanduser().resolve()
    if not (ws / ".git").exists():
        return f"Not a git repo: {ws} — /diff needs versioned workspace."
    try:
        status = subprocess.run(
            ["git", "-C", str(ws), "status", "--short"],
            capture_output=True, text=True, timeout=15,
        )
        diff = subprocess.run(
            ["git", "-C", str(ws), "diff", "--", "."],
            capture_output=True, text=True, timeout=15,
        )
    except FileNotFoundError:
        return "git is not installed — /diff unavailable."
    except subprocess.TimeoutExpired:
        return "git timed out — /diff unavailable."
    if status.returncode != 0:
        return f"git status failed: {(status.stderr or status.stdout).strip()[:200]}"
    files = [ln for ln in status.stdout.splitlines() if ln.strip()]
    out: list[str] = []
    out.append("No uncommitted changes." if not files else f"{len(files)} changed file(s):")
    out.extend(f"  {ln}" for ln in files[:30])
    if len(files) > 30:
        out.append(f"  …and {len(files) - 30} more")
    body = diff.stdout.splitlines()
    if body:
        out.append("")
        out.extend(f"  {ln}" for ln in body[:max_lines])
        if len(body) > max_lines:
            out.append(f"  …({len(body) - max_lines} more diff lines)")
    return "\n".join(out)


def init_project_file(workspace: Path) -> str:
    """Scaffold CERBERUS.md project memory (opencode-style /init). Never overwrites."""
    ws = workspace.expanduser().resolve()
    target = ws / "CERBERUS.md"
    if target.exists():
        return f"Project memory already exists: {target} (not overwritten)."
    try:
        entries = sorted(p.name + ("/" if p.is_dir() else "") for p in ws.iterdir())
    except OSError as exc:
        return f"Cannot read workspace: {exc}"
    layout = "\n".join(f"- {e}" for e in entries[:40]) or "- (empty workspace)"
    if len(entries) > 40:
        layout += f"\n- …and {len(entries) - 40} more"
    target.write_text(
        f"""# CERBERUS.md — project memory for Cerberus agents

> Edit me: this file is attached as long-term context for agent runs in this workspace.

## Workspace

- root: `{ws}`

## Layout (top level)

{layout}

## Conventions

- Plan mode by default — the agent proposes before changing files.
- Verify with `cerberus scan .` before opening a PR.
- Keep secrets out of the repo; use `cerberus login` (Pollen BYOP) for auth.

## Notes

- …
""",
        encoding="utf-8",
    )
    return f"Wrote project memory → {target} (edit it, then /add it to attach)."


def parse_team_arg(arg: str, valid: list[str]) -> tuple[list[str], str, str]:
    """Split `/team name[,name…] task…` into (agents, task, error).

    Leading tokens that match known personas are consumed as the team;
    everything after is the task. Error is "" on success.
    """
    known = {str(v).lower() for v in valid}
    tokens = arg.split()
    names: list[str] = []
    i = 0
    while i < len(tokens):
        parts = [p.strip().lower() for p in tokens[i].split(",")]
        parts = [p for p in parts if p]
        if parts and all(p in known for p in parts):
            for p in parts:
                if p not in names:
                    names.append(p)
            i += 1
        else:
            break
    task = " ".join(tokens[i:]).strip()
    if not names:
        return [], "", "Usage: /team <agent[,agent…]> <task>  (see /personas)"
    if not task:
        return [], "", f"Give the team a task: /team {','.join(names)} <task>"
    return names, task, ""


def persona_lines(valid: list[str]) -> list[str]:
    """One-line roster for /personas (name + domain)."""
    try:
        from servers.agent.prompts import get_persona
    except Exception:
        get_persona = None  # type: ignore[assignment]
    lines = [
        "Specialists — /persona <name> to talk to one, "
        "/team <names> <task> for a crew:"
    ]
    for name in valid:
        domain = ""
        if get_persona is not None:
            try:
                found = get_persona(name)
                domain = found.domain if found else ""
            except Exception:
                domain = ""
        lines.append(f"  {name:12} {domain}")
    return lines
