"""Normalization, redaction, fingerprinting, and deduplication helpers."""

from __future__ import annotations

import hashlib
import json
import os
import re
from typing import Any, Dict, Iterable, List, Optional


SEVERITIES = ("critical", "high", "medium", "low", "info")
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


def normalize_severity(value: Any, default: str = "medium") -> str:
    if isinstance(value, (int, float)):
        score = float(value)
        if score >= 9.0:
            return "critical"
        if score >= 7.0:
            return "high"
        if score >= 4.0:
            return "medium"
        if score > 0:
            return "low"
        return "info"
    text = str(value or "").strip().lower()
    aliases = {
        "error": "high", "warning": "medium", "warn": "medium",
        "moderate": "medium", "unknown": default, "none": "info",
        "negligible": "info", "note": "info",
    }
    if text in SEVERITIES:
        return text
    if text in aliases:
        return aliases[text]
    try:
        return normalize_severity(float(text), default)
    except ValueError:
        return default


def redact_text(value: Any) -> str:
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
        return [redact(v) for v in value]
    if isinstance(value, str):
        return redact_text(value)
    return value


def normalize_path(path: Any, root: str) -> str:
    raw = str(path or ".").replace("\\", "/")
    root_abs = os.path.abspath(root)
    if os.path.isabs(raw):
        try:
            if os.path.commonpath((root_abs, os.path.abspath(raw))) == root_abs:
                raw = os.path.relpath(raw, root_abs).replace(os.sep, "/")
            else:
                return "."
        except (OSError, ValueError):
            return "."
    normalized = os.path.normpath(raw).replace(os.sep, "/")
    if normalized == ".." or normalized.startswith("../"):
        return "."
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized or "."


def fingerprint_for(finding: Dict[str, Any]) -> str:
    identity = {
        "tool": finding.get("source", {}).get("tool", ""),
        "rule": finding.get("ruleId", ""),
        "path": finding.get("path", "."),
        "line": finding.get("line") or 1,
        "column": finding.get("column") or 1,
        "message": " ".join(str(finding.get("message", "")).split()),
    }
    payload = json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def normalize_finding(
    tool: str,
    raw_rule_id: Any,
    severity: Any,
    path: Any,
    line: Any,
    column: Any,
    message: Any,
    root: str,
    *,
    remediation: Any = "",
    confidence: Optional[float] = None,
    agent: str = "external",
    evidence: Any = None,
) -> Dict[str, Any]:
    try:
        line_num = max(1, int(line or 1))
    except (TypeError, ValueError):
        line_num = 1
    try:
        column_num = max(1, int(column or 1))
    except (TypeError, ValueError):
        column_num = 1
    rule_id = str(raw_rule_id or "unknown")
    finding = {
        "ruleId": rule_id,
        "severity": normalize_severity(severity),
        "path": normalize_path(path, root),
        "line": line_num,
        "column": column_num,
        "message": redact_text(message)[:2000],
        "agent": agent,
        "source": {"tool": tool, "rawRuleId": rule_id},
    }
    if remediation:
        finding["remediation"] = redact_text(remediation)[:2000]
    if confidence is not None:
        finding["confidence"] = max(0.0, min(1.0, float(confidence)))
    if evidence is not None:
        finding["evidence"] = redact(evidence)
    finding["fingerprint"] = fingerprint_for(finding)
    return finding


def deduplicate(findings: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    unique = {}
    for finding in findings:
        fingerprint = finding.get("fingerprint") or fingerprint_for(finding)
        finding["fingerprint"] = fingerprint
        unique.setdefault(fingerprint, finding)
    return list(unique.values())
