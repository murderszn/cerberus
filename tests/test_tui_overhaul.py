"""Regression tests for the scrollback-first terminal overhaul."""

from __future__ import annotations

import tempfile
import unittest
from io import StringIO
from pathlib import Path

from rich.console import Console

from servers.cli import _make_completer, build_parser
from servers.config import AppConfig, load_config
from servers.models import ChatChoice, ChatCompletion, Message, ToolCall, ToolCallFunction
from servers.models_catalog import estimate_cost
from servers.provider.client import OpenAICompatibleClient
from servers.tools.edit import edit_file
from servers.tools.files import write_file
from servers.ui.console import TerminalUI


class ScrollbackDefaultTest(unittest.TestCase):
    def test_workbench_is_opt_in(self) -> None:
        self.assertFalse(build_parser().parse_args([]).workbench)
        self.assertTrue(build_parser().parse_args(["--workbench"]).workbench)

    def test_banner_is_three_lines(self) -> None:
        buf = StringIO()
        ui = TerminalUI(console=Console(file=buf, force_terminal=False, width=80))
        ui.banner(model="claude-sonnet", base_url="ignored", workspace="/work", mode="plan")
        self.assertEqual(len(buf.getvalue().splitlines()), 3)
        self.assertIn("CERBERUS", buf.getvalue())

    def test_compact_tool_uses_one_completed_line(self) -> None:
        buf = StringIO()
        ui = TerminalUI(console=Console(file=buf, force_terminal=False, width=80))
        call = ToolCall(
            id="one",
            type="function",
            function=ToolCallFunction(name="read_file", arguments="{}"),
        )
        ui.tool_start(call, {"path": "server/db.py"})
        ui.spinner_stop()
        ui.tool_end(call, "path: server/db.py")
        lines = [line for line in buf.getvalue().splitlines() if line.strip()]
        self.assertEqual(len(lines), 1)
        self.assertIn("Read server/db.py", lines[0])


class ComposerCompletionTest(unittest.TestCase):
    def test_at_file_completion(self) -> None:
        try:
            from prompt_toolkit.document import Document
        except ImportError:
            self.skipTest("prompt_toolkit unavailable")
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "server.py").write_text("pass\n", encoding="utf-8")
            completer = _make_completer(Path(tmp))
            assert completer is not None
            values = [c.text for c in completer.get_completions(Document("@ser"), None)]
            self.assertIn("@server.py ", values)


class InlineDiffTest(unittest.TestCase):
    def test_write_and_edit_return_unified_diffs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            created = write_file("a.py", "one\n", workspace=ws)
            changed = edit_file("a.py", "one", "two", workspace=ws)
            self.assertIn("CERBERUS_EDIT_DIFF", created)
            self.assertIn("+one", created)
            self.assertIn("-one", changed)
            self.assertIn("+two", changed)


class ContextAndCostTest(unittest.TestCase):
    def test_context_window_loads(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp, "config.json")
            path.write_text('{"context_window": 64000}', encoding="utf-8")
            config = load_config(path, project_dir=Path(tmp))
            self.assertEqual(config.context_window, 64_000)
        self.assertEqual(AppConfig().context_window, 128_000)

    def test_known_and_unknown_costs(self) -> None:
        self.assertEqual(estimate_cost("gpt-4o", 1_000_000, 0), 2.5)
        self.assertIsNone(estimate_cost("kimi", 1000, 1000))

    def test_agent_auto_compacts_at_eighty_percent(self) -> None:
        from servers.agent.loop import AgentLoop

        class Client:
            last_usage = {}
            on_retry = None

            def chat(self, messages, tools=None, model=None):
                return ChatCompletion(
                    id="test",
                    model="test",
                    choices=[ChatChoice(message=Message(role="assistant", content="done"))]
                )

        class Registry:
            def openai_tools(self):
                return []

        config = AppConfig(context_window=100)
        config.provider.stream_final = False
        statuses: list[str] = []
        loop = AgentLoop(config, Client(), Registry(), on_status=statuses.append)
        loop.messages.extend(Message(role="user", content="x" * 60) for _ in range(12))
        loop.run("finish")
        self.assertTrue(any("Auto-compacted" in status for status in statuses))
        self.assertLess(len(loop.messages), 15)

    def test_rate_limit_retry_emits_status(self) -> None:
        try:
            import httpx
        except ImportError:
            self.skipTest("httpx unavailable")
        attempts = 0

        def handler(request):
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                return httpx.Response(429, headers={"retry-after": "0"}, text="slow down")
            return httpx.Response(
                200,
                json={"choices": [{"message": {"role": "assistant", "content": "ok"}}]},
            )

        client = OpenAICompatibleClient(AppConfig().provider)
        client._client.close()
        client._client = httpx.Client(
            base_url="https://example.test", transport=httpx.MockTransport(handler)
        )
        notices: list[str] = []
        client.on_retry = notices.append
        result = client.chat([Message(role="user", content="hi")])
        client.close()
        self.assertEqual(result.first_message.content, "ok")
        self.assertEqual(attempts, 2)
        self.assertIn("attempt 2/3", notices[0])


if __name__ == "__main__":
    unittest.main()
