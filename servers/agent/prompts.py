"""
System prompts and persona builder for Cerberus.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

PERSONAS_DIR = Path(__file__).resolve().parent / "personas"
CHECKS_PATH = Path(__file__).resolve().parent.parent.parent / "checks.json"

CERBERUS_AGENTS = (
    "sentinel",
    "vault",
    "gatekeeper",
    "librarian",
    "conduit",
    "watchtower",
    "shield",
    "auditor",
    "architect",
)


@dataclass
class PersonaDefinition:
    name: str
    title: str
    domain: str
    weight: int
    default_mode: str
    allowed_tools: list[str] = field(default_factory=list)
    markdown_prompt: str = ""


def list_personas() -> list[str]:
    return list(CERBERUS_AGENTS)


def get_persona(agent_name: str, personas_dir: Optional[Path] = None) -> Optional[PersonaDefinition]:
    name = (agent_name or "").strip().lower()
    if name not in CERBERUS_AGENTS:
        return None

    pdir = personas_dir or PERSONAS_DIR
    md_file = pdir / f"{name}.md"
    markdown_prompt = md_file.read_text(encoding="utf-8") if md_file.exists() else ""

    domain_map = {
        "sentinel": ("Code Analysis", 14, "build", ["read_file", "edit_file", "multiedit_file", "search_workspace", "list_symbols", "execute_bash_command", "git_status", "git_diff", "git_log"]),
        "vault": ("Data Security", 13, "plan", ["read_file", "search_workspace", "list_symbols", "git_status", "git_diff", "git_log", "create_pull_request"]),
        "gatekeeper": ("Access Control", 12, "plan", ["read_file", "edit_file", "multiedit_file", "search_workspace", "list_symbols", "git_status", "git_diff", "git_log"]),
        "librarian": ("Dependencies", 12, "build", ["read_file", "edit_file", "multiedit_file", "search_workspace", "execute_bash_command", "browse_web_content", "git_status", "git_diff", "git_log"]),
        "conduit": ("Network & API", 11, "build", ["read_file", "edit_file", "multiedit_file", "search_workspace", "list_symbols", "execute_bash_command", "git_status", "git_diff", "git_log"]),
        "watchtower": ("Application Config", 11, "build", ["read_file", "edit_file", "multiedit_file", "search_workspace", "list_symbols", "execute_bash_command", "git_status", "git_diff", "git_log"]),
        "shield": ("Client Security", 11, "build", ["read_file", "edit_file", "multiedit_file", "search_workspace", "list_symbols", "git_status", "git_diff", "git_log"]),
        "auditor": ("Logging & Monitoring", 8, "build", ["read_file", "edit_file", "multiedit_file", "search_workspace", "list_symbols", "git_status", "git_diff", "git_log"]),
        "architect": ("Infrastructure", 8, "build", ["read_file", "edit_file", "multiedit_file", "search_workspace", "list_symbols", "git_status", "git_diff", "git_log"]),
    }

    domain, weight, default_mode, tools = domain_map.get(
        name, ("Security", 10, "build", ["read_file", "search_workspace", "git_status"])
    )

    return PersonaDefinition(
        name=name,
        title=f"{name.capitalize()} Agent",
        domain=domain,
        weight=weight,
        default_mode=default_mode,
        allowed_tools=tools,
        markdown_prompt=markdown_prompt,
    )


def build_system_prompt(
    agent_name: str,
    mode: str = "build",
    custom_instructions: str = "",
) -> str:
    persona = get_persona(agent_name)
    persona_body = persona.markdown_prompt if persona else ""

    mode_note = (
        "You are operating in BUILD mode: you have full access to edit files and verify changes with tests."
        if mode == "build"
        else "You are operating in PLAN mode: you must NOT mutate any files. Explore, analyze, and formulate a clear remediation plan."
    )

    prompt_parts = [
        "You are Cerberus, an advanced autonomous security engineering agent.",
        mode_note,
        "",
        persona_body,
    ]

    if custom_instructions:
        prompt_parts.extend(["", "## User Custom Directives", custom_instructions])

    return "\n".join(prompt_parts)


def get_orchestrator_prompt(mode: str = "build", custom_instructions: str = "") -> str:
    mode_note = (
        "Operating in BUILD mode. Coordinate check agents, apply fixes, and verify."
        if mode == "build"
        else "Operating in PLAN mode. Audit repository, collect findings, and generate a comprehensive hardening roadmap without file mutations."
    )

    return f"""You are the Cerberus Orchestrator Agent.
Your responsibility is coordinating the 9 specialized Cerberus check-agents:
  - sentinel: backend code vulnerabilities, injection, memory safety
  - gatekeeper: authentication, authorization, access control, session handling
  - vault: secrets management, credential scanning, token rotation
  - librarian: dependencies, supply chain, package manifest updates
  - conduit: network APIs, communication security, transport encryption
  - watchtower: application configuration, debug suppression, secure defaults
  - shield: client security, CSP, HTTP security headers
  - auditor: logging integrity, monitoring, compliance trails
  - architect: system boundaries, infrastructure, Dockerfiles, CI/CD actions

{mode_note}

Guidelines:
1. Always analyze repository structure and findings first.
2. Delegate tasks to the matching persona when delegating.
3. Keep edits surgical and verify against test suites or `examine.py` checks.
4. Redact sensitive values from explanations.
{f'Custom instructions: {custom_instructions}' if custom_instructions else ''}
"""
