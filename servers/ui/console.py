"""
Scrollback terminal UI for the Cerberus agent CLI.

Deep-black monochrome aesthetic (Grok/Cursor-like): bright white for what
matters, grays for detail, no chroma. Every turn is containerized — banner
on entry, narrated step blocks while working, the final answer in its own
panel — and all widths follow the terminal so nothing wraps ugly.
"""

from __future__ import annotations

import time
from typing import Any, Optional

from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.rule import Rule

from servers.logging_setup import get_logger
from servers.ui.narrate import TAGLINE, _short, describe_activity, welcome_rows

log = get_logger("ui")

_C_WHITE = "#FFFFFF"
_C_SOFT = "#D8D8D8"
_C_GRAY = "#9A9A9A"
_C_DIM = "#5A5A5A"

_MAX_WIDTH = 96


class TerminalUI:
    """Rich scrollback UI — plain prints, no alt-screen buffer."""

    def __init__(
        self,
        *,
        syntax_theme: str = "monokai",
        show_tool_args: bool = True,
        console: Optional[Console] = None,
    ):
        self.console = console or Console()
        self.syntax_theme = syntax_theme
        self.show_tool_args = show_tool_args
        self._spinner = None
        self._step = 0
        self._t0: Optional[float] = None

    # -- layout helpers ------------------------------------------------
    @property
    def width(self) -> int:
        try:
            return max(40, min(self.console.width, _MAX_WIDTH))
        except Exception:
            return 80

    # -- chrome ------------------------------------------------------
    def banner(
        self,
        *,
        model: str,
        base_url: str,
        workspace: str,
        mode: str = "plan",
    ) -> None:
        from rich.rule import Rule
        from rich.table import Table
        from rich.text import Text

        from servers import __version__
        from servers.auth.store import mask_key, resolve_api_key
        from servers.logging_setup import log_path

        resolved = resolve_api_key()
        auth = "not signed in — run `cerberus login`"
        if resolved:
            origin = resolved.source
            if resolved.kind != resolved.source:
                origin = f"{resolved.source}/{resolved.kind}"
            auth = f"{origin} · {mask_key(resolved.key)}"

        mode_label = "ACCEPT-EDITS" if mode == "build" else "PLAN · read-only"
        self.console.print(
            Rule(
                f"[bold {_C_WHITE}]CERBERUS[/] "
                f"[{_C_DIM}]v{__version__} · {mode_label}[/]",
                style=_C_GRAY,
            )
        )
        self.console.print(
            Text(TAGLINE, style=_C_DIM, justify="center")
        )

        grid = Table(show_header=False, box=None, pad_edge=False)
        grid.add_column(style=_C_DIM, width=10)
        grid.add_column(style=_C_SOFT)
        for label, value in welcome_rows(
            model=model,
            base_url=base_url,
            workspace=workspace,
            mode=mode,
            auth=auth,
            log_file=str(log_path()),
        ):
            grid.add_row(label, escape(str(value)))
        self.console.print(grid)
        self.console.print(
            Text.from_markup(
                f"[{_C_DIM}]Try:[/] [{_C_SOFT}]\"audit auth for injection\"[/] "
                f"[{_C_DIM}]·[/] [{_C_SOFT}]sentinel \"review server/db.py\"[/] "
                f"[{_C_DIM}]·[/] [{_C_SOFT}]/models[/]"
            )
        )
        self.console.print(Rule(style=_C_DIM))

    def turn_open(self) -> None:
        """Divider that opens a new user turn's container."""
        self.console.print()
        self.console.print(Rule(style=_C_DIM))

    def info(self, msg: str) -> None:
        self.console.print(f"[{_C_GRAY}]○[/] [{_C_SOFT}]{escape(msg)}[/]")

    def warn(self, msg: str) -> None:
        self.console.print(f"[bold {_C_WHITE}]△[/] [bold {_C_WHITE}]{escape(msg)}[/]")

    def error(self, msg: str) -> None:
        self.console.print(f"[bold {_C_WHITE} on {_C_DIM}] ✖ [/] [bold {_C_WHITE}]{escape(msg)}[/]")

    # -- narrated activity -------------------------------------------
    def tool_start(self, tc: Any, args: dict[str, Any]) -> None:
        name = getattr(getattr(tc, "function", tc), "name", "?")
        headline, reason = describe_activity(name, args or {})
        self._step += 1
        self._t0 = time.monotonic()
        self.console.print(
            f"[{_C_DIM}]Step {self._step}[/]  [bold {_C_WHITE}]{escape(headline)}[/]"
        )
        self.console.print(f"[{_C_DIM}]  ↳ {escape(reason)}[/]")
        if self.show_tool_args and args:
            self.console.print(
                f"[{_C_DIM}]  · {escape(name)}({escape(_short(_fmt_args(args), 120))})[/]"
            )

    def tool_end(self, tc: Any, result: str) -> None:
        elapsed = ""
        if self._t0 is not None:
            elapsed = f" [{time.monotonic() - self._t0:.1f}s]"
            self._t0 = None
        text = (result or "").strip()
        outcome = _short(text.splitlines()[0] if text else "(no output)", 140)
        self.console.print(f"[{_C_GRAY}]  ✓ {escape(outcome)}{elapsed}[/]")

    def plan_update(self, msg: str) -> None:
        """What the agent will do next — keeps the viewer oriented."""
        self.console.print(f"[{_C_DIM}]  → next:[/] [{_C_SOFT}]{escape(msg)}[/]")

    def next_hint(self, mode: str) -> None:
        if mode == "plan":
            self.console.print(
                f"[{_C_DIM}]Plan above is a proposal — nothing was changed. "
                f"Shift-Tab for accept-edits, or describe what to adjust.[/]"
            )
        else:
            self.console.print(
                f"[{_C_DIM}]Changes applied. Verify with "
                f"`cerberus scan` before opening a PR.[/]"
            )

    # -- agent plumbing ----------------------------------------------
    def spinner_start(self, msg: str) -> None:
        self.spinner_stop()
        self._spinner = self.console.status(f"[{_C_GRAY}]{escape(msg)}[/]", spinner="dots")
        self._spinner.start()

    def spinner_stop(self) -> None:
        if self._spinner is not None:
            try:
                self._spinner.stop()
            except Exception:
                pass
            self._spinner = None

    def assistant_final(self, text: str) -> None:
        from rich.text import Text

        self.console.print(
            Panel(
                Text((text or "(no response)").strip()),
                title=f"[bold {_C_WHITE}]Cerberus[/]",
                title_align="left",
                border_style=_C_DIM,
                width=self.width,
                padding=(1, 2),
            )
        )

    def model_table(self, rows: list[tuple[int, str, str, bool]]) -> None:
        """Numbered model picker: (index, model, section, is_current)."""
        from rich.table import Table

        table = Table(show_header=True, header_style=_C_GRAY, box=None, width=self.width)
        table.add_column("#", style=_C_WHITE, width=4)
        table.add_column("model", style=_C_WHITE)
        table.add_column("section", style=_C_DIM)
        for index, model, section, is_current in rows:
            mark = "● " if is_current else "  "
            table.add_row(str(index), f"{mark}{escape(model)}", escape(section))
        self.console.print(table)
        self.console.print(
            f"[{_C_DIM}]Switch with /model <number|name>[/]"
        )

    def confirm_destructive(self, command: str, reason: str) -> bool:
        return self.confirm_choice(command, reason) in {"once", "session"}

    def confirm_choice(self, command: str, reason: str) -> str:
        """Ask approval: 'once' | 'session' (always allow this kind) | 'deny'."""
        try:
            answer = self.console.input(
                f"[bold {_C_WHITE}]Allow this?[/]\n"
                f"  [bold]{escape(command)}[/]\n  [{_C_GRAY}]{escape(reason)}[/]\n"
                f"  [{_C_DIM}]y = once · a = always allow this kind · N = deny[/]\n"
                f"  [y/a/N] "
            ).strip().lower()
        except (EOFError, KeyboardInterrupt):
            return "deny"
        if answer in {"a", "always", "session"}:
            return "session"
        if answer in {"y", "yes", "once"}:
            return "once"
        return "deny"


def _fmt_args(args: dict[str, Any]) -> str:
    return ", ".join(f"{k}={_short(v, 40)}" for k, v in args.items())
