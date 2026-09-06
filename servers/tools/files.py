"""
Workspace file read/write for Cerberus.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from servers.tools.pathutil import (
    WorkspacePathError,
    is_binary_sample,
    resolve_workspace_path,
)
from servers.tools.safety import is_cerberusignored, load_cerberusignore_patterns


def read_file(
    path: str,
    *,
    workspace: Path,
    enforce_boundary: bool = True,
    offset: int = 1,
    limit: int = 400,
    max_chars: int = 100_000,
) -> str:
    """Read a text file with 1-based line offset and limit."""
    try:
        target = resolve_workspace_path(
            path, workspace, enforce_boundary=enforce_boundary, for_write=False
        )
    except WorkspacePathError as exc:
        return f"ERROR: {exc}"

    if not target.exists():
        return f"ERROR: file not found: {target}"
    if not target.is_file():
        return f"ERROR: not a regular file: {target}"

    try:
        raw = target.read_bytes()
    except OSError as exc:
        return f"ERROR: cannot read {target}: {exc}"

    if is_binary_sample(raw):
        return f"ERROR: binary file refused: {target}"

    text = raw.decode("utf-8", errors="replace")
    lines = text.splitlines()
    total = len(lines)

    offset = max(1, int(offset or 1))
    limit = max(1, min(int(limit or 400), 2000))
    start_idx = offset - 1
    if start_idx >= total:
        return (
            f"path: {target}\n"
            f"lines: empty (offset {offset} past end; total_lines={total})\n"
            "---\n"
        )

    end_idx = min(start_idx + limit, total)
    slice_lines = lines[start_idx:end_idx]

    width = max(3, len(str(end_idx)))
    numbered = []
    for i, line in enumerate(slice_lines, start=offset):
        numbered.append(f"{i:>{width}}| {line}")

    body = "\n".join(numbered)
    if len(body) > max_chars:
        body = body[:max_chars] + f"\n... [truncated at {max_chars} chars]"

    note = ""
    try:
        rel = target.relative_to(workspace.resolve())
        patterns = load_cerberusignore_patterns(workspace)
        if is_cerberusignored(str(rel), patterns):
            note = "[note: path matches .cerberusignore]\n"
    except ValueError:
        note = f"[note: outside workspace {workspace.resolve()}]\n"

    more = ""
    if end_idx < total:
        more = f"\n… {total - end_idx} more lines (use offset={end_idx + 1})"

    return (
        f"{note}path: {target}\n"
        f"lines: {offset}-{end_idx} / {total}\n"
        f"---\n{body}{more}"
    )


def view_workspace_file(
    path: str,
    *,
    workspace: Path,
    enforce_boundary: bool = True,
    max_chars: int = 80_000,
) -> str:
    return read_file(
        path,
        workspace=workspace,
        enforce_boundary=enforce_boundary,
        offset=1,
        limit=2000,
        max_chars=max_chars,
    )


def write_file(
    path: str,
    content: str,
    *,
    workspace: Path,
    enforce_boundary: bool = True,
    enforce_cerberusignore: bool = True,
) -> str:
    """Create or overwrite a text file under the workspace."""
    try:
        target = resolve_workspace_path(
            path, workspace, enforce_boundary=enforce_boundary, for_write=True
        )
    except WorkspacePathError as exc:
        return f"ERROR: {exc}"

    if enforce_cerberusignore:
        try:
            rel = target.relative_to(workspace.resolve())
            patterns = load_cerberusignore_patterns(workspace)
            if is_cerberusignored(str(rel), patterns):
                return f"ERROR: Refusing write to .cerberusignore protected path: {rel}"
        except ValueError:
            pass

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        data = content if content is not None else ""
        target.write_text(data, encoding="utf-8")
    except OSError as exc:
        return f"ERROR: failed to write {target}: {exc}"

    lines = len(data.splitlines())
    return f"WROTE: {target} ({len(data)} bytes, {lines} lines)"


def write_workspace_file(
    path: str,
    content: str,
    *,
    workspace: Path,
    enforce_boundary: bool = True,
) -> str:
    return write_file(
        path,
        content,
        workspace=workspace,
        enforce_boundary=enforce_boundary,
    )


def list_directory(
    path: str = ".",
    *,
    workspace: Path,
    enforce_boundary: bool = True,
    max_entries: int = 200,
) -> str:
    """List directory contents with file types and sizes."""
    try:
        target = resolve_workspace_path(
            path, workspace, enforce_boundary=enforce_boundary, for_write=False
        )
    except WorkspacePathError as exc:
        return f"ERROR: {exc}"

    if not target.exists():
        return f"ERROR: directory not found: {target}"
    if not target.is_dir():
        return f"ERROR: not a directory: {target}"

    try:
        entries = sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
    except OSError as exc:
        return f"ERROR: cannot read directory {target}: {exc}"

    patterns = load_cerberusignore_patterns(workspace)
    lines = [f"Directory: {target}"]
    count = 0
    for entry in entries:
        try:
            rel = entry.relative_to(workspace.resolve())
            ignored_mark = " [ignored]" if is_cerberusignored(str(rel), patterns) else ""
        except ValueError:
            ignored_mark = ""

        if entry.is_dir():
            lines.append(f"  [DIR]  {entry.name}/{ignored_mark}")
        else:
            size = entry.stat().st_size
            lines.append(f"  [FILE] {entry.name} ({size} bytes){ignored_mark}")
        count += 1
        if count >= max_entries:
            lines.append(f"  ... [truncated at {max_entries} entries]")
            break

    return "\n".join(lines)


def glob_files(
    pattern: str = "*",
    path: str = ".",
    *,
    workspace: Path,
    enforce_boundary: bool = True,
    max_results: int = 150,
) -> str:
    """Search for files matching a glob pattern."""
    try:
        target = resolve_workspace_path(
            path, workspace, enforce_boundary=enforce_boundary, for_write=False
        )
    except WorkspacePathError as exc:
        return f"ERROR: {exc}"

    if not target.exists() or not target.is_dir():
        return f"ERROR: directory not found: {target}"

    try:
        matches = sorted(target.glob(pattern))
    except Exception as exc:
        return f"ERROR: invalid glob pattern: {exc}"

    patterns = load_cerberusignore_patterns(workspace)
    lines = [f"Glob: {pattern} in {target}"]
    count = 0
    for m in matches:
        try:
            rel = m.relative_to(workspace.resolve())
            if is_cerberusignored(str(rel), patterns):
                continue
            lines.append(f"  {rel}{'/' if m.is_dir() else ''}")
        except ValueError:
            lines.append(f"  {m}{'/' if m.is_dir() else ''}")
        count += 1
        if count >= max_results:
            lines.append(f"  ... [truncated at {max_results} results]")
            break

    return "\n".join(lines)
