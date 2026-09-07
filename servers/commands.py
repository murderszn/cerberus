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


#: Canonical slash-command registry: (command, usage, blurb).
#: Shared by TUI inline autocomplete, the classic REPL completer, and help.
SLASH_COMMANDS: tuple[tuple[str, str, str], ...] = (
    ("help", "", "list commands"),
    ("mode", " [plan|yolo]", "switch plan / accept-edits"),
    ("model", " [name]", "show or switch active model"),
    ("models", "", "list configured models"),
    ("persona", " [name]", "show or switch the agent you're talking to"),
    ("personas", "", "list specialist agents"),
    ("team", " a,b <task>", "fan a task out to a crew"),
    ("scan", " <target>", "run scanner, attach findings"),
    ("approvals", "", "ask-first policy for web + builds"),
    ("tools", "", "list registered tools"),
    ("usage", "", "token usage this session"),
    ("login", "", "sign in with Pollen"),
    ("logout", "", "sign out"),
    ("init", "", "scaffold CERBERUS.md"),
    ("add", " <files…>", "attach workspace files"),
    ("diff", "", "workspace changes"),
    ("review", " [--discard]", "hunk review: stage or drop changes"),
    ("undo", "", "restore tracked files to HEAD"),
    ("compact", "", "trim older history"),
    ("reset", "", "clear conversation history"),
    ("save", " [name]", "save conversation"),
    ("load", " <name>", "restore saved conversation"),
    ("sessions", "", "list saved sessions"),
    ("config", "", "show effective configuration"),
    ("workspace", " [path]", "show or change workspace"),
    ("clear", "", "clear the screen"),
    ("exit", "", "quit"),
)


def suggest_commands(fragment: str, limit: int = 7) -> list[tuple[str, str, str]]:
    """Fuzzy-filter SLASH_COMMANDS: prefix matches first, then substring."""
    frag = fragment.strip().lower().lstrip("/")
    if not frag:
        return list(SLASH_COMMANDS[:limit])
    starts = [c for c in SLASH_COMMANDS if c[0].startswith(frag)]
    subs = [c for c in SLASH_COMMANDS if frag in c[0] and c not in starts]
    return (starts + subs)[:limit]


def parse_composer_line(text: str) -> tuple[str, str, str]:
    """Classify composer input: (action, attach_spec, payload).

    - ("attach", "path …", "") — input is only @file mentions.
    - ("run", "path …", "task") — leading @files plus a task.
    - ("bash", "", "cmd") — single-line !command.
    - ("run", "", text) — anything else (plain task or multiline).
    """
    stripped = text.strip()
    if stripped.startswith("!") and "\n" not in stripped and len(stripped) > 1:
        return ("bash", "", stripped[1:].strip())
    if "@" not in stripped:
        return ("run", "", text)
    import shlex

    try:
        tokens = shlex.split(stripped, posix=True)
    except ValueError:
        tokens = stripped.split()
    attached: list[str] = []
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok.startswith("@") and len(tok) > 1:
            for part in tok[1:].split(","):
                part = part.strip()
                if part.startswith("@"):
                    part = part[1:]
                if part and part not in attached:
                    attached.append(part)
            i += 1
        else:
            break
    if not attached:
        return ("run", "", text)
    task = " ".join(tokens[i:]).strip()
    if not task:
        return ("attach", " ".join(attached), "")
    return ("run", " ".join(attached), task)


def git_working_tree(workspace: Path) -> tuple[list[str], list[str], str]:
    """Porcelain scan: (tracked_modified, untracked, error)."""
    ws = workspace.expanduser().resolve()
    if not (ws / ".git").exists():
        return [], [], f"Not a git repo: {ws}"
    try:
        proc = subprocess.run(
            ["git", "-C", str(ws), "status", "--porcelain"],
            capture_output=True, text=True, timeout=15,
        )
    except FileNotFoundError:
        return [], [], "git is not installed."
    except subprocess.TimeoutExpired:
        return [], [], "git timed out."
    if proc.returncode != 0:
        return [], [], f"git status failed: {(proc.stderr or proc.stdout).strip()[:200]}"
    modified: list[str] = []
    untracked: list[str] = []
    for line in proc.stdout.splitlines():
        if len(line) < 4:
            continue
        xy, path = line[:2], line[3:].strip().strip('"')
        if " -> " in path:  # renames: operate on the new path
            path = path.split(" -> ")[-1].strip()
        if xy.strip() == "??":
            untracked.append(path)
        else:
            modified.append(path)
    return modified, untracked, ""


def git_restore_paths(workspace: Path, paths: list[str]) -> str:
    """Restore tracked paths to HEAD (undo). Untracked files never touched."""
    ws = workspace.expanduser().resolve()
    try:
        proc = subprocess.run(
            ["git", "-C", str(ws), "checkout", "--", *paths],
            capture_output=True, text=True, timeout=60,
        )
    except FileNotFoundError:
        return "git is not installed."
    except subprocess.TimeoutExpired:
        return "git timed out."
    if proc.returncode != 0:
        return f"Restore failed: {(proc.stderr or proc.stdout).strip()[:300]}"
    return f"Restored {len(paths)} file(s) to HEAD."


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
