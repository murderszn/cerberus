"""
Cerberus Multi-Agent Swarm Coordinator.

Coordinates the 9 specialized Cerberus personas:
  - sentinel, vault, gatekeeper, librarian, conduit,
  - watchtower, shield, auditor, architect

Provides:
  1. Isolated subagent thread delegation with role-restricted tool registries
  2. Concurrent map-reduce fanout across personas
  3. Goal classification and check-agent routing
  4. Deduplication of findings and scan verification integration
"""

from __future__ import annotations

import concurrent.futures
import hashlib
import json
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

from servers.agent.loop import AgentLoop, LoopResult
from servers.agent.prompts import CERBERUS_AGENTS, get_persona
from servers.config import AppConfig, ToolConfig
from servers.logging_setup import get_logger
from servers.models import ToolParameter, ToolSpec
from servers.provider.client import OpenAICompatibleClient
from servers.tools.registry import ToolRegistry

log = get_logger("swarm")


@dataclass
class SwarmReport:
    agent: str
    task: str
    summary: str
    status: str  # "completed" | "error" | "circuit_breaker"
    duration_seconds: float
    tool_rounds: int
    findings: list[dict[str, Any]] = field(default_factory=list)


class CerberusSwarm:
    def __init__(self, config: AppConfig, client: OpenAICompatibleClient):
        self.config = config
        self.client = client
        self.workspace = config.workspace

    def delegate(
        self,
        agent_name: str,
        task: str,
        *,
        context: str = "",
        max_rounds: Optional[int] = None,
        mode: Optional[str] = None,
        on_status: Optional[Callable[[str], None]] = None,
    ) -> SwarmReport:
        agent_key = (agent_name or "").strip().lower()
        if agent_key not in CERBERUS_AGENTS:
            return SwarmReport(
                agent=agent_key,
                task=task,
                summary=f"ERROR: Unknown Cerberus agent: {agent_name}. Must be one of: {', '.join(CERBERUS_AGENTS)}",
                status="error",
                duration_seconds=0.0,
                tool_rounds=0,
            )

        policy = self.config.policy_for(agent_key)
        exec_mode = mode or policy.default_mode or self.config.agent_mode
        rounds_limit = max_rounds or policy.max_rounds or 32

        # Create isolated subagent tool registry
        sub_tool_cfg = ToolConfig(
            bash_timeout=self.config.tools.bash_timeout,
            max_tool_rounds=rounds_limit,
            enforce_workspace_boundary=self.config.tools.enforce_workspace_boundary,
            enforce_cerberusignore=self.config.tools.enforce_cerberusignore,
            redact_secrets_in_output=self.config.tools.redact_secrets_in_output,
        )

        sub_registry = ToolRegistry(
            workspace=self.workspace,
            config=sub_tool_cfg,
            mode=exec_mode,
            allowed_tools=policy.allowed_tools,
        )

        sub_loop = AgentLoop(
            config=self.config,
            client=self.client,
            registry=sub_registry,
            persona_name=agent_key,
            on_status=on_status,
        )

        prompt = task
        if context:
            prompt = f"Context:\n{context}\n\nTask for {agent_key.upper()}:\n{task}"

        t0 = time.monotonic()
        try:
            result = sub_loop.run(prompt)
            duration = time.monotonic() - t0
            return SwarmReport(
                agent=agent_key,
                task=task,
                summary=result.final_text,
                status=result.stopped_reason,
                duration_seconds=duration,
                tool_rounds=result.tool_rounds,
            )
        except Exception as exc:
            duration = time.monotonic() - t0
            log.exception("Persona delegation failed for %s", agent_key)
            return SwarmReport(
                agent=agent_key,
                task=task,
                summary=f"ERROR during execution: {exc}",
                status="error",
                duration_seconds=duration,
                tool_rounds=0,
            )

    def fan_out(
        self,
        tasks: list[tuple[str, str]],
        *,
        context: str = "",
        max_workers: int = 4,
    ) -> list[SwarmReport]:
        """Run multiple persona tasks concurrently in isolated threads."""
        reports: list[SwarmReport] = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(self.delegate, agent, task, context=context)
                for agent, task in tasks
            ]
            for f in concurrent.futures.as_completed(futures):
                try:
                    reports.append(f.result())
                except Exception as exc:
                    reports.append(
                        SwarmReport(
                            agent="unknown",
                            task="batch",
                            summary=f"Batch thread error: {exc}",
                            status="error",
                            duration_seconds=0.0,
                            tool_rounds=0,
                        )
                    )
        return reports

    def classify_goal(self, goal: str) -> list[str]:
        """Heuristically identify the most relevant Cerberus personas for a goal."""
        g = (goal or "").lower()
        matched = set()

        keywords = {
            "vault": ["secret", "credential", "api_key", "token", "password", "leak", "env", "v-01", "v-02"],
            "gatekeeper": ["auth", "login", "jwt", "session", "permission", "rbac", "access", "oauth", "g-01"],
            "sentinel": ["sqli", "injection", "xss", "ssrf", "overflow", "sanitize", "vulnerability", "cwe", "s-01"],
            "librarian": ["dependency", "cve", "package", "npm", "pip", "requirements", "upgrade", "outdated", "l-01"],
            "conduit": ["network", "cors", "api", "rest", "endpoint", "tls", "https", "webhook", "c-01"],
            "watchtower": ["debug", "config", "cookie", "setting", "env", "logging", "w-01"],
            "shield": ["header", "csp", "clickjacking", "hsts", "f-01"],
            "auditor": ["audit", "log", "compliance", "trail", "a-01"],
            "architect": ["docker", "ci", "action", "workflow", "infra", "architecture", "r-01"],
        }

        for agent, words in keywords.items():
            if any(w in g for w in words):
                matched.add(agent)

        if not matched:
            # Default to sentinel and architect
            return ["sentinel"]
        return sorted(matched)

    def verify_with_scanner(self, only_agent: Optional[str] = None) -> dict[str, Any]:
        """Run examine.py in the workspace to verify fixes without modifying score rules."""
        examine_path = Path(__file__).resolve().parent.parent.parent / "examine.py"
        if not examine_path.exists():
            return {"error": "examine.py not found"}

        cmd = ["python3", str(examine_path), str(self.workspace), "--json-stdout"]
        if only_agent:
            cmd.extend(["--only", only_agent])

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
            if proc.returncode == 0 and proc.stdout.strip():
                try:
                    return json.loads(proc.stdout)
                except Exception:
                    pass
            return {"stdout": proc.stdout[:1000], "stderr": proc.stderr[:1000], "exit": proc.returncode}
        except Exception as exc:
            return {"error": str(exc)}

    def register_swarm_tool(self, registry: ToolRegistry) -> None:
        """Register the `delegate_persona` tool into an orchestrator registry."""
        registry.register(
            ToolSpec(
                name="delegate_persona",
                description=(
                    "Delegate a task to one of the 9 Cerberus check-agents "
                    "(sentinel, vault, gatekeeper, librarian, conduit, watchtower, shield, auditor, architect) "
                    "running with its specialized policy and toolbelt."
                ),
                parameters=[
                    ToolParameter("persona", "string", "Persona name: sentinel, vault, gatekeeper, librarian, conduit, watchtower, shield, auditor, architect."),
                    ToolParameter("task", "string", "Specific task instruction for the persona."),
                    ToolParameter("context", "string", "Background context or relevant file paths.", required=False),
                    ToolParameter("max_rounds", "integer", "Tool budget for this subtask (default 24).", required=False),
                ],
                handler=lambda persona, task, context="", max_rounds=24: (
                    f"[{persona.upper()} REPORT]\n"
                    f"Status: {self.delegate(persona, task, context=context, max_rounds=int(max_rounds or 24)).status}\n"
                    f"Summary:\n{self.delegate(persona, task, context=context, max_rounds=int(max_rounds or 24)).summary}"
                ),
            )
        )
