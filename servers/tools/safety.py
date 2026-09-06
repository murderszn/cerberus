"""
Safety verification, command sanitization, .cerberusignore enforcement,
and secret redaction for Cerberus.
"""

from __future__ import annotations

import fnmatch
import os
import re
from pathlib import Path
from typing import Any, Iterable, Optional

# ---------------------------------------------------------------------------
# Destructive command patterns
# ---------------------------------------------------------------------------

_DEFAULT_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\brm\s+(-[a-zA-Z]*[rR][a-zA-Z]*f|[a-zA-Z]*f[a-zA-Z]*[rR]|-[rR]\s+-[fF]|-[fF]\s+-[rR])\b"),
    re.compile(r"\brm\s+-[^\s]*r[^\s]*\b"),
    re.compile(r"\brm\s+--recursive\b"),
    re.compile(r"\bmkfs(\.\w+)?\b"),
    re.compile(r"\bdd\s+if=", re.I),
    re.compile(r">\s*/dev/sd"),
    re.compile(r"\bchmod\b"),
    re.compile(r"\bchown\b"),
    re.compile(r"\bchgrp\b"),
    re.compile(r"\bsudo\b"),
    re.compile(r"\bdoas\b"),
    re.compile(r"\bshutdown\b"),
    re.compile(r"\breboot\b"),
    re.compile(r"\bhalt\b"),
    re.compile(r"\bpoweroff\b"),
    re.compile(r"\binit\s+[06]\b"),
    re.compile(r"\bapt(-get)?\s+remove\b"),
    re.compile(r"\bapt(-get)?\s+purge\b"),
    re.compile(r"\byum\s+remove\b"),
    re.compile(r"\bdnf\s+remove\b"),
    re.compile(r"\bbrew\s+uninstall\b"),
    re.compile(r"\bpip(3)?\s+uninstall\b"),
    re.compile(r"\bgit\s+push\s+.*--force\b"),
    re.compile(r"\bgit\s+push\s+.*-f\b"),
    re.compile(r"\bgit\s+reset\s+--hard\b"),
    re.compile(r"\bgit\s+clean\s+.*-[a-zA-Z]*f"),
    re.compile(r"\bdiskutil\s+(erase|partition|unmount)\b", re.I),
    re.compile(r"\bparted\b"),
    re.compile(r"\bfdisk\b"),
    re.compile(r">\s*/etc/"),
    re.compile(r"\bmv\s+.+\s+/dev/null\b"),
    re.compile(r":\(\)\s*\{\s*:\|:\s*&\s*\}\s*;\s*:"),
    re.compile(r"\bkill\s+-9\s+-1\b"),
    re.compile(r"\bkillall\b"),
    re.compile(r"\bshred\b"),
    re.compile(r"\bunlink\b"),
    re.compile(r"\brmdir\b"),
    re.compile(r"\blaunchctl\s+(bootout|unload)\b"),
]


def is_destructive(command: str, extra_patterns: Optional[Iterable[str]] = None) -> tuple[bool, str]:
    """Return (True, reason) if the command looks destructive."""
    cmd = command.strip()
    if not cmd:
        return False, ""

    for pattern in _DEFAULT_PATTERNS:
        if pattern.search(cmd):
            return True, f"matched safety pattern: /{pattern.pattern}/"

    if extra_patterns:
        for raw in extra_patterns:
            try:
                if re.search(raw, cmd, flags=re.I):
                    return True, f"matched custom pattern: /{raw}/"
            except re.error:
                continue

    return False, ""


# ---------------------------------------------------------------------------
# Build / test command heuristic (ask-first approvals)
# ---------------------------------------------------------------------------

# Command position only (start or after a shell separator) so arguments that
# merely mention a tool — e.g. `grep -r pytest .` — do not trigger approval.
_BUILD_PATTERN = re.compile(
    r"(?:^|[;&|()])\s*"
    r"(pytest|python\s+-m\s+(pytest|build)|"
    r"npm\s+(run\s+)?(build|test|ci)|yarn\s+(build|test)|pnpm\s+(build|test)|"
    r"make(\s|$)|cmake\s+--build|cargo\s+(build|test)|go\s+(build|test)|"
    r"docker\s+build|tsc(\s|$)|gradle|mvn(\s|$)|tox|nox|"
    r"poetry\s+(build|install)|pip\s+install)",
    re.IGNORECASE,
)


def is_build_command(command: str) -> bool:
    """Heuristic: does this shell line run a build, test suite, or installer?"""
    return bool(command and _BUILD_PATTERN.search(command))


# ---------------------------------------------------------------------------
# Secret Redaction (mirrors feeders/normalize.py)
# ---------------------------------------------------------------------------

_SENSITIVE_KEY = re.compile(
    r"(?:secret|password|passwd|token|credential|private[_-]?key|access[_-]?key|api[_-]?key)",
    re.I,
)

_SECRET_PATTERNS = (
    re.compile(r"(?i)\b(bearer\s+)[A-Za-z0-9._~+/=-]{8,}"),
    re.compile(r"\b(?:gh[opusr]_[A-Za-z0-9]{12,}|github_pat_[A-Za-z0-9_]{12,})\b"),
    re.compile(r"\bAKIA[0-9A-Z]{12,}\b"),
    re.compile(
        r"(?i)\b(password|passwd|secret|token|api[_-]?key|access[_-]?key)"
        r"(\s*[:=]\s*)([^\s,;]+)"
    ),
)


def redact_text(value: Any) -> str:
    """Redact known secret patterns from output text."""
    text = str(value or "")
    for pattern in _SECRET_PATTERNS:
        if pattern.groups >= 3:
            text = pattern.sub(lambda m: m.group(1) + m.group(2) + "[REDACTED]", text)
        elif pattern.groups:
            text = pattern.sub(lambda m: m.group(1) + "[REDACTED]", text)
        else:
            text = pattern.sub("[REDACTED]", text)
    return text


def redact(value: Any, key: str = "") -> Any:
    if _SENSITIVE_KEY.search(key):
        return "[REDACTED]"
    if isinstance(value, dict):
        return {str(k): redact(v, str(k)) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v) for v in value]
    if isinstance(value, tuple):
        return tuple(redact(v) for v in value)
    if isinstance(value, str):
        return redact_text(value)
    return value


# ---------------------------------------------------------------------------
# .cerberusignore handling (mirrors examine.py)
# ---------------------------------------------------------------------------

CERBERUSIGNORE = ".cerberusignore"


def parse_cerberusignore(text: str) -> list[str]:
    """Parse a .cerberusignore text into glob patterns."""
    patterns: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        line = line.rstrip("/")
        if "/" not in line and not line.startswith("**"):
            patterns.append("**/" + line)
            patterns.append("**/" + line + "/**")
        else:
            patterns.append(line)
            patterns.append(line.rstrip("*").rstrip("/") + "/**")
    return patterns


def load_cerberusignore_patterns(workspace: Path) -> list[str]:
    ignore_file = workspace / CERBERUSIGNORE
    if not ignore_file.exists():
        return []
    try:
        content = ignore_file.read_text(encoding="utf-8")
        return parse_cerberusignore(content)
    except Exception:
        return []


def is_cerberusignored(rel_path: str, patterns: list[str]) -> bool:
    """Check if relative path matches any .cerberusignore pattern."""
    norm = rel_path.replace("\\", "/").lstrip("./")
    for pattern in patterns:
        p_clean = pattern.lstrip("./")
        if fnmatch.fnmatch(norm, p_clean) or fnmatch.fnmatch(f"/{norm}", p_clean):
            return True
        if p_clean.startswith("**/"):
            base_pat = p_clean[3:]
            if fnmatch.fnmatch(norm, base_pat) or fnmatch.fnmatch(os.path.basename(norm), base_pat):
                return True
    return False
