"""
Cerberus agent CLI entrypoint.

    cerberus scan <examine.py args…>   deterministic scanner (stdlib-only)
    cerberus agent [GOAL…]             orchestrator session (all 9 personas)
    cerberus <persona> [TASK…]         one named agent, Grokbot-style
    cerberus model [name]              list models / switch persisted default
    cerberus login|logout|status|logs  auth + diagnostics

`scan` shells out to the untouched examine.py so --native-only scans never
need agent dependencies. Everything else runs the servers/ runtime.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
EXAMINE_PY = REPO_ROOT / "examine.py"

# Allow `python servers/cli.py` from the repo root without install.
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from servers import __version__  # noqa: E402
from servers.agent.prompts import CERBERUS_AGENTS, list_personas  # noqa: E402
from servers.auth.store import (  # noqa: E402
    credentials_path,
    mask_key,
    resolve_api_key,
)
from servers.config import (  # noqa: E402
    DEFAULT_CONFIG_DIR,
    DEFAULT_CONFIG_PATH,
    AppConfig,
    ensure_default_config,
    load_config,
)
from servers.logging_setup import get_logger  # noqa: E402
from servers.models import Message, ToolCall, ToolCallFunction  # noqa: E402
from servers.tools.pr import create_pull_request, slugify  # noqa: E402

try:  # Rich UI is optional: scan/status work on stdlib alone.
    from servers.ui.console import TerminalUI
except ImportError:
    import re as _re

    class TerminalUI:  # type: ignore[no-redef]
        """Stdlib fallback when rich is not installed (monochrome prints)."""

        def __init__(self, **kwargs: object) -> None:
            self.console = self
            self._step = 0

        @staticmethod
        def _clean(text: object) -> str:
            return _re.sub(r"\[[^\]]*\]", "", str(text))

        def print(self, *args: object, **kwargs: object) -> None:
            print(" ".join(self._clean(a) for a in args))

        def input(self, prompt: object = "") -> str:
            return input(self._clean(prompt))

        def banner(self, **kwargs: object) -> None:
            from servers.ui.narrate import TAGLINE as _tag
            from servers.ui.narrate import welcome_rows as _rows

            rule = "─" * 64
            print(f"── CERBERUS ──")
            print(f"  {_tag}")
            for label, value in _rows(
                model=str(kwargs.get("model", "-")),
                base_url=str(kwargs.get("base_url", "-")),
                workspace=str(kwargs.get("workspace", "-")),
                mode=str(kwargs.get("mode", "plan")),
                auth="(see status)",
                log_file="(see logs)",
            ):
                print(f"  {label:9} {value}")
            print('  Try: "audit auth for injection" · /models · /help')
            print(rule)

        def info(self, msg: object) -> None:
            print(f"○ {self._clean(msg)}")

        def warn(self, msg: object) -> None:
            print(f"△ {self._clean(msg)}")

        def error(self, msg: object) -> None:
            print(f"✖ {self._clean(msg)}", file=sys.stderr)

        def spinner_start(self, msg: object) -> None:
            pass

        def spinner_stop(self) -> None:
            pass

        def tool_start(self, tc: object, args: object) -> None:
            from servers.ui.narrate import describe_activity as _describe

            name = getattr(getattr(tc, "function", tc), "name", "?")
            try:
                headline, reason = _describe(name, dict(args or {}))
            except Exception:
                headline, reason = ("Working", "continuing the task")
            self._step += 1
            print(f"Step {self._step}  {headline}\n  ↳ {reason}")

        def tool_end(self, tc: object, result: object) -> None:
            line = (str(result or "").strip().splitlines() or ["(no output)"])[0]
            print(f"  ✓ {line[:140]}")

        def turn_open(self) -> None:
            print()
            print("─" * 40)

        def model_table(self, rows: object) -> None:
            for index, model, section, is_current in rows or []:
                mark = "● " if is_current else "  "
                print(f"  {index}  {mark}{model}  [{section}]")
            print("Switch with /model <number|name>")

        def plan_update(self, msg: object) -> None:
            print(f"  → next: {self._clean(msg)}")

        def next_hint(self, mode: object) -> None:
            if mode == "plan":
                print("Plan above is a proposal — nothing was changed.")
            else:
                print("Changes applied. Verify with `cerberus scan`.")

        def assistant_final(self, text: object) -> None:
            print()
            print(text)

        def confirm_destructive(self, command: str, reason: str) -> bool:
            return self.confirm_choice(command, reason) in {"once", "session"}

        def confirm_choice(self, command: str, reason: str) -> str:
            try:
                ans = input(
                    f"Allow this?\n  {command}\n  {reason}\n"
                    "  y = once · a = always allow this kind · N = deny\n  [y/a/N] "
                )
            except (EOFError, KeyboardInterrupt):
                return "deny"
            ans = ans.strip().lower()
            if ans in {"a", "always", "session"}:
                return "session"
            if ans in {"y", "yes", "once"}:
                return "once"
            return "deny"


def _need_agent_deps(what: str) -> None:
    raise RuntimeError(
        f"{what} needs the agent runtime: "
        "pip install -r servers/requirements-agent.txt"
    )


def _resolve_key(ui: TerminalUI, config: AppConfig) -> str:
    """Lazy require_api_key so stdlib-only commands never need rich/httpx."""
    try:
        from servers.auth.login import require_api_key
    except ImportError:
        _need_agent_deps("agent sessions")
    return require_api_key(
        config_file_key=config.provider.api_key, console=ui.console
    )


def _launch_tui(ui: TerminalUI, config: AppConfig, api_key: str, persona: Optional[str]) -> int:
    """Start the Ink full-screen workbench (needs Textual)."""
    try:
        from servers.ui.tui import run_tui
    except ImportError:
        ui.error("The Ink workbench needs Textual: pip install -r servers/requirements-agent.txt")
        return 1
    if persona:
        ui.info(f"{persona} · {config.agent_mode} mode · {config.workspace}")
    return run_tui(config, api_key, persona_name=persona)


def _prog_name() -> str:
    base = Path(sys.argv[0]).name if sys.argv else "cerberus"
    if base in {"cli.py", "__main__.py", "python", "python3"}:
        return "cerberus"
    return base


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog=_prog_name(),
        description="Cerberus — deterministic scanner + Pollinations agent swarm",
    )
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    p.add_argument("-c", "--config", type=Path, default=None,
                   help=f"Config path (default: {DEFAULT_CONFIG_PATH})")
    p.add_argument("-m", "--model", default=None, help="Override provider model")
    p.add_argument("-w", "--workspace", type=Path, default=None,
                   help="Workspace root for file/bash tools (default: CWD)")
    p.add_argument("--base-url", default=None, help="Override API base URL")
    p.add_argument("--api-key", default=None, help="API key (prefer env or login)")
    p.add_argument("--plan", action="store_true",
                   help="Read-only plan mode (default; no file/environment mutations)")
    p.add_argument("--yolo", "--accept-edits", dest="yolo", action="store_true",
                   help="Accept-edits mode: allow mutations (Shift-Tab toggles this live)")
    p.add_argument("--classic", action="store_true",
                   help="Use the classic scrollback REPL instead of the Ink workbench")
    p.add_argument("--max-rounds", type=int, default=None,
                   help="Override per-run tool budget")
    p.add_argument("--pr", action="store_true",
                   help="Open a GitHub PR from workspace changes after the run")
    p.add_argument("--base", default="main", help="PR base branch (default: main)")
    p.add_argument("--title", default="", help="PR title (default: derived from goal)")
    p.add_argument("--dry-run", action="store_true",
                   help="Preview PR actions without pushing")
    p.add_argument("--swarm", action="store_true",
                   help="Fan one-shot agent goals out to classified personas")
    p.add_argument("-y", "--yes", action="store_true",
                   help="Auto-approve destructive commands (non-interactive)")
    p.add_argument("--init", action="store_true",
                   help="Write default config to ~/.cerberus/config.yaml and exit")
    p.add_argument("-v", "--verbose", action="store_true")
    p.add_argument("-q", "--quiet", action="store_true")
    p.add_argument("--log-file", type=Path, default=None)
    p.add_argument("command", nargs="?",
                   help="scan|agent|model|login|logout|status|logs|<persona>")
    p.add_argument("rest", nargs=argparse.REMAINDER,
                   help="Goal/task text or scan args")
    return p


# ---------------------------------------------------------------------------
# scan passthrough (untouched deterministic engine)
# ---------------------------------------------------------------------------

def cmd_scan(scan_args: list[str]) -> int:
    if not EXAMINE_PY.exists():
        print(f"ERROR: scanner not found at {EXAMINE_PY}", file=sys.stderr)
        return 1
    proc = subprocess.run(
        [sys.executable, str(EXAMINE_PY), *scan_args],
        cwd=str(REPO_ROOT),
    )
    return proc.returncode


def _run_scan_report(target: str) -> tuple[int, Optional[dict], str]:
    """Run examine.py on a target and load its JSON report.

    Engine stdout streams to the terminal; returns (exit_code, report|None,
    error_tail). Shared by the REPL /scan (TUI has its own worker version).
    """
    import json
    import tempfile

    if not EXAMINE_PY.exists():
        return 1, None, f"scanner not found at {EXAMINE_PY}"
    fd, json_path = tempfile.mkstemp(suffix=".json", prefix="cerberus-scan-")
    os.close(fd)
    try:
        proc = subprocess.run(
            [sys.executable, str(EXAMINE_PY), target, "--json", json_path],
            cwd=str(REPO_ROOT),
        )
        if proc.returncode != 0:
            return proc.returncode, None, "engine exited non-zero (see output above)"
        try:
            report = json.loads(Path(json_path).read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            return proc.returncode, None, f"could not read report: {exc}"
        return 0, report, ""
    finally:
        try:
            Path(json_path).unlink()
        except OSError:
            pass


def _handle_approvals(
    arg: str, loop: Any, ui: TerminalUI, config: AppConfig
) -> bool:
    """Show or toggle the ask-first policy for external tools and builds."""
    tools = config.tools
    registry = getattr(loop, "registry", None)
    try:
        session = registry.session_approvals() if registry is not None else []
    except Exception:
        session = []

    def show() -> None:
        ui.console.print(
            f"  external (web/search/PR):  {'ask' if tools.approve_external else 'allow'}\n"
            f"  builds (pytest/npm/make):  {'ask' if tools.approve_builds else 'allow'}\n"
            f"  always-allowed this run:   {', '.join(session) if session else '(none)'}"
        )

    parts = arg.strip().lower().split()
    if not parts or parts[0] in {"status", "show"}:
        show()
        ui.info("Usage: /approvals <external|builds> <on|off> · /approvals reset")
        return True
    if parts[0] == "reset":
        try:
            if registry is not None:
                registry.reset_session_approvals()
        except Exception:
            pass
        ui.info("Session approvals cleared — will ask again.")
        return True
    if len(parts) == 2 and parts[0] in {"external", "builds"}:
        if parts[1] not in {"on", "off", "ask", "allow"}:
            ui.warn("Usage: /approvals <external|builds> <on|off>")
            return True
        value = parts[1] in {"on", "ask"}
        if parts[0] == "external":
            tools.approve_external = value
        else:
            tools.approve_builds = value
        ui.info(
            f"Approvals → {parts[0]}: {'ask first' if value else 'allowed without asking'}"
        )
        return True
    ui.warn("Usage: /approvals [external|builds] [on|off] · /approvals reset")
    return True


# ---------------------------------------------------------------------------
# auth / diagnostics
# ---------------------------------------------------------------------------

def _auth_label(config: AppConfig) -> str:
    resolved = resolve_api_key(config_file_key=config.provider.api_key)
    if not resolved:
        return "not signed in"
    if resolved.kind == "byop":
        return f"pollen · {mask_key(resolved.key)}"
    if resolved.source == "env":
        return f"env · {mask_key(resolved.key)}"
    return f"key · {mask_key(resolved.key)}"


def _is_tty() -> bool:
    try:
        return bool(sys.stdin.isatty() and sys.stdout.isatty())
    except Exception:
        return False


def cmd_login(console: TerminalUI) -> int:
    try:
        from servers.auth.login import interactive_login
    except ImportError:
        _need_agent_deps("login")
    if not _is_tty():
        console.error("login requires an interactive terminal.")
        console.info("Or set CERBERUS_API_KEY / POLLINATIONS_API_KEY.")
        return 1
    try:
        existing = resolve_api_key()
        if existing:
            console.info(
                f"Signed in as {mask_key(existing.key)} "
                f"({existing.source}/{existing.kind}) — continuing replaces it."
            )
        interactive_login(save=True, console=console.console, allow_cancel=True)
        return 0
    except Exception as exc:
        if "cancelled" in str(exc).lower():
            console.info(str(exc))
            return 130
        console.error(f"Login failed: {exc}")
        return 1


def cmd_logout(console: TerminalUI) -> int:
    try:
        from servers.auth.login import perform_logout
    except ImportError:
        _need_agent_deps("logout")
    perform_logout(console=console.console)
    return 0


def cmd_status(config: AppConfig, console: TerminalUI) -> int:
    from servers.logging_setup import log_path

    resolved = resolve_api_key(config_file_key=config.provider.api_key)
    console.console.print("[bold #FFFFFF]CERBERUS[/] v" + __version__)
    console.console.print(f"  endpoint:    {config.provider.base_url}")
    console.console.print(f"  model:       {config.provider.model}")
    console.console.print(f"  workspace:   {config.workspace}")
    console.console.print(f"  mode:        {config.agent_mode}")
    console.console.print(f"  personas:    {', '.join(list_personas())}")
    console.console.print(f"  credentials: {credentials_path()}")
    console.console.print(f"  log file:    {log_path()}")
    if resolved:
        console.console.print(
            f"  api key:     {mask_key(resolved.key)}  "
            f"[dim]({resolved.source}/{resolved.kind})[/]"
        )
    else:
        console.console.print("  api key:     [bold #FFFFFF]not set[/]  → run `cerberus login`")
    return 0


def cmd_model(
    config: AppConfig,
    console: TerminalUI,
    config_path: Optional[Path] = None,
    arg: str = "",
) -> int:
    """List models or switch the persisted default (no API key needed)."""
    from servers.commands import catalog_lines, pick_model
    from servers.config import save_model

    if not arg.strip():
        for line in catalog_lines(config):
            console.console.print(line)
        return 0
    picked, message = pick_model(config, arg)
    if picked is None:
        console.warn(message)
        return 1
    config.provider.model = picked
    try:
        saved = save_model(picked, config_path)
    except OSError as exc:
        console.error(f"Model switched for this run only — cannot save config: {exc}")
        return 1
    console.info(f"{message} (saved → {saved})")
    return 0


def cmd_logs(console: TerminalUI, *, lines: int = 40) -> int:
    from servers.logging_setup import DEFAULT_LOG_FILE

    path = DEFAULT_LOG_FILE
    console.console.print(f"[bold]Activity log[/]  {path}")
    if not path.exists():
        console.info("No log file yet — run the agent once to create it.")
        return 0
    try:
        tail = path.read_text(encoding="utf-8", errors="replace").splitlines()[-lines:]
    except OSError as exc:
        console.error(f"Cannot read log: {exc}")
        return 1
    for line in tail:
        console.console.print(line)
    return 0


# ---------------------------------------------------------------------------
# session wiring
# ---------------------------------------------------------------------------

def build_loop(
    config: AppConfig,
    ui: TerminalUI,
    api_key: str,
    *,
    persona_name: Optional[str] = None,
    auto_approve: bool = False,
) -> AgentLoop:
    try:
        from servers.agent.loop import AgentLoop
        from servers.provider.client import OpenAICompatibleClient
        from servers.tools.registry import ToolRegistry
    except ImportError:
        _need_agent_deps("agent sessions")
    client = OpenAICompatibleClient(config.provider, api_key=api_key)

    def confirm(command: str, reason: str) -> Any:
        if auto_approve:
            return True
        # Tri-state: "once" | "session" (registry remembers the kind) | "deny".
        return ui.confirm_choice(command, reason)

    allowed: Optional[list[str]] = None
    if persona_name:
        allowed = config.policy_for(persona_name).allowed_tools or None

    registry = ToolRegistry(
        workspace=config.workspace,
        config=config.tools,
        mode=config.agent_mode,
        allowed_tools=allowed,
        confirm_callback=confirm,
    )

    def on_status(msg: str) -> None:
        ui.spinner_stop()
        ui.spinner_start(msg)

    def on_tool_start(tc: ToolCall, args: dict) -> None:
        ui.spinner_stop()
        ui.tool_start(tc, args)
        ui.spinner_start(f"Running {tc.function.name}…")

    def on_tool_end(tc: ToolCall, result: str) -> None:
        ui.spinner_stop()
        ui.tool_end(tc, result)

    def on_assistant_text(text: str) -> None:
        ui.spinner_stop()
        ui.assistant_final(text)

    def on_stream_delta(chunk: str) -> None:
        ui.spinner_stop()
        ui.console.print(chunk, end="", highlight=False, soft_wrap=True)

    return AgentLoop(
        config=config,
        client=client,
        registry=registry,
        persona_name=persona_name,
        on_tool_start=on_tool_start,
        on_tool_end=on_tool_end,
        on_assistant_text=on_assistant_text,
        on_status=on_status,
        on_stream_delta=on_stream_delta,
    )


def _set_mode(loop: AgentLoop, ui: TerminalUI, config: AppConfig, mode: str) -> None:
    """Flip plan/build live: loop prompt, registry gate, and config agree."""
    loop.set_mode(mode)
    loop.registry.mode = mode
    if mode == "build":
        ui.warn("Mode → ACCEPT-EDITS — the agent can now change files.")
    else:
        ui.info("Mode → PLAN — read-only, nothing will be changed.")


def _toggle_mode(loop: AgentLoop, ui: TerminalUI, config: AppConfig) -> None:
    _set_mode(loop, ui, config, "build" if config.agent_mode == "plan" else "plan")


def _mode_tag(config: AppConfig) -> str:
    return "YOLO" if config.agent_mode == "build" else "plan"


def run_once(loop: AgentLoop, ui: TerminalUI, prompt: str) -> int:
    try:
        from servers.provider.client import ProviderError
    except ImportError:
        _need_agent_deps("agent sessions")
    try:
        ui.turn_open()
        ui.spinner_start("Consulting model…")
        result = loop.run(prompt)
        ui.spinner_stop()
        ui.info(
            f"done · {result.tool_rounds} tool rounds · "
            f"{result.usage.format_short()} · {result.stopped_reason}"
        )
        ui.next_hint(loop.config.agent_mode)
        return 2 if result.stopped_reason == "circuit_breaker" else 0
    except ProviderError as exc:
        ui.spinner_stop()
        ui.error(str(exc))
        return 1
    except KeyboardInterrupt:
        ui.spinner_stop()
        ui.warn("Interrupted.")
        return 130


def _restore_message(raw: dict) -> Message:
    tcs = None
    if raw.get("tool_calls"):
        tcs = [
            ToolCall(
                id=t.get("id", ""),
                type=t.get("type", "function"),
                function=ToolCallFunction(
                    name=t.get("function", {}).get("name", ""),
                    arguments=t.get("function", {}).get("arguments", "{}"),
                ),
            )
            for t in raw["tool_calls"]
        ]
    return Message(
        role=raw.get("role", "user"),
        content=raw.get("content"),
        tool_calls=tcs,
        tool_call_id=raw.get("tool_call_id"),
        name=raw.get("name"),
    )


def _handle_slash(line: str, loop: AgentLoop, ui: TerminalUI, config: AppConfig) -> bool:
    parts = line.strip().split(maxsplit=1)
    cmd = parts[0].lower()
    arg = parts[1].strip() if len(parts) > 1 else ""

    if cmd in {"/exit", "/quit", "/q"}:
        ui.info("Goodbye.")
        raise SystemExit(0)
    if cmd == "/help":
        ui.console.print(
            """
[bold #FFFFFF]Slash commands[/]
  /help              Show this help
  /mode [plan|yolo]  Show or switch plan / accept-edits (Shift-Tab)
  /model [name]      Show or switch active model
  /models            List configured models
  /tools             List registered tools
  /usage             Token usage this session
  /login             Sign in with Pollen (BYOP device flow)
  /logout            Sign out (clear stored key)
  /scan <target>     Run scanner and attach findings to the chat
  /approvals         Show/toggle ask-first policy for web + builds
  /personas          List specialist agents
  /persona [name]    Show or switch the agent you're talking to
  /team a,b <task>   Fan a task out to a crew of agents
  /init              Scaffold CERBERUS.md project memory
  /add <files…>      Attach workspace files to the conversation
  /diff              Show uncommitted workspace changes
  /compact           Drop older history, keep recent context
  /reset             Clear conversation history
  /save [name]       Save conversation to disk
  /load <name>       Restore saved conversation
  /sessions          List saved sessions
  /config            Show effective configuration
  /workspace [path]  Show or change workspace
  /exit              Quit
"""
        )
        return True
    if cmd == "/login":
        cmd_login(ui)
        return True
    if cmd == "/logout":
        cmd_logout(ui)
        return True
    if cmd == "/scan":
        if not arg:
            ui.warn("Usage: /scan <path-or-github-url>")
            return True
        ui.info(f"Scanning {arg} with the deterministic engine…")
        rc, report, err = _run_scan_report(arg)
        if report is None:
            ui.error(f"Scan failed · {err} (exit {rc})")
            return True
        counts = report.get("counts", {}) or {}
        ui.info(
            f"Scan complete — {report.get('score', '?')}/100 "
            f"(grade {report.get('grade', '?')}) · "
            f"{counts.get('pass', '?')} passed · {counts.get('fail', '?')} failed"
        )
        history = getattr(loop, "messages", None)
        if history is None:
            ui.warn("History unavailable — findings not attached.")
        else:
            from servers.scan_context import remember_scan

            ui.info(remember_scan(history, report, arg))
        return True
    if cmd == "/approvals":
        return _handle_approvals(arg, loop, ui, config)
    if cmd == "/personas":
        from servers.agent.prompts import list_personas
        from servers.commands import persona_lines

        for line in persona_lines(list_personas()):
            ui.console.print(line)
        return True
    if cmd == "/persona":
        from servers.agent.prompts import list_personas

        names = list_personas()
        if not arg:
            current = getattr(loop, "persona_name", None) or "agent (orchestrator)"
            ui.info(f"Talking to: {current}  (/personas to browse, /persona <name> to switch)")
            return True
        name = arg.strip().lower()
        if name not in names:
            ui.warn(f"Unknown persona: {name}  (/personas to browse)")
            return True
        from servers.tools.registry import ToolRegistry

        old_reg = getattr(loop, "registry", None)
        loop.registry = ToolRegistry(
            workspace=config.workspace,
            config=config.tools,
            mode=config.agent_mode,
            allowed_tools=config.policy_for(name).allowed_tools or None,
            confirm_callback=getattr(old_reg, "confirm_callback", None),
        )
        loop.persona_name = name
        if hasattr(loop, "_bootstrap_system"):
            loop._bootstrap_system()
        ui.info(f"Now talking to {name} (history kept).")
        return True
    if cmd == "/team":
        from servers.agent.prompts import list_personas
        from servers.commands import parse_team_arg

        names, task, err = parse_team_arg(arg, list_personas())
        if err:
            ui.warn(err)
            return True
        try:
            api_key = _resolve_key(ui, config)
        except Exception as exc:
            ui.error(str(exc))
            return True
        _run_swarm_goal(config, ui, api_key, task, agents=names, loop=loop)
        return True
    if cmd == "/init":
        from servers.commands import init_project_file

        ui.info(init_project_file(config.workspace))
        return True
    if cmd == "/add":
        from servers.commands import attach_files

        history = getattr(loop, "messages", None)
        if history is None:
            ui.warn("History unavailable — cannot attach files here.")
        else:
            ui.info(attach_files(history, config.workspace, arg))
        return True
    if cmd == "/diff":
        from servers.commands import workspace_diff_summary

        ui.console.print(workspace_diff_summary(config.workspace))
        return True
    if cmd == "/compact":
        from servers.commands import compact_history

        history = getattr(loop, "messages", None)
        if history is None:
            ui.warn("History unavailable — nothing to compact.")
        else:
            ui.info(compact_history(history))
        return True
    if cmd == "/mode":
        if not arg:
            ui.info(
                f"Mode: {config.agent_mode}  "
                "(Shift-Tab or `/mode plan|yolo` to switch)"
            )
        else:
            a = arg.strip().lower()
            if a in {"yolo", "accept-edits", "accept", "build", "edit"}:
                _set_mode(loop, ui, config, "build")
            elif a in {"plan", "read-only", "readonly", "safe"}:
                _set_mode(loop, ui, config, "plan")
            else:
                ui.warn("Usage: /mode plan|yolo")
        return True
    if cmd == "/usage":
        u = loop.session_usage
        if u.total_tokens <= 0 and u.prompt_tokens <= 0:
            ui.info("No token usage reported yet (provider may omit usage)")
        else:
            ui.info(f"Session tokens · {u.format_detail()}")
        return True
    if cmd == "/model":
        from servers.commands import pick_model

        picked, message = pick_model(config, arg)
        if picked is None:
            if arg.strip():
                ui.warn(message)
            else:
                ui.info(message)
            return True
        config.provider.model = picked
        ui.info(message)
        return True
    if cmd == "/models":
        from servers.models_catalog import build_catalog

        catalog = build_catalog(
            current=config.provider.model, configured=config.provider.models
        )
        ui.model_table(
            [(r.index, r.model, r.section, r.is_current) for r in catalog]
        )
        return True
    if cmd == "/tools":
        for name in loop.registry.list_names():
            spec = loop.registry.get(name)
            desc = spec.description if spec else ""
            desc = (desc[:80] + "…") if len(desc) > 80 else desc
            ui.console.print(f"  [bold]{name}[/]  [dim]{desc}[/]")
        return True
    if cmd == "/reset":
        loop.reset()
        ui.info("Conversation history cleared.")
        return True
    if cmd == "/config":
        ui.console.print(
            f"  base_url:   {config.provider.base_url}\n"
            f"  model:      {config.provider.model}\n"
            f"  workspace:  {config.workspace}\n"
            f"  mode:       {config.agent_mode}\n"
            f"  max_rounds: {config.tools.max_tool_rounds}\n"
            f"  auth:       {_auth_label(config)}"
        )
        return True
    if cmd == "/save":
        from servers.session_store import save_session

        name = arg or f"session-{int(time.time())}"
        transcript = [m.to_api_dict() for m in loop.messages]
        path = save_session(
            name, transcript,
            model=config.provider.model, workspace=str(config.workspace),
        )
        ui.info(f"Saved '{name}' ({len(transcript)} messages) → {path}")
        return True
    if cmd == "/load":
        from servers.session_store import load_session

        if not arg:
            ui.warn("Usage: /load <session-name>")
            return True
        try:
            loop.messages = [_restore_message(m) for m in load_session(arg)]
            ui.info(f"Loaded '{arg}' ({len(loop.messages)} messages)")
        except FileNotFoundError:
            ui.error(f"Session not found: {arg!r}")
        except Exception as exc:
            ui.error(f"Failed to load session: {exc}")
        return True
    if cmd in {"/sessions", "/list"}:
        from servers.session_store import list_sessions

        sessions = list_sessions()
        if not sessions:
            ui.info("No saved sessions")
            return True
        for s in sessions:
            ui.console.print(
                f"  {s.name:20}  {s.message_count:3} msgs  "
                f"model={s.model or '-'}  "
                f"updated={time.strftime('%Y-%m-%d %H:%M', time.localtime(s.updated_at))}"
            )
        return True
    if cmd == "/workspace":
        if not arg:
            ui.info(f"Workspace: {config.workspace}")
        else:
            new_ws = Path(arg).expanduser().resolve()
            if not new_ws.is_dir():
                ui.error(f"Not a directory: {new_ws}")
            else:
                config.workspace = new_ws
                loop.registry.workspace = new_ws
                loop.reset()
                ui.info(f"Workspace → {new_ws} (history reset)")
        return True

    ui.warn(f"Unknown command: {cmd}  (try /help)")
    return True


def repl(loop: AgentLoop, ui: TerminalUI, config: AppConfig) -> int:
    session: Optional[Any] = None
    try:
        from prompt_toolkit import PromptSession
        from prompt_toolkit.history import FileHistory
        from prompt_toolkit.key_binding import KeyBindings

        DEFAULT_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        bindings = KeyBindings()

        @bindings.add("s-tab")  # Shift-Tab, Claude-Code style
        def _shift_tab(event: Any) -> None:
            _toggle_mode(loop, ui, config)

        session = PromptSession(
            history=FileHistory(str(DEFAULT_CONFIG_DIR / "history")),
            key_bindings=bindings,
        )
    except ImportError:
        session = None
        ui.info("Tip: install prompt_toolkit for history + Shift-Tab mode toggle.")

    ui.banner(
        model=config.provider.model,
        base_url=config.provider.base_url,
        workspace=str(config.workspace),
        mode=config.agent_mode,
    )

    def _prompt_fragments() -> list[tuple[str, str]]:
        return [("class:prompt", f"you [{_mode_tag(config)} · {config.provider.model}] › ")]

    while True:
        try:
            if session is not None:
                line = session.prompt(_prompt_fragments)
            else:
                line = input(f"you [{_mode_tag(config)} · {config.provider.model}] › ")
        except KeyboardInterrupt:
            ui.console.print()
            ui.info("Goodbye.")
            return 0
        except EOFError:
            ui.console.print()
            ui.info("Goodbye.")
            return 0

        line = line.strip()
        if not line:
            continue
        if line.startswith("/"):
            try:
                _handle_slash(line, loop, ui, config)
            except SystemExit as e:
                return int(e.code or 0)
            continue
        run_once(loop, ui, line)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def _apply_cli_overrides(args: argparse.Namespace, config: AppConfig) -> AppConfig:
    if args.workspace:
        config.workspace = args.workspace.expanduser().resolve()
    if args.model:
        config.provider.model = args.model
    if args.base_url:
        config.provider.base_url = args.base_url.rstrip("/")
    if args.api_key:
        config.provider.api_key = args.api_key
    if args.plan:
        config.agent_mode = "plan"
    elif getattr(args, "yolo", False):
        config.agent_mode = "build"
    if args.max_rounds:
        config.tools.max_tool_rounds = max(1, args.max_rounds)
    return config


def _maybe_open_pr(
    *,
    config: AppConfig,
    ui: TerminalUI,
    agent_name: str,
    goal: str,
    args: argparse.Namespace,
) -> int:
    """Run create_pull_request after a build-mode task when --pr was passed."""
    if config.agent_mode == "plan" and not args.dry_run:
        ui.warn("--pr with --plan: running PR helper in dry-run preview only.")
        args.dry_run = True
    title = args.title.strip() or (goal[:72] if goal else f"Cerberus {agent_name} patch")
    result = create_pull_request(
        title,
        workspace=config.workspace,
        agent_name=agent_name,
        base_branch=args.base,
        task_slug=slugify(goal or title),
        dry_run=args.dry_run,
    )
    ui.console.print()
    ui.console.print(result)
    if result.startswith("ERROR") or "failed" in result:
        return 1
    return 0


def _run_swarm_goal(
    config: AppConfig,
    ui: TerminalUI,
    api_key: str,
    goal: str,
    agents: Optional[list[str]] = None,
    loop: Any = None,
) -> int:
    """Fan a goal out to personas (given or classified), then print reports.

    When loop is passed (REPL /team), combined summaries are attached to
    the conversation for follow-ups.
    """
    try:
        from servers.agent.cerberus_swarm import CerberusSwarm
        from servers.provider.client import OpenAICompatibleClient
    except ImportError:
        _need_agent_deps("swarm sessions")
    client = OpenAICompatibleClient(config.provider, api_key=api_key)
    swarm = CerberusSwarm(config=config, client=client)
    if not agents:
        agents = swarm.classify_goal(goal)
    if not agents:
        agents = ["sentinel"]
    ui.info(f"Routing to: {', '.join(agents)}")
    reports = swarm.fan_out(
        [(name, goal) for name in agents],
        context=f"workspace: {config.workspace}",
    )
    combined: list[str] = []
    for rep in reports:
        ui.console.print()
        ui.console.print(
            f"[bold]{rep.agent}[/] · {rep.status} · "
            f"{rep.tool_rounds} rounds · {rep.duration_seconds:.1f}s"
        )
        ui.console.print(rep.summary or "(no summary)")
        combined.append(f"### {rep.agent}\n{(rep.summary or '')[:1500]}")
    if loop is not None:
        history = getattr(loop, "messages", None)
        if history is not None:
            history.append(
                Message(
                    role="user",
                    content=(
                        f"[team-context] Team findings ({', '.join(agents)}) "
                        f"on `{goal}`:\n\n" + "\n\n".join(combined)
                    ),
                )
            )
            ui.info("Team findings attached — ask follow-ups.")
    failed = [r for r in reports if r.status == "error"]
    return 1 if failed else 0


GLOBAL_BOOL_FLAGS = {
    "--plan", "--swarm", "--dry-run", "-y", "--yes",
    "--init", "-v", "--verbose", "-q", "--quiet",
    "--yolo", "--accept-edits", "--classic",
}
GLOBAL_VALUE_FLAGS = {
    "-c", "--config", "-m", "--model", "-w", "--workspace",
    "--base-url", "--api-key", "--max-rounds", "--base",
    "--title", "--log-file",
}


def _normalize_argv(argv: list[str]) -> list[str]:
    """Allow global flags after the command: `cerberus sentinel --plan "fix"`.

    Pulls known globals (and their values) to the front so argparse sees
    them. `scan` args are verbatim examine.py passthrough — never touched.
    """
    if argv[:1] == ["scan"]:
        return argv
    pulled: list[str] = []
    rest: list[str] = []
    i = 0
    while i < len(argv):
        tok = argv[i]
        if tok in GLOBAL_BOOL_FLAGS:
            pulled.append(tok)
        elif tok in GLOBAL_VALUE_FLAGS and i + 1 < len(argv):
            pulled.extend([tok, argv[i + 1]])
            i += 1
        elif tok.startswith("--") and "=" in tok and tok.split("=", 1)[0] in GLOBAL_VALUE_FLAGS:
            pulled.append(tok)
        else:
            rest.append(tok)
        i += 1
    return pulled + rest


def main(argv: Optional[list[str]] = None) -> int:
    raw = list(argv) if argv is not None else sys.argv[1:]
    args = build_parser().parse_args(_normalize_argv(raw))
    ui = TerminalUI()
    log = get_logger("cli")

    if args.init:
        path = ensure_default_config()
        ui.info(f"Wrote default config → {path}")
        return 0

    if not DEFAULT_CONFIG_PATH.exists() and not (DEFAULT_CONFIG_DIR / "config.json").exists():
        ensure_default_config()

    from servers.logging_setup import setup_logging

    level = "DEBUG" if args.verbose else ("WARNING" if args.quiet else "INFO")
    log_file = setup_logging(
        level=level, log_file=args.log_file,
        console=bool(args.verbose), quiet=args.quiet,
    )
    log.debug("cli start argv=%s", argv if argv is not None else sys.argv[1:])

    command = (args.command or "").strip().lower()
    rest = list(args.rest or [])
    if rest and rest[0] == "--":
        rest = rest[1:]

    # -- scan (verbatim passthrough, no auth/config needed) ---------------
    if command == "scan":
        return cmd_scan(rest)

    try:
        config = _apply_cli_overrides(args, load_config(args.config))
    except RuntimeError as exc:
        # No PyYAML but a YAML config exists: run on defaults + CLI flags.
        if "PyYAML" not in str(exc):
            raise
        ui.warn(f"{exc} — continuing with defaults + CLI flags.")
        config = _apply_cli_overrides(args, AppConfig())

    # -- auth / diagnostics (no API key needed) ----------------------------
    if command == "login":
        return cmd_login(ui)
    if command == "logout":
        return cmd_logout(ui)
    if command == "model":
        return cmd_model(config, ui, args.config, " ".join(rest))
    if command in {"status", "logs"}:
        if command == "status":
            return cmd_status(config, ui)
        return cmd_logs(ui)

    # -- Ink workbench --------------------------------------------------
    if command == "tui":
        try:
            api_key = _resolve_key(ui, config)
        except Exception as exc:
            ui.error(str(exc))
            return 1
        return _launch_tui(ui, config, api_key, None)

    # -- agent / persona runs (need API key) -------------------------------
    if command in {"agent", "orchestrator", *CERBERUS_AGENTS}:
        persona = None if command in {"agent", "orchestrator"} else command
        who = persona or "agent"
        if persona and not (args.plan or getattr(args, "yolo", False)):
            # Persona safety preference still applies unless YOLO was explicit.
            if config.policy_for(persona).default_mode == "plan":
                config.agent_mode = "plan"

        try:
            api_key = _resolve_key(ui, config)
        except Exception as exc:
            ui.error(str(exc))
            return 1

        goal = " ".join(rest).strip()
        if goal:
            log.info("%s one-shot goal=%r log=%s", who, goal[:80], log_file)
            if persona is None and args.swarm:
                rc = _run_swarm_goal(config, ui, api_key, goal)
            else:
                loop = build_loop(
                    config, ui, api_key,
                    persona_name=persona, auto_approve=args.yes,
                )
                if persona is None:
                    ui.banner(
                        model=config.provider.model,
                        base_url=config.provider.base_url,
                        workspace=str(config.workspace),
                        mode=config.agent_mode,
                    )
                else:
                    ui.info(f"{persona} · {config.agent_mode} mode · {config.workspace}")
                rc = run_once(loop, ui, goal)
            if rc == 0 and args.pr:
                return _maybe_open_pr(
                    config=config, ui=ui, agent_name=who, goal=goal, args=args,
                )
            return rc

        # interactive: Ink workbench on a TTY, classic REPL with --classic
        if _is_tty() and not args.classic:
            return _launch_tui(ui, config, api_key, persona)
        loop = build_loop(
            config, ui, api_key,
            persona_name=persona, auto_approve=args.yes,
        )
        return repl(loop, ui, config)

    # -- bare one-shot: `cerberus "goal…"` → orchestrator ------------------
    if command and not command.startswith("-"):
        goal = " ".join([command, *rest]).strip()
        try:
            api_key = _resolve_key(ui, config)
        except Exception as exc:
            ui.error(str(exc))
            return 1
        loop = build_loop(config, ui, api_key, auto_approve=args.yes)
        ui.banner(
            model=config.provider.model,
            base_url=config.provider.base_url,
            workspace=str(config.workspace),
            mode=config.agent_mode,
        )
        rc = run_once(loop, ui, goal)
        if rc == 0 and args.pr:
            return _maybe_open_pr(
                config=config, ui=ui, agent_name="agent", goal=goal, args=args,
            )
        return rc

    # -- no command: interactive workbench (TTY) -------------------------
    if not _is_tty():
        build_parser().print_help()
        ui.info("Tip: `cerberus scan .` runs the deterministic scanner (no login).")
        return 2
    try:
        api_key = _resolve_key(ui, config)
    except Exception as exc:
        ui.error(str(exc))
        return 1
    if not args.classic:
        return _launch_tui(ui, config, api_key, None)
    loop = build_loop(config, ui, api_key, auto_approve=args.yes)
    return repl(loop, ui, config)


if __name__ == "__main__":
    sys.exit(main())
