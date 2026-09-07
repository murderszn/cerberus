"""TUI markup regression tests for the Textual workbench.

Dynamic content (tool reasons, model text, session names, diffs) routinely
contains ``[``/``]`` sequences. Mounted in a ``Static`` with markup enabled,
a glob like ``[*.html]`` raised ``MarkupError: Expected markup value`` and a
lone ``[/]`` raised ``auto closing tag has nothing to close`` — both crashed
app layout on launch. Every dynamic widget must render literally.
"""

import asyncio
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

try:
    from servers.ui.tui import ApprovalScreen, InkApp, RunDone, ToolEnded, ToolStarted

    HAS_TUI = True
except ImportError:  # textual not installed (stdlib-only CI)
    HAS_TUI = False

ROOT = Path(__file__).resolve().parents[1]

NASTY_HEADLINE = "read [*.html] files [/]"
NASTY_REASON = "glob [pattern=*.html] in ./[bracket]"
NASTY_DETAIL = "ls [mode=*.html] -> [/]"
NASTY_OUTCOME = "ok [/] 3 files [x=*.html]"
NASTY_TEXT = "model said [/] with [bold]not-bold[/] and [link=*.html]y[/link]"


def make_config(workspace):
    from servers.config import load_config

    cfg = load_config(ROOT / "does-not-exist.yaml")
    cfg.workspace = Path(workspace)
    return cfg


class StubLoop:
    """Minimal AgentLoop duck-type; never runs anything."""

    def __init__(self, config):
        self.config = config
        self.registry = SimpleNamespace(mode="plan", workspace=config.workspace)
        self.messages = []
        self.cancelled = False

    def set_mode(self, mode):
        self.config.agent_mode = mode

    def reset(self):
        self.messages = []

    def request_cancel(self):
        self.cancelled = True

    def run(self, goal):
        raise AssertionError("must not run in markup tests")


@unittest.skipUnless(HAS_TUI, "textual not installed")
class TuiMarkupTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        Path(self.tmp.name, "a.py").write_text("print(1)\n", encoding="utf-8")
        self.cfg = make_config(self.tmp.name)
        store_patch = mock.patch("servers.session_store.list_sessions", return_value=[])
        self.addCleanup(store_patch.stop)
        store_patch.start()

    def tearDown(self):
        self.tmp.cleanup()

    def make_app(self, **kw):
        kw.setdefault("loop_factory", StubLoop)
        return InkApp(self.cfg, "dummy-key", **kw)

    async def wait_for(self, cond, timeout=8.0):
        loop = asyncio.get_event_loop()
        end = loop.time() + timeout
        while loop.time() < end:
            if cond():
                return True
            await asyncio.sleep(0.05)
        return False

    def work_text(self, app):
        """Render every Static in #work — raises MarkupError if markup leaks."""
        work = app.query_one("#work")
        return "\n".join(str(w.render()) for w in work.query("Static"))

    async def test_tool_step_with_markup_chars(self):
        app = self.make_app()
        async with app.run_test() as pilot:
            app.post_message(
                ToolStarted(app.run_token, "t1", NASTY_HEADLINE, NASTY_REASON, NASTY_DETAIL)
            )
            await pilot.pause()
            await pilot.pause()
            app.post_message(ToolEnded(app.run_token, "t1", NASTY_OUTCOME))
            await pilot.pause()
            await pilot.pause()
            body = self.work_text(app)  # must not raise
            self.assertIn("[*.html]", body)
            self.assertIn("[/]", body)

    async def test_run_done_with_markup_chars(self):
        app = self.make_app()
        async with app.run_test() as pilot:
            app.post_message(
                RunDone(app.run_token, NASTY_TEXT, rounds=2, stopped="completed", usage="1k")
            )
            await pilot.pause()
            await pilot.pause()
            body = self.work_text(app)  # must not raise
            self.assertIn("[/]", body)
            self.assertIn("[bold]not-bold[/]", body)

    async def test_history_and_welcome_with_markup_session_names(self):
        nasty = [
            SimpleNamespace(name="we[/]ird", message_count=3, model="[*.html]", updated_at=0),
            SimpleNamespace(name="[bold]x[/]", message_count=1, model="m", updated_at=0),
        ]
        app = self.make_app()
        async with app.run_test() as pilot:
            with mock.patch("servers.session_store.list_sessions", return_value=nasty):
                app.show_view("history")
                await pilot.pause()
                await pilot.pause()
                body = self.work_text(app)  # must not raise
            self.assertIn("we[/]ird", body)

    async def test_approval_dialog_renders_command_literally(self):
        app = self.make_app()
        async with app.run_test() as pilot:
            await app.push_screen(ApprovalScreen("rm -rf [*.html]", "reason [/] here"))
            await pilot.pause()
            await pilot.pause()
            texts = []
            for w in app.screen.query("Static"):
                try:
                    texts.append(str(w.render()))  # must not raise
                except Exception as exc:  # pragma: no cover
                    self.fail("dialog render raised: {}".format(exc))
            self.assertTrue(any("[*.html]" in t for t in texts))
            self.assertTrue(any("[/]" in t for t in texts))


if __name__ == "__main__":
    unittest.main()
