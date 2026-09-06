"""
Central tool registry for Cerberus.

Supports:
  - `build` vs `plan` (read-only) mode
  - Persona-level tool filtering (restricting available tools per agent)
  - Parameter validation and execution dispatch
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Iterable, Optional, Set, Tuple

from servers.config import ToolConfig
from servers.logging_setup import get_logger
from servers.models import ToolParameter, ToolSpec
from servers.tools.bash import run_bash
from servers.tools.edit import edit_file
from servers.tools.files import glob_files, list_directory, read_file, write_file
from servers.tools.git import git_branch, git_diff, git_log, git_status
from servers.tools.inspect import file_tree, http_request, python_eval
from servers.tools.multiedit import multi_edit_file
from servers.tools.pr import create_pull_request
from servers.tools.safety import is_build_command
from servers.tools.search import grep_search, search_workspace
from servers.tools.symbols import list_symbols
from servers.tools.web import browse_web_content

log = get_logger("tools.registry")

READ_ONLY_TOOLS = {
    "read_file",
    "view_workspace_file",
    "search_workspace",
    "grep_search",
    "list_symbols",
    "view_outline",
    "list_directory",
    "glob_files",
    "file_tree",
    "http_request",
    "git_status",
    "git_diff",
    "git_log",
    "git_branch",
    "browse_web_content",
}

#: Tools that leave the workspace (network/API) — gated when
#: ToolConfig.approve_external is on, in any mode.
EXTERNAL_APPROVAL_TOOLS = {
    "browse_web_content",
    "http_request",
    "create_pull_request",
}


class ToolRegistry:
    def __init__(
        self,
        workspace: Path,
        config: Optional[ToolConfig] = None,
        *,
        mode: str = "build",
        allowed_tools: Optional[Iterable[str]] = None,
        confirm_callback: Optional[Callable[[str, str], bool]] = None,
    ):
        self.workspace = Path(workspace).resolve()
        self.config = config or ToolConfig()
        self.mode = (mode or "build").lower()
        self.allowed_tools: Optional[Set[str]] = set(allowed_tools) if allowed_tools is not None else None
        self.confirm_callback = confirm_callback
        self._tools: dict[str, ToolSpec] = {}
        self._session_allowed: Set[str] = set()

        self._register_default_tools()

    def reset_session_approvals(self) -> None:
        """Forget 'always allow this session' choices (/approvals reset)."""
        self._session_allowed.clear()

    def session_approvals(self) -> list[str]:
        """Kinds currently always-allowed for this session."""
        return sorted(self._session_allowed)

    def _ask_approval(self, kind: str, command: str, reason: str) -> bool:
        """Tri-state approval: True/'once' runs once, 'session' remembers kind."""
        if kind in self._session_allowed:
            return True
        callback = self.confirm_callback
        if callback is None:
            log.warning("approval needed but no confirm callback: %s", command[:120])
            return False
        try:
            decision = callback(command, reason)
        except Exception:
            log.exception("approval callback failed")
            return False
        if decision == "session":
            self._session_allowed.add(kind)
            return True
        return bool(decision) and decision != "deny"

    def _approval_gate(self, name: str, args: dict[str, Any]) -> Optional[Tuple[str, str, str]]:
        """Return (kind, command, reason) when this call needs approval."""
        if name in EXTERNAL_APPROVAL_TOOLS and self.config.approve_external:
            return (
                f"external:{name}",
                name,
                f"External action `{name}` leaves the workspace (network/API call).",
            )
        if name == "execute_bash_command" and self.config.approve_builds:
            command = str((args or {}).get("command", ""))
            if is_build_command(command):
                return (
                    "build",
                    command,
                    "Build/test/install command — can take a while and use network.",
                )
        return None

    def register(self, spec: ToolSpec) -> None:
        self._tools[spec.name] = spec

    def get(self, name: str) -> Optional[ToolSpec]:
        return self._tools.get(name)

    def is_tool_allowed(self, name: str) -> bool:
        if self.mode == "plan" and name not in READ_ONLY_TOOLS:
            return False
        if self.allowed_tools is not None and name not in self.allowed_tools:
            return False
        return True

    def list_names(self) -> list[str]:
        return [name for name in sorted(self._tools.keys()) if self.is_tool_allowed(name)]

    def openai_tools(self) -> list[dict[str, Any]]:
        """Return OpenAI function schemas for all currently active/allowed tools."""
        out = []
        for name in sorted(self._tools.keys()):
            if self.is_tool_allowed(name):
                out.append(self._tools[name].openai_schema())
        return out

    def dispatch(self, name: str, args: dict[str, Any]) -> str:
        """Invoke a tool by name with arguments dict."""
        if name not in self._tools:
            return f"ERROR: unknown tool: {name}"

        if not self.is_tool_allowed(name):
            if self.mode == "plan" and name not in READ_ONLY_TOOLS:
                return (
                    f"BLOCKED: Tool '{name}' modifies files or environment, but agent is in PLAN mode.\n"
                    "Formulate a plan or recommendation instead of applying mutations directly."
                )
            return f"BLOCKED: Tool '{name}' is not permitted for this persona."

        gate = self._approval_gate(name, args)
        if gate is not None:
            kind, command, reason = gate
            if not self._ask_approval(kind, command, reason):
                return (
                    f"BLOCKED: `{command}` needs user approval and was not approved.\n"
                    f"{reason}\n"
                    "Tell the user what you wanted to do and why, then wait — "
                    "they can approve it or relax the policy with /approvals."
                )

        spec = self._tools[name]
        try:
            return spec.invoke(**args)
        except Exception as exc:
            log.exception("Tool execution failed: %s with args %s", name, args)
            return f"ERROR executing {name}: {exc}"

    def _register_default_tools(self) -> None:
        ws = self.workspace
        enforce_bound = self.config.enforce_workspace_boundary
        enforce_ignore = self.config.enforce_cerberusignore
        bash_to = self.config.bash_timeout
        extra_pat = self.config.extra_destructive_patterns
        confirm = self.confirm_callback

        # 1. read_file
        self.register(
            ToolSpec(
                name="read_file",
                description="Read a file from workspace with line pagination (offset/limit).",
                parameters=[
                    ToolParameter("path", "string", "Relative or absolute path to the file."),
                    ToolParameter("offset", "integer", "1-based line offset to start reading from (default: 1).", required=False),
                    ToolParameter("limit", "integer", "Maximum number of lines to read (default: 400).", required=False),
                ],
                handler=lambda path, offset=1, limit=400: read_file(
                    path, workspace=ws, enforce_boundary=enforce_bound, offset=offset, limit=limit
                ),
            )
        )

        # 2. write_file
        self.register(
            ToolSpec(
                name="write_file",
                description="Create or overwrite a file in the workspace.",
                parameters=[
                    ToolParameter("path", "string", "Relative path to the file."),
                    ToolParameter("content", "string", "Full text content to write."),
                ],
                handler=lambda path, content="": write_file(
                    path, content, workspace=ws, enforce_boundary=enforce_bound, enforce_cerberusignore=enforce_ignore
                ),
            )
        )

        # 3. edit_file
        self.register(
            ToolSpec(
                name="edit_file",
                description="Surgically replace an exact string in a file.",
                parameters=[
                    ToolParameter("path", "string", "Path to file."),
                    ToolParameter("old_string", "string", "Exact string to replace."),
                    ToolParameter("new_string", "string", "Replacement string."),
                    ToolParameter("replace_all", "boolean", "Replace all matches (default false).", required=False),
                ],
                handler=lambda path, old_string, new_string, replace_all=False: edit_file(
                    path, old_string, new_string, workspace=ws, enforce_boundary=enforce_bound, enforce_cerberusignore=enforce_ignore, replace_all=replace_all
                ),
            )
        )

        # 4. multiedit_file
        self.register(
            ToolSpec(
                name="multiedit_file",
                description="Apply multiple string replacements to a file atomically.",
                parameters=[
                    ToolParameter("path", "string", "Path to file."),
                    ToolParameter("replacements", "string", "JSON list of {old_string, new_string, replace_all} objects."),
                ],
                handler=lambda path, replacements: multi_edit_file(
                    path, replacements, workspace=ws, enforce_boundary=enforce_bound, enforce_cerberusignore=enforce_ignore
                ),
            )
        )

        # 5. search_workspace
        self.register(
            ToolSpec(
                name="search_workspace",
                description="Search workspace files using ripgrep/regex with secret redaction.",
                parameters=[
                    ToolParameter("pattern", "string", "Search pattern or regex."),
                    ToolParameter("path", "string", "Directory path to search in (default: .)", required=False),
                    ToolParameter("glob", "string", "Glob filter for filenames (e.g. *.py)", required=False),
                    ToolParameter("case_insensitive", "boolean", "Case-insensitive matching", required=False),
                ],
                handler=lambda pattern, path=".", glob="", case_insensitive=False: search_workspace(
                    pattern, workspace=ws, path=path, glob=glob, case_insensitive=case_insensitive
                ),
            )
        )

        # 6. list_symbols
        self.register(
            ToolSpec(
                name="list_symbols",
                description="Extract symbol outline (functions, classes, imports) from a file.",
                parameters=[
                    ToolParameter("path", "string", "Path to code file."),
                ],
                handler=lambda path: list_symbols(path, workspace=ws, enforce_boundary=enforce_bound),
            )
        )

        # 7. list_directory
        self.register(
            ToolSpec(
                name="list_directory",
                description="List directory contents with file types and sizes.",
                parameters=[
                    ToolParameter("path", "string", "Path to directory (default: .)", required=False),
                ],
                handler=lambda path=".": list_directory(path, workspace=ws, enforce_boundary=enforce_bound),
            )
        )

        # 8. glob_files
        self.register(
            ToolSpec(
                name="glob_files",
                description="Find files matching a glob pattern.",
                parameters=[
                    ToolParameter("pattern", "string", "Glob pattern (e.g. **/*.ts, src/*)"),
                    ToolParameter("path", "string", "Directory to search from (default: .)", required=False),
                ],
                handler=lambda pattern, path=".": glob_files(pattern, path, workspace=ws, enforce_boundary=enforce_bound),
            )
        )

        # 9. execute_bash_command
        self.register(
            ToolSpec(
                name="execute_bash_command",
                description="Execute a bash command with safety check, timeout, and secret redaction.",
                parameters=[
                    ToolParameter("command", "string", "Bash command to execute."),
                    ToolParameter("timeout", "integer", "Execution timeout in seconds.", required=False),
                ],
                handler=lambda command, timeout=None: run_bash(
                    command,
                    timeout=timeout or bash_to,
                    cwd=str(ws),
                    confirm=confirm,
                    extra_destructive_patterns=extra_pat,
                ),
            )
        )

        # 10. git_status
        self.register(
            ToolSpec(
                name="git_status",
                description="Show git status of the workspace.",
                parameters=[
                    ToolParameter("short", "boolean", "Short status format.", required=False),
                ],
                handler=lambda short=False: git_status(ws, short=short),
            )
        )

        # 11. git_diff
        self.register(
            ToolSpec(
                name="git_diff",
                description="Show git diff of unstaged or staged changes with secret redaction.",
                parameters=[
                    ToolParameter("staged", "boolean", "View staged changes.", required=False),
                    ToolParameter("path", "string", "Specific file path.", required=False),
                ],
                handler=lambda staged=False, path="": git_diff(ws, staged=staged, path=path),
            )
        )

        # 12. git_log
        self.register(
            ToolSpec(
                name="git_log",
                description="Show recent git commit history.",
                parameters=[
                    ToolParameter("n", "integer", "Number of commits (default 10).", required=False),
                    ToolParameter("oneline", "boolean", "Compact single-line format.", required=False),
                ],
                handler=lambda n=10, oneline=True: git_log(ws, n=n, oneline=oneline),
            )
        )

        # 13. git_branch
        self.register(
            ToolSpec(
                name="git_branch",
                description="List git branches in workspace.",
                parameters=[],
                handler=lambda: git_branch(ws),
            )
        )

        # 14. create_pull_request
        self.register(
            ToolSpec(
                name="create_pull_request",
                description="Create a branch, commit changes, push, and open a GitHub pull request.",
                parameters=[
                    ToolParameter("title", "string", "Pull request title."),
                    ToolParameter("body", "string", "Pull request description / body.", required=False),
                    ToolParameter("base_branch", "string", "Base branch to target (default: main).", required=False),
                    ToolParameter("dry_run", "boolean", "Preview PR actions without creating remote branches (default: false).", required=False),
                ],
                handler=lambda title, body="", base_branch="main", dry_run=False: create_pull_request(
                    title,
                    workspace=ws,
                    body=body,
                    base_branch=base_branch,
                    dry_run=dry_run,
                ),
            )
        )

        # 15. browse_web_content
        self.register(
            ToolSpec(
                name="browse_web_content",
                description="Fetch and parse a webpage or advisory into clean text.",
                parameters=[
                    ToolParameter("url", "string", "URL to fetch (http/https)."),
                ],
                handler=lambda url: browse_web_content(url),
            )
        )

        # 16. file_tree
        self.register(
            ToolSpec(
                name="file_tree",
                description="Show a bounded nested tree of a workspace directory.",
                parameters=[
                    ToolParameter("path", "string", "Directory to outline (default: .)", required=False),
                    ToolParameter("max_depth", "integer", "Max nesting depth (default: 4).", required=False),
                ],
                handler=lambda path=".", max_depth=4: file_tree(
                    path, workspace=ws, enforce_boundary=enforce_bound,
                    max_depth=int(max_depth),
                ),
            )
        )

        # 17. http_request
        self.register(
            ToolSpec(
                name="http_request",
                description="Fetch an http/https URL and return truncated text.",
                parameters=[
                    ToolParameter("url", "string", "URL to fetch (http/https)."),
                    ToolParameter("method", "string", "HTTP method (default: GET).", required=False),
                ],
                handler=lambda url, method="GET": http_request(url, method=method),
            )
        )

        # 18. python_eval
        self.register(
            ToolSpec(
                name="python_eval",
                description="Run a python snippet in the workspace (never in PLAN mode).",
                parameters=[
                    ToolParameter("code", "string", "Python code to execute."),
                ],
                handler=lambda code: python_eval(code, workspace=ws, timeout=bash_to),
            )
        )
