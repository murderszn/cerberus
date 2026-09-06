"""
Inspection tools for Cerberus — structure, network, and interpreter probes.

  file_tree     nested directory outline (bounded depth + entry count)
  http_request  minimal http/https fetch returning truncated text
  python_eval   run a python snippet via subprocess with timeout

http_request and file_tree are read-only. python_eval executes code and is
never available in PLAN mode. All stdlib-only so `examine.py --native-only`
stays dependency-free.
"""

from __future__ import annotations

import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional

from servers.logging_setup import get_logger
from servers.tools.pathutil import WorkspacePathError, resolve_workspace_path

log = get_logger("tools.inspect")

DEFAULT_TIMEOUT = 20
DEFAULT_MAX_BYTES = 20000


def file_tree(
    path: str = ".",
    *,
    workspace: Path,
    enforce_boundary: bool = True,
    max_depth: int = 4,
    max_entries: int = 200,
) -> str:
    """Render a bounded nested tree of a workspace directory."""
    try:
        root = resolve_workspace_path(
            path, workspace, enforce_boundary=enforce_boundary, for_write=False
        )
    except WorkspacePathError as exc:
        return f"ERROR: {exc}"
    if not root.exists():
        return f"ERROR: path does not exist: {path}"
    if not root.is_dir():
        return f"ERROR: not a directory: {path}"

    lines: list[str] = []
    count = 0
    truncated = False

    def walk(node: Path, prefix: str, depth: int) -> None:
        nonlocal count, truncated
        if depth > max_depth or truncated:
            return
        try:
            entries = sorted(node.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        except OSError as exc:
            lines.append(f"{prefix}⬦ <unreadable: {exc}>")
            return
        for i, entry in enumerate(entries):
            if count >= max_entries:
                truncated = True
                return
            count += 1
            last = i == len(entries) - 1
            branch = "└── " if last else "├── "
            suffix = "/" if entry.is_dir() else ""
            lines.append(f"{prefix}{branch}{entry.name}{suffix}")
            if entry.is_dir():
                walk(entry, prefix + ("    " if last else "│   "), depth + 1)

    header = str(root)
    try:
        header = str(root.relative_to(workspace.resolve())) or "."
    except ValueError:
        pass
    lines.append(f"{header}/")
    walk(root, "", 1)
    if truncated:
        lines.append(f"… truncated at {max_entries} entries (depth ≤ {max_depth})")
    return "\n".join(lines)


def http_request(
    url: str,
    *,
    method: str = "GET",
    timeout: int = DEFAULT_TIMEOUT,
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> str:
    """Fetch an http/https URL and return truncated decoded text."""
    scheme = (url or "").strip().split("://", 1)[0].lower()
    if scheme not in {"http", "https"}:
        return "ERROR: only http:// and https:// URLs are allowed"
    req = urllib.request.Request(url, method=method.upper())
    req.add_header("User-Agent", "Cerberus/2.0")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            raw = resp.read(max_bytes + 1)
            status = getattr(resp, "status", "?")
    except urllib.error.HTTPError as exc:
        return f"ERROR: HTTP {exc.code} for {url}"
    except urllib.error.URLError as exc:
        return f"ERROR: request failed for {url}: {exc.reason}"
    except Exception as exc:
        return f"ERROR: request failed for {url}: {exc}"
    cut = len(raw) > max_bytes
    text = raw[:max_bytes].decode("utf-8", errors="replace")
    note = f"\n… truncated at {max_bytes} bytes" if cut else ""
    return f"HTTP {status} {url}\n{text}{note}"


def python_eval(
    code: str,
    *,
    workspace: Path,
    timeout: int = DEFAULT_TIMEOUT,
) -> str:
    """Execute a python snippet in a subprocess rooted at the workspace."""
    if not code or not code.strip():
        return "ERROR: empty code snippet"
    try:
        proc = subprocess.run(
            ["python3", "-c", code],
            cwd=str(workspace),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError:
        return "ERROR: python3 not found in PATH"
    except subprocess.TimeoutExpired:
        return f"ERROR: python snippet timed out after {timeout}s"
    except Exception as exc:
        return f"ERROR: {exc}"
    out = (proc.stdout or "").strip()
    err = (proc.stderr or "").strip()
    parts = [f"exit={proc.returncode}"]
    if out:
        parts.append(f"stdout:\n{out[:DEFAULT_MAX_BYTES]}")
    if err:
        parts.append(f"stderr:\n{err[:DEFAULT_MAX_BYTES]}")
    if not out and not err:
        parts.append("(no output)")
    return "\n".join(parts)
