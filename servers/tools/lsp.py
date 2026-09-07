"""LSP-lite read-only helpers: symbol outlines and file diagnostics.

No language-server dependency: outlines reuse the existing AST walker and
diagnostics are a syntax parse (Python) plus marker scan (other text).
Everything here is read-only and workspace-bounded.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Tuple

MARKER_PATTERN = re.compile(r"TODO|FIXME|XXX|HACK\b")
MAX_SCAN_BYTES = 64 * 1024


def _resolve(path: str, workspace: Path) -> Tuple[Path, str]:
    ws = workspace.expanduser().resolve()
    target = (ws / path).resolve() if not Path(path).is_absolute() else Path(path).resolve()
    try:
        target.relative_to(ws)
    except ValueError:
        return target, f"ERROR: {path} is outside the workspace."
    if not target.is_file():
        return target, f"ERROR: not a file: {path}"
    return target, ""


def python_diagnostics(
    path: str,
    *,
    workspace: Path,
    enforce_boundary: bool = True,
) -> str:
    """Syntax errors (Python) or TODO-style markers (other text). Read-only."""
    target, err = _resolve(path, workspace)
    if err and enforce_boundary and "outside" in err:
        return err
    if err:
        return err
    try:
        raw = target.read_bytes()[: MAX_SCAN_BYTES + 1]
    except OSError as exc:
        return f"ERROR: cannot read {path}: {exc}"
    truncated = len(raw) > MAX_SCAN_BYTES
    text = raw[:MAX_SCAN_BYTES].decode("utf-8", errors="replace")
    if target.suffix.lower() in {".py", ".pyi"}:
        try:
            tree = ast.parse(text, filename=str(target))
        except SyntaxError as exc:
            return f"SyntaxError {target.name}:{exc.lineno}: {exc.msg}"
        names = sum(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                    for n in ast.walk(tree))
        out = f"OK: {target.name} parses ({names} defs)"
    else:
        hits = [
            f"{i + 1}: {line.strip()[:120]}"
            for i, line in enumerate(text.splitlines())
            if MARKER_PATTERN.search(line)
        ][:20]
        if not hits:
            return f"OK: {target.name} — no TODO/FIXME markers"
        out = f"{target.name} markers:\n" + "\n".join(f"  {h}" for h in hits)
    if truncated:
        out += "\n…(scanned first 64 KiB)"
    return out
