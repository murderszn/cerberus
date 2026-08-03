#!/usr/bin/env python3
"""Validate checks.json and generate assets/checks.js.

Usage: python3 scripts/build-checks.py

Validates:
  - every check id is unique
  - every check's `agent` references a defined agent
  - agent weights sum to 100
  - every regex pattern (detector.pattern / not_match / placeholder_pattern)
    compiles under Python's `re`
  - every regex pattern is ES2018-compatible: rejects Python-only syntax such
    as inline flags `(?i)`, named groups `(?P<name>...)`, and possessive
    quantifiers (`*+`, `++`, `?+`, `{m,n}+`).

Exits non-zero (with messages on stderr) if any check fails.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHECKS_JSON = ROOT / "checks.json"
OUT_JS = ROOT / "assets" / "checks.js"

# Patterns that are valid in Python's `re` but not supported by ES2018
# (i.e. RegExp without the 'u'/'s' flag additions from later specs).
PY_ONLY_SYNTAX = [
    (re.compile(r"\(\?P<"), "named group (?P<name>...) — use (?<name>...) instead"),
    (re.compile(r"\(\?P="), "named backreference (?P=name)"),
    (re.compile(r"\(\?#"), "comment group (?#...)"),
    (re.compile(r"\(\?[aiLmsux]+\)"), "inline flag group e.g. (?i) — pass flags via the `flags` field instead"),
    (re.compile(r"\(\?[aiLmsux]+:"), "inline scoped flag group e.g. (?i:...)"),
    (re.compile(r"[*+?}]\+"), "possessive quantifier (*+, ++, ?+, {m,n}+)"),
    (re.compile(r"\\Z"), r"\Z is Python-only — use $ (with 'm' flag if needed)"),
    (re.compile(r"\\A"), r"\A is Python-only — use ^ (with 'm' flag if needed)"),
]

VALID_KINDS = {"content", "content_required", "path_required", "path_forbidden", "meta"}
VALID_SEVERITIES = {"critical", "high", "medium", "low"}


def fail(msg):
    print(f"ERROR: {msg}", file=sys.stderr)


def check_es2018_compat(pattern, label, errors):
    for rx, desc in PY_ONLY_SYNTAX:
        if rx.search(pattern):
            errors.append(f"{label}: pattern uses Python-only/incompatible syntax: {desc}\n    pattern: {pattern}")


def check_py_compiles(pattern, flags_str, label, errors):
    py_flags = 0
    for f in flags_str or "":
        if f == "i":
            py_flags |= re.IGNORECASE
        elif f == "m":
            py_flags |= re.MULTILINE
        elif f == "s":
            py_flags |= re.DOTALL
        elif f == "g":
            continue  # JS-only, meaningless to Python re
        else:
            errors.append(f"{label}: unknown flag '{f}' in flags field '{flags_str}'")
    try:
        re.compile(pattern, py_flags)
    except re.error as e:
        errors.append(f"{label}: pattern fails to compile in Python re: {e}\n    pattern: {pattern}")



def _validate_no_misplaced_applies_if(catalog):
    """`applies_if` belongs on the check, next to `detector` — never inside it.

    Nesting it under `detector` is silently ignored by both engines, which turns a
    precondition into a failing check (a repo with no package.json getting failed for
    a missing lockfile). This shape is easy to get wrong by hand, so it is a hard error.
    """
    bad = [c["id"] for c in catalog["checks"] if "applies_if" in c.get("detector", {})]
    if bad:
        raise SystemExit(
            "FATAL: applies_if nested under detector for: " + ", ".join(bad) +
            "\n       Move it up one level, alongside 'detector'."
        )


def main():
    errors = []

    if not CHECKS_JSON.exists():
        fail(f"{CHECKS_JSON} not found")
        return 1

    raw = CHECKS_JSON.read_text(encoding="utf-8")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        fail(f"checks.json is not valid JSON: {e}")
        return 1

    agents = data.get("agents", [])
    if not agents:
        errors.append("no `agents` array found")

    agent_ids = set()
    weight_sum = 0
    for a in agents:
        aid = a.get("id")
        if not aid:
            errors.append(f"agent missing id: {a}")
            continue
        if aid in agent_ids:
            errors.append(f"duplicate agent id: {aid}")
        agent_ids.add(aid)
        w = a.get("weight")
        if not isinstance(w, (int, float)):
            errors.append(f"agent {aid} missing numeric weight")
        else:
            weight_sum += w

    if abs(weight_sum - 100) > 0.001:
        errors.append(f"agent weights sum to {weight_sum}, expected 100")

    # placeholder_pattern validation (used globally, must also be valid)
    placeholder_pattern = data.get("placeholder_pattern")
    if placeholder_pattern:
        check_py_compiles(placeholder_pattern, "", "placeholder_pattern", errors)
        check_es2018_compat(placeholder_pattern, "placeholder_pattern", errors)

    checks = data.get("checks", [])
    if not checks:
        errors.append("no `checks` array found")

    seen_ids = set()
    for ch in checks:
        cid = ch.get("id")
        label = f"check {cid or '<missing id>'}"

        if not cid:
            errors.append(f"check missing id: {ch}")
        elif cid in seen_ids:
            errors.append(f"duplicate check id: {cid}")
        else:
            seen_ids.add(cid)

        agent = ch.get("agent")
        if agent not in agent_ids:
            errors.append(f"{label}: agent '{agent}' does not exist in agents[]")

        sev = ch.get("severity")
        if sev not in VALID_SEVERITIES:
            errors.append(f"{label}: invalid severity '{sev}'")

        det = ch.get("detector")
        if not det:
            errors.append(f"{label}: missing detector")
            continue

        kind = det.get("kind")
        if kind not in VALID_KINDS:
            errors.append(f"{label}: invalid detector.kind '{kind}'")

        # Validate every regex-bearing field present on the detector.
        for field in ("pattern", "not_match"):
            pat = det.get(field)
            if pat:
                flags_str = det.get("flags", "") if field == "pattern" else ""
                flabel = f"{label}.detector.{field}"
                check_py_compiles(pat, flags_str, flabel, errors)
                check_es2018_compat(pat, flabel, errors)

        # path_required / path_forbidden must have paths
        if kind in ("path_required", "path_forbidden") and not det.get("paths"):
            errors.append(f"{label}: detector.kind={kind} requires non-empty `paths`")

        if kind == "content_required" and not det.get("paths"):
            errors.append(f"{label}: detector.kind=content_required requires `paths`")

        if kind == "meta" and not det.get("handler"):
            errors.append(f"{label}: detector.kind=meta requires `handler`")

    if errors:
        fail(f"{len(errors)} problem(s) found in checks.json:")
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    OUT_JS.parent.mkdir(parents=True, exist_ok=True)
    header = (
        "// GENERATED FILE — do not hand-edit.\n"
        "// Produced by scripts/build-checks.py from checks.json.\n"
        f"// checks.json version: {data.get('version', 'unknown')}\n"
    )
    body = "window.CERBERUS_CHECKS = " + json.dumps(data, indent=2, ensure_ascii=False) + ";\n"
    OUT_JS.write_text(header + body, encoding="utf-8")

    n_checks = len(checks)
    n_agents = len(agents)
    print(f"OK: wrote {OUT_JS.relative_to(ROOT)} — {n_checks} checks across {n_agents} agents, weights sum to {weight_sum}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
