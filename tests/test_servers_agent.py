"""Tests for the Cerberus agent runtime additions (stdlib-only, CI-safe).

Covers servers/tools/inspect.py, persona policy defaults, CLI argv
normalization, PR dry-run safety, and `cli scan` passthrough. Deliberately
avoids httpx/rich imports so plain `python -m unittest discover -s tests`
stays green without agent dependencies.
"""

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class InspectToolTest(unittest.TestCase):
    def setUp(self):
        from servers.tools.inspect import file_tree  # noqa: F401

        self.ws = ROOT

    def test_file_tree_lists_known_files(self):
        from servers.tools.inspect import file_tree

        out = file_tree("servers/tools", workspace=self.ws)
        self.assertIn("inspect.py", out)
        self.assertIn("pr.py", out)

    def test_file_tree_missing_dir_errors(self):
        from servers.tools.inspect import file_tree

        self.assertTrue(
            file_tree("no-such-dir", workspace=self.ws).startswith("ERROR")
        )

    def test_python_eval_runs(self):
        from servers.tools.inspect import python_eval

        out = python_eval("print(2 + 2)", workspace=self.ws)
        self.assertIn("exit=0", out)
        self.assertIn("4", out)

    def test_python_eval_timeout(self):
        from servers.tools.inspect import python_eval

        out = python_eval("import time; time.sleep(30)", workspace=self.ws, timeout=1)
        self.assertIn("timed out", out)

    def test_http_rejects_non_http_scheme(self):
        from servers.tools.inspect import http_request

        self.assertTrue(http_request("ftp://example.com/x").startswith("ERROR"))


class PersonaPolicyTest(unittest.TestCase):
    def test_nine_personas_listed(self):
        from servers.agent.prompts import CERBERUS_AGENTS, list_personas

        self.assertEqual(len(CERBERUS_AGENTS), 9)
        self.assertIn("sentinel", list_personas())
        self.assertIn("vault", list_personas())

    def test_vault_defaults_plan_and_no_exec(self):
        from servers.config import load_config

        with tempfile.TemporaryDirectory() as tmp:
            # Explicit missing path: pure defaults, no ~/.cerberus leakage.
            policy = load_config(Path(tmp) / "missing.yaml").policy_for("vault")
        self.assertEqual(policy.default_mode, "plan")
        self.assertNotIn("execute_bash_command", policy.allowed_tools)
        self.assertNotIn("python_eval", policy.allowed_tools)
        self.assertIn("create_pull_request", policy.allowed_tools)

    def test_plan_prompt_forbids_mutation(self):
        from servers.agent.prompts import build_system_prompt

        prompt = build_system_prompt("vault", mode="plan")
        self.assertIn("PLAN", prompt)
        self.assertIn("NOT mutate", prompt)


class NarrationTest(unittest.TestCase):
    def test_bash_pytest_headline_is_plain_language(self):
        from servers.ui.narrate import describe_activity

        headline, detail = describe_activity(
            "execute_bash_command", {"command": "pytest tests/ -q"}
        )
        self.assertIn("test", headline.lower())
        self.assertNotIn("bash", headline.lower())

    def test_bash_generic_hides_shell_jargon(self):
        from servers.ui.narrate import describe_activity

        headline, _ = describe_activity(
            "execute_bash_command", {"command": "rm -rf /tmp/x"}
        )
        self.assertNotIn("bash", headline.lower())
        self.assertNotIn("rm ", headline)

    def test_read_headline_names_file(self):
        from servers.ui.narrate import describe_activity

        headline, _ = describe_activity("read_file", {"path": "server/db.py"})
        self.assertIn("server/db.py", headline)

    def test_unknown_tool_falls_back(self):
        from servers.ui.narrate import describe_activity

        headline, detail = describe_activity("frobnicator", {})
        self.assertTrue(headline and detail)


class ModeDefaultTest(unittest.TestCase):
    def test_global_default_is_plan(self):
        from servers.config import AppConfig, _from_dict, load_config

        self.assertEqual(AppConfig().agent_mode, "plan")
        self.assertEqual(_from_dict({}).agent_mode, "plan")
        self.assertEqual(_from_dict({"agent_mode": "nonsense"}).agent_mode, "plan")
        with tempfile.TemporaryDirectory() as tmp:
            cfg = load_config(Path(tmp) / "missing.yaml")
            self.assertEqual(cfg.agent_mode, "plan")

    def test_yolo_flag_selects_build_plan_wins(self):
        from servers.cli import _normalize_argv, build_parser
        from servers.cli import _apply_cli_overrides
        from servers.config import AppConfig

        ns = build_parser().parse_args(_normalize_argv(["agent", "--yolo", "go"]))
        self.assertTrue(ns.yolo)
        self.assertEqual(_apply_cli_overrides(ns, AppConfig()).agent_mode, "build")

        ns2 = build_parser().parse_args(
            _normalize_argv(["agent", "--yolo", "--plan", "go"])
        )
        self.assertEqual(_apply_cli_overrides(ns2, AppConfig()).agent_mode, "plan")

        ns3 = build_parser().parse_args(_normalize_argv(["agent", "go"]))
        self.assertEqual(_apply_cli_overrides(ns3, AppConfig()).agent_mode, "plan")

    def test_mode_tag(self):
        from servers.cli import _mode_tag
        from servers.config import AppConfig

        self.assertEqual(_mode_tag(AppConfig()), "plan")
        cfg = AppConfig()
        cfg.agent_mode = "build"
        self.assertEqual(_mode_tag(cfg), "YOLO")


class StubRegistry:
    mode = "plan"


class StubLoop:
    def __init__(self, config):
        self.config = config
        self.registry = StubRegistry()

    def set_mode(self, mode):
        # Mirrors AgentLoop.set_mode contract for slash-command wiring tests.
        if mode not in {"build", "plan"}:
            raise ValueError(mode)
        self.config.agent_mode = mode


class RecordingUI:
    def __init__(self):
        self.lines = []
        self.tables = []

    def info(self, msg):
        self.lines.append(("info", str(msg)))

    def warn(self, msg):
        self.lines.append(("warn", str(msg)))

    def error(self, msg):
        self.lines.append(("error", str(msg)))

    def model_table(self, rows):
        self.tables.append(list(rows))


class ModeSlashTest(unittest.TestCase):
    def _run(self, line):
        from servers.cli import _handle_slash
        from servers.config import AppConfig

        config = AppConfig()
        loop = StubLoop(config)
        ui = RecordingUI()
        _handle_slash(line, loop, ui, config)
        return config, loop, ui

    def test_mode_shows_current(self):
        config, _, ui = self._run("/mode")
        self.assertEqual(config.agent_mode, "plan")
        self.assertTrue(any("plan" in m for _, m in ui.lines))

    def test_mode_yolo_switches(self):
        config, loop, ui = self._run("/mode yolo")
        self.assertEqual(config.agent_mode, "build")
        self.assertEqual(loop.registry.mode, "build")
        self.assertTrue(any(k == "warn" for k, _ in ui.lines))

    def test_mode_plan_switches_back(self):
        from servers.cli import _handle_slash
        from servers.config import AppConfig

        config = AppConfig()
        config.agent_mode = "build"
        loop = StubLoop(config)
        ui = RecordingUI()
        _handle_slash("/mode plan", loop, ui, config)
        self.assertEqual(config.agent_mode, "plan")
        self.assertEqual(loop.registry.mode, "plan")

    def test_mode_bad_arg_warns(self):
        _, _, ui = self._run("/mode frobnicate")
        self.assertTrue(any(k == "warn" for k, _ in ui.lines))


class WelcomeScreenTest(unittest.TestCase):
    def test_tagline_is_plain_text(self):
        from servers.ui.narrate import TAGLINE

        self.assertTrue(TAGLINE and "\n" not in TAGLINE)
        self.assertLessEqual(len(TAGLINE), 40)

    def test_welcome_rows_cover_status(self):
        from servers.ui.narrate import welcome_rows

        rows = welcome_rows(
            model="kimi",
            base_url="https://gen.pollinations.ai/v1",
            workspace="/tmp/x",
            mode="plan",
            auth="env · ab**yz",
            log_file="/tmp/x.log",
        )
        labels = [label for label, _ in rows]
        for expected in ("Model", "Mode", "Workspace", "Auth", "Log"):
            self.assertIn(expected, labels)
        mode_row = dict(rows)["Mode"]
        self.assertIn("PLAN", mode_row)

        build_rows = welcome_rows(
            model="kimi",
            base_url="u",
            workspace="w",
            mode="build",
            auth="a",
            log_file="l",
        )
        self.assertIn("ACCEPT-EDITS", dict(build_rows)["Mode"])


class ModelCatalogTest(unittest.TestCase):
    def test_catalog_numbers_and_marks_current(self):
        from servers.models_catalog import build_catalog, find_by_index, find_by_name

        rows = build_catalog(current="kimi", configured=["kimi", "deepseek"])
        by_model = {r.model: r for r in rows}
        self.assertTrue(by_model["kimi"].is_current)
        self.assertFalse(by_model["deepseek"].is_current)
        indices = [r.index for r in rows]
        self.assertEqual(indices, sorted(indices))
        self.assertEqual(find_by_index(rows, by_model["deepseek"].index), "deepseek")
        self.assertIsNone(find_by_index(rows, 9999))
        self.assertEqual(find_by_name(rows, "KIMI"), "kimi")
        # Custom passthrough for private endpoints.
        self.assertEqual(find_by_name(rows, "my-custom-7b"), "my-custom-7b")

    def test_unknown_current_still_listed(self):
        from servers.models_catalog import build_catalog

        rows = build_catalog(current="weird-model", configured=[])
        self.assertIn("weird-model", [r.model for r in rows])


class ModelSlashTest(unittest.TestCase):
    def _run(self, line, models=None):
        from servers.cli import _handle_slash
        from servers.config import AppConfig

        config = AppConfig()
        if models is not None:
            config.provider.models = models
        loop = StubLoop(config)
        ui = RecordingUI()
        _handle_slash(line, loop, ui, config)
        return config, ui

    def test_models_renders_table(self):
        _, ui = self._run("/models")
        self.assertEqual(len(ui.tables), 1)
        names = [r[1] for r in ui.tables[0]]
        self.assertIn("kimi", names)
        current = [r for r in ui.tables[0] if r[3]]
        self.assertEqual(len(current), 1)

    def test_model_by_number(self):
        from servers.models_catalog import build_catalog

        config_rows = build_catalog(current="kimi", configured=["kimi", "deepseek"])
        target = next(r.index for r in config_rows if r.model == "deepseek")
        config, ui = self._run(f"/model {target}")
        self.assertEqual(config.provider.model, "deepseek")
        self.assertTrue(any("deepseek" in m for _, m in ui.lines))

    def test_model_by_name_case_insensitive(self):
        config, _ = self._run("/model DEEPSEEK")
        self.assertEqual(config.provider.model, "deepseek")

    def test_model_bad_number_warns_and_keeps(self):
        config, ui = self._run("/model 9999")
        self.assertEqual(config.provider.model, "kimi")
        self.assertTrue(any(k == "warn" for k, _ in ui.lines))

    def test_model_bare_shows_current(self):
        _, ui = self._run("/model")
        self.assertTrue(any("kimi" in m for _, m in ui.lines))


class CliParseTest(unittest.TestCase):
    def test_flags_after_command(self):
        from servers.cli import _normalize_argv, build_parser

        ns = build_parser().parse_args(_normalize_argv(["sentinel", "--plan", "fix x"]))
        self.assertEqual(ns.command, "sentinel")
        self.assertTrue(ns.plan)
        self.assertEqual(ns.rest, ["fix x"])

    def test_value_flags_after_command(self):
        from servers.cli import _normalize_argv, build_parser

        ns = build_parser().parse_args(
            _normalize_argv(["sentinel", "--title", "Fix auth", "--base", "dev", "fix"])
        )
        self.assertEqual(ns.title, "Fix auth")
        self.assertEqual(ns.base, "dev")
        self.assertEqual(ns.rest, ["fix"])

    def test_scan_passthrough_untouched(self):
        from servers.cli import _normalize_argv, build_parser

        # --quiet is a real examine.py flag and must NOT be pulled out.
        ns = build_parser().parse_args(_normalize_argv(["scan", "--quiet"]))
        self.assertEqual(ns.command, "scan")
        self.assertEqual(ns.rest, ["--quiet"])


@unittest.skipUnless(shutil.which("git"), "git not available")
class PrDryRunTest(unittest.TestCase):
    def test_dry_run_previews_without_pushing(self):
        from servers.tools.pr import create_pull_request

        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            subprocess.run(["git", "init", "-q"], cwd=ws, check=True)
            subprocess.run(
                ["git", "config", "user.email", "t@t.t"], cwd=ws, check=True
            )
            subprocess.run(["git", "config", "user.name", "t"], cwd=ws, check=True)
            (ws / "fix.txt").write_text("patched\n", encoding="utf-8")
            out = create_pull_request(
                "Fix test flaw",
                workspace=ws,
                agent_name="sentinel",
                dry_run=True,
            )
            self.assertIn("[DRY RUN]", out)
            self.assertIn("cerberus/sentinel-", out)
            # Nothing committed, no remote touched.
            log = subprocess.run(
                ["git", "log", "--oneline"],
                cwd=ws,
                capture_output=True,
                text=True,
            )
            self.assertEqual(log.stdout.strip(), "")


class ScanPassthroughTest(unittest.TestCase):
    def test_scan_forwards_to_examine(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            (repo / "README.md").write_text("safe fixture\n", encoding="utf-8")
            proc = subprocess.run(
                [sys.executable, str(ROOT / "servers" / "cli.py"),
                 "scan", str(repo), "--native-only", "--quiet"],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                timeout=180,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr[-2000:])
            self.assertRegex(proc.stdout.strip().splitlines()[-1], r"/100")


if __name__ == "__main__":
    unittest.main()
