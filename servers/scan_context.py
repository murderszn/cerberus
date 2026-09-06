"""
Scan findings as conversation context (RAG).

After a `/scan`, the full report JSON is summarized into a compact digest
and appended to the agent's message history, so natural follow-ups like
"how do I get to 100%?" or "where did these scores come from?" are
answerable without re-running the scanner. A new scan replaces the
previous digest so stale findings never stack up.
"""

from __future__ import annotations

from typing import Any

from servers.models import Message

SCAN_DIGEST_TAG = "[scan-context]"
MAX_DIGEST_CHARS = 6000
MAX_FINDINGS_PER_CHECK = 3
MAX_FAILED_CHECKS = 12

# Mirrors examine.py: per-severity point deduction and grade bands.
_METHODOLOGY = (
    "Method: each agent domain starts at its full weight (weights sum to 100). "
    "Each distinct failed finding deducts points by severity "
    "(critical −4, high −2, medium −1, low −0.5, capped at 3 hits per check). "
    "Grades: A ≥90, B ≥80, C ≥70, D ≥60, else F. "
    "To reach 100, resolve every failed check below — each lists its "
    "deduction, remediation, and file locations."
)


def build_scan_digest(report: dict[str, Any], target: str = "") -> str:
    """Summarize a scan report JSON into conversation-ready context."""
    score = report.get("score", "?")
    grade = report.get("grade", "?")
    counts = report.get("counts", {}) or {}
    agents = report.get("agents", []) or []
    engine = report.get("engine", {}) or {}
    coverage = report.get("coverage", {}) or {}
    notes = report.get("notes", []) or []

    lines: list[str] = [
        f"{SCAN_DIGEST_TAG} Scan findings for `{target or report.get('target', '?')}` "
        f"(reference — answer follow-up questions from this; "
        f"do not treat it as a new user request).",
        f"Score: {score}/100 (grade {grade}). "
        f"Passed: {counts.get('pass', '?')}, failed: {counts.get('fail', '?')} "
        f"of {counts.get('total', '?')} checks "
        f"(critical={counts.get('critical', 0)} high={counts.get('high', 0)} "
        f"medium={counts.get('medium', 0)} low={counts.get('low', 0)}).",
        f"Engine v{engine.get('version', '?')} · "
        f"{coverage.get('filesScanned', '?')} files scanned.",
        _METHODOLOGY,
        "",
        "Per-domain scores:",
    ]
    for agent in agents:
        lines.append(
            "  - {}: {}/{} — {}".format(
                agent.get("name", "?"), agent.get("score", "?"),
                agent.get("weight", "?"), agent.get("domain", ""),
            )
        )

    failed: list[str] = []
    for agent in agents:
        for check in agent.get("checks", []) or []:
            if check.get("status") != "fail":
                continue
            entry = [
                "  - [{}] {} (−{} pts): {}".format(
                    check.get("severity", "?"), check.get("name", "?"),
                    check.get("deduction", "?"),
                    check.get("summary", "") or check.get("risk", ""),
                )
            ]
            remediation = (check.get("remediation", "") or "").strip()
            if remediation:
                entry.append(f"    Fix: {remediation}")
            findings = check.get("findings", []) or []
            for finding in findings[:MAX_FINDINGS_PER_CHECK]:
                loc = "{}:{}".format(
                    finding.get("path", "."), finding.get("line", 1)
                )
                snippet = (finding.get("snippet", "") or "").strip().splitlines()
                hint = f" — {snippet[0][:100]}" if snippet and snippet[0] else ""
                entry.append(f"    at {loc}{hint}")
            total = check.get("totalFindings", len(findings))
            if total and total > len(findings[:MAX_FINDINGS_PER_CHECK]):
                entry.append(f"    …and {total - MAX_FINDINGS_PER_CHECK} more occurrences")
            failed.append("\n".join(entry))
            if len(failed) >= MAX_FAILED_CHECKS:
                break
        if len(failed) >= MAX_FAILED_CHECKS:
            break

    lines.append("")
    if failed:
        lines.append("Failed checks (highest severity first across domains):")
        lines.extend(failed)
    else:
        lines.append("No failed checks — the remaining gap to 100 (if any) is rounding.")
    if notes:
        lines.append("")
        lines.append("Notes: " + " ".join(str(n) for n in notes))

    digest = "\n".join(lines)
    if len(digest) > MAX_DIGEST_CHARS:
        digest = digest[:MAX_DIGEST_CHARS] + "\n…(digest truncated)"
    return digest


def scan_agent_sections(
    report: dict[str, Any], max_checks: int = 6
) -> list[tuple[str, list[str]]]:
    """Per-agent (title, body lines) for swarm-style scan rendering.

    Title carries name, score/weight, domain, and fail count; body lists
    failed checks with severity, deduction, remediation, and locations.
    """
    sections: list[tuple[str, list[str]]] = []
    for agent in report.get("agents", []) or []:
        checks = agent.get("checks", []) or []
        failed = [c for c in checks if c.get("status") == "fail"]
        passed = sum(1 for c in checks if c.get("status") == "pass")
        title = "{} {}/{} — {} · {}".format(
            agent.get("name", "?"), agent.get("score", "?"),
            agent.get("weight", "?"), agent.get("domain", ""),
            f"{len(failed)} failed" if failed else "all clear",
        )
        body: list[str] = []
        for check in failed[:max_checks]:
            body.append(
                "[{}] {} (−{} pts): {}".format(
                    check.get("severity", "?"), check.get("name", "?"),
                    check.get("deduction", "?"),
                    check.get("summary", "") or check.get("risk", ""),
                )
            )
            remediation = (check.get("remediation", "") or "").strip()
            if remediation:
                body.append(f"  Fix: {remediation}")
            for finding in (check.get("findings", []) or [])[:2]:
                body.append("  at {}:{}".format(
                    finding.get("path", "."), finding.get("line", 1)))
        if len(failed) > max_checks:
            body.append(f"  …and {len(failed) - max_checks} more failed checks")
        if passed:
            body.append(f"{passed} passed")
        if not body:
            body.append("no checks reported")
        sections.append((title, body))
    return sections


def remember_scan(
    messages: list[Message], report: dict[str, Any], target: str = ""
) -> str:
    """Replace any previous scan digest and append the new one.

    Returns a short human confirmation describing what was attached.
    """
    messages[:] = [
        m for m in messages
        if not ((m.content or "").startswith(SCAN_DIGEST_TAG))
    ]
    digest = build_scan_digest(report, target)
    messages.append(Message(role="user", content=digest))
    score = report.get("score", "?")
    grade = report.get("grade", "?")
    failed = (report.get("counts", {}) or {}).get("fail", "?")
    return (
        f"Findings attached to the conversation — "
        f"{score}/100 (grade {grade}, {failed} failed checks). "
        f'Ask things like "how do I get to 100?" or "why did X fail?"'
    )
