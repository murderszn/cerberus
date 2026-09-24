"""Sprout-treatment regression tests: load box, motion, and tool cards."""

from __future__ import annotations

import unittest
from io import StringIO

from rich.console import Console

from servers.models import ToolCall, ToolCallFunction
from servers.ui.console import TerminalUI


def _ui(width: int = 80) -> tuple[TerminalUI, StringIO]:
    buf = StringIO()
    return TerminalUI(console=Console(file=buf, force_terminal=False, width=width)), buf


class WelcomeBoxTest(unittest.TestCase):
    def test_box_shows_brand_model_and_workspace(self) -> None:
        ui, buf = _ui()
        ui.welcome_box(
            model="claude-sonnet",
            base_url="https://example.test",
            workspace="/work",
            mode="plan",
        )
        out = buf.getvalue()
        self.assertIn("CERBERUS", out)
        self.assertIn("claude-sonnet", out)
        self.assertIn("/work", out)
        # rounded-box chrome, Sprout-style
        self.assertIn("╭", out)
        self.assertIn("╰", out)
        self.assertIn("│", out)

    def test_box_escapes_markup(self) -> None:
        ui, buf = _ui()
        ui.welcome_box(
            model="m[/]m",
            base_url="https://x/[y]",
            workspace="/tmp/[bracket]",
            mode="plan",
        )  # must not raise
        self.assertIn("/tmp/[bracket]", buf.getvalue())

    def test_compact_banner_still_three_lines(self) -> None:
        ui, buf = _ui()
        ui.banner(model="m", base_url="b", workspace="/work", mode="plan")
        self.assertEqual(len(buf.getvalue().splitlines()), 3)


class MotionTest(unittest.TestCase):
    def test_spinner_start_stop_is_clean(self) -> None:
        ui, _ = _ui()
        ui.spinner_start("Thinking")
        self.assertIsNotNone(ui._spinner)
        ui.spinner_stop()
        self.assertIsNone(ui._spinner)
        self.assertIsNone(ui._spinner_stop_event)
        # second stop is a safe no-op
        ui.spinner_stop()

    def test_restart_replaces_spinner(self) -> None:
        ui, _ = _ui()
        ui.spinner_start("Thinking")
        first = ui._spinner
        ui.spinner_start("Reading server/db.py")
        self.assertIsNot(ui._spinner, first)
        ui.spinner_stop()
        self.assertIsNone(ui._spinner)

    def test_compact_tool_card_is_one_completed_line(self) -> None:
        ui, buf = _ui()
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
        # Sprout-style result connector on the completed line
        self.assertIn("⎿", lines[0])
        self.assertIn("✓", lines[0])


class ChromeHelpersTest(unittest.TestCase):
    def test_section_heading_and_hr(self) -> None:
        ui, buf = _ui()
        ui.section_heading("verify")
        ui.hr()
        out = buf.getvalue()
        self.assertIn("verify", out)
        self.assertIn("─", out)


if __name__ == "__main__":
    unittest.main()
