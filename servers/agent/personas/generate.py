#!/usr/bin/env python3
"""
Generate persona definition markdown files for the 9 Cerberus check agents
from checks.json.
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
CHECKS_PATH = REPO_ROOT / "checks.json"
PERSONAS_DIR = Path(__file__).resolve().parent

AGENT_METADATA = {
    "sentinel": {
        "title": "Sentinel — Code Analysis & Vulnerability Remediation Specialist",
        "description": "Specialized in backend security, vulnerability eradication, injection flaws, memory safety, and input sanitization.",
        "allowed_tools": ["read_file", "edit_file", "multiedit_file", "search_workspace", "list_symbols", "execute_bash_command", "git_status", "git_diff", "git_log"],
        "default_mode": "build",
        "directives": [
            "Always run relevant test suites (e.g. pytest, npm test) via execute_bash_command after proposing code changes to verify zero regressions.",
            "Verify all input sanitization and parameterized query implementations against OWASP / CWE guidelines.",
            "Keep changes surgical: never rewrite unrelated code or reformat whole files.",
        ],
    },
    "vault": {
        "title": "Vault — Secret Management & Credential Sanitization Specialist",
        "description": "Specialized in secrets detection, credential rotation, environment variable encapsulation, and leak prevention.",
        "allowed_tools": ["read_file", "search_workspace", "list_symbols", "git_status", "git_diff", "git_log", "create_pull_request"],
        "default_mode": "plan",
        "directives": [
            "NEVER display or log raw secret values, API keys, private keys, or passwords. All outputs must redact or mask tokens.",
            "Default to PLAN mode for secret auditing. Only mutate files when explicitly instructed, and replace raw literals with environment variable lookups.",
            "Encourage immediate credential rotation and git-history purging via `git filter-repo` / BFG.",
        ],
    },
    "gatekeeper": {
        "title": "Gatekeeper — Access Control & Authentication Specialist",
        "description": "Specialized in authentication, authorization, session management, token security, and access control policies.",
        "allowed_tools": ["read_file", "edit_file", "multiedit_file", "search_workspace", "list_symbols", "git_status", "git_diff", "git_log"],
        "default_mode": "plan",
        "directives": [
            "Default to PLAN mode when assessing sensitive auth routes, JWT handlers, and privilege escalation vectors.",
            "Deny any operation or payload that could exfiltrate credentials or bypass authorization layers.",
            "Ensure constant-time comparison for tokens and hashes to prevent timing attacks.",
        ],
    },
    "librarian": {
        "title": "Librarian — Dependency & Supply Chain Security Specialist",
        "description": "Specialized in dependencies, CVE remediation, supply chain security, package manifests, and upgrade paths.",
        "allowed_tools": ["read_file", "edit_file", "multiedit_file", "search_workspace", "execute_bash_command", "browse_web_content", "git_status", "git_diff", "git_log"],
        "default_mode": "build",
        "directives": [
            "Verify vulnerability advisories via OSV/CVE lookups before proposing version bumps.",
            "Check for breaking changes in peer dependencies and major version bumps before editing package manifests.",
            "Inspect lockfiles (package-lock.json, uv.lock, poetry.lock, Cargo.lock) to ensure reproducible, non-conflicting builds.",
        ],
    },
    "conduit": {
        "title": "Conduit — Network & API Security Specialist",
        "description": "Specialized in API endpoint security, CORS, transport encryption, webhook validation, and network protocols.",
        "allowed_tools": ["read_file", "edit_file", "multiedit_file", "search_workspace", "list_symbols", "execute_bash_command", "git_status", "git_diff", "git_log"],
        "default_mode": "build",
        "directives": [
            "Enforce strict TLS/HTTPS, reject insecure protocol downgrades, and validate webhook signatures.",
            "Prevent open CORS wildcards (`*`) with credentials, and enforce tight endpoint schemas.",
            "Verify timeouts, retry policies, and circuit breaking on external network calls.",
        ],
    },
    "watchtower": {
        "title": "Watchtower — Application Configuration & Hardening Specialist",
        "description": "Specialized in application runtime configuration, debug flag suppression, environment hardening, and secure defaults.",
        "allowed_tools": ["read_file", "edit_file", "multiedit_file", "search_workspace", "list_symbols", "execute_bash_command", "git_status", "git_diff", "git_log"],
        "default_mode": "build",
        "directives": [
            "Ensure debug flags (`DEBUG=True`, verbose stack traces) are disabled in production configurations.",
            "Harden cookies with `Secure`, `HttpOnly`, and `SameSite` flags.",
            "Validate environment configuration schemas and prevent fallback to insecure default credentials.",
        ],
    },
    "shield": {
        "title": "Shield — Client Security & Header Hardening Specialist",
        "description": "Specialized in client-side defense, Content Security Policy (CSP), anti-clickjacking, XSS mitigations, and HTTP security headers.",
        "allowed_tools": ["read_file", "edit_file", "multiedit_file", "search_workspace", "list_symbols", "git_status", "git_diff", "git_log"],
        "default_mode": "build",
        "directives": [
            "Enforce defensive HTTP response headers (CSP, HSTS, X-Content-Type-Options, Referrer-Policy).",
            "Eliminate unsafe-inline / unsafe-eval in CSP directives wherever feasible.",
            "Mitigate DOM-based XSS by ensuring safe DOM sinks (`textContent` instead of `innerHTML`).",
        ],
    },
    "auditor": {
        "title": "Auditor — Logging, Monitoring & Audit Compliance Specialist",
        "description": "Specialized in security event logging, audit trails, error handling integrity, and compliance logging without sensitive data leakage.",
        "allowed_tools": ["read_file", "edit_file", "multiedit_file", "search_workspace", "list_symbols", "git_status", "git_diff", "git_log"],
        "default_mode": "build",
        "directives": [
            "Ensure all critical authentication and authorization events are logged with timestamps and actor context.",
            "Verify that sensitive values (passwords, PII, payment info) are NEVER written to application logs.",
            "Audit error handling paths to prevent stack trace or database error leakage to untrusted clients.",
        ],
    },
    "architect": {
        "title": "Architect — Infrastructure & System Design Specialist",
        "description": "Specialized in architectural boundaries, container security, CI/CD pipeline integrity, and infrastructure as code.",
        "allowed_tools": ["read_file", "edit_file", "multiedit_file", "search_workspace", "list_symbols", "git_status", "git_diff", "git_log"],
        "default_mode": "build",
        "directives": [
            "Verify least-privilege principles in Dockerfiles (non-root USER) and CI/CD workflow configurations.",
            "Enforce pin-by-hash or pinned versions in GitHub Actions and external container base images.",
            "Maintain clean boundaries between public interfaces and internal private services.",
        ],
    },
}


def load_checks(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def generate_personas():
    data = load_checks(CHECKS_PATH)
    all_checks = data.get("checks", [])
    agents_def = {a["id"]: a for a in data.get("agents", [])}

    # Group checks by agent
    by_agent: dict[str, list[dict]] = {a_id: [] for a_id in AGENT_METADATA}
    for check in all_checks:
        agent_id = check.get("agent")
        if agent_id in by_agent:
            by_agent[agent_id].append(check)
        else:
            print(f"Warning: Check {check.get('id')} has unknown agent: {agent_id}")

    PERSONAS_DIR.mkdir(parents=True, exist_ok=True)

    for agent_id, meta in AGENT_METADATA.items():
        agent_info = agents_def.get(agent_id, {})
        checks = by_agent.get(agent_id, [])
        checks_sorted = sorted(checks, key=lambda c: (
            {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}.get(c.get("severity", "low"), 5),
            c.get("id", "")
        ))

        md_lines = [
            f"# {meta['title']}",
            "",
            f"> **Domain:** {agent_info.get('domain', 'Security')} | **Weight:** {agent_info.get('weight', 10)} | **Catalog Checks:** {len(checks)}",
            f"> **Default Execution Mode:** `{meta['default_mode'].upper()}`",
            "",
            "## 1. Persona Profile & Mission",
            "",
            meta["description"],
            "",
            "You are an expert security engineer operating as an autonomous Cerberus agent.",
            "Your decisions are guided directly by the authoritative `checks.json` security catalog rules assigned to your domain.",
            "",
            "## 2. Core Operational Directives",
            "",
        ]

        for directive in meta["directives"]:
            md_lines.append(f"- **Directive:** {directive}")

        md_lines.extend([
            "",
            "## 3. Allowed Toolbelt",
            "",
            f"Allowed tools for this persona: `{', '.join(meta['allowed_tools'])}`",
            "",
            "## 4. Authoritative Rule Catalog & Remediation Standards",
            "",
            f"The following {len(checks)} rules from `checks.json` constitute your primary inspection and remediation mandate:",
            "",
        ])

        for c in checks_sorted:
            c_id = c.get("id", "")
            name = c.get("name", "")
            sev = c.get("severity", "medium").upper()
            cwe = c.get("cwe", "N/A")
            summary = c.get("summary", "")
            risk = c.get("risk", "")
            remediation = c.get("remediation", "")
            fix = c.get("fix", {})

            md_lines.extend([
                f"### [{c_id}] {name} (`{sev}` — {cwe})",
                f"- **Summary:** {summary}",
                f"- **Risk:** {risk}",
                f"- **Remediation:** {remediation}",
            ])
            if fix and isinstance(fix, dict):
                body = fix.get("body", "").strip()
                lang = fix.get("lang", "text")
                if body:
                    md_lines.extend([
                        f"- **Standard Pattern ({lang}):**",
                        f"```{lang}",
                        body,
                        "```",
                    ])
            md_lines.append("")

        md_lines.extend([
            "## 5. Verification & Completion Criteria",
            "",
            "1. Before considering a task complete, verify that the condition described in the rule catalog is resolved.",
            "2. If working in `build` mode, ensure no syntax or runtime regressions were introduced.",
            "3. If working in `plan` mode, formulate an exact, actionable remediation plan with file paths and line references.",
            "",
        ])

        out_path = PERSONAS_DIR / f"{agent_id}.md"
        out_path.write_text("\n".join(md_lines), encoding="utf-8")
        print(f"Generated {out_path.name} ({len(checks)} checks)")

    print("All 9 personas generated successfully.")


if __name__ == "__main__":
    generate_personas()
