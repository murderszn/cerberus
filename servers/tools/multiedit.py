"""
Multi-chunk surgical file edits for Cerberus.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from servers.tools.pathutil import WorkspacePathError, resolve_workspace_path
from servers.tools.safety import is_cerberusignored, load_cerberusignore_patterns


def multi_edit_file(
    path: str,
    replacements: list[dict[str, Any]] | str,
    *,
    workspace: Path,
    enforce_boundary: bool = True,
    enforce_cerberusignore: bool = True,
) -> str:
    """Apply multiple distinct string replacements to a single file safely."""
    if not path:
        return "ERROR: path must be non-empty"

    if isinstance(replacements, str):
        try:
            replacements = json.loads(replacements)
        except json.JSONDecodeError as exc:
            return f"ERROR: replacements must be valid JSON list: {exc}"

    if not isinstance(replacements, list):
        return "ERROR: replacements must be a list of replacement objects"

    if len(replacements) == 0:
        return "ERROR: replacements list cannot be empty"

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
                return f"ERROR: Refusing multi-edit to .cerberusignore protected file: {rel}"
        except ValueError:
            pass

    if not target.exists():
        return f"ERROR: file not found: {target} (use write_file to create it)"
    if not target.is_file():
        return f"ERROR: not a regular file: {target}"

    try:
        original_text = target.read_text(encoding="utf-8")
    except OSError as exc:
        return f"ERROR: cannot read {target}: {exc}"

    working_text = original_text
    total_replacements = 0

    for idx, item in enumerate(replacements, start=1):
        if not isinstance(item, dict):
            return f"ERROR: Replacement #{idx} is not a dictionary"

        old_string = item.get("old_string")
        if old_string is None:
            old_string = item.get("old") or item.get("targetContent")

        new_string = item.get("new_string")
        if new_string is None:
            new_string = item.get("new") if "new" in item else item.get("replacementContent")
        if new_string is None:
            new_string = ""

        replace_all = bool(
            item.get("replace_all", item.get("allow_multiple", False))
        )

        if not old_string:
            return f"ERROR: Replacement #{idx}: old_string must be non-empty"

        if old_string == new_string:
            return f"ERROR: Replacement #{idx}: old_string and new_string are identical — nothing to change"

        count = working_text.count(old_string)
        if count == 0:
            hint = _near_miss_hint(working_text, old_string)
            return (
                f"ERROR: Replacement #{idx} failed: old_string not found in {target}.\n"
                f"{hint}"
            ).strip()

        if count > 1 and not replace_all:
            return (
                f"ERROR: Replacement #{idx} failed: old_string matched {count} times in {target}.\n"
                f"Provide a larger unique old_string, or set replace_all=true."
            )

        if replace_all:
            working_text = working_text.replace(old_string, new_string)
            total_replacements += count
        else:
            working_text = working_text.replace(old_string, new_string, 1)
            total_replacements += 1

    temp_file = target.with_name(f".{target.name}.tmp_{os.getpid()}_{time.time_ns()}")
    try:
        temp_file.write_text(working_text, encoding="utf-8")
        temp_file.replace(target)
    except OSError as exc:
        if temp_file.exists():
            try:
                temp_file.unlink()
            except OSError:
                pass
        return f"ERROR: cannot write {target}: {exc}"

    return (
        f"OK: multi-edited {target} ({total_replacements} replacement(s) "
        f"across {len(replacements)} chunk(s))"
    )


def _near_miss_hint(text: str, old: str) -> str:
    first = next((ln.strip() for ln in old.splitlines() if ln.strip()), "")
    if not first or len(first) < 4:
        return ""
    idx = text.find(first)
    if idx < 0:
        return ""
    start = max(0, idx - 40)
    end = min(len(text), idx + len(first) + 80)
    snippet = text[start:end].replace("\n", "\\n")
    return f"Near miss snippet: …{snippet}…"
