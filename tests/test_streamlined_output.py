"""Streamlined-output regression tests: clip, digest, caps, grouping."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from io import StringIO
from pathlib import Path

from rich.console import Console

from servers.agent.prompts import build_system_prompt, get_orchestrator_prompt
from servers.models import ToolCall, ToolCallFunction
from servers.ui.console import TerminalUI
from servers.ui.summarize import (
    cap_diff,
    clip_text,
    format_digest,
    group_file_changes,
    needs_digest,
    outline_markdown,
)


def _ui(**kwargs) -> tuple[TerminalUI, StringIO]:
    buf = StringIO()
    return (
        TerminalUI(console=Console(file=buf, force_terminal=False, width=80), **kwargs),
        buf,
    )


def _long_answer(n: int = 80) -> str:
    parts = ["# Findings", ""]
    for i in range(n):
        parts.append(f"- finding {i}: hardcoded secret in `app/config.py:{i}`")
    parts += ["", "# Next steps", "", "- rotate keys", "- rerun scan"]
    return "\n".join(parts)


class ClipTest(unittest.TestCase):
    def test_short_text_untouched(self) -> None:
        self.assertEqual(clip_text("a\nb"), "a\nb")

    def test_long_text_clipped_with_note(self) -> None:
        text = "\n".join(f"line {i}" for i in range(50))
        out = clip_text(text, max_lines=10)
        self.assertIn("line 0", out)
        self.assertNotIn("line 49", out)
        self.assertIn("40 more lines", out)


class OutlineTest(unittest.TestCase):
    def test_groups_by_heading(self) -> None:
        groups = outline_markdown("# A\n- x\n- y\n# B\n- z")
        self.assertEqual([t for t, _ in groups], ["A", "B"])
        self.assertEqual(groups[0][1], ["x", "y"])

    def test_digest_caps_bullets_per_group(self) -> None:
        digest = format_digest(_long_answer(), per_group=5)
        self.assertIn("### Findings", digest)
        self.assertIn("… and", digest)
        self.assertNotIn("finding 79", digest)

    def test_needs_digest_thresholds(self) -> None:
        self.assertFalse(needs_digest("short answer"))
        self.assertTrue(needs_digest(_long_answer()))


class DiffCapTest(unittest.TestCase):
    def test_cap_diff_passthrough_when_small(self) -> None:
        visible, omitted = cap_diff("+a\n-b")
        self.assertEqual(omitted, 0)
        self.assertIn("+a", visible)

    def test_tool_end_caps_large_diff(self) -> None:
        ui, buf = _ui()
        call = ToolCall(
            id="d1",
            type="function",
            function=ToolCallFunction(name="edit_file", arguments="{}"),
        )
        big_diff = "\n".join(f"+line {i}" for i in range(100))
        ui.tool_start(call, {"path": "a.py"})
        ui.spinner_stop()
        ui.tool_end(call, f"ok\n--- CERBERUS_EDIT_DIFF ---\n{big_diff}")
        out = buf.getvalue()
        self.assertIn("more diff lines", out)
        self.assertNotIn("line 99", out)


class FinalDigestTest(unittest.TestCase):
    def test_short_answer_renders_full(self) -> None:
        ui, buf = _ui()
        ui.assistant_final("Fixed the login bug.")
        out = buf.getvalue()
        self.assertIn("Fixed the login bug.", out)
        self.assertIn("Cerberus", out)

    def test_long_answer_renders_grouped_summary(self) -> None:
        ui, buf = _ui()
        ui.assistant_final(_long_answer())
        out = buf.getvalue()
        self.assertIn("summary", out)
        self.assertIn("Findings", out)
        self.assertNotIn("finding 79", out)

    def test_verbose_restores_full_answer(self) -> None:
        ui, buf = _ui(show_tool_args=True)
        ui.assistant_final(_long_answer())
        self.assertIn("finding 79", buf.getvalue())


class GroupingTest(unittest.TestCase):
    def test_status_grouped_into_table(self) -> None:
        status = "M  a.py\n M b.py\nA  new.py\n?? scratch.txt"
        out = group_file_changes(status)
        self.assertIn("Modified (2)", out)
        self.assertIn("Added (1)", out)
        self.assertIn("Untracked (1)", out)
        self.assertIn("4 files total", out)

    @unittest.skipUnless(shutil.which("git"), "git unavailable")
    def test_pr_dry_run_groups_changes(self) -> None:
        from servers.tools.pr import create_pull_request

        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            subprocess.run(["git", "init", "-q"], cwd=ws, check=True)
            subprocess.run(["git", "config", "user.email", "t@t"], cwd=ws, check=True)
            subprocess.run(["git", "config", "user.name", "t"], cwd=ws, check=True)
            (ws / "a.py").write_text("x\n")
            (ws / "b.py").write_text("y\n")
            subprocess.run(["git", "add", "-A"], cwd=ws, check=True)
            subprocess.run(["git", "commit", "-qm", "init"], cwd=ws, check=True)
            (ws / "a.py").write_text("x2\n")
            (ws / "c.py").write_text("z\n")
            out = create_pull_request("Test PR", workspace=ws, dry_run=True)
            self.assertIn("[DRY RUN]", out)
            self.assertIn("Modified (1)", out)
            self.assertIn("Untracked (1)", out)


class PromptFormatTest(unittest.TestCase):
    def test_prompts_carry_format_rules(self) -> None:
        for prompt in (build_system_prompt("sentinel"), get_orchestrator_prompt()):
            self.assertIn("grouped summaries", prompt)
            self.assertIn("unless the user asked", prompt)


if __name__ == "__main__":
    unittest.main()
