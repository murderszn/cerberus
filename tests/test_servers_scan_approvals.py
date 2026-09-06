"""Tests for scan-to-conversation (RAG digest) and ask-first approval gates."""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from servers.config import AppConfig, ToolConfig  # noqa: E402
from servers.models import Message  # noqa: E402

try:
    import httpx  # noqa: F401

    HAS_AGENT_DEPS = True
except ImportError:
    HAS_AGENT_DEPS = False


def fake_report() -> dict:
    return {
        "target": "demo-repo",
        "score": 91.5,
        "grade": "A",
        "counts": {"critical": 0, "high": 1, "medium": 0, "low": 0,
                   "pass": 20, "fail": 1, "total": 21},
        "engine": {"version": "9.9.9"},
        "coverage": {"filesScanned": 42},
        "notes": [],
        "agents": [
            {
                "id": "sentinel", "name": "Sentinel", "domain": "code safety",
                "weight": 40.0, "score": 38.0,
                "checks": [
                    {
                        "id": "s1", "name": "No eval()", "severity": "high",
                        "summary": "Dynamic code execution found.",
                        "risk": "", "remediation": "Replace eval with json parsing.",
                        "status": "fail", "deduction": 2.0,
                        "findings": [
                            {"path": "app.py", "line": 12, "snippet": "eval(data)"},
                            {"path": "app.py", "line": 30, "snippet": "eval(other)"},
                        ],
                        "totalFindings": 2,
                    },
                    {
                        "id": "s2", "name": "Clean imports", "severity": "low",
                        "summary": "", "risk": "", "remediation": "",
                        "status": "pass", "deduction": 0.0,
                        "findings": [], "totalFindings": 0,
                    },
                ],
            }
        ],
    }


class ScanDigestTest(unittest.TestCase):
    def test_digest_answers_followups(self):
        from servers.scan_context import build_scan_digest

        digest = build_scan_digest(fake_report(), "demo-repo")
        self.assertIn("91.5/100", digest)
        self.assertIn("grade A", digest)
        # methodology grounded in examine.py scoring
        self.assertIn("critical −4", digest)
        self.assertIn("A ≥90", digest)
        # failed check detail for "how do I get to 100?"
        self.assertIn("No eval()", digest)
        self.assertIn("−2.0 pts", digest)
        self.assertIn("Replace eval with json parsing.", digest)
        self.assertIn("app.py:12", digest)
        # per-domain table for "where did scores come from?"
        self.assertIn("Sentinel", digest)
        self.assertIn("38.0/40.0", digest)

    def test_remember_replaces_stale_digest(self):
        from servers.scan_context import remember_scan

        msgs: list[Message] = [Message(role="user", content="hello")]
        first = remember_scan(msgs, fake_report(), "demo")
        self.assertIn("91.5/100", first)
        self.assertIn("how do I get to 100?", first)
        second_report = fake_report()
        second_report["score"] = 100.0
        remember_scan(msgs, second_report, "demo")
        digests = [m for m in msgs if (m.content or "").startswith("[scan-context]")]
        self.assertEqual(len(digests), 1)
        self.assertIn("100.0/100", digests[0].content or "")
        # original user message preserved
        self.assertTrue(any(m.content == "hello" for m in msgs))


class BuildDetectTest(unittest.TestCase):
    def test_positives(self):
        from servers.tools.safety import is_build_command

        for cmd in ["pytest -q", "python -m pytest tests/", "npm run build",
                    "npm test", "make all", "cargo test", "go build ./...",
                    "docker build -t x .", "pip install -r req.txt",
                    "ls && pytest"]:
            self.assertTrue(is_build_command(cmd), cmd)

    def test_negatives(self):
        from servers.tools.safety import is_build_command

        for cmd in ["ls -la", "cat README.md", "git status",
                    "echo hello", "", "grep -r pytest ."]:
            self.assertFalse(is_build_command(cmd), cmd)


@unittest.skipUnless(HAS_AGENT_DEPS, "agent deps not installed")
class ApprovalGateTest(unittest.TestCase):
    def _registry(self, **kw):
        import tempfile

        from servers.tools.registry import ToolRegistry

        tmp = tempfile.mkdtemp()
        cfg = ToolConfig()
        for k, v in kw.items():
            setattr(cfg, k, v)
        calls: list[tuple[str, str]] = []

        def confirm(command, reason):
            calls.append((command, reason))
            return kw.get("decision", False)

        reg = ToolRegistry(workspace=Path(tmp), config=cfg, confirm_callback=confirm)
        return reg, calls

    def test_external_gate_and_deny(self):
        reg, calls = self._registry(decision=False)
        out = reg.dispatch("browse_web_content", {"url": "https://example.com"})
        self.assertIn("BLOCKED", out)
        self.assertIn("approval", out)
        self.assertEqual(len(calls), 1)

    def test_external_allowed_runs(self):
        reg, calls = self._registry(decision=True)
        gate = reg._approval_gate("browse_web_content", {})
        self.assertIsNotNone(gate)
        self.assertTrue(reg._ask_approval(*gate))
        self.assertEqual(len(calls), 1)

    def test_external_flag_off_skips_prompt(self):
        reg, calls = self._registry(approve_external=False, decision=False)
        self.assertIsNone(reg._approval_gate("browse_web_content", {}))
        self.assertEqual(calls, [])

    def test_build_gate_blocks(self):
        reg, calls = self._registry(decision=False)
        out = reg.dispatch("execute_bash_command", {"command": "pytest -q"})
        self.assertIn("BLOCKED", out)
        self.assertIn("approval", out)

    def test_non_build_no_prompt(self):
        reg, calls = self._registry(decision=False)
        self.assertIsNone(
            reg._approval_gate("execute_bash_command", {"command": "echo hi"})
        )
        self.assertEqual(calls, [])

    def test_session_allow_asks_once(self):
        reg, calls = self._registry(decision="session")
        self.assertTrue(reg._ask_approval("build", "pytest", "reason"))
        self.assertTrue(reg._ask_approval("build", "npm test", "reason"))
        self.assertEqual(len(calls), 1)
        self.assertEqual(reg.session_approvals(), ["build"])
        reg.reset_session_approvals()
        self.assertEqual(reg.session_approvals(), [])
        self.assertTrue(reg._ask_approval("build", "pytest", "reason"))
        self.assertEqual(len(calls), 2)

    def test_deny_strings(self):
        reg, _ = self._registry(decision="deny")
        self.assertFalse(reg._ask_approval("build", "pytest", "reason"))

    def test_no_callback_denies(self):
        import tempfile

        from servers.tools.registry import ToolRegistry

        reg = ToolRegistry(workspace=Path(tempfile.mkdtemp()), config=ToolConfig())
        self.assertFalse(reg._ask_approval("build", "pytest", "reason"))


class ApprovalsSlashTest(unittest.TestCase):
    def _run(self, line):
        import tempfile

        from servers.cli import _handle_slash

        with tempfile.TemporaryDirectory() as tmp:
            config = AppConfig()
            config.workspace = Path(tmp)

            class Registry:
                def __init__(self):
                    self.allowed = {"build"}

                def session_approvals(self):
                    return sorted(self.allowed)

                def reset_session_approvals(self):
                    self.allowed.clear()

            class Loop:
                def __init__(self):
                    self.registry = Registry()
                    self.messages: list[Message] = []

            class UI:
                def __init__(self):
                    self.lines: list[tuple[str, str]] = []
                    self.console = self

                def print(self, *a, **k):
                    self.lines.append(("print", " ".join(str(x) for x in a)))

                def info(self, m):
                    self.lines.append(("info", str(m)))

                def warn(self, m):
                    self.lines.append(("warn", str(m)))

                def error(self, m):
                    self.lines.append(("error", str(m)))

            loop, ui = Loop(), UI()
            _handle_slash(line, loop, ui, config)
            return config, loop, ui

    def test_status_and_toggle(self):
        config, _, ui = self._run("/approvals")
        self.assertTrue(any("external" in m for _, m in ui.lines))
        config, _, ui = self._run("/approvals builds off")
        self.assertFalse(config.tools.approve_builds)
        self.assertTrue(any("allowed without asking" in m for _, m in ui.lines))
        _, _, ui = self._run("/approvals external frobnicate")
        self.assertTrue(any("Usage" in m for _, m in ui.lines))

    def test_reset(self):
        _, loop, ui = self._run("/approvals reset")
        self.assertEqual(loop.registry.allowed, set())
        self.assertTrue(any("cleared" in m for _, m in ui.lines))

    def test_scan_usage_hint(self):
        _, _, ui = self._run("/scan")
        self.assertTrue(any("Usage" in m for _, m in ui.lines))


class ScanSectionsTest(unittest.TestCase):
    def test_agent_cards(self):
        from servers.scan_context import scan_agent_sections

        sections = scan_agent_sections(fake_report())
        self.assertEqual(len(sections), 1)
        title, body = sections[0]
        self.assertIn("Sentinel", title)
        self.assertIn("38.0/40.0", title)
        self.assertIn("1 failed", title)
        text = "\n".join(body)
        self.assertIn("No eval()", text)
        self.assertIn("Replace eval", text)
        self.assertIn("app.py:12", text)
        self.assertIn("1 passed", text)

    def test_all_clear(self):
        from servers.scan_context import scan_agent_sections

        report = fake_report()
        for check in report["agents"][0]["checks"]:
            check["status"] = "pass"
        title, body = scan_agent_sections(report)[0]
        self.assertIn("all clear", title)


class PersonaSlashTest(unittest.TestCase):
    def _run(self, line):
        import tempfile

        from servers.cli import _handle_slash

        with tempfile.TemporaryDirectory() as tmp:
            config = AppConfig()
            config.workspace = Path(tmp)

            class Loop:
                def __init__(self):
                    self.registry = None
                    self.messages: list[Message] = []
                    self.persona_name = None

            class UI:
                def __init__(self):
                    self.lines: list[tuple[str, str]] = []
                    self.console = self

                def print(self, *a, **k):
                    self.lines.append(("print", " ".join(str(x) for x in a)))

                def info(self, m):
                    self.lines.append(("info", str(m)))

                def warn(self, m):
                    self.lines.append(("warn", str(m)))

                def error(self, m):
                    self.lines.append(("error", str(m)))

            loop, ui = Loop(), UI()
            _handle_slash(line, loop, ui, config)
            return config, loop, ui

    def test_personas_roster(self):
        _, _, ui = self._run("/personas")
        printed = [m for k, m in ui.lines if k == "print"]
        self.assertTrue(any("sentinel" in m for m in printed))
        self.assertTrue(any("Specialists" in m for m in printed))

    def test_persona_show_and_unknown(self):
        _, _, ui = self._run("/persona")
        self.assertTrue(any("orchestrator" in m for _, m in ui.lines))
        _, _, ui = self._run("/persona frobnicate")
        self.assertTrue(any("Unknown persona" in m for _, m in ui.lines))

    @unittest.skipUnless(HAS_AGENT_DEPS, "agent deps not installed")
    def test_persona_switch_rebuilds_registry(self):
        config, loop, ui = self._run("/persona vault")
        self.assertEqual(loop.persona_name, "vault")
        self.assertTrue(any("vault" in m for _, m in ui.lines))
        self.assertIn("execute_bash_command",
                      config.policy_for("sentinel").allowed_tools)
        self.assertNotIn("execute_bash_command",
                         loop.registry.list_names())

    def test_team_usage_errors(self):
        _, _, ui = self._run("/team")
        self.assertTrue(any("Usage" in m for _, m in ui.lines))
        _, _, ui = self._run("/team nosuchagent do things")
        self.assertTrue(any("Usage" in m for _, m in ui.lines))


class RealScanReportTest(unittest.TestCase):
    def test_examine_report_loads_and_digests(self):
        import tempfile

        from servers.cli import _run_scan_report
        from servers.scan_context import build_scan_digest

        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "README.md").write_text("hello\n", encoding="utf-8")
            rc, report, err = _run_scan_report(tmp)
            self.assertEqual(rc, 0, err)
            self.assertIn("score", report)
            self.assertIn("grade", report)
            self.assertTrue(report.get("agents"))
            digest = build_scan_digest(report, tmp)
            self.assertIn("/100", digest)
            self.assertLessEqual(len(digest), 6000 + 100)


if __name__ == "__main__":
    unittest.main()
