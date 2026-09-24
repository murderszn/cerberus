"""
Compact, human-readable rendering for agent output (stdlib-only).

Long model answers, diffs, and file lists are clipped or grouped so a
status question gets bullets/tables instead of a wall of text. Importable
without rich so the CLI fallback UI and unit tests never need
third-party packages.
"""

from __future__ import annotations

import re

# Thresholds: below these, output renders in full.
DIGEST_LINES = 60
DIGEST_CHARS = 6000
DIFF_MAX_LINES = 40
BODY_MAX_LINES = 25
GROUP_BULLETS = 8

_HEADING_RE = re.compile(r"^\s{0,3}(#{1,4})\s+(.*\S)\s*$")
_BULLET_RE = re.compile(r"^\s*(?:[-*]|\d+[.)])\s+(.*\S)\s*$")
_FENCE_RE = re.compile(r"^\s*```")


def clip_text(text: str, max_lines: int = BODY_MAX_LINES, max_chars: int = 4000) -> str:
    """Clip to a readable prefix, noting what was omitted."""
    lines = (text or "").splitlines()
    omitted = 0
    if len(lines) > max_lines:
        omitted = len(lines) - max_lines
        lines = lines[:max_lines]
    out = "\n".join(lines)
    if len(out) > max_chars:
        out = out[:max_chars].rstrip()
        omitted = max(omitted, 1)
    if omitted:
        out += f"\n… ({omitted} more line{'s' if omitted != 1 else ''} — ask for a section in full)"
    return out


def outline_markdown(text: str) -> list[tuple[str, list[str]]]:
    """Group markdown into (heading, bullets); code fences are skipped.

    Headings become group titles, list items become their rows, and plain
    paragraphs attach to the current group so nothing silently vanishes.
    """
    groups: list[tuple[str, list[str]]] = []
    current: list[str] = []
    groups.append(("", current))
    in_fence = False
    for raw in (text or "").splitlines():
        if _FENCE_RE.match(raw):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        heading = _HEADING_RE.match(raw)
        if heading:
            current = []
            groups.append((heading.group(2).strip(), current))
            continue
        bullet = _BULLET_RE.match(raw)
        if bullet:
            current.append(bullet.group(1).strip())
        elif raw.strip():
            current.append(raw.strip())
    return [(title, rows) for title, rows in groups if rows]


def format_digest(text: str, per_group: int = GROUP_BULLETS) -> str:
    """Render a grouped outline: headings with capped bullet rows."""
    lines_out: list[str] = []
    for title, rows in outline_markdown(text):
        if title:
            lines_out.append(f"### {title}")
        shown = rows[:per_group]
        lines_out.extend(f"- {row}" for row in shown)
        extra = len(rows) - len(shown)
        if extra > 0:
            lines_out.append(f"- … and {extra} more")
        lines_out.append("")
    return "\n".join(lines_out).rstrip() or "(no summary)"


def needs_digest(text: str) -> bool:
    """True when a final answer is large enough to deserve grouped output."""
    text = text or ""
    return len(text.splitlines()) > DIGEST_LINES or len(text) > DIGEST_CHARS


def cap_diff(diff: str, max_lines: int = DIFF_MAX_LINES) -> tuple[str, int]:
    """Cap a unified diff; returns (visible_text, omitted_line_count)."""
    lines = (diff or "").strip().splitlines()
    if len(lines) <= max_lines:
        return "\n".join(lines), 0
    return "\n".join(lines[:max_lines]), len(lines) - max_lines


_STATUS_LABELS = {
    "M": "Modified",
    "A": "Added",
    "D": "Deleted",
    "R": "Renamed",
    "C": "Copied",
    "U": "Unmerged",
    "?": "Untracked",
    "!": "Ignored",
}


def group_file_changes(status_output: str, max_paths: int = 10) -> str:
    """Group `git status --porcelain` lines by change kind for scanability."""
    buckets: dict[str, list[str]] = {}
    order: list[str] = []
    for raw in (status_output or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        code = (line[0] if line[0] != " " else line[1] if len(line) > 1 else "?").upper()
        label = _STATUS_LABELS.get(code, "Changed")
        if label not in buckets:
            buckets[label] = []
            order.append(label)
        path = line[1:].strip().lstrip("-> ").strip() if len(line) > 1 else line
        buckets[label].append(path)
    total = sum(len(paths) for paths in buckets.values())
    rows = [f"| Change | Files |", f"|---|---|"]
    for label in order:
        paths = buckets[label]
        shown = ", ".join(f"`{p}`" for p in paths[:max_paths])
        extra = f" (+{len(paths) - max_paths} more)" if len(paths) > max_paths else ""
        rows.append(f"| {label} ({len(paths)}) | {shown}{extra} |")
    rows.append(f"\n{total} file{'s' if total != 1 else ''} total.")
    return "\n".join(rows)
