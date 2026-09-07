"""
Ink Terminal workbench for Cerberus — full-screen Textual UI.

Warm paper, black ink, thin rules: the web Ink Terminal translated to the
terminal. Header / sidebar / workspace / composer / footer, four views,
command palette, and the same AgentLoop runtime as the REPL.
"""

from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import Any, Callable, Optional

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.command import Hit, Hits, Provider
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    Collapsible,
    Input,
    Label,
    ListItem,
    ListView,
    Static,
    TextArea,
    Tree,
)

INK_CSS = """
Screen {
    background: #EDECE7;
    color: #171817;
}
#head {
    height: 3;
    border-bottom: solid #AAA9A0;
    padding: 0 2;
}
#head .brand {
    width: 1fr;
    content-align: left middle;
    text-style: bold;
}
#head .env {
    width: auto;
    content-align: right middle;
    color: #575C55;
}
#body { height: 1fr; }
#side {
    width: 26;
    border-right: solid #AAA9A0;
    padding: 1 0;
}
#side .side-label {
    padding: 0 2;
    color: #575C55;
    text-style: bold;
}
#side Button {
    width: 100%;
    border: none;
    border-left: solid #EDECE7;
    background: #EDECE7;
    color: #171817;
    padding: 0 2;
    text-align: left;
    min-height: 2;
}
#side Button:hover { background: #DFDFD6; }
#side Button.current {
    background: #D3D3CA;
    border-left: solid #171817;
}
#side .spacer { height: 1fr; }
#side-foot {
    height: auto;
    border-top: solid #AAA9A0;
    padding: 1 2 0 2;
    color: #575C55;
}
#work { padding: 1 3; }
#work .sess {
    color: #575C55;
    border-bottom: solid #AAA9A0;
    padding-bottom: 1;
    margin-bottom: 1;
}
.idle-q { padding: 2 0 1 0; text-style: bold; }
.sec-label { color: #575C55; text-style: bold; padding: 1 0 0 0; }
.hist-row { padding: 0 1; }
.hist-row:hover { background: #D3D3CA; }
.meta { color: #575C55; }
.tag-local {
    border: solid #AAA9A0;
    color: #575C55;
    padding: 0 1;
}
.answer {
    border: solid #AAA9A0;
    background: #DFDFD6;
    padding: 1 2;
    margin: 1 0;
}
.step { padding: 0 0 0 1; }
.step-head { text-style: bold; }
.step-why { color: #575C55; }
.step-out { color: #575C55; padding-left: 2; }
.result-line { border-top: solid #AAA9A0; margin-top: 1; padding-top: 1; }
#compose {
    height: auto;
    min-height: 3;
    border-top: solid #AAA9A0;
    padding: 0 2;
}
#compose .glyph { width: 3; content-align: left middle; text-style: bold; }
#prompt { height: auto; min-height: 2; max-height: 6; border: none; background: #EDECE7; }
#compose-side { width: 14; height: auto; }
#compose-side Button { width: 100%; min-width: 0; margin-bottom: 0; }
Button {
    border: solid #171817;
    background: #EDECE7;
    color: #171817;
}
Button:hover { background: #171817; color: #EDECE7; }
#foot {
    height: 1;
    background: #20231F;
    color: #EFEEE7;
    padding: 0 2;
}
#foot-narrow {
    display: none;
    height: 1;
    background: #20231F;
    color: #EFEEE7;
    padding: 0 2;
}
#topnav {
    display: none;
    height: auto;
    border-bottom: solid #AAA9A0;
    padding: 0 1;
}
#topnav Button {
    border: none;
    border-bottom: solid #EDECE7;
    min-height: 1;
    padding: 0 1;
    margin-right: 1;
}
#topnav Button.current { border-bottom: solid #171817; background: #D3D3CA; }

/* Narrow terminals: sidebar becomes a top strip, chrome compacts. */
.narrow #side { display: none; }
.narrow #topnav { display: block; }
.narrow #work { padding: 1 1; }
.narrow #compose { padding: 1 1; }
.narrow #compose-side { width: 9; }
.narrow #foot { display: none; }
.narrow #foot-narrow { display: block; }
#palette-list { height: auto; max-height: 12; }

/* Dark mode: charcoal. ctrl+t cycles paper → dark → black. */
Screen.dark { background: #101210; color: #EDECE7; }
.dark #head { border-bottom: solid #2E322C; }
.dark #head .env { color: #8B9089; }
.dark .brand .mark { border: solid #EDECE7; background: #EDECE7; }
.dark .palette-btn { color: #8B9089; border: solid #2E322C; }
.dark .palette-btn:hover { background: #242824; color: #EDECE7; }
.dark #side { border-right: solid #2E322C; }
.dark #side .side-label { color: #8B9089; }
.dark #side Button { border-left: solid #101210; background: #101210; color: #EDECE7; }
.dark #side Button:hover { background: #1C1F1A; }
.dark #side Button.current { background: #242824; border-left: solid #EDECE7; }
.dark #side-foot { border-top: solid #2E322C; color: #8B9089; }
.dark #topnav { border-bottom: solid #2E322C; }
.dark #topnav Button { border-bottom: solid #101210; color: #EDECE7; background: #101210; }
.dark #topnav Button.current { border-bottom: solid #EDECE7; background: #242824; }
.dark #work .sess { color: #8B9089; border-bottom: solid #2E322C; }
.dark .idle-q { color: #EDECE7; }
.dark .sec-label { color: #8B9089; }
.dark .hist-row:hover { background: #242824; }
.dark .meta { color: #8B9089; }
.dark .tag-local { border: solid #2E322C; color: #8B9089; }
.dark .answer { border: solid #2E322C; background: #1C1F1A; }
.dark .step-why { color: #8B9089; }
.dark .step-out { color: #8B9089; }
.dark .result-line { border-top: solid #2E322C; }
.dark #compose { border-top: solid #2E322C; }
.dark #prompt { background: #101210; color: #EDECE7; }
.dark #compose-side Button { border: solid #EDECE7; background: #101210; color: #EDECE7; }
.dark #compose-side Button:hover { background: #EDECE7; color: #101210; }
.dark Button { border: solid #EDECE7; background: #101210; color: #EDECE7; }
.dark Button:hover { background: #EDECE7; color: #101210; }
.dark Button:disabled { color: #5A5A5A; border: solid #2E322C; }

/* Black mode: pure OLED black. Layered on top of .dark (screen carries
   both classes), so these only need to beat the .dark rules above.
   Toggled by cycling ctrl+t: paper → dark → black → paper. */
Screen.black { background: #000000; color: #F5F5F5; }
.black #head { border-bottom: solid #262626; }
.black #head .env { color: #9A9A9A; }
.black .brand .mark { border: solid #F5F5F5; background: #F5F5F5; }
.black .palette-btn { color: #9A9A9A; border: solid #262626; }
.black .palette-btn:hover { background: #141414; color: #FFFFFF; }
.black #side { border-right: solid #262626; }
.black #side .side-label { color: #9A9A9A; }
.black #side Button { border-left: solid #000000; background: #000000; color: #F5F5F5; }
.black #side Button:hover { background: #141414; }
.black #side Button.current { background: #1A1A1A; border-left: solid #FFFFFF; }
.black #side-foot { border-top: solid #262626; color: #9A9A9A; }
.black #topnav { border-bottom: solid #262626; }
.black #topnav Button { border-bottom: solid #000000; color: #F5F5F5; background: #000000; }
.black #topnav Button.current { border-bottom: solid #FFFFFF; background: #1A1A1A; }
.black #work .sess { color: #9A9A9A; border-bottom: solid #262626; }
.black .idle-q { color: #FFFFFF; }
.black .sec-label { color: #9A9A9A; }
.black .hist-row:hover { background: #1A1A1A; }
.black .meta { color: #9A9A9A; }
.black .tag-local { border: solid #262626; color: #9A9A9A; }
.black .answer { border: solid #262626; background: #0A0A0A; }
.black .step-why { color: #9A9A9A; }
.black .step-out { color: #9A9A9A; }
.black .result-line { border-top: solid #262626; }
.black #compose { border-top: solid #262626; }
.black #prompt { background: #000000; color: #F5F5F5; }
.black #compose-side Button { border: solid #F5F5F5; background: #000000; color: #F5F5F5; }
.black #compose-side Button:hover { background: #F5F5F5; color: #000000; }
.black Button { border: solid #F5F5F5; background: #000000; color: #F5F5F5; }
.black Button:hover { background: #F5F5F5; color: #000000; }
.black Button:disabled { color: #5A5A5A; border: solid #262626; }
.black #foot { background: #000000; color: #F5F5F5; }
.black #foot-narrow { background: #000000; color: #F5F5F5; }
.black #approval-box { border: solid #262626; background: #000000; }
.black #approval-box .dlg-cmd { color: #F5F5F5; }
.black #approval-box .dlg-why { color: #9A9A9A; }
.black .thinking { color: #9A9A9A; }

/* Approval dialog: centered, fits narrow screens. */
ApprovalScreen { align: center middle; }
#approval-box {
    width: 64; max-width: 92%; height: auto;
    border: solid #AAA9A0; background: #EDECE7; padding: 1 2;
}
#approval-box .dlg-title { text-style: bold; }
#approval-box .dlg-cmd { color: #171817; }
#approval-box .dlg-why { color: #575C55; }
#approval-btns { height: auto; margin-top: 1; }
#approval-btns Button { margin-right: 1; }
.dark #approval-box { border: solid #2E322C; background: #101210; }
.dark #approval-box .dlg-cmd { color: #EDECE7; }
.dark #approval-box .dlg-why { color: #8B9089; }

/* Run activity: user echo + waiting pulse. */
.you { text-style: bold; }
.thinking { color: #575C55; }
.dark .thinking { color: #8B9089; }

/* Inline autocomplete above the composer. */
#suggest { display: none; height: auto; max-height: 10; border-top: solid #AAA9A0; }
#suggest-rows { padding: 0 2; color: #575C55; }
.dark #suggest { border-top: solid #2E322C; }
.dark #suggest-rows { color: #8B9089; }
.black #suggest { border-top: solid #262626; }
.black #suggest-rows { color: #9A9A9A; }
"""

VIEWS = (("task", "01 / Current task"), ("files", "02 / Files"), ("changes", "03 / Changes"), ("history", "04 / History"))


class SubmitArea(TextArea):
    """Multiline input where Enter submits and Shift+Enter breaks the line."""

    class Submitted(Message):
        def __init__(self, text: str) -> None:
            super().__init__()
            self.text = text

    def on_key(self, event) -> None:
        if event.key == "ctrl+k":
            # TextArea would otherwise consume this (kill-to-end-of-line).
            event.prevent_default()
            event.stop()
            self.app.action_command_palette()
            return
        if event.key == "ctrl+t":
            event.prevent_default()
            event.stop()
            self.app.action_cycle_theme()
            return
        if getattr(event, "character", "") == "?" and not self.text.strip():
            # Empty composer + ? opens the palette (Claude-style).
            event.prevent_default()
            event.stop()
            self.app.action_command_palette()
            return
        if self.app._suggest_visible():
            if event.key in {"up", "down"}:
                event.prevent_default()
                event.stop()
                self.app._suggest_move(-1 if event.key == "up" else 1)
                return
            if event.key == "tab":
                event.prevent_default()
                event.stop()
                self.app._accept_suggest()
                return
            if event.key == "escape":
                event.prevent_default()
                event.stop()
                self.app._hide_suggest()
                return
        if event.key == "enter":
            event.prevent_default()
            event.stop()
            self.post_message(SubmitArea.Submitted(self.text.strip()))
            self.clear()


class InkCommands(Provider):
    """Ctrl+K palette: commands, views, saved sessions."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._app_ref: Any = None

    async def search(self, query: str) -> Hits:
        from servers.ui import tui as _self

        matcher = self.matcher(query)
        app = self.app
        commands = [
            ("/scan owner/repo", "run a security scan", lambda: app.action_compose_text("/scan ")),
            ("/help", "list commands", lambda: app.action_show_help()),
            ("/mode", "toggle plan / accept-edits", lambda: app.action_toggle_mode()),
            ("/models", "pick model", lambda: app.action_show_models()),
            ("/model name", "switch model", lambda: app.action_compose_text("/model ")),
            ("/add files", "attach files to context", lambda: app.action_compose_text("/add ")),
            ("/diff", "show workspace changes", lambda: app.action_compose_text("/diff")),
            ("/compact", "trim older history", lambda: app.action_compose_text("/compact")),
            ("/init", "scaffold project memory", lambda: app.action_compose_text("/init")),
            ("/approvals", "ask-first policy", lambda: app.action_compose_text("/approvals")),
            ("/personas", "list specialists", lambda: app.action_compose_text("/personas")),
            ("/persona name", "talk to a specialist", lambda: app.action_compose_text("/persona ")),
            ("/team a,b task", "consult a crew", lambda: app.action_compose_text("/team ")),
            ("/review", "hunk review", lambda: app.action_compose_text("/review")),
            ("/undo", "restore tracked files", lambda: app.action_compose_text("/undo")),
            ("/sessions delete", "delete a session", lambda: app.action_compose_text("/sessions delete ")),
            ("/usage", "token usage", lambda: app.action_compose_text("/usage")),
            ("/reset", "clear conversation", lambda: app.action_reset()),
            ("/save name", "save session", lambda: app.action_compose_text("/save ")),
            ("/load name", "load session", lambda: app.action_compose_text("/load ")),
            ("theme: paper", "warm light theme", lambda: app.set_ink_theme("paper")),
            ("theme: dark", "charcoal dark theme", lambda: app.set_ink_theme("dark")),
            ("theme: black", "pure OLED black theme", lambda: app.set_ink_theme("black")),
            ("go: task", "current task view", lambda: app.show_view("task")),
            ("go: files", "file browser", lambda: app.show_view("files")),
            ("go: changes", "git changes", lambda: app.show_view("changes")),
            ("go: history", "saved sessions", lambda: app.show_view("history")),
        ]
        for label, help_text, fn in commands:
            score = matcher.match(label)
            if score > 0:
                yield Hit(score, matcher.highlight(label), fn, help=help_text)
        try:
            for s in _self.list_sessions():
                label = "session: " + s.name
                score = matcher.match(label)
                if score > 0:
                    yield Hit(score, matcher.highlight(label), (lambda n: lambda: app.action_load_session(n))(s.name), help="reopen session")
        except Exception:
            pass


# -- run messages (thread worker → UI thread) ------------------------------
class ToolStarted(Message):
    def __init__(self, run: int, call_id: str, headline: str, reason: str, detail: str) -> None:
        super().__init__()
        self.run = run
        self.call_id = call_id
        self.headline = headline
        self.reason = reason
        self.detail = detail


class ToolEnded(Message):
    def __init__(self, run: int, call_id: str, outcome: str) -> None:
        super().__init__()
        self.run = run
        self.call_id = call_id
        self.outcome = outcome


class Streamed(Message):
    def __init__(self, run: int, chunk: str) -> None:
        super().__init__()
        self.run = run
        self.chunk = chunk


class RunDone(Message):
    def __init__(self, run: int, text: str, rounds: int, stopped: str, usage: str) -> None:
        super().__init__()
        self.run = run
        self.text = text
        self.rounds = rounds
        self.stopped = stopped
        self.usage = usage


class ApprovalScreen(ModalScreen):
    """Ask-first gate for external tools and builds.

    Dismisses with True (once), "session" (always allow this kind), or
    False (deny). Opened from the agent worker thread via call_from_thread.
    """

    def __init__(self, command: str, reason: str) -> None:
        super().__init__()
        self._command = command
        self._reason = reason

    def compose(self) -> ComposeResult:
        with Vertical(id="approval-box"):
            yield Static("ALLOW THIS?", classes="dlg-title")
            yield Static(self._command, classes="dlg-cmd")
            yield Static(self._reason, classes="dlg-why")
            with Horizontal(id="approval-btns"):
                yield Button("Once [y]", id="ap-once")
                yield Button("Always [a]", id="ap-always")
                yield Button("Deny [esc]", id="ap-deny", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        mapping = {"ap-once": True, "ap-always": "session", "ap-deny": False}
        self.dismiss(mapping.get(event.button.id, False))

    def on_key(self, event) -> None:
        key = (event.key or "").lower()
        if key == "y":
            self.dismiss(True)
        elif key == "a":
            self.dismiss("session")
        elif key in {"escape", "n"}:
            self.dismiss(False)
def list_sessions():
    from servers.session_store import list_sessions as _list

    return _list()




class InkApp(App):
    """Cerberus Ink workbench."""

    CSS = INK_CSS
    COMMANDS = {InkCommands}
    BINDINGS = [
        Binding("ctrl+k", "command_palette", "Palette", show=True),
        Binding("shift+tab", "toggle_mode", "Plan/YOLO", show=True),
        Binding("ctrl+t", "cycle_theme", "Theme", show=True),
        Binding("escape", "stop_or_close", "Stop", show=True),
        Binding("ctrl+c", "stop_or_close", "Stop", show=False),
    ]
    NARROW_UNDER = 96

    def __init__(
        self,
        config,
        api_key: str = "",
        *,
        persona_name: Optional[str] = None,
        loop_factory: Optional[Callable] = None,
        preload_messages: Optional[list] = None,
    ) -> None:
        super().__init__()
        self.config = config
        self.api_key = api_key
        self.persona_name = persona_name
        self._ink_theme = "paper"
        self.loop_factory = loop_factory
        self.preload_messages = list(preload_messages) if preload_messages else []
        self.loop = None
        self.view = "task"
        self.run_token = 0
        self.running = False
        self._draft_text = ""
        self._draft_widget = None
        self._suggest_matches: list = []
        self._suggest_index = 0

    # -- compose ------------------------------------------------------
    def compose(self) -> ComposeResult:
        yield Horizontal(
            Static("▪ C E R B E R U S", classes="brand", id="brand"),
            Static(self._env_text(), classes="env", id="env"),
            id="head",
        )
        with Horizontal(id="topnav"):
            for key, label in (("task", "01"), ("files", "02"), ("changes", "03"), ("history", "04")):
                yield Button(label, id="tnav-" + key, classes="nav")
        with Horizontal(id="body"):
            with Vertical(id="side"):
                yield Static("WORKBENCH", classes="side-label")
                for key, label in VIEWS:
                    yield Button(label, id="nav-" + key, classes="nav")
                yield Static("", classes="spacer")
                yield Static("", id="side-foot")
            yield VerticalScroll(id="work")
        with Vertical(id="suggest"):
            yield Static("", id="suggest-rows")
        with Horizontal(id="compose"):
            yield Static("❯", classes="glyph")
            yield SubmitArea(id="prompt")
            with Vertical(id="compose-side"):
                yield Button("SEND", id="send", variant="primary")
                yield Button("STOP", id="stop", disabled=True)
        yield Static(self._foot_text(), id="foot")
        yield Static("/ commands · ctrl+k · enter · esc", id="foot-narrow")

    def _env_text(self) -> str:
        who = self.persona_name or "agent"
        return "{} · {} · {}".format(who, self.config.provider.model, "YOLO" if self.config.agent_mode == "build" else "plan")

    def _foot_text(self) -> str:
        return "/ commands · ? palette · enter submit · esc/ctrl+c stop · shift+tab mode · ctrl+t theme"

    def on_mount(self) -> None:
        self._build_loop()
        self._mark_nav()
        self._render_side_foot()
        self.show_view("task")
        if self.preload_messages:
            try:
                self.loop.messages = list(self.preload_messages)
            except Exception:
                pass
            self._append_msg(
                "Resumed session ({} messages) — history kept.".format(len(self.preload_messages))
            )
        self.query_one("#prompt", SubmitArea).focus()

    # -- loop ----------------------------------------------------------
    def _build_loop(self) -> None:
        self.loop = self._make_loop(self.persona_name)
        self._refresh_env()

    def _make_loop(self, persona_name):
        """Build an AgentLoop for a persona (test seam: honors loop_factory)."""
        if self.loop_factory is not None:
            loop = self.loop_factory(self.config)
            try:
                loop.persona_name = persona_name
            except Exception:
                pass
            return loop
        from servers.agent.loop import AgentLoop
        from servers.provider.client import OpenAICompatibleClient
        from servers.tools.registry import ToolRegistry

        client = OpenAICompatibleClient(self.config.provider, api_key=self.api_key)
        allowed = None
        if persona_name:
            allowed = self.config.policy_for(persona_name).allowed_tools or None
        registry = ToolRegistry(
            workspace=self.config.workspace,
            config=self.config.tools,
            mode=self.config.agent_mode,
            allowed_tools=allowed,
            confirm_callback=self._agent_confirm,
        )
        return AgentLoop(
            config=self.config,
            client=client,
            registry=registry,
            persona_name=persona_name,
        )

    def _switch_persona(self, name: str) -> None:
        """Swap the active persona mid-session, keeping history and usage."""
        old = self.loop
        saved_messages = list(old.messages)
        saved_usage = getattr(old, "session_usage", None)
        new_loop = self._make_loop(name)
        try:
            new_loop.messages = saved_messages
        except Exception:
            pass
        if saved_usage is not None:
            try:
                new_loop.session_usage = saved_usage
            except Exception:
                pass
        self.loop = new_loop
        self.persona_name = name
        self._refresh_env()
        self._append_msg("Now talking to {} (history kept).".format(name))

    def _refresh_env(self) -> None:
        try:
            self.query_one("#env", Static).update(self._env_text())
        except Exception:
            pass
        self._render_side_foot()
        self._update_foot()

    def _update_foot(self) -> None:
        """Footer hints plus live session token counter."""
        try:
            base = self._foot_text()
            usage = getattr(getattr(self, "loop", None), "session_usage", None)
            total = getattr(usage, "total_tokens", 0) or 0
            if total > 0:
                if total >= 1_000_000:
                    tok = "{:.1f}M".format(total / 1_000_000)
                elif total >= 1000:
                    tok = "{:.1f}k".format(total / 1000)
                else:
                    tok = str(total)
                base += " · {} tok".format(tok)
            self.query_one("#foot", Static).update(base)
        except Exception:
            pass

    def _mark_nav(self) -> None:
        for key, _label in VIEWS:
            for prefix in ("#nav-", "#tnav-"):
                try:
                    self.query_one(prefix + key, Button).set_classes("current" if key == self.view else "nav")
                except Exception:
                    pass

    def _render_side_foot(self) -> None:
        try:
            foot = self.query_one("#side-foot", Static)
        except Exception:
            return
        ws = str(self.config.workspace)
        if len(ws) > 24:
            ws = "…" + ws[-23:]
        foot.update("{}\nmode {}".format(ws, self.config.agent_mode))

    # -- views ----------------------------------------------------------
    def show_view(self, name: str) -> None:
        self.view = name
        self._mark_nav()
        work = self.query_one("#work", VerticalScroll)
        work.remove_children()
        if name == "files":
            work.mount(FilesView(self.config.workspace))
        elif name == "changes":
            work.mount(ChangesView(self.config.workspace))
        elif name == "history":
            work.mount(HistoryView())
        else:
            work.mount(TaskView(self))
        work.scroll_to(y=0, animate=False)

    def action_show_help(self) -> None:
        self.show_view("task")
        self._append_msg("Commands: /scan target · /help · /mode · /theme · /model · /persona · /team · /approvals · /init · /add files · /diff · /review · /undo · /compact · /usage · /save · /load · /clear · plain text runs the agent. @files attach · !cmd runs bash.")

    @property
    def ink_theme(self) -> str:
        """Active Ink theme: paper, dark, or black (pure OLED black)."""
        return self._ink_theme

    def set_ink_theme(self, name: str) -> None:
        """Apply an Ink theme by name. Black layers on top of dark."""
        if name not in {"paper", "dark", "black"}:
            raise ValueError(name)
        self._ink_theme = name
        try:
            self.screen.set_class(name in {"dark", "black"}, "dark")
            self.screen.set_class(name == "black", "black")
        except Exception:
            pass  # pre-mount: classes apply on next set after mount

    def action_cycle_theme(self) -> None:
        order = ("paper", "dark", "black")
        try:
            nxt = order[(order.index(self._ink_theme) + 1) % len(order)]
        except ValueError:
            nxt = "paper"
        self.set_ink_theme(nxt)
        self._append_msg("Theme → {}.".format(nxt))

    def action_toggle_dark(self) -> None:
        # Legacy two-state toggle (paper ↔ dark); clears black.
        self.set_ink_theme("paper" if self._ink_theme != "paper" else "dark")
        self._append_msg("Theme → {}.".format(self._ink_theme))

    def on_resize(self, event) -> None:
        try:
            self.screen.set_class(event.size.width < self.NARROW_UNDER, "narrow")
        except Exception:
            pass

    def action_toggle_mode(self) -> None:
        new = "build" if self.config.agent_mode == "plan" else "plan"
        self.loop.set_mode(new)
        self.loop.registry.mode = new
        self._refresh_env()
        self._append_msg("Mode → " + ("ACCEPT-EDITS — the agent can now change files." if new == "build" else "PLAN — read-only."))

    def action_reset(self) -> None:
        self.loop.reset()
        self.show_view("task")
        self._append_msg("Conversation history cleared.")
        self._update_foot()

    def action_show_models(self) -> None:
        from servers.models_catalog import build_catalog

        rows = build_catalog(current=self.config.provider.model, configured=self.config.provider.models)
        lines = ["MODELS — /model <number|name> to switch:"]
        for r in rows:
            mark = "●" if r.is_current else " "
            lines.append("[{}] {} {} {}".format(r.index, mark, r.model, r.section))
        self.show_view("task")
        self._append_msg("\n".join(lines))

    def action_load_session(self, name: str) -> None:
        from servers.models import Message, ToolCall, ToolCallFunction
        from servers.session_store import load_session

        try:
            raw = load_session(name)
        except Exception as exc:
            self._append_msg("Could not load session: {}".format(exc))
            return
        msgs = []
        for m in raw:
            tcs = None
            if m.get("tool_calls"):
                tcs = [ToolCall(id=t.get("id", ""), type="function", function=ToolCallFunction(name=t.get("function", {}).get("name", ""), arguments=t.get("function", {}).get("arguments", "{}"))) for t in m["tool_calls"]]
            msgs.append(Message(role=m.get("role", "user"), content=m.get("content"), tool_calls=tcs, tool_call_id=m.get("tool_call_id"), name=m.get("name")))
        self.loop.messages = msgs
        self.show_view("task")
        self._append_msg("Loaded '{}' ({} messages).".format(name, len(msgs)))

    def action_compose_text(self, text: str) -> None:
        try:
            area = self.query_one("#prompt", SubmitArea)
            area.text = text
            area.focus()
        except Exception:
            pass

    def _append_msg(self, text: str) -> None:
        try:
            work = self.query_one("#work", VerticalScroll)
            widget = Static(text, classes="msg")
            widget.markup = False
            work.mount(widget)
            work.scroll_end(animate=False)
        except Exception:
            pass

    # -- events ---------------------------------------------------------
    @on(Button.Pressed)
    def _buttons(self, event: Button.Pressed) -> None:
        bid = (event.button.id or "")
        if bid.startswith("nav-"):
            self.show_view(bid[4:])
        elif bid.startswith("tnav-"):
            self.show_view(bid[5:])
        elif bid == "send":
            try:
                area = self.query_one("#prompt", SubmitArea)
                self.submit_text(area.text.strip())
                area.clear()
            except Exception:
                pass
        elif bid == "stop":
            self.action_stop_or_close()

    @on(SubmitArea.Submitted)
    def _submitted(self, event: SubmitArea.Submitted) -> None:
        self.submit_text(event.text)

    def _pulse_thinking(self) -> None:
        """Animate the waiting indicator until first real activity."""
        try:
            widget = getattr(self, "_thinking_widget", None)
            if widget is None or getattr(self, "_thinking_run", None) != self.run_token:
                return
            elapsed = time.monotonic() - getattr(self, "_thinking_start", time.monotonic())
            dots = "." * (1 + int(elapsed / 0.4) % 3)
            widget.update("Thinking{} · {:.0f}s".format(dots, elapsed))
        except Exception:
            pass

    def _clear_thinking(self, run: int) -> None:
        """Remove the waiting indicator once the run produces output."""
        try:
            if getattr(self, "_thinking_run", None) != run:
                return
            self._thinking_run = None
            timer = getattr(self, "_thinking_timer", None)
            if timer is not None:
                timer.stop()
                self._thinking_timer = None
            widget = getattr(self, "_thinking_widget", None)
            if widget is not None:
                widget.remove()
                self._thinking_widget = None
        except Exception:
            pass

    @on(ToolStarted)
    def _tool_started(self, event: ToolStarted) -> None:
        if event.run != self.run_token:
            return
        self._clear_thinking(event.run)
        try:
            work = self.query_one("#work", VerticalScroll)
            box = Collapsible(
                Static("{}\n{}".format(event.reason, event.detail), classes="step-why"),
                title="Step {} — {}".format(self._step_count(event.run), event.headline),
            )
            box.add_class("step")
            work.mount(box)
            self._blocks[event.call_id] = box
            work.scroll_end(animate=False)
        except Exception:
            pass

    def _step_count(self, run: int) -> int:
        self._steps = getattr(self, "_steps", {})
        self._steps[run] = self._steps.get(run, 0) + 1
        return self._steps[run]

    @on(ToolEnded)
    def _tool_ended(self, event: ToolEnded) -> None:
        if event.run != self.run_token:
            return
        box = self._blocks.pop(event.call_id, None)
        if box is None:
            return
        try:
            box.mount(Static("✓ {}".format(event.outcome), classes="step-out"))
        except Exception:
            pass

    @on(Streamed)
    def _streamed(self, event: Streamed) -> None:
        if event.run != self.run_token:
            return
        self._clear_thinking(event.run)
        try:
            self._draft_text += event.chunk
            if self._draft_widget is None:
                work = self.query_one("#work", VerticalScroll)
                self._draft_widget = Static("", classes="msg")
                self._draft_widget.markup = False
                work.mount(self._draft_widget)
            self._draft_widget.update(self._draft_text)
            self.query_one("#work", VerticalScroll).scroll_end(animate=False)
        except Exception:
            pass

    @on(RunDone)
    def _run_done(self, event: RunDone) -> None:
        if event.run != self.run_token:
            return
        self._clear_thinking(event.run)
        self.running = False
        try:
            self.query_one("#stop", Button).disabled = True
        except Exception:
            pass
        try:
            if self._draft_widget is not None:
                self._draft_widget.remove()
        except Exception:
            pass
        finally:
            self._draft_widget = None
            self._draft_text = ""
        try:
            work = self.query_one("#work", VerticalScroll)
            if event.text:
                work.mount(Static(event.text, classes="answer"))
            work.mount(Static(
                "done · {} tool rounds · {} · {}".format(event.rounds, event.usage, event.stopped),
                classes="meta",
            ))
            if event.stopped != "error":
                work.mount(Static(
                    "Plan above is a proposal — nothing was changed. Shift-Tab for accept-edits."
                    if self.config.agent_mode == "plan"
                    else "Changes applied. Verify with `cerberus scan` before opening a PR.",
                    classes="meta",
                ))
            work.scroll_end(animate=False)
        except Exception:
            pass
        self._update_foot()

    # -- actions ----------------------------------------------------------
    def action_command_palette(self) -> None:
        from textual.command import CommandPalette

        self.push_screen(CommandPalette())

    def action_stop_or_close(self) -> None:
        if self.running and self.loop is not None:
            try:
                self.loop.request_cancel()
            except Exception:
                pass
            self._append_msg("Stopping after the current step…")
        self._dismiss_approval()

    def _dismiss_approval(self) -> None:
        try:
            if isinstance(self.screen, ApprovalScreen):
                self.dismiss(False)
        except Exception:
            pass

    def _agent_confirm(self, command: str, reason: str):
        """Approval gate for the worker thread: modal, y/a/esc, STOP-safe."""
        import threading

        box: dict = {}
        done = threading.Event()

        def ask() -> None:
            try:
                self.push_screen(
                    ApprovalScreen(command, reason),
                    lambda r: (box.setdefault("r", False if r is None else r), done.set()),
                )
            except Exception:
                box["r"] = False
                done.set()

        try:
            self.call_from_thread(ask)
        except Exception:
            return False
        while not done.wait(0.25):
            if not self.running:
                try:
                    self.call_from_thread(self._dismiss_approval)
                except Exception:
                    pass
                done.wait(5.0)
                break
        return box.get("r", False)

    # -- inline autocomplete ------------------------------------------------
    def _suggest_visible(self) -> bool:
        return bool(getattr(self, "_suggest_matches", []))

    def _update_suggest(self, text: str) -> None:
        from servers.commands import suggest_commands

        matches: list = []
        if text.startswith("/") and "\n" not in text and " " not in text:
            matches = suggest_commands(text[1:])
        self._suggest_matches = matches
        self._suggest_index = 0
        self._render_suggest()

    def _render_suggest(self) -> None:
        try:
            box = self.query_one("#suggest")
            rows = self.query_one("#suggest-rows", Static)
        except Exception:
            return
        matches = getattr(self, "_suggest_matches", [])
        if not matches:
            box.styles.display = "none"
            return
        lines = ["commands — tab to complete · esc dismiss"]
        for i, (cmd, usage, blurb) in enumerate(matches):
            mark = "❯" if i == getattr(self, "_suggest_index", 0) else " "
            lines.append("{} /{}{} — {}".format(mark, cmd, usage, blurb))
        rows.update("\n".join(lines))
        box.styles.display = "block"

    def _suggest_move(self, delta: int) -> None:
        matches = getattr(self, "_suggest_matches", [])
        if not matches:
            return
        self._suggest_index = (getattr(self, "_suggest_index", 0) + delta) % len(matches)
        self._render_suggest()

    def _accept_suggest(self) -> None:
        matches = getattr(self, "_suggest_matches", [])
        if not matches:
            return
        cmd = matches[getattr(self, "_suggest_index", 0) % len(matches)][0]
        try:
            area = self.query_one("#prompt", SubmitArea)
            area.load_text("/{} ".format(cmd))
            try:
                # load_text parks the cursor at the start; put it after the text.
                area.action_cursor_line_end()
            except Exception:
                pass
            area.focus()
        except Exception:
            pass
        self._hide_suggest()

    def _hide_suggest(self) -> None:
        self._suggest_matches = []
        self._suggest_index = 0
        try:
            self.query_one("#suggest").styles.display = "none"
        except Exception:
            pass

    @on(TextArea.Changed)
    def _prompt_changed(self, event: TextArea.Changed) -> None:
        try:
            if event.control.id != "prompt":
                return
            self._update_suggest(event.control.text)
        except Exception:
            pass

    # -- submit routing -----------------------------------------------------
    def submit_text(self, text: str) -> None:
        self._hide_suggest()
        if not text:
            return
        if self.running:
            self._append_msg("A run is already active — STOP it first, or wait.")
            return
        if text.startswith("/"):
            self._slash(text)
            return
        from servers.commands import attach_files, parse_composer_line

        action, spec, payload = parse_composer_line(text)
        if action == "attach":
            self._append_msg(attach_files(self.loop.messages, self.config.workspace, spec))
            return
        if action == "bash":
            self._start_bash(payload)
            return
        if spec:
            self._append_msg(attach_files(self.loop.messages, self.config.workspace, spec))
        self._start_run(payload)

    def _job_begin(self) -> int:
        token = self.run_token + 1
        self.run_token = token
        self.running = True
        try:
            self.query_one("#stop", Button).disabled = False
        except Exception:
            pass
        return token

    def _job_end(self, token: int) -> None:
        if token == self.run_token:
            self.running = False
            try:
                self.query_one("#stop", Button).disabled = True
            except Exception:
                pass

    def _start_bash(self, command: str) -> None:
        self._append_msg("❯ !{}".format(command))
        self.run_worker(self._do_bash(command), exclusive=True)

    async def _do_bash(self, command: str) -> None:
        import asyncio as _aio

        token = self._job_begin()
        try:
            out = await _aio.to_thread(
                self.loop.registry.dispatch,
                "execute_bash_command", {"command": command},
            )
            if token != self.run_token:
                return
            self._append_msg((out or "(no output)")[:4000])
        except Exception as exc:
            if token == self.run_token:
                self._append_msg("Bash failed: {}".format(exc))
        finally:
            self._job_end(token)

    def _slash(self, text: str) -> None:
        parts = text.split(None, 1)
        cmd = parts[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else ""
        if cmd == "/help":
            self.action_show_help()
        elif cmd == "/mode":
            self._slash_mode(arg)
        elif cmd == "/model":
            self._slash_model(arg)
        elif cmd == "/models":
            self.action_show_models()
        elif cmd == "/reset":
            self.action_reset()
        elif cmd == "/clear":
            self.show_view("task")
        elif cmd in {"/exit", "/quit", "/q"}:
            self._append_msg("Goodbye.")
            self.exit()
        elif cmd == "/theme":
            self._slash_theme(arg)
        elif cmd == "/usage":
            u = self.loop.session_usage
            if u.total_tokens <= 0 and u.prompt_tokens <= 0:
                self._append_msg("No token usage reported yet (provider may omit usage).")
            else:
                self._append_msg("Session tokens · {}".format(u.format_detail()))
        elif cmd == "/login":
            from servers.auth.store import mask_key, resolve_api_key

            found = resolve_api_key(config_file_key=self.config.provider.api_key)
            if found:
                self._append_msg(
                    "Signed in as {} ({}/{}). To switch accounts, quit and run "
                    "`cerberus login` in a plain terminal.".format(
                        mask_key(found.key), found.source, found.kind
                    )
                )
            else:
                self._append_msg(
                    "Not signed in. Quit and run `cerberus login` in a plain "
                    "terminal (or set CERBERUS_API_KEY), then restart."
                )
        elif cmd == "/logout":
            from servers.auth.store import clear_stored_key

            if clear_stored_key():
                self._append_msg("Signed out — stored key cleared. Restart to sign in again.")
            else:
                self._append_msg(
                    "No stored credentials. If you use CERBERUS_API_KEY / "
                    "POLLINATIONS_API_KEY, unset it in your shell."
                )
        elif cmd == "/init":
            from servers.commands import init_project_file

            self._append_msg(init_project_file(self.config.workspace))
        elif cmd == "/add":
            from servers.commands import attach_files

            self._append_msg(attach_files(self.loop.messages, self.config.workspace, arg))
        elif cmd == "/diff":
            from servers.commands import workspace_diff_summary

            self._append_msg(workspace_diff_summary(self.config.workspace))
        elif cmd == "/compact":
            from servers.commands import compact_history

            self._append_msg(compact_history(self.loop.messages))
        elif cmd == "/save":
            self._slash_save(arg)
        elif cmd == "/load":
            self.action_load_session(arg)
        elif cmd == "/sessions":
            self._slash_sessions(arg)
        elif cmd == "/review":
            self._slash_review(arg)
        elif cmd == "/undo":
            self._slash_undo()
        elif cmd == "/tools":
            names = self.loop.registry.list_names()
            self._append_msg("Tools ({}): {}".format(len(names), ", ".join(names)))
        elif cmd == "/scan":
            self._slash_scan(arg)
        elif cmd == "/approvals":
            self._slash_approvals(arg)
        elif cmd == "/personas":
            from servers.agent.prompts import list_personas
            from servers.commands import persona_lines

            self._append_msg("\n".join(persona_lines(list_personas())))
        elif cmd == "/persona":
            from servers.agent.prompts import list_personas

            if not arg:
                current = self.persona_name or "agent (orchestrator)"
                self._append_msg(
                    "Talking to: {}  (/personas to browse, /persona <name> to switch)".format(current)
                )
            elif arg.strip().lower() not in list_personas():
                self._append_msg("Unknown persona: {}  (/personas to browse)".format(arg.strip()))
            elif self.running:
                self._append_msg("A run is already active — STOP it first, or wait.")
            else:
                self._switch_persona(arg.strip().lower())
        elif cmd == "/team":
            self._slash_team(arg)
        elif cmd == "/config":
            self._append_msg(
                "base_url: {}\nmodel: {}\nworkspace: {}\nmode: {}\nmax_rounds: {}".format(
                    self.config.provider.base_url, self.config.provider.model,
                    self.config.workspace, self.config.agent_mode,
                    self.config.tools.max_tool_rounds,
                )
            )
        elif cmd == "/workspace":
            self._slash_workspace(arg)
        else:
            self._append_msg("Unknown command: {}  (try /help)".format(cmd))

    def _slash_theme(self, arg: str) -> None:
        name = arg.strip().lower()
        if not name:
            self._append_msg("Theme: {}  (ctrl+t cycles, or /theme paper|dark|black)".format(self.ink_theme))
            return
        if name in {"paper", "light"}:
            self.set_ink_theme("paper")
        elif name == "dark":
            self.set_ink_theme("dark")
        elif name in {"black", "oled", "amoled", "pure"}:
            self.set_ink_theme("black")
        else:
            self._append_msg("Usage: /theme paper|dark|black")
            return
        self._append_msg("Theme → {}.".format(self.ink_theme))

    def _slash_mode(self, arg: str) -> None:
        if not arg:
            self._append_msg("Mode: {}  (Shift-Tab or /mode plan|yolo)".format(self.config.agent_mode))
            return
        a = arg.lower()
        if a in {"yolo", "accept-edits", "accept", "build"}:
            self.loop.set_mode("build")
            self.loop.registry.mode = "build"
            self._refresh_env()
            self._append_msg("Mode → ACCEPT-EDITS — the agent can now change files.")
        elif a in {"plan", "read-only", "readonly", "safe"}:
            self.loop.set_mode("plan")
            self.loop.registry.mode = "plan"
            self._refresh_env()
            self._append_msg("Mode → PLAN — read-only.")
        else:
            self._append_msg("Usage: /mode plan|yolo")

    def _slash_model(self, arg: str) -> None:
        from servers.commands import apply_model_meta, pick_model

        picked, message = pick_model(self.config, arg)
        if picked is not None:
            self.config.provider.model = picked
            note = apply_model_meta(self.config, picked)
            if note:
                message += f" · {note}"
            self._refresh_env()
        self._append_msg(message)

    def _slash_save(self, arg: str) -> None:
        import time as _time

        from servers.session_store import save_session

        name = arg or "session-{}".format(int(_time.time()))
        transcript = [m.to_api_dict() for m in self.loop.messages]
        path = save_session(name, transcript, model=self.config.provider.model, workspace=str(self.config.workspace))
        self._append_msg("Saved '{}' ({} messages) → {}".format(name, len(transcript), path))

    def _slash_sessions(self, arg: str = "") -> None:
        from servers.session_store import delete_session, fork_session, list_sessions

        parts = arg.split()
        if parts and parts[0] == "delete" and len(parts) == 2:
            try:
                ok = delete_session(parts[1])
            except Exception as exc:
                self._append_msg("Could not delete session: {}".format(exc))
                return
            self._append_msg(
                "Deleted session '{}'.".format(parts[1]) if ok
                else "Session not found: '{}'.".format(parts[1])
            )
            if self.view == "history":
                self.show_view("history")
            return
        if parts and parts[0] == "fork" and len(parts) == 3:
            try:
                path = fork_session(parts[2], parts[1])
            except FileNotFoundError:
                self._append_msg("Session not found: '{}'.".format(parts[2]))
                return
            except Exception as exc:
                self._append_msg("Could not fork session: {}".format(exc))
                return
            self._append_msg("Forked '{}' → '{}' ({}).".format(parts[2], parts[1], path))
            if self.view == "history":
                self.show_view("history")
            return
        if parts:
            self._append_msg("Usage: /sessions [delete <name>|fork <new> <src>]")
            return
        try:
            sessions = list_sessions()
        except Exception as exc:
            self._append_msg("Could not read sessions: {}".format(exc))
            return
        if not sessions:
            self._append_msg("No saved sessions.")
            return
        self._append_msg("\n".join("  {} ({} msgs)".format(s.name, s.message_count) for s in sessions))

    def _slash_workspace(self, arg: str) -> None:
        if not arg:
            self._append_msg("Workspace: {}".format(self.config.workspace))
            return
        new_ws = Path(arg).expanduser().resolve()
        if not new_ws.is_dir():
            self._append_msg("Not a directory: {}".format(new_ws))
            return
        self.config.workspace = new_ws
        self.loop.registry.workspace = new_ws
        self.loop.reset()
        self.show_view("task")
        self._append_msg("Workspace → {} (history reset)".format(new_ws))

    def _slash_approvals(self, arg: str) -> None:
        from servers.config import effective_tier, set_permission_tier

        tools = self.config.tools
        try:
            session = self.loop.registry.session_approvals()
        except Exception:
            session = []
        parts = arg.strip().lower().split()
        if not parts or parts[0] in {"status", "show"}:
            lines = [
                "Approvals — external (web/search/PR): {}".format(effective_tier(tools, "external")),
                "Approvals — builds (pytest/npm/make): {}".format(effective_tier(tools, "builds")),
            ]
            for key in sorted(tools.permissions):
                if key not in {"external", "builds"}:
                    lines.append("Approvals — {}: {}".format(key, tools.permissions[key]))
            lines.append("Always-allowed this run: {}".format(
                ", ".join(session) if session else "(none)"))
            self._append_msg("\n".join(lines))
            self._append_msg(
                "Usage: /approvals <external|builds> <on|off|ask|allow|deny> · /approvals reset")
            return
        if parts[0] == "reset":
            try:
                self.loop.registry.reset_session_approvals()
            except Exception:
                pass
            self._append_msg("Session approvals cleared — will ask again.")
            return
        if len(parts) == 2 and parts[0] in {"external", "builds"}:
            if parts[1] in {"on", "ask"}:
                tier = "ask"
            elif parts[1] in {"off", "allow"}:
                tier = "allow"
            elif parts[1] == "deny":
                tier = "deny"
            else:
                self._append_msg("Usage: /approvals <external|builds> <on|off|ask|allow|deny>")
                return
            set_permission_tier(tools, parts[0], tier)
            self._append_msg("Approvals → {}: {}".format(parts[0], tier))
            return
        self._append_msg("Usage: /approvals [external|builds] [on|off|ask|allow|deny] · /approvals reset")

    def _slash_team(self, arg: str) -> None:
        from servers.agent.prompts import list_personas
        from servers.commands import parse_team_arg

        names, task, err = parse_team_arg(arg, list_personas())
        if err:
            self._append_msg(err)
            return
        if self.running:
            self._append_msg("A run is already active — STOP it first, or wait.")
            return
        self._append_msg("Consulting team: {}…".format(", ".join(names)))
        self.run_worker(self._do_team(names, task), exclusive=True)

    def _fan_out_sync(self, names: list, task: str):
        from servers.agent.cerberus_swarm import CerberusSwarm
        from servers.provider.client import OpenAICompatibleClient

        client = OpenAICompatibleClient(self.config.provider, api_key=self.api_key)
        swarm = CerberusSwarm(config=self.config, client=client)
        return swarm.fan_out(
            [(name, task) for name in names],
            context="workspace: {}".format(self.config.workspace),
        )

    async def _do_team(self, names: list, task: str) -> None:
        import asyncio as _aio

        token = self.run_token + 1
        self.run_token = token
        self.running = True
        try:
            self.query_one("#stop", Button).disabled = False
        except Exception:
            pass
        try:
            reports = await _aio.to_thread(self._fan_out_sync, names, task)
            if token != self.run_token:
                return
            combined = []
            for rep in reports:
                self._append_msg(
                    "{} · {} · {} rounds · {:.1f}s\n{}".format(
                        rep.agent, rep.status, rep.tool_rounds,
                        rep.duration_seconds, rep.summary or "(no summary)",
                    )
                )
                combined.append("### {}\n{}".format(rep.agent, (rep.summary or "")[:1500]))
            try:
                from servers.models import Message

                self.loop.messages.append(Message(
                    role="user",
                    content="[team-context] Team findings ({}) on `{}`:\n\n{}".format(
                        ", ".join(names), task, "\n\n".join(combined)),
                ))
                self._append_msg("Team findings attached — ask follow-ups.")
            except Exception as exc:
                self._append_msg("(could not attach team findings: {})".format(exc))
        except Exception as exc:
            if token == self.run_token:
                self._append_msg("Team run failed: {}".format(exc))
        finally:
            if token == self.run_token:
                self.running = False
                try:
                    self.query_one("#stop", Button).disabled = True
                except Exception:
                    pass

    def _slash_review(self, arg: str) -> None:
        self._append_msg(
            "/review needs an interactive terminal — "
            "run `cerberus --classic` and type /review{} there.".format(
                " " + arg if arg else ""
            )
        )

    def _slash_undo(self) -> None:
        from servers.commands import git_working_tree

        modified, untracked, err = git_working_tree(self.config.workspace)
        if err:
            self._append_msg(err)
            return
        if not modified:
            self._append_msg("Nothing to undo — no tracked modifications.")
            return
        lines = ["Undo will restore to HEAD:"]
        lines.extend("  {}".format(p) for p in modified[:20])
        if len(modified) > 20:
            lines.append("  …and {} more".format(len(modified) - 20))
        self._append_msg("\n".join(lines))
        self.push_screen(
            ApprovalScreen(
                "git checkout -- {} file(s)".format(len(modified)),
                "Discards uncommitted changes to tracked files. Untracked files are kept.",
            ),
            lambda r: self._undo_decided(bool(r), modified),
        )

    def _undo_decided(self, approved: bool, modified: list) -> None:
        if not approved:
            self._append_msg("Undo cancelled.")
            return
        from servers.commands import git_restore_paths

        self._append_msg(git_restore_paths(self.config.workspace, modified))

    def _slash_scan(self, arg: str) -> None:
        import sys as _sys

        from servers.cli import EXAMINE_PY

        if not arg:
            self._append_msg("Usage: /scan <path-or-github-url>")
            return
        self._append_msg("⏳ Scanning {} with the deterministic engine…".format(arg))
        self.run_worker(self._do_scan(arg, _sys.executable, str(EXAMINE_PY)), exclusive=True)

    async def _do_scan(self, target: str, exe: str, examine: str) -> None:
        import json
        import subprocess
        import tempfile
        import time

        token = self.run_token + 1
        self.run_token = token
        self.running = True
        try:
            self.query_one("#stop", Button).disabled = False
        except Exception:
            pass
        try:
            # Write JSON report to a temp file so we get full structured data
            json_path = tempfile.mktemp(suffix=".json", prefix="cerberus-scan-")
            proc = await asyncio.to_thread(
                subprocess.run,
                [exe, examine, target, "--json", json_path],
                capture_output=True, text=True, timeout=300,
            )

            if token != self.run_token:
                return

            # If the scan failed, show the error from stderr
            if proc.returncode != 0:
                err = (proc.stderr or "").strip().splitlines()
                msg = err[-1] if err else "(unknown error)"
                self._append_msg(
                    "✖ Scan failed · {} (Scan exit {})".format(msg, proc.returncode)
                )
                return

            # Load the full report JSON
            try:
                import os
                with open(json_path, "r", encoding="utf-8") as f:
                    report = json.load(f)
            except Exception as exc:
                self._append_msg("✖ Could not read scan results: {}".format(exc))
                return
            finally:
                try:
                    os.remove(json_path)
                except Exception:
                    pass

            score = report.get("score", 0)
            grade = report.get("grade", "?")
            counts = report.get("counts", {})

            # Grade emoji
            grade_icon = {"A": "🟢", "B": "🟡", "C": "🟠", "D": "🔴", "F": "⛔"}.get(
                grade, "⬜"
            )

            # Build a rich inline summary
            lines = []
            lines.append("─" * 52)
            lines.append("  {} CERBERUS SCAN COMPLETE — {}/100  ({} {})".format(
                grade_icon, score, grade, grade_icon,
            ))
            lines.append("─" * 52)
            lines.append("")

            lines.append("")            # Counts summary (banner); per-agent detail follows as swarm cards.
            crit = counts.get("critical", 0)
            high = counts.get("high", 0)
            med = counts.get("medium", 0)
            low = counts.get("low", 0)
            passed = counts.get("pass", 0)
            failed = counts.get("fail", 0)
            total = counts.get("total", 0)
            agents = report.get("agents", []) or []
            lines.append("  {} specialist agents fanned out · {} passed · {} failed · {} total".format(
                len(agents), passed, failed, total))
            if crit or high:
                lines.append("  ⚠ critical={} high={} medium={} low={}".format(crit, high, med, low))
            lines.append("  Expand an agent below for its failed checks.")

            self._append_msg("\n".join(lines))
            lines = []
            try:
                from servers.scan_context import scan_agent_sections

                work = self.query_one("#work", VerticalScroll)
                for title, body in scan_agent_sections(report):
                    content = Static("\n".join(body), classes="step-why")
                    content.markup = False
                    box = Collapsible(content, title=title, collapsed=True)
                    box.add_class("step")
                    work.mount(box)
                work.scroll_end(animate=False)
            except Exception:
                pass

            # Generate HTML report and open in browser
            html_opened = False
            try:
                from servers.config import DEFAULT_CONFIG_DIR

                reports_dir = DEFAULT_CONFIG_DIR / "reports"
                reports_dir.mkdir(parents=True, exist_ok=True)

                # Build a filename from the target
                safe_name = target.replace("/", "-").replace("\\", "-").replace(".", "-").strip("-")
                ts = int(time.time())
                html_filename = "scan-{}-{}.html".format(safe_name, ts)
                html_path = reports_dir / html_filename

                # Import the renderer from examine.py
                import importlib.util
                spec = importlib.util.spec_from_file_location("examine", examine)
                examine_mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(examine_mod)

                html_content = examine_mod.render_html(report)
                html_path.write_text(html_content, encoding="utf-8")

                # Auto-open in browser
                import platform
                system = platform.system()
                if system == "Darwin":
                    await asyncio.to_thread(
                        subprocess.run, ["open", str(html_path)],
                        capture_output=True, timeout=10,
                    )
                elif system == "Linux":
                    await asyncio.to_thread(
                        subprocess.run, ["xdg-open", str(html_path)],
                        capture_output=True, timeout=10,
                    )
                elif system == "Windows":
                    await asyncio.to_thread(
                        subprocess.run, ["start", "", str(html_path)],
                        capture_output=True, timeout=10, shell=True,
                    )

                html_opened = True
                lines.append("  📄 Report → {}".format(html_path))
                lines.append("  🌐 Opened in browser")
            except Exception as exc:
                lines.append("  (could not generate HTML report: {})".format(exc))

            lines.append("  Scan exit {} · findings attached to chat".format(proc.returncode))
            lines.append("─" * 52)

            self._append_msg("\n".join(lines))
            try:
                from servers.scan_context import remember_scan

                self._append_msg(remember_scan(self.loop.messages, report, target))
            except Exception as exc:
                self._append_msg("(findings shown above but not attached: {})".format(exc))

        except Exception as exc:
            if token == self.run_token:
                self._append_msg("✖ Scan failed: {}".format(exc))
        finally:
            if token == self.run_token:
                self.running = False
                try:
                    self.query_one("#stop", Button).disabled = True
                except Exception:
                    pass

    # -- agent run ------------------------------------------------------------
    def _start_run(self, goal: str) -> None:
        from servers.ui.narrate import describe_activity

        token = self.run_token + 1
        self.run_token = token
        self.running = True
        self._blocks = {}
        self._steps = {}
        try:
            self.query_one("#stop", Button).disabled = False
        except Exception:
            pass
        if self.view != "task":
            self.show_view("task")
        # Echo the request immediately so submit never feels dead, then show
        # a live thinking pulse until the first streamed token or tool step.
        try:
            work = self.query_one("#work", VerticalScroll)
            you = Static("❯ {}".format(goal), classes="you")
            you.markup = False
            work.mount(you)
            self._thinking_start = time.monotonic()
            self._thinking_run = token
            self._thinking_widget = Static("Thinking.", classes="thinking")
            self._thinking_widget.markup = False
            work.mount(self._thinking_widget)
            work.scroll_end(animate=False)
            try:
                if getattr(self, "_thinking_timer", None) is not None:
                    self._thinking_timer.stop()
            except Exception:
                pass
            self._thinking_timer = self.set_interval(0.4, self._pulse_thinking)
        except Exception:
            pass
        app = self

        def on_tool_start(tc, args):
            name = getattr(getattr(tc, "function", tc), "name", "?")
            try:
                headline, reason = describe_activity(name, dict(args or {}))
            except Exception:
                headline, reason = ("Working", "continuing the task")
            detail = ""
            try:
                shown = {k: (str(v)[:80]) for k, v in (args or {}).items()}
                detail = ", ".join("{}={}".format(k, v) for k, v in shown.items())
            except Exception:
                pass
            app.post_message(ToolStarted(token, getattr(tc, "id", name), headline, reason, detail))

        def on_tool_end(tc, result):
            line = (str(result or "").strip().splitlines() or ["(no output)"])[0][:140]
            app.post_message(ToolEnded(token, getattr(tc, "id", getattr(tc, "function", "")), line))

        def on_stream_delta(chunk):
            app.post_message(Streamed(token, chunk))

        # AgentLoop takes callbacks at construction; attach them around run().
        self.run_worker(
            lambda: self._execute_sync(token, goal, on_tool_start, on_tool_end, on_stream_delta),
            thread=True,
            exclusive=True,
        )

    def _execute_sync(self, token, goal, on_tool_start, on_tool_end, on_stream_delta):
        from servers.provider.client import ProviderError

        try:
            result = self._run_with_callbacks(goal, on_tool_start, on_tool_end, on_stream_delta)
        except ProviderError as exc:
            # Post RunDone (not just a message) so running/thinking reset.
            self.post_message(RunDone(token, "Provider error: {}".format(exc), 0, "error", ""))
            return
        except Exception as exc:
            self.post_message(RunDone(token, "Run failed: {}".format(exc), 0, "error", ""))
            return
        try:
            usage = result.usage.format_short()
        except Exception:
            usage = ""
        self.post_message(RunDone(token, result.final_text or "", result.tool_rounds, result.stopped_reason, usage))

    def _run_with_callbacks(self, goal, on_tool_start, on_tool_end, on_stream_delta):
        # Temporarily attach callbacks (AgentLoop takes them at construction).
        loop = self.loop
        saved = (loop.on_tool_start, loop.on_tool_end, loop.on_assistant_text, loop.on_status, loop.on_stream_delta)
        loop.on_tool_start = on_tool_start
        loop.on_tool_end = on_tool_end
        loop.on_assistant_text = lambda _t: None
        loop.on_stream_delta = on_stream_delta
        try:
            return loop.run(goal)
        finally:
            (loop.on_tool_start, loop.on_tool_end, loop.on_assistant_text, loop.on_status, loop.on_stream_delta) = saved


def run_tui(config, api_key: str = "", *, persona_name=None, preload_messages=None) -> int:
    """Launch the Ink full-screen workbench. Returns the app exit code."""
    app = InkApp(config, api_key, persona_name=persona_name, preload_messages=preload_messages)
    app.run()
    return 0


class TaskView(Static):
    """Idle welcome: question, recent sessions, local tasks."""

    def __init__(self, app: "InkApp") -> None:
        super().__init__("")
        self._app = app

    def on_mount(self) -> None:
        from servers.session_store import list_sessions

        lines = ["What are we building?", ""]
        try:
            sessions = list_sessions()
        except Exception:
            sessions = []
        if sessions:
            lines.append("PICK UP WHERE YOU LEFT OFF")
            for s in sessions[:3]:
                lines.append("  › {} ({} msgs)".format(s.name, s.message_count))
            lines.append("")
        lines.append("RECENT WORK")
        recent = sessions
        if recent:
            for s in recent:
                lines.append("  ○ {} · model={}".format(s.name, s.model or "-"))
        else:
            lines.append("  No saved sessions yet — run something, then /save name.")
        lines.append("")
        lines.append("Type a task below, or /scan owner/repo for a security audit.")
        self.update("\n".join(lines))


class FilesView(Vertical):
    """Workspace file tree + viewer."""

    SKIP = {".git", "__pycache__", ".venv", "node_modules", ".DS_Store", ".mypy_cache", ".pytest_cache"}

    def __init__(self, workspace) -> None:
        super().__init__()
        self.workspace = Path(workspace)

    def compose(self) -> ComposeResult:
        yield Static("FILES", classes="sec-label")
        tree = Tree(str(self.workspace))
        tree.root.expand()
        self._fill(tree.root, self.workspace, 0)
        yield tree
        yield Static("", id="fileview")

    def _fill(self, node, path: Path, depth: int) -> None:
        if depth > 4:
            return
        try:
            entries = sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
        except OSError:
            return
        count = 0
        for e in entries:
            if e.name in self.SKIP:
                continue
            if e.name.startswith(".") and e.name != ".cerberusignore":
                continue
            if count >= 200:
                node.add_leaf("… (truncated)")
                return
            count += 1
            if e.is_dir():
                sub = node.add(e.name + "/", expand=False)
                self._fill(sub, e, depth + 1)
            else:
                leaf = node.add_leaf(e.name)
                leaf.data = e

    @on(Tree.NodeSelected)
    def show_file(self, event: Tree.NodeSelected) -> None:
        node = event.node
        if not getattr(node, "data", None):
            return
        try:
            text = Path(node.data).read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            text = "Could not read file: {}".format(exc)
        lines = text.split("\n")[:500]
        numbered = "\n".join("{:4d}  {}".format(i + 1, ln[:160]) for i, ln in enumerate(lines))
        try:
            self.query_one("#fileview", Static).update("$ {}\n{}".format(node.data, numbered))
        except Exception:
            pass


class ChangesView(Vertical):
    """Real git diff for the workspace — honest empty state otherwise."""

    def __init__(self, workspace) -> None:
        super().__init__()
        self.workspace = Path(workspace)

    def compose(self) -> ComposeResult:
        yield Static("CHANGES · git diff", classes="sec-label")
        import subprocess

        try:
            proc = subprocess.run(
                ["git", "-C", str(self.workspace), "diff", "--stat"],
                capture_output=True, text=True, timeout=20, check=False,
            )
        except Exception as exc:
            yield Static("Could not run git: {}".format(exc))
            return
        if proc.returncode != 0:
            yield Static("Not a git repository (or git is missing). Diff view needs a checkout.")
            return
        stat = proc.stdout.strip()
        if not stat:
            yield Static("Workspace clean — no uncommitted changes.")
            return
        yield Static(stat)
        try:
            full = subprocess.run(
                ["git", "-C", str(self.workspace), "diff", "--", ".", ":(exclude)yarn.lock", ":(exclude)package-lock.json"],
                capture_output=True, text=True, timeout=20, check=False,
            ).stdout
        except Exception:
            full = ""
        body = []
        for ln in full.split("\n")[:400]:
            if ln.startswith("+") and not ln.startswith("+++"):
                body.append("[green]{}[/]".format(ln[:200]))
            elif ln.startswith("-") and not ln.startswith("---"):
                body.append("[red]{}[/]".format(ln[:200]))
            else:
                body.append(ln[:200])
        yield Static("\n".join(body) if body else "(diff body withheld)")


class HistoryView(Vertical):
    """Saved sessions from the session store; click to reopen."""

    def compose(self) -> ComposeResult:
        from servers.session_store import list_sessions

        yield Static("HISTORY", classes="sec-label")
        try:
            sessions = list_sessions()
        except Exception as exc:
            yield Static("Could not read sessions: {}".format(exc))
            return
        if not sessions:
            yield Static("No saved sessions yet — run something, then /save name.")
            return
        items = []
        for s in sessions:
            items.append(ListItem(Label("{} ({} msgs) · {}".format(s.name, s.message_count, s.model or "-")), id="sess-" + s.name))
        yield ListView(*items, id="hist-list")

    @on(ListView.Selected)
    def reopen(self, event: ListView.Selected) -> None:
        label = str(event.item.query_one(Label).render())
        name = label.split(" (")[0]
        app = self.app
        if isinstance(app, InkApp):
            app.action_load_session(name)


