"""
Plain-language narration for agent activity (stdlib-only).

Translates raw tool calls ("execute_bash_command") into sentences a
non-engineer can follow. Importable without rich so the CLI fallback UI
and unit tests never need third-party packages.
"""

from __future__ import annotations

from typing import Any


def _short(value: Any, limit: int = 80) -> str:
    text = str(value) if value is not None else ""
    text = text.replace("\n", " ").strip()
    return text if len(text) <= limit else text[: limit - 1] + "…"


TAGLINE = "three heads · one will"


def welcome_rows(
    *,
    model: str,
    base_url: str,
    workspace: str,
    mode: str,
    auth: str,
    log_file: str,
) -> list[tuple[str, str]]:
    """Status-grid rows for the init screen (pure data, easily tested)."""
    mode_label = "ACCEPT-EDITS" if mode == "build" else "PLAN · read-only"
    return [
        ("Model", f"{model} · {base_url}"),
        ("Mode", f"{mode_label}   (Shift-Tab to toggle)"),
        ("Workspace", workspace),
        ("Auth", auth),
        ("Log", log_file),
    ]


def describe_activity(name: str, args: dict[str, Any]) -> tuple[str, str]:
    """Plain-language (headline, detail) for a tool call.

    Headlines never assume the reader knows tool names or shell syntax.
    """
    args = args or {}
    if name == "read_file":
        return f"Reading {_short(args.get('path'), 60)}", "understanding the current code first"
    if name in {"write_file", "edit_file", "multiedit_file"}:
        return f"Editing {_short(args.get('path'), 60)}", "applying a surgical change"
    if name in {"search_workspace", "grep_search", "glob_files"}:
        target = args.get("pattern", args.get("glob", args.get("path", "")))
        return f"Searching the codebase for {_short(target, 50)}", "mapping where things live"
    if name in {"list_symbols", "view_outline"}:
        return f"Outlining {_short(args.get('path'), 60)}", "seeing the structure, not every line"
    if name in {"list_directory", "file_tree"}:
        return f"Looking at {_short(args.get('path', '.'), 60)}", "getting oriented in the project"
    if name == "execute_bash_command":
        cmd = str(args.get("command", ""))
        low = cmd.lower()
        if any(k in low for k in ("pytest", "npm test", "cargo test", "go test", "unittest")):
            return "Running the test suite", "checking nothing broke"
        if low.startswith("git "):
            return "Checking version history", "seeing what changed and when"
        if any(k in low for k in ("ls", "find ", "cat ", "head ", "tree")):
            return "Looking around the project files", "getting oriented"
        return "Running a check on your machine", "verifying something only the terminal can tell us"
    if name == "python_eval":
        return "Trying a quick calculation", "double-checking logic before touching files"
    if name in {"git_status", "git_diff", "git_log", "git_branch"}:
        return "Reviewing what changed", "comparing against version history"
    if name == "create_pull_request":
        return f"Preparing a pull request: {_short(args.get('title'), 60)}", "packaging the fix for review"
    if name in {"browse_web_content", "http_request"}:
        return f"Looking up {_short(args.get('url'), 60)}", "pulling in outside reference material"
    return f"Working ({_short(name, 40)})", "continuing the task"
