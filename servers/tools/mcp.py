"""Optional MCP client stub over stdio.

Disabled unless `tools.mcp_servers` lists servers — Cerberus never
auto-installs or downloads servers. Each entry::

    - name: "gh"
      command: "gh"
      args: ["mcp", "call"]      # optional extra argv
      tools: ["issue_read"]      # exposed as mcp_gh_issue_read

Invocation protocol (stub): argv = [command, *args, tool],
JSON-encoded tool arguments on stdin, result text on stdout.
"""

from __future__ import annotations

import json
import subprocess
from subprocess import TimeoutExpired as _TimeoutExpired
from typing import Any

MAX_RESULT_CHARS = 8000


def tool_name(server: str, tool: str) -> str:
    return f"mcp_{server}_{tool}"


def normalize_servers(raw: Any) -> list[dict[str, Any]]:
    """Validate config entries into [{name, command, args, tools}]."""
    servers: list[dict[str, Any]] = []
    if not isinstance(raw, list):
        return servers
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        name = str(entry.get("name", "") or "").strip()
        command = str(entry.get("command", "") or "").strip()
        tools = [str(t) for t in (entry.get("tools") or []) if str(t).strip()]
        if not name or not command or not tools:
            continue
        args = [str(a) for a in (entry.get("args") or [])]
        servers.append({"name": name, "command": command, "args": args, "tools": tools})
    return servers


def invoke(server: dict[str, Any], tool: str, args: Any, *, timeout: int = 30) -> str:
    """Run one MCP tool call. Returns result text or an ERROR string."""
    command = server.get("command", "")
    if not command:
        return "ERROR: MCP server has no command configured."
    argv = [command, *(server.get("args") or []), tool]
    try:
        payload = args if isinstance(args, str) else json.dumps(args or {})
    except (TypeError, ValueError):
        return "ERROR: MCP arguments are not JSON-serializable."
    try:
        proc = subprocess.run(
            argv, input=payload, capture_output=True, text=True, timeout=timeout
        )
    except FileNotFoundError:
        return f"ERROR: MCP command not found: {command} (never auto-installed)"
    except _TimeoutExpired:
        return f"ERROR: MCP tool {tool} timed out."
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()[:500]
        return f"ERROR: MCP tool {tool} failed: {detail}"
    return (proc.stdout or "").strip()[:MAX_RESULT_CHARS] or "(empty MCP result)"
