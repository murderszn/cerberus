"""Headless Textual pilot tests for the Ink workbench.

Requires textual: skipped entirely on stdlib-only CI runners. Everything
else stays hermetic (stubbed loop, temp workspace, mocked session store).
"""

import asyncio
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

try:
    from servers.ui.tui import InkApp

    HAS_TUI = True
except ImportError:
    HAS_TUI = False

ROOT = Path(__file__).resolve().parents[1]


def make_config(workspace):
    from servers.config import load_config

    cfg = load_config(ROOT / "does-not-exist.yaml")
    cfg.workspace = Path(workspace)
    return cfg


class StubRegistry:
    def __init__(self):
        self.mode = "plan"
        self.workspace = Path("/tmp")

    def list_names(self):
        return ["read_file", "execute_bash_command"]


class StubLoop:
    """Duck-typed AgentLoop: callbacks fire synchronously inside run()."""

    def __init__(self, config):
        self.config = config
        self.registry = StubRegistry()
        self.registry.workspace = config.workspace
        self.messages = []
        self.on_tool_start = None
        self.on_tool_end = None
        self.on_assistant_text = None
        self.on_status = None
        self.on_stream_delta = None
        self.cancelled = False
        self.block = None  # optional threading.Event to hold run() open

    def set_mode(self, mode):
        if mode not in {"build", "plan"}:
            raise ValueError(mode)
        self.config.agent_mode = mode

    def reset(self):
        self.messages = []

    def request_cancel(self):
        self.cancelled = True

    def run(self, goal):
        from servers.agent.loop import LoopResult
        from servers.models import TokenUsage

        tc = SimpleNamespace(id="t1", function=SimpleNamespace(name="read_file"))
        if self.on_tool_start:
            self.on_tool_start(tc, {"path": "a.py"})
        if self.block is not None:
            self.block.wait(timeout=10)
        if self.on_tool_end:
            self.on_tool_end(tc, "contents of a.py")
        if self.on_stream_delta:
            self.on_stream_delta("working…")
        if self.cancelled:
            return LoopResult(final_text="Stopped by user.", tool_rounds=1,
                              messages=self.messages, stopped_reason="cancelled",
                              usage=TokenUsage())
        return LoopResult(final_text="done: " + goal, tool_rounds=1,
                          messages=self.messages, stopped_reason="completed",
                          usage=TokenUsage())


@unittest.skipUnless(HAS_TUI, "textual not installed")
class InkTuiTest(unittest.IsolatedAsyncioTestCase):
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
        work = app.query_one("#work")
        return "\n".join(str(w.render()) for w in work.query("Static"))

    async def test_boot_layout(self):
        app = self.make_app()
        async with app.run_test() as pilot:
            for nid in ("#nav-task", "#nav-files", "#nav-changes", "#nav-history"):
                self.assertIsNotNone(app.query_one(nid), nid)
            self.assertIsNotNone(app.query_one("#prompt"))
            foot = str(app.query_one("#foot").render())
            self.assertIn("shift+tab", foot)
            self.assertIn("What are we building?", self.work_text(app))
            await pilot.pause()

    async def test_sidebar_click_targets(self):
        # Deterministic mouse coverage: every nav button must be the
        # topmost widget at its own center (no overlaps), and pressing
        # it must route to the view.
        from textual.widgets import Button

        app = self.make_app()
        async with app.run_test(size=(130, 32)) as pilot:
            await pilot.pause()
            await pilot.pause()
            for view in ("task", "files", "changes", "history"):
                btn = app.query_one("#nav-" + view, Button)
                r = btn.content_region
                top, _ = app.screen.get_widget_at(
                    r.x + r.width // 2, r.y + r.height // 2
                )
                self.assertIs(top, btn, "overlap over nav-" + view)
                btn.press()
                await pilot.pause()
                self.assertEqual(app.view, view)

    async def test_sidebar_switches_views(self):
        app = self.make_app()
        async with app.run_test() as pilot:
            app.show_view("files")
            await pilot.pause()

            def tree_labels():
                trees = list(app.query("Tree"))
                if not trees or not trees[0].root:
                    return []
                return [str(n.label) for n in trees[0].root.children]

            self.assertTrue(
                await self.wait_for(lambda: "a.py" in tree_labels()),
                "file tree never populated",
            )
            app.show_view("history")
            await pilot.pause()
            self.assertIn("No saved sessions", self.work_text(app))
            app.show_view("changes")
            await pilot.pause()
            self.assertTrue(
                "clean" in self.work_text(app).lower() or "git" in self.work_text(app).lower()
            )

    async def test_slash_help_mode_model(self):
        app = self.make_app()
        async with app.run_test() as pilot:
            app.submit_text("/help")
            await pilot.pause()
            self.assertIn("/scan", self.work_text(app))
            app.submit_text("/mode yolo")
            await pilot.pause()
            self.assertEqual(self.cfg.agent_mode, "build")
            self.assertIn("ACCEPT-EDITS", self.work_text(app))
            app.submit_text("/mode plan")
            await pilot.pause()
            self.assertEqual(self.cfg.agent_mode, "plan")
            app.submit_text("/model deepseek")
            await pilot.pause()
            self.assertEqual(self.cfg.provider.model, "deepseek")

    async def test_run_streams_activity_and_answer(self):
        app = self.make_app()
        async with app.run_test() as pilot:
            app.submit_text("do the thing")
            done = await self.wait_for(lambda: not app.running, timeout=10.0)
            self.assertTrue(done, "run did not finish")
            await pilot.pause()
            body = self.work_text(app)
            self.assertIn("Reading", body)
            self.assertIn("done: do the thing", body)
            self.assertTrue(app.query_one("#stop").disabled)

    async def test_stop_requests_cancel(self):
        import threading

        app = self.make_app()
        async with app.run_test() as pilot:
            app.loop.block = threading.Event()
            app.submit_text("long task")
            self.assertTrue(await self.wait_for(lambda: app.running, timeout=5.0))
            self.assertFalse(app.query_one("#stop").disabled)
            app.action_stop_or_close()
            self.assertTrue(app.loop.cancelled)
            app.loop.block.set()
            self.assertTrue(await self.wait_for(lambda: not app.running, timeout=10.0))
            await pilot.pause()
            self.assertIn("cancelled", self.work_text(app))

    async def test_scan_slash_reports_exit(self):
        app = self.make_app()
        async with app.run_test() as pilot:
            app.submit_text("/scan " + self.tmp.name)
            done = await self.wait_for(
                lambda: "Scan exit" in self.work_text(app), timeout=30.0
            )
            self.assertTrue(done, "scan report line missing")

    async def test_scan_mounts_agent_cards(self):
        from textual.widgets import Collapsible

        app = self.make_app()
        async with app.run_test() as pilot:
            app.submit_text("/scan " + self.tmp.name)
            done = await self.wait_for(
                lambda: "Scan exit" in self.work_text(app), timeout=30.0
            )
            self.assertTrue(done, "scan report line missing")
            await pilot.pause()
            cards = [
                c for c in app.query(Collapsible)
                if "/" in str(getattr(c, "title", "")) and "—" in str(getattr(c, "title", ""))
            ]
            self.assertEqual(len(cards), 9)
            self.assertTrue(any("SENTINEL" in str(getattr(c, "title", "")) for c in cards))

    async def test_persona_switch_keeps_history(self):
        from servers.models import Message

        app = self.make_app()
        async with app.run_test() as pilot:
            app.loop.messages.append(Message(role="user", content="hi"))
            app.submit_text("/personas")
            await pilot.pause()
            self.assertIn("sentinel", self.work_text(app))
            app.submit_text("/persona vault")
            await pilot.pause()
            self.assertEqual(app.persona_name, "vault")
            self.assertTrue(any(m.content == "hi" for m in app.loop.messages))
            self.assertIn("Now talking to vault", self.work_text(app))
            self.assertIn("vault", str(app.query_one("#env").render()))
            app.submit_text("/persona frobnicate")
            await pilot.pause()
            self.assertEqual(app.persona_name, "vault")
            self.assertIn("Unknown persona", self.work_text(app))

    async def test_team_usage_error(self):
        app = self.make_app()
        async with app.run_test() as pilot:
            app.submit_text("/team")
            await pilot.pause()
            self.assertIn("Usage", self.work_text(app))

    async def test_composer_attach_and_bang_routing(self):
        from servers.ui.tui import SubmitArea

        app = self.make_app()
        async with app.run_test() as pilot:
            # @file attaches without starting a run.
            app.submit_text("@a.py")
            await pilot.pause()
            self.assertFalse(app.running)
            self.assertIn("Attached 1 file", self.work_text(app))
            self.assertEqual(len(app.loop.messages), 1)
            # !cmd without registry dispatch reports failure, no run.
            app.submit_text("!echo hi")
            done = await self.wait_for(lambda: not app.running, timeout=10.0)
            self.assertTrue(done)
            await pilot.pause()
            body = self.work_text(app)
            self.assertIn("❯ !echo hi", body)

    async def test_ctrl_c_cancels_run(self):
        import threading

        app = self.make_app()
        async with app.run_test() as pilot:
            app.loop.block = threading.Event()
            app.submit_text("long task")
            self.assertTrue(await self.wait_for(lambda: app.running, timeout=5.0))
            await pilot.press("ctrl+c")
            self.assertTrue(app.loop.cancelled)
            app.loop.block.set()
            self.assertTrue(await self.wait_for(lambda: not app.running, timeout=10.0))

    async def test_question_opens_palette(self):
        from textual.command import CommandPalette

        app = self.make_app()
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("?")
            await pilot.pause()
            self.assertIsInstance(app.screen, CommandPalette)
            await pilot.press("escape")
            await pilot.pause()

    async def test_question_types_when_composer_busy(self):
        from servers.ui.tui import SubmitArea

        app = self.make_app()
        async with app.run_test() as pilot:
            area = app.query_one("#prompt", SubmitArea)
            area.load_text("what?")
            area.action_cursor_line_end()
            await pilot.press("?")
            await pilot.pause()
            self.assertEqual(area.text, "what??")

    async def test_approvals_tier_display(self):
        app = self.make_app()
        async with app.run_test() as pilot:
            app.submit_text("/approvals external deny")
            await pilot.pause()
            self.assertIn("external: deny", self.work_text(app))
            self.assertTrue(app.config.tools.approve_external)

    async def test_undo_and_review_hints(self):
        app = self.make_app()
        async with app.run_test() as pilot:
            app.submit_text("/undo")
            await pilot.pause()
            body = self.work_text(app)
            self.assertTrue("Not a git repo" in body or "Nothing to undo" in body)
            app.submit_text("/review")
            await pilot.pause()
            self.assertIn("--classic", self.work_text(app))

    async def test_preload_resumes_history(self):
        from servers.models import Message

        msgs = [Message(role="user", content="earlier")]
        app = self.make_app(preload_messages=msgs)
        async with app.run_test() as pilot:
            await pilot.pause()
            self.assertIn("Resumed session (1 messages)", self.work_text(app))
            self.assertTrue(any(m.content == "earlier" for m in app.loop.messages))

    async def test_inline_autocomplete(self):
        from servers.ui.tui import SubmitArea

        app = self.make_app()
        async with app.run_test() as pilot:
            area = app.query_one("#prompt", SubmitArea)
            await pilot.press("/", "p", "e", "r")
            shown = await self.wait_for(
                lambda: "/persona" in str(app.query_one("#suggest-rows").render()),
                timeout=5.0,
            )
            self.assertTrue(shown, "suggest list missing /persona")
            body = str(app.query_one("#suggest-rows").render())
            self.assertIn("/personas", body)
            # Down moves the highlight, Tab completes it.
            await pilot.press("down", "tab")
            await pilot.pause()
            self.assertEqual(area.text, "/personas ")
            self.assertFalse(app._suggest_visible())
            # Typing a new fragment then Esc dismisses without completing.
            await pilot.press("backspace", "backspace", "backspace", "backspace",
                              "backspace", "backspace", "backspace", "backspace",
                              "backspace", "backspace", "/", "m", "o")
            shown = await self.wait_for(
                lambda: "/mode" in str(app.query_one("#suggest-rows").render()),
                timeout=5.0,
            )
            self.assertTrue(shown, "suggest list missing /mode")
            await pilot.press("escape")
            await pilot.pause()
            self.assertFalse(app._suggest_visible())
            self.assertEqual(area.text, "/mo")

    async def test_narrow_layout_collapses_sidebar(self):
        from textual.widgets import Button

        app = self.make_app()
        async with app.run_test(size=(70, 22)) as pilot:
            await pilot.pause()
            self.assertTrue(app.screen.has_class("narrow"))
            self.assertFalse(app.query_one("#side").display)
            self.assertTrue(app.query_one("#topnav").display)
            self.assertFalse(app.query_one("#foot").display)
            self.assertTrue(app.query_one("#foot-narrow").display)
            app.query_one("#tnav-files", Button).press()
            await pilot.pause()
            self.assertEqual(app.view, "files")

    async def test_wide_layout_keeps_sidebar(self):
        app = self.make_app()
        async with app.run_test(size=(130, 32)) as pilot:
            await pilot.pause()
            self.assertFalse(app.screen.has_class("narrow"))
            self.assertTrue(app.query_one("#side").display)
            self.assertFalse(app.query_one("#topnav").display)

    async def test_dark_toggle(self):
        app = self.make_app()
        async with app.run_test() as pilot:
            self.assertFalse(app.screen.has_class("dark"))
            app.action_toggle_dark()
            await pilot.pause()
            self.assertTrue(app.screen.has_class("dark"))
            self.assertIn("dark", self.work_text(app))
            app.action_toggle_dark()
            await pilot.pause()
            self.assertFalse(app.screen.has_class("dark"))

    async def test_run_shows_thinking_then_clears(self):
        import threading

        gate = threading.Event()

        class SlowLoop(StubLoop):
            def run(self, goal):
                gate.wait(timeout=10)
                return super().run(goal)

        app = self.make_app(loop_factory=SlowLoop)
        async with app.run_test() as pilot:
            app.submit_text("do the thing")
            # While the worker is stuck before first output, the pulse shows.
            shown = await self.wait_for(lambda: "Thinking" in self.work_text(app),
                                        timeout=5.0)
            self.assertTrue(shown, "no waiting indicator during latency")
            self.assertIn("❯ do the thing", self.work_text(app))
            gate.set()
            done = await self.wait_for(lambda: not app.running, timeout=10.0)
            self.assertTrue(done, "run did not finish")
            await pilot.pause()
            body = self.work_text(app)
            self.assertNotIn("Thinking", body)
            self.assertIn("done: do the thing", body)

    async def test_run_failure_resets_state(self):
        class BoomLoop(StubLoop):
            def run(self, goal):
                raise RuntimeError("boom")

        app = self.make_app(loop_factory=BoomLoop)
        async with app.run_test() as pilot:
            app.submit_text("blow up")
            done = await self.wait_for(lambda: not app.running, timeout=10.0)
            self.assertTrue(done, "failed run left running=True")
            await pilot.pause()
            body = self.work_text(app)
            self.assertIn("Run failed: boom", body)
            self.assertNotIn("Thinking", body)
            self.assertTrue(app.query_one("#stop").disabled)

    async def test_chrome_fits_terminal_width(self):
        # SEND/STOP once overflowed their column (Button min-width: 16).
        # Chrome (everything outside #work) must never cross the edge.
        for size in ((70, 22), (80, 24), (130, 32), (200, 50)):
            app = self.make_app()
            async with app.run_test(size=size) as pilot:
                await pilot.pause()
                await pilot.pause()
                sw = app.screen.size.width
                for q in ("#head", "#topnav", "#side", "#compose", "#foot", "#foot-narrow"):
                    try:
                        w = app.query_one(q)
                    except Exception:
                        continue
                    if not w.display:
                        continue
                    for sub in [w] + list(w.walk_children()):
                        try:
                            r = sub.region
                        except Exception:
                            continue
                        self.assertLessEqual(
                            r.right, sw,
                            "{} overflows at {}: {!r} right={} screen={}".format(
                                q, size, getattr(sub, "id", type(sub).__name__), r.right, sw),
                        )

    async def test_palette_opens(self):
        app = self.make_app()
        async with app.run_test() as pilot:
            await pilot.press("ctrl+k")
            await pilot.pause()
            from textual.command import CommandPalette

            self.assertIsInstance(app.screen, CommandPalette)
            await pilot.press("escape")
            await pilot.pause()


if __name__ == "__main__":
    unittest.main()
