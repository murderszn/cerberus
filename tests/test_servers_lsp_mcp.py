"""Tests for LSP-lite diagnostics and the MCP client stub."""

import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    import httpx  # noqa: F401

    HAS_AGENT_DEPS = True
except ImportError:
    HAS_AGENT_DEPS = False


class DiagnosticsTest(unittest.TestCase):
    def test_python_ok_and_syntax_error(self):
        import tempfile

        from servers.tools.lsp import python_diagnostics

        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            (ws / "ok.py").write_text("def f():\n    return 1\n", encoding="utf-8")
            (ws / "bad.py").write_text("def f(:\n", encoding="utf-8")
            self.assertIn("OK", python_diagnostics("ok.py", workspace=ws))
            bad = python_diagnostics("bad.py", workspace=ws)
            self.assertIn("SyntaxError", bad)
            self.assertIn(":1:", bad)

    def test_markers_and_boundary(self):
        import tempfile

        from servers.tools.lsp import python_diagnostics

        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            (ws / "n.txt").write_text("hello\n# TODO fix this\n", encoding="utf-8")
            out = python_diagnostics("n.txt", workspace=ws)
            self.assertIn("TODO", out)
            self.assertIn("2:", out)
            (ws / "clean.txt").write_text("hello\n", encoding="utf-8")
            self.assertIn("OK", python_diagnostics("clean.txt", workspace=ws))
            outside = python_diagnostics("../escape.py", workspace=ws)
            self.assertIn("outside the workspace", outside)

    def test_missing(self):
        import tempfile

        from servers.tools.lsp import python_diagnostics

        with tempfile.TemporaryDirectory() as tmp:
            self.assertIn(
                "not a file",
                python_diagnostics("nope.py", workspace=Path(tmp)),
            )


class McpConfigTest(unittest.TestCase):
    def test_normalize(self):
        from servers.tools.mcp import normalize_servers, tool_name

        self.assertEqual(tool_name("gh", "issue_read"), "mcp_gh_issue_read")
        servers = normalize_servers([
            {"name": "gh", "command": "gh", "tools": ["issue_read"]},
            {"name": "bad"},  # dropped: no command/tools
            "nope",
        ])
        self.assertEqual(len(servers), 1)
        self.assertEqual(servers[0]["args"], [])

    def test_invoke_success_and_errors(self):
        from servers.tools.mcp import invoke

        server = {"name": "gh", "command": "gh", "args": [], "tools": ["t"]}
        with mock.patch("servers.tools.mcp.subprocess") as sub:
            sub.run.return_value = mock.Mock(returncode=0, stdout='{"ok": true}\n', stderr="")
            out = invoke(server, "t", {"a": 1})
            self.assertIn('"ok": true', out)
            called = sub.run.call_args
            self.assertEqual(called[0][0][:2], ["gh", "t"])
            self.assertEqual(called[1]["input"], '{"a": 1}')
        with mock.patch("servers.tools.mcp.subprocess") as sub:
            sub.run.side_effect = FileNotFoundError()
            self.assertIn("never auto-installed", invoke(server, "t", {}))
        with mock.patch("servers.tools.mcp.subprocess") as sub:
            import subprocess as real_sub

            sub.run.side_effect = real_sub.TimeoutExpired(cmd="x", timeout=1)
            self.assertIn("timed out", invoke(server, "t", {}))
        with mock.patch("servers.tools.mcp.subprocess") as sub:
            sub.run.return_value = mock.Mock(returncode=1, stdout="", stderr="boom")
            self.assertIn("boom", invoke(server, "t", {}))
        self.assertIn("ERROR", invoke({}, "t", {}))
        self.assertIn("ERROR", invoke(server, "t", object()))


@unittest.skipUnless(HAS_AGENT_DEPS, "agent deps not installed")
class McpRegistryTest(unittest.TestCase):
    def _registry(self, **kw):
        import tempfile

        from servers.config import ToolConfig
        from servers.tools.registry import ToolRegistry

        cfg = ToolConfig()
        for k, v in kw.items():
            setattr(cfg, k, v)
        return ToolRegistry(workspace=Path(tempfile.mkdtemp()), config=cfg,
                            confirm_callback=lambda c, r: True)

    def test_mcp_tools_registered_and_readonly(self):
        from servers.tools.registry import READ_ONLY_TOOLS

        reg = self._registry(mcp_servers=[
            {"name": "gh", "command": "gh", "args": [], "tools": ["issue_read"]},
        ])
        self.assertIn("mcp_gh_issue_read", reg.list_names())
        self.assertIn("lsp_symbols", READ_ONLY_TOOLS)
        self.assertIn("diagnostics", READ_ONLY_TOOLS)
        # MCP tools spawn subprocesses: gated like external access.
        gate = reg._approval_gate("mcp_gh_issue_read", {"input": "{}"})
        self.assertIsNotNone(gate)
        self.assertTrue(gate[0].startswith("external:"))

    def test_mcp_dispatch_mocked(self):
        reg = self._registry(mcp_servers=[
            {"name": "gh", "command": "gh", "args": [], "tools": ["issue_read"]},
        ])
        with mock.patch("servers.tools.mcp.subprocess") as sub:
            sub.run.return_value = mock.Mock(returncode=0, stdout="issue #1", stderr="")
            out = reg.dispatch("mcp_gh_issue_read", {"input": '{"n": 1}'})
            self.assertIn("issue #1", out)

    def test_no_servers_no_tools(self):
        reg = self._registry()
        self.assertFalse([n for n in reg.list_names() if n.startswith("mcp_")])

    def test_lsp_symbols_dispatch(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "a.py").write_text("def f():\n    pass\n", encoding="utf-8")
            from servers.config import ToolConfig
            from servers.tools.registry import ToolRegistry

            reg = ToolRegistry(workspace=Path(tmp), config=ToolConfig(),
                               confirm_callback=lambda c, r: True)
            out = reg.dispatch("lsp_symbols", {"path": "a.py"})
            self.assertIn("f", out)
            out = reg.dispatch("diagnostics", {"path": "a.py"})
            self.assertIn("OK", out)


if __name__ == "__main__":
    unittest.main()
