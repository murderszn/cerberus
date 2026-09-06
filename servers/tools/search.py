"""
Workspace search tools for Cerberus with secret redaction and .cerberusignore support.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from servers.tools.pathutil import WorkspacePathError, resolve_workspace_path
from servers.tools.safety import is_cerberusignored, load_cerberusignore_patterns, redact_text

_SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "dist",
    "build",
    ".next",
    ".turbo",
    "target",
    ".cerberus",
    ".opencode_harness",
}


def search_workspace(
    pattern: str,
    *,
    workspace: Path,
    path: str = ".",
    glob: str = "",
    max_results: int = 50,
    case_insensitive: bool = False,
) -> str:
    """Search file contents for a regex/string pattern with secret redaction."""
    return grep_search(
        pattern,
        workspace=workspace,
        path=path,
        glob=glob,
        max_results=max_results,
        case_insensitive=case_insensitive,
    )


def grep_search(
    pattern: str,
    *,
    workspace: Path,
    path: str = ".",
    glob: str = "",
    max_results: int = 50,
    case_insensitive: bool = False,
) -> str:
    """Search file contents for a regex/string pattern with secret redaction."""
    if not pattern:
        return "ERROR: empty pattern"

    try:
        root = resolve_workspace_path(
            path or ".", workspace, enforce_boundary=True, for_write=False
        )
    except WorkspacePathError as exc:
        return f"ERROR: {exc}"

    if not root.exists():
        return f"ERROR: path not found: {root}"

    max_results = max(1, min(int(max_results or 50), 200))
    matches: list[str] = []
    patterns = load_cerberusignore_patterns(workspace)

    rg = shutil.which("rg")
    if rg:
        cmd = [
            rg,
            "--line-number",
            "--color",
            "never",
            "--no-heading",
            "--max-count",
            "20",
            "-m",
            str(max_results * 2),
        ]
        if case_insensitive:
            cmd.append("-i")
        if glob:
            cmd.extend(["-g", glob])
        cmd.extend(["--", pattern, str(root)])
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=45,
                check=False,
            )
            for line in (proc.stdout or "").splitlines():
                if not line.strip():
                    continue
                parts = line.split(":", 2)
                if len(parts) >= 3:
                    file_part = parts[0]
                    try:
                        rel = Path(file_part).resolve().relative_to(workspace.resolve())
                        if is_cerberusignored(str(rel), patterns):
                            continue
                        shown_file = str(rel)
                    except ValueError:
                        shown_file = file_part
                    line_num = parts[1]
                    raw_content = parts[2]
                    redacted_content = redact_text(raw_content)
                    matches.append(f"{shown_file}:{line_num}:{redacted_content[:240]}")
                else:
                    matches.append(redact_text(line)[:240])

                if len(matches) >= max_results:
                    break
            if matches:
                return _format_grep(pattern, root, matches, truncated=len(matches) >= max_results)
            if proc.returncode in (0, 1):
                return _format_grep(pattern, root, [], truncated=False)
        except (OSError, subprocess.TimeoutExpired):
            pass

    # Pure Python fallback
    try:
        flags = re.I if case_insensitive else 0
        rx = re.compile(pattern, flags)
    except re.error as exc:
        return f"ERROR: invalid regex: {exc}"

    glob_rx = None
    if glob:
        g = re.escape(glob).replace(r"\*", ".*").replace(r"\?", ".")
        glob_rx = re.compile(f"^{g}$", re.I)

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS and not d.startswith(".")]
        for name in filenames:
            if glob_rx and not glob_rx.match(name):
                continue
            fp = Path(dirpath) / name
            try:
                rel = fp.resolve().relative_to(workspace.resolve())
                if is_cerberusignored(str(rel), patterns):
                    continue
                shown = str(rel)
            except ValueError:
                shown = str(fp)

            try:
                if fp.stat().st_size > 1_000_000:
                    continue
                sample = fp.read_bytes()[:512]
                if b"\x00" in sample:
                    continue
                text = fp.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue

            for i, line in enumerate(text.splitlines(), start=1):
                if rx.search(line):
                    redacted = redact_text(line)
                    matches.append(f"{shown}:{i}:{redacted[:240]}")
                    if len(matches) >= max_results:
                        return _format_grep(pattern, root, matches, truncated=True)

    return _format_grep(pattern, root, matches, truncated=False)


def _format_grep(pattern: str, root: Path, matches: list[str], *, truncated: bool) -> str:
    header = [
        f"pattern: {pattern}",
        f"root: {root}",
        f"matches: {len(matches)}" + (" (truncated)" if truncated else ""),
        "---",
    ]
    if not matches:
        return "\n".join(header + ["(no matches)"])
    return "\n".join(header + matches)
