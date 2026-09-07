"""Markup-injection regression tests for the Rich scrollback UI.

Dynamic content (tool output, model text, file paths, log lines) routinely
contains ``[``/``]`` sequences. Rendering those with Rich markup enabled
raised ``MarkupError: auto closing tag ('[/]') has nothing to close`` and
crashed the session. Every TerminalUI entry point must therefore render
dynamic payloads literally.
"""

import io
import unittest

from rich.console import Console

from servers.ui.console import TerminalUI


NASTY = [
    "[/]",
    "result: [/] done",
    "[bold]not really bold[/]",
    "[link=http://example.com]x[/link]",
    "[external|builds]",
    "[1] numbered",
    "path/to/[bracket]/file.py",
    "C:\\[test\\]\\[x\\]",
    "mix [/] and [ok] and unpaired [ bracket",
]


def _ui(width: int = 80) -> tuple[TerminalUI, io.StringIO]:
    buf = io.StringIO()
    console = Console(file=buf, width=width, force_terminal=False)
    return TerminalUI(console=console), buf


class MarkupSafetyTest(unittest.TestCase):
    def test_info_warn_error_render_nasty_literally(self) -> None:
        for payload in NASTY:
            for method in ("info", "warn", "error"):
                ui, buf = _ui()
                getattr(ui, method)(payload)  # must not raise
                self.assertIn(payload, buf.getvalue())

    def test_tool_start_end_with_nasty_args(self) -> None:
        from types import SimpleNamespace

        for payload in NASTY:
            ui, _ = _ui()
            tc = SimpleNamespace(function=SimpleNamespace(name="run_bash"))
            ui.tool_start(tc, {"command": payload})  # must not raise
            ui.tool_end(tc, payload)  # must not raise

    def test_plan_update_and_spinner(self) -> None:
        for payload in NASTY:
            ui, _ = _ui()
            ui.plan_update(payload)  # must not raise
            ui.spinner_start(payload)  # must not raise
            ui.spinner_stop()

    def test_assistant_final_renders_model_text_literally(self) -> None:
        for payload in NASTY:
            ui, buf = _ui()
            ui.assistant_final(payload)  # must not raise
            # literal text survives; no markup interpretation swallows it
            self.assertIn(payload, buf.getvalue())

    def test_model_table_with_nasty_names(self) -> None:
        ui, _ = _ui()
        ui.model_table([(1, "weird[/]model", "sec[tion]", True)])  # must not raise

    def test_banner_with_nasty_workspace(self) -> None:
        ui, _ = _ui()
        ui.banner(
            model="m[/]m",
            base_url="https://x/[y]",
            workspace="/tmp/[bracket]",
            mode="plan",
        )  # must not raise

    def test_raw_print_with_markup_false(self) -> None:
        ui, buf = _ui()
        for payload in NASTY:
            ui.console.print(payload, markup=False)  # pattern used by cli.py
        self.assertIn("[/]", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
