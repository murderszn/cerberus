"""Native repository/agent alignment analysis for Cerberus.

This module deliberately does not execute repository content.  It performs bounded,
read-only inspection and returns a report that can be attached to a
``cerberus.report/2`` document without changing the native catalog score.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path


SCHEMA = "cerberus.alignment/1"
MAX_FILE_BYTES = 512 * 1024
MAX_TOTAL_BYTES = 16 * 1024 * 1024
MAX_FILES = 5000

SEVERITY_DEDUCTIONS = {
    "critical": 10.0,
    "high": 5.0,
    "medium": 2.0,
    "low": 1.0,
    "info": 0.0,
}

RULES = {
    "ALIGN-001": ("high", "instruction-conflict", "Conflicting agent instructions",
                  "Reconcile the instructions and designate one authoritative policy."),
    "ALIGN-002": ("high", "security-control", "Instruction weakens validation or security controls",
                  "Require tests and security checks, and document any narrow exception."),
    "ALIGN-003": ("critical", "secret-handling", "Instruction may expose credentials or secrets",
                  "Prohibit printing, returning, committing, or transmitting secret material."),
    "ALIGN-004": ("high", "repository-safety", "Instruction permits destructive repository changes",
                  "Require non-destructive Git operations and explicit human approval for exceptional changes."),
    "ALIGN-005": ("critical", "remote-execution", "Instruction executes downloaded code without verification",
                  "Download a version-pinned artifact, verify its digest/signature, then execute it separately."),
    "ALIGN-006": ("high", "trust-boundary", "Untrusted repository or web content is treated as executable policy",
                  "Treat external and repository-provided text as data; follow only trusted project policy."),
    "ALIGN-007": ("medium", "hidden-instruction", "Suspicious agent instruction is hidden in non-policy content",
                  "Remove hidden directives and place legitimate guidance in a visible agent policy file."),
    "ALIGN-008": ("low", "policy-coverage", "Project-level agent policy is missing",
                  "Add AGENTS.md or another supported project-level agent policy."),
    "ALIGN-009": ("low", "validation-coverage", "Validation commands are not declared",
                  "Document the exact test, lint, build, and security commands agents should run."),
    "ALIGN-010": ("low", "secret-handling", "Secret-handling guidance is missing",
                  "Document that credentials must not be read unnecessarily, printed, committed, or disclosed."),
    "ALIGN-011": ("medium", "command-alignment", "Documented command does not match repository scripts",
                  "Correct the documented command or add the referenced script/target."),
    "ALIGN-012": ("low", "stack-alignment", "Declared technology stack does not match detected files",
                  "Update the stack description or add the expected project files."),
    "ALIGN-013": ("high", "workflow-permissions", "GitHub Actions permissions are overly broad",
                  "Grant only the minimum permissions needed, preferably at job scope."),
    "ALIGN-014": ("medium", "workflow-pinning", "Third-party GitHub Action is not pinned to a commit SHA",
                  "Pin the action to a reviewed full commit SHA and record the human-readable version in a comment."),
    "ALIGN-015": ("critical", "workflow-injection", "Untrusted GitHub context is interpolated into a shell command",
                  "Pass untrusted values through an environment variable and validate them before use."),
    "ALIGN-016": ("medium", "repository-boundary", "Agent instructions permit access outside the repository",
                  "Keep agent access repository-scoped or document the narrow path and justification."),
    "ALIGN-017": ("high", "prompt-injection", "Instruction attempts to override prior or security policy",
                  "Remove instruction-hierarchy overrides and explicitly preserve security policy."),
}

POLICY_BASENAMES = {
    "agents.md", "claude.md", "gemini.md", "team.md", ".cursorrules",
    "copilot-instructions.md", "contributing.md", "readme.md", "security.md",
}
DEDICATED_POLICY_BASENAMES = {
    "agents.md", "claude.md", "gemini.md", "team.md", ".cursorrules",
    "copilot-instructions.md",
}
WORKFLOW_RE = re.compile(r"^\.github/workflows/.+\.ya?ml$", re.I)
SCRIPT_RE = re.compile(r"(^|/)(scripts?|setup)/.*\.(sh|bash|zsh|ps1|py|js)$|(^|/)(makefile|justfile)$", re.I)
PROJECT_MARKERS = {
    "package.json", "pyproject.toml", "setup.py", "requirements.txt", "go.mod",
    "cargo.toml", "pom.xml", "build.gradle", "makefile", "justfile",
}

UNSAFE_CONTEXT_RE = re.compile(
    r"\b(unsafe|dangerous|avoid|example of|detect(?:s|ing)?|"
    r"flags?|prohibit(?:s|ed)?|prevent(?:s|ing)?|instead of)\b", re.I
)
ACTION_CONTEXT_RE = re.compile(
    r"\b(must|should|required|always|please|agent|assistant|model|run|execute|use|install|when|before|after)\b",
    re.I,
)
VALIDATION_RE = re.compile(
    r"(?:python\d*\s+-m\s+(?:unittest|pytest)|pytest\b|npm\s+(?:test|run\s+[\w:-]+)|"
    r"pnpm\s+(?:test|run\s+[\w:-]+)|yarn\s+(?:test|run\s+[\w:-]+)|"
    r"go\s+test\b|cargo\s+test\b|make\s+(?:test|check|lint|build)\b|"
    r"ruff\b|eslint\b|mypy\b)", re.I
)


def _norm(value):
    return " ".join(str(value).split()).lower()


def _fingerprint(rule_id, path, evidence):
    material = "\0".join((rule_id, path.replace("\\", "/"), _norm(evidence)))
    return "sha256:" + hashlib.sha256(material.encode("utf-8")).hexdigest()


def _finding(rule_id, path, line, explanation=None, confidence=0.9, evidence=""):
    severity, category, default_explanation, remediation = RULES[rule_id]
    message = explanation or default_explanation
    fingerprint = _fingerprint(rule_id, path, evidence or default_explanation)
    return {
        "id": fingerprint,
        "ruleId": rule_id,
        "severity": severity,
        "path": path,
        "line": max(1, int(line)),
        "column": 1,
        "message": message,
        "explanation": message,
        "remediation": remediation,
        "confidence": round(float(confidence), 2),
        "category": category,
        "fingerprint": fingerprint,
        "agent": "alignment",
        "source": {"tool": "cerberus-alignment", "rawRuleId": rule_id},
    }


def _repo_files(root):
    paths = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in {".git", "node_modules", ".venv", "venv"})
        for name in sorted(filenames):
            full = Path(dirpath, name)
            try:
                rel = full.relative_to(root).as_posix()
            except ValueError:
                continue
            paths.append(rel)
            if len(paths) >= MAX_FILES:
                return paths
    return paths


def _read_text(root, rel, budget):
    candidate = (root / rel).resolve()
    try:
        candidate.relative_to(root)
        size = candidate.stat().st_size
    except (OSError, ValueError):
        return None
    if size > MAX_FILE_BYTES or size > budget[0]:
        return None
    try:
        raw = candidate.read_bytes()
    except OSError:
        return None
    if b"\x00" in raw[:8192]:
        return None
    budget[0] -= len(raw)
    return raw.decode("utf-8", errors="replace")


def _is_policy_path(rel):
    low = rel.lower()
    name = low.rsplit("/", 1)[-1]
    return (name in POLICY_BASENAMES or low.startswith(".cursor/rules/"))


def _is_dedicated_policy(rel):
    low = rel.lower()
    name = low.rsplit("/", 1)[-1]
    # A generic lowercase team.md commonly describes human team membership (as it
    # does in Cerberus itself).  TEAM.md is the conventional agent-policy surface.
    if name == "team.md" and rel.rsplit("/", 1)[-1] != "TEAM.md":
        return False
    return name in DEDICATED_POLICY_BASENAMES or low.startswith(".cursor/rules/")


def _line_is_actionable(lines, index, dedicated=False):
    line = lines[index]
    nearby = " ".join(lines[max(0, index - 2): index + 1])
    if UNSAFE_CONTEXT_RE.search(nearby):
        return False
    return bool(dedicated or ACTION_CONTEXT_RE.search(nearby))


def _scan_policy(rel, text, findings, positions):
    lines = text.splitlines()
    dedicated = _is_dedicated_policy(rel)
    disabled = re.compile(r"\b(skip|disable|turn off|do not run|don't run|never run|bypass)\b.{0,80}\b(test|tests|lint|scanner|security check|review)\b", re.I)
    expose = re.compile(r"\b(print|log|show|display|return|send|upload|post|commit|paste|share|expose)\b.{0,100}\b(env(?:ironment)?(?: variables?)?|credentials?|secrets?|tokens?|api keys?|passwords?)\b", re.I)
    destructive = re.compile(r"\b(force[- ]?push|git\s+push\s+--force|git\s+reset\s+--hard|delete\s+(?:the\s+)?branch|bypass\s+(?:code\s+)?review|merge\s+without\s+review)\b", re.I)
    remote = re.compile(r"(?:curl|wget)\b[^\n|]{0,300}\|\s*(?:sudo\s+)?(?:sh|bash|zsh)\b", re.I)
    untrusted = re.compile(r"\b(follow|obey|execute|treat)\b.{0,100}\b(issue bod(?:y|ies)|pr comments?|pull request comments?|web pages?|repository content)\b.{0,100}\b(instruction|policy|command|trusted)\b", re.I)
    outside = re.compile(r"\b(access|read|write|modify|search|scan)\b.{0,100}(?:\.\./|~/|/users/|/home/|outside (?:of )?(?:the )?repositor)", re.I)
    injection = re.compile(r"\b(ignore|disregard|override|forget)\b.{0,80}\b(previous|prior|system|developer|security)\b.{0,50}\b(instruction|policy|rules?)\b", re.I)
    patterns = (("ALIGN-002", disabled), ("ALIGN-003", expose), ("ALIGN-004", destructive),
                ("ALIGN-005", remote), ("ALIGN-006", untrusted), ("ALIGN-016", outside),
                ("ALIGN-017", injection))
    for index, line in enumerate(lines):
        if not _line_is_actionable(lines, index, dedicated):
            continue
        for rule_id, pattern in patterns:
            if pattern.search(line):
                # A prohibition of a dangerous operation is protective policy, not
                # an instruction to perform that operation.  Test disabling is the
                # exception: "do not run tests" is itself the unsafe directive.
                if rule_id in {"ALIGN-003", "ALIGN-004", "ALIGN-005", "ALIGN-006", "ALIGN-016"}:
                    if re.search(r"\b(do not|don't|never|must not|should not)\b.{0,100}" + pattern.pattern, line, re.I):
                        continue
                findings.append(_finding(rule_id, rel, index + 1, evidence=pattern.sub("[directive]", line)))
                positions.setdefault(rule_id, []).append((rel, index + 1, line))


def _scan_hidden(rel, text, findings):
    if _is_policy_path(rel):
        return
    low = rel.lower()
    hidden_surface = ("/fixtures/" in "/" + low or "/test" in "/" + low or
                      low.endswith((".svg", ".md", ".html", ".xml")))
    if not hidden_surface:
        return
    marker = re.compile(
        r"(?:<!--|/\*|//|#|<metadata|<desc)[^\n]{0,160}\b(agent|assistant|model)\b[^\n]{0,160}"
        r"\b(ignore|disregard|override|print|expose|force[- ]?push|execute)\b", re.I
    )
    for match in marker.finditer(text):
        line = text.count("\n", 0, match.start()) + 1
        findings.append(_finding("ALIGN-007", rel, line, confidence=0.82, evidence=match.group(0)))


def _workflow_findings(rel, text, findings):
    lines = text.splitlines()
    permission_indent = None
    for index, line in enumerate(lines):
        stripped = line.strip()
        indent = len(line) - len(line.lstrip())
        if re.match(r"permissions\s*:\s*write-all\s*$", stripped, re.I):
            findings.append(_finding("ALIGN-013", rel, index + 1, confidence=0.99, evidence=stripped))
        if re.match(r"permissions\s*:\s*$", stripped, re.I):
            permission_indent = indent
            continue
        if permission_indent is not None:
            if stripped and indent <= permission_indent:
                permission_indent = None
            elif re.match(r"(?:contents|actions|checks|deployments|packages|pull-requests|statuses)\s*:\s*write\s*$", stripped, re.I):
                findings.append(_finding("ALIGN-013", rel, index + 1,
                    explanation="A broadly capable GitHub token permission is writable; verify that this job requires it.",
                    confidence=0.78, evidence=stripped))

        uses = re.search(r"\buses\s*:\s*([^\s#]+)", stripped, re.I)
        if uses:
            action = uses.group(1).strip("'\"")
            if not action.startswith(("./", "docker://")) and "/" in action and "@" in action:
                owner, ref = action.split("@", 1)
                namespace = owner.split("/", 1)[0].lower()
                if namespace not in {"actions", "github"} and not re.fullmatch(r"[0-9a-fA-F]{40}", ref):
                    findings.append(_finding("ALIGN-014", rel, index + 1, evidence=action))

        if re.search(r"\$\{\{\s*github\.event\.(?:issue|pull_request|comment|review|head_commit)\.(?:body|title|message|ref|name)", line, re.I):
            window = "\n".join(lines[max(0, index - 8):index + 1])
            if re.search(r"(?:^|\n)\s*(?:-\s*)?(?:run\s*:|[^#\n]*(?:sh|bash|eval)\b)", window, re.I):
                findings.append(_finding("ALIGN-015", rel, index + 1, confidence=0.98, evidence=line))


def _operational_remote_execution(rel, text, findings):
    if not SCRIPT_RE.search(rel):
        return
    pattern = re.compile(r"(?:curl|wget)\b[^\n|]{0,300}\|\s*(?:sudo\s+)?(?:sh|bash|zsh)\b", re.I)
    for match in pattern.finditer(text):
        line = text.count("\n", 0, match.start()) + 1
        findings.append(_finding("ALIGN-005", rel, line, confidence=0.99, evidence=match.group(0)))


def _package_scripts(text):
    try:
        data = json.loads(text)
    except (TypeError, ValueError):
        return set()
    scripts = data.get("scripts", {}) if isinstance(data, dict) else {}
    return set(scripts) if isinstance(scripts, dict) else set()


def _make_targets(text):
    return {m.group(1) for m in re.finditer(r"^([A-Za-z0-9_.-]+)\s*:(?![=])", text, re.M)}


def _command_mismatches(docs, package_scripts, make_targets, files,
                        package_present=False, make_present=False):
    findings = []
    npm_re = re.compile(
        r"\b(?:npm|pnpm|yarn)\s+(?:run\s+([\w:-]+)|(test|start|build|lint)\b)", re.I
    )
    make_re = re.compile(r"\bmake\s+([\w.-]+)", re.I)
    python_file_re = re.compile(r"\bpython3?\s+([A-Za-z0-9_./-]+\.py)\b", re.I)
    known_files = {f.lower() for f in files}
    for rel, text in docs.items():
        for match in npm_re.finditer(text):
            command = match.group(1) or match.group(2)
            if package_present and command not in package_scripts:
                line = text.count("\n", 0, match.start()) + 1
                findings.append(_finding("ALIGN-011", rel, line,
                    explanation=f"Documentation references package script '{command}', but package.json does not define it.",
                    confidence=0.96, evidence=match.group(0)))
        for match in make_re.finditer(text):
            target = match.group(1)
            if make_present and target not in make_targets:
                line = text.count("\n", 0, match.start()) + 1
                findings.append(_finding("ALIGN-011", rel, line,
                    explanation=f"Documentation references make target '{target}', but the Makefile does not define it.",
                    confidence=0.96, evidence=match.group(0)))
        for match in python_file_re.finditer(text):
            script = os.path.normpath(match.group(1)).replace(os.sep, "/").lstrip("./").lower()
            if script not in known_files and not script.startswith("../"):
                line = text.count("\n", 0, match.start()) + 1
                findings.append(_finding("ALIGN-011", rel, line,
                    explanation=f"Documentation references Python entry point '{script}', but that file was not detected.",
                    confidence=0.94, evidence=match.group(0)))
    return findings


def _stack_mismatches(readme, files):
    findings = []
    if not readme:
        return findings
    evidence = {
        "python": any(f.lower().endswith(".py") or f.lower() in {"pyproject.toml", "requirements.txt"} for f in files),
        "javascript": any(f.lower().endswith((".js", ".mjs", ".cjs")) or f.lower() == "package.json" for f in files),
        "typescript": any(f.lower().endswith((".ts", ".tsx")) or f.lower() == "tsconfig.json" for f in files),
        "go": any(f.lower().endswith(".go") or f.lower() == "go.mod" for f in files),
        "rust": any(f.lower().endswith(".rs") or f.lower() == "cargo.toml" for f in files),
        "java": any(f.lower().endswith(".java") or f.lower() in {"pom.xml", "build.gradle"} for f in files),
    }
    declaration = re.compile(r"(?:built|written|implemented|developed)\s+(?:entirely|exclusively|solely)?\s*(?:in|with|using)\s+(python|javascript|typescript|go|rust|java)\b", re.I)
    for match in declaration.finditer(readme):
        stack = match.group(1).lower()
        if not evidence.get(stack, False):
            line = readme.count("\n", 0, match.start()) + 1
            findings.append(_finding("ALIGN-012", "README.md", line,
                explanation=f"README declares {stack.title()}, but no corresponding source or manifest was detected.",
                confidence=0.88, evidence=match.group(0)))
    return findings


def _conflicts(positions):
    findings = []
    # Unsafe directives conflict with explicit protective language in a different policy file.
    topics = {
        "ALIGN-002": re.compile(r"\b(must|always|required to|do not skip|never skip)\b.{0,80}\b(tests?|lint|scanner|security check|review)\b", re.I),
        "ALIGN-003": re.compile(r"\b(never|must not|do not|don't)\b.{0,80}\b(print|log|show|share|expose)\b.{0,80}\b(secret|token|credential|password|environment variable)\b", re.I),
        "ALIGN-004": re.compile(r"\b(never|must not|do not|don't)\b.{0,80}\b(force[- ]?push|reset\s+--hard|delete\s+(?:the\s+)?branch|bypass\s+(?:code\s+)?review)\b", re.I),
    }
    policy_texts = positions.pop("_policy_texts", {})
    for unsafe_rule, safe_pattern in topics.items():
        for unsafe_path, unsafe_line, unsafe_text in positions.get(unsafe_rule, []):
            for safe_path, safe_text in policy_texts.items():
                if safe_path == unsafe_path:
                    continue
                safe = safe_pattern.search(safe_text)
                if safe:
                    safe_line = safe_text.count("\n", 0, safe.start()) + 1
                    explanation = f"Instruction conflicts with protective guidance in {safe_path}:{safe_line}."
                    findings.append(_finding("ALIGN-001", unsafe_path, unsafe_line,
                        explanation=explanation, confidence=0.94, evidence=unsafe_text + "|" + safe.group(0)))
                    break
    return findings


def analyze_alignment(root_dir):
    """Analyze *root_dir* and return a deterministic ``cerberus.alignment/1`` dict."""
    root = Path(root_dir).resolve()
    if not root.is_dir():
        raise ValueError("alignment target must be an existing directory")

    files = _repo_files(root)
    budget = [MAX_TOTAL_BYTES]
    texts = {}
    for rel in files:
        text = _read_text(root, rel, budget)
        if text is not None:
            texts[rel] = text

    findings = []
    positions = {"_policy_texts": {}}
    docs = {}
    dedicated_policies = []
    for rel, text in texts.items():
        low = rel.lower()
        if _is_policy_path(rel):
            _scan_policy(rel, text, findings, positions)
            positions["_policy_texts"][rel] = text
            docs[rel] = text
            if _is_dedicated_policy(rel):
                dedicated_policies.append(rel)
        if WORKFLOW_RE.match(rel):
            _workflow_findings(rel, text, findings)
        _operational_remote_execution(rel, text, findings)
        _scan_hidden(rel, text, findings)

    findings.extend(_conflicts(positions))

    if not dedicated_policies:
        findings.append(_finding("ALIGN-008", ".", 1, confidence=1.0, evidence="missing-agent-policy"))

    project_like = any(f.lower().rsplit("/", 1)[-1] in PROJECT_MARKERS for f in files)
    policy_blob = "\n".join(docs.values())
    if project_like and not VALIDATION_RE.search(policy_blob):
        findings.append(_finding("ALIGN-009", ".", 1, confidence=0.92, evidence="missing-validation-guidance"))

    secret_guidance = re.compile(
        r"\b(do not|don't|never|must not|avoid)\b.{0,100}\b(print|log|commit|share|expose|disclose|store)\b.{0,100}\b(secret|token|credential|password|api key)", re.I
    )
    if dedicated_policies and not secret_guidance.search(policy_blob):
        findings.append(_finding("ALIGN-010", dedicated_policies[0], 1, confidence=0.9,
                                 evidence="missing-secret-guidance"))

    package_key = next((k for k in texts if k.lower() == "package.json"), None)
    package_scripts = _package_scripts(texts[package_key]) if package_key else set()
    make_key = next((k for k in texts if k.lower() == "makefile"), None)
    make_text = texts.get(make_key, "") if make_key else ""
    findings.extend(_command_mismatches(
        docs, package_scripts, _make_targets(make_text), files,
        package_present=package_key is not None, make_present=make_key is not None,
    ))
    readme_key = next((k for k in texts if k.lower() == "readme.md"), None)
    findings.extend(_stack_mismatches(texts.get(readme_key) if readme_key else None, files))

    # De-duplicate exact logical findings while retaining deterministic ordering.
    unique = {}
    for finding in findings:
        key = finding["fingerprint"]
        unique.setdefault(key, finding)
    findings = sorted(unique.values(), key=lambda f: (f["path"], f["line"], f["ruleId"], f["fingerprint"]))

    counts = {severity: 0 for severity in SEVERITY_DEDUCTIONS}
    for finding in findings:
        counts[finding["severity"]] += 1
    score = max(0.0, round(100.0 - sum(SEVERITY_DEDUCTIONS[f["severity"]] for f in findings), 1))
    grade = "A" if score >= 90 else "B" if score >= 80 else "C" if score >= 70 else "D" if score >= 60 else "F"
    return {
        "schema": SCHEMA,
        "version": "1",
        "agent": {"id": "alignment", "name": "ALIGNMENT", "domain": "Repository & Agent Alignment"},
        "status": "completed",
        "score": score,
        "grade": grade,
        "counts": counts,
        "findings": findings,
        "filesInspected": len(texts),
        "filesSkipped": len(files) - len(texts),
        "truncated": len(files) >= MAX_FILES or budget[0] <= 0,
    }
