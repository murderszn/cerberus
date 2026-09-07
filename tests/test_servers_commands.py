"""Tests for shared slash-command helpers, model persistence, and new REPL slash wiring."""

import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from servers.config import AppConfig  # noqa: E402
from servers.models import Message  # noqa: E402


class StubRegistry:
    mode = "plan"


class StubLoop:
    def __init__(self, config):
        self.config = config
        self.registry = StubRegistry()
        self.messages: list[Message] = []

    def set_mode(self, mode):
        if mode not in {"build", "plan"}:
            raise ValueError(mode)
        self.config.agent_mode = mode


class ConsoleStub:
    def __init__(self, ui):
        self.ui = ui

    def print(self, *args, **kwargs):
        self.ui.lines.append(("print", " ".join(str(a) for a in args)))


class RecordingUI:
    def __init__(self):
        self.lines: list[tuple[str, str]] = []
        self.console = ConsoleStub(self)

    def info(self, msg):
        self.lines.append(("info", str(msg)))

    def warn(self, msg):
        self.lines.append(("warn", str(msg)))

    def error(self, msg):
        self.lines.append(("error", str(msg)))

    def texts(self, kind=None):
        return [m for k, m in self.lines if kind is None or k == kind]


def make_config(tmpdir: str) -> AppConfig:
    config = AppConfig()
    config.workspace = Path(tmpdir)
    return config


class PickModelTest(unittest.TestCase):
    def test_empty_shows_active(self):
        from servers.commands import pick_model

        picked, msg = pick_model(AppConfig(), "")
        self.assertIsNone(picked)
        self.assertIn("Active model", msg)

    def test_bad_index_warns(self):
        from servers.commands import pick_model

        picked, msg = pick_model(AppConfig(), "999")
        self.assertIsNone(picked)
        self.assertIn("No model #999", msg)

    def test_name_passthrough(self):
        from servers.commands import pick_model

        picked, msg = pick_model(AppConfig(), "my-private-model")
        self.assertEqual(picked, "my-private-model")
        self.assertIn("Switched model", msg)

    def test_catalog_lines_mark_current(self):
        from servers.commands import catalog_lines

        lines = catalog_lines(AppConfig())
        self.assertTrue(lines[0].startswith("Models"))
        self.assertTrue(any("●" in ln for ln in lines))


class SaveModelTest(unittest.TestCase):
    def test_json_roundtrip(self):
        import json
        import tempfile

        from servers.config import load_config, save_model

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text('{"provider": {"model": "kimi"}}', encoding="utf-8")
            saved = save_model("deepseek", path)
            self.assertEqual(saved, path)
            raw = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(raw["provider"]["model"], "deepseek")
            self.assertEqual(load_config(path).provider.model, "deepseek")

    def test_yaml_roundtrip(self):
        import tempfile

        try:
            import yaml  # noqa: F401
            has_yaml = True
        except ImportError:
            has_yaml = False
        from servers.config import load_config, save_model

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.yaml"
            body = (
                "# comment\nprovider:\n  base_url: \"https://x/v1\"\n"
                '  model: "kimi"\n\nagent_mode: "plan"\n'
            )
            path.write_text(body, encoding="utf-8")
            save_model("openai", path)
            text = path.read_text(encoding="utf-8")
            self.assertRegex(text, r"model:\s*[\"']?openai[\"']?")  # quoted or plain
            self.assertNotIn("kimi", text)
            self.assertIn("agent_mode:", text)  # rest of file preserved
            if has_yaml:
                self.assertEqual(load_config(path).provider.model, "openai")


class CompactTest(unittest.TestCase):
    def test_drops_middle_keeps_system_and_tail(self):
        from servers.commands import compact_history

        msgs = [Message(role="system", content="sys")]
        msgs += [Message(role="user", content=f"m{i}") for i in range(15)]
        out = compact_history(msgs)
        self.assertIn("dropped 5", out)
        self.assertEqual(len(msgs), 11)
        self.assertEqual(msgs[0].role, "system")
        self.assertEqual(msgs[-1].content, "m14")

    def test_short_history_noop(self):
        from servers.commands import compact_history

        msgs = [Message(role="user", content="hi")]
        out = compact_history(msgs)
        self.assertIn("already compact", out)
        self.assertEqual(len(msgs), 1)


class AttachTest(unittest.TestCase):
    def test_attaches_file_content(self):
        import tempfile

        from servers.commands import attach_files

        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "a.txt").write_text("hello attach\n", encoding="utf-8")
            msgs: list[Message] = []
            out = attach_files(msgs, Path(tmp), "a.txt")
            self.assertIn("Attached 1 file", out)
            self.assertEqual(len(msgs), 1)
            self.assertIn("hello attach", msgs[0].content or "")

    def test_rejects_outside_and_missing(self):
        import tempfile

        from servers.commands import attach_files

        with tempfile.TemporaryDirectory() as tmp:
            msgs: list[Message] = []
            out = attach_files(msgs, Path(tmp), "../escape.txt nope.txt")
            self.assertIn("Nothing attached", out)
            self.assertEqual(msgs, [])

    def test_empty_spec_usage(self):
        import tempfile

        from servers.commands import attach_files

        with tempfile.TemporaryDirectory() as tmp:
            self.assertIn("Usage", attach_files([], Path(tmp), ""))


class TeamParseTest(unittest.TestCase):
    def test_comma_and_space_teams(self):
        from servers.commands import parse_team_arg

        valid = ["sentinel", "vault", "architect"]
        names, task, err = parse_team_arg("sentinel,vault audit auth", valid)
        self.assertEqual((names, task, err), (["sentinel", "vault"], "audit auth", ""))
        names, task, err = parse_team_arg("sentinel vault audit auth", valid)
        self.assertEqual(names, ["sentinel", "vault"])
        self.assertEqual(task, "audit auth")

    def test_repeated_name_dedupes(self):
        from servers.commands import parse_team_arg

        names, task, err = parse_team_arg("vault vault audit", ["vault"])
        self.assertEqual(names, ["vault"])
        self.assertEqual(task, "audit")
        self.assertEqual(err, "")

    def test_usage_errors(self):
        from servers.commands import parse_team_arg

        _, _, err = parse_team_arg("do the thing", ["sentinel"])
        self.assertIn("Usage", err)
        _, _, err = parse_team_arg("sentinel", ["sentinel"])
        self.assertIn("Give the team a task", err)

    def test_persona_lines_roster(self):
        from servers.commands import persona_lines

        lines = persona_lines(["sentinel", "vault"])
        self.assertTrue(lines[0].startswith("Specialists"))
        self.assertTrue(any("sentinel" in ln for ln in lines))


class ModelMetaTest(unittest.TestCase):
    def test_apply_meta(self):
        import os

        from servers.commands import apply_model_meta
        from servers.config import AppConfig

        config = AppConfig()
        config.provider.provider_models = {
            "far": {"base_url": "https://far.example/v1",
                    "api_key_env": "CERBERUS_TEST_FAR_KEY",
                    "temperature": 0.7},
        }
        os.environ["CERBERUS_TEST_FAR_KEY"] = "sekret"
        try:
            note = apply_model_meta(config, "far")
        finally:
            del os.environ["CERBERUS_TEST_FAR_KEY"]
        self.assertIn("endpoint → https://far.example/v1", note)
        self.assertIn("key from CERBERUS_TEST_FAR_KEY", note)
        self.assertIn("temperature → 0.7", note)
        self.assertEqual(config.provider.base_url, "https://far.example/v1")
        self.assertEqual(config.provider.api_key, "sekret")
        self.assertEqual(config.provider.temperature, 0.7)

    def test_missing_env_warns(self):
        from servers.commands import apply_model_meta
        from servers.config import AppConfig

        config = AppConfig()
        config.provider.provider_models = {"far": {"api_key_env": "CERBERUS_TEST_MISSING_KEY"}}
        note = apply_model_meta(config, "far")
        self.assertIn("not set", note)
        self.assertEqual(config.provider.api_key, "")

    def test_no_meta_noop(self):
        from servers.commands import apply_model_meta
        from servers.config import AppConfig

        config = AppConfig()
        before = config.provider.base_url
        self.assertEqual(apply_model_meta(config, "kimi"), "")
        self.assertEqual(config.provider.base_url, before)

    def test_model_use_persists_only_model(self):
        import tempfile

        from servers.cli import cmd_model
        from servers.config import AppConfig

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "c.json"
            path.write_text(
                '{"provider": {"model": "kimi", "base_url": "https://x/v1",'
                ' "models": [{"id": "deepseek", "base_url": "https://y/v1"}]}}',
                encoding="utf-8",
            )
            from servers.config import load_config

            config = load_config(path)

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

            ui = UI()
            rc = cmd_model(config, ui, path, "use deepseek")
            self.assertEqual(rc, 0)
            self.assertEqual(config.provider.model, "deepseek")
            self.assertEqual(config.provider.base_url, "https://y/v1")  # in-memory
            import json

            raw = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(raw["provider"]["model"], "deepseek")
            self.assertEqual(raw["provider"]["base_url"], "https://x/v1")  # untouched
            rc = cmd_model(config, ui, path, "use")
            self.assertEqual(rc, 2)


class SuggestTest(unittest.TestCase):
    def test_prefix_first(self):
        from servers.commands import suggest_commands

        names = [c[0] for c in suggest_commands("per")]
        self.assertEqual(names[:2], ["persona", "personas"])

    def test_substring_still_found(self):
        from servers.commands import suggest_commands

        names = [c[0] for c in suggest_commands("mod")]
        self.assertIn("model", names)
        self.assertIn("models", names)

    def test_bare_slash_lists_head(self):
        from servers.commands import suggest_commands, SLASH_COMMANDS

        self.assertEqual(suggest_commands(""), list(SLASH_COMMANDS[:7]))
        self.assertEqual(suggest_commands("/"), list(SLASH_COMMANDS[:7]))

    def test_no_match_and_limit(self):
        from servers.commands import suggest_commands

        self.assertEqual(suggest_commands("zzz"), [])
        self.assertLessEqual(len(suggest_commands("", limit=3)), 3)

    def test_registry_covers_handlers(self):
        from servers.commands import SLASH_COMMANDS

        cli = Path(__file__).resolve().parents[1].joinpath("servers/cli.py").read_text()
        tui = Path(__file__).resolve().parents[1].joinpath("servers/ui/tui.py").read_text()
        for cmd, _, _ in SLASH_COMMANDS:
            self.assertIn(f'"/{cmd}"', cli, f"REPL missing /{cmd}")
            self.assertIn(f'"/{cmd}"', tui, f"TUI missing /{cmd}")


class ComposerParseTest(unittest.TestCase):
    def test_plain_run(self):
        from servers.commands import parse_composer_line

        self.assertEqual(parse_composer_line("fix auth"), ("run", "", "fix auth"))

    def test_attach_only_and_with_task(self):
        from servers.commands import parse_composer_line

        self.assertEqual(parse_composer_line("@a.py"), ("attach", "a.py", ""))
        self.assertEqual(
            parse_composer_line("@a.py @b.py explain this"),
            ("run", "a.py b.py", "explain this"),
        )
        self.assertEqual(
            parse_composer_line("@a.py,@b.py explain"),
            ("run", "a.py b.py", "explain"),
        )

    def test_bang(self):
        from servers.commands import parse_composer_line

        self.assertEqual(parse_composer_line("!pytest -q"), ("bash", "", "pytest -q"))
        self.assertEqual(parse_composer_line("!"), ("run", "", "!"))
        self.assertEqual(
            parse_composer_line("!a\n!b"), ("run", "", "!a\n!b")
        )

    def test_mid_sentence_at_is_run(self):
        from servers.commands import parse_composer_line

        action, _, payload = parse_composer_line("look at this file")
        self.assertEqual(action, "run")
        self.assertIn("look at", payload)


class GitHelpersTest(unittest.TestCase):
    def test_non_repo(self):
        import tempfile

        from servers.commands import git_restore_paths, git_working_tree

        with tempfile.TemporaryDirectory() as tmp:
            mod, unt, err = git_working_tree(Path(tmp))
            self.assertTrue(err.startswith("Not a git repo"))
            self.assertEqual((mod, unt), ([], []))

    def test_tracked_vs_untracked(self):
        import subprocess
        import tempfile

        from servers.commands import git_working_tree

        with tempfile.TemporaryDirectory() as tmp:
            r = subprocess.run(["git", "init", tmp], capture_output=True)
            if r.returncode != 0:
                self.skipTest("git not available")
            subprocess.run(["git", "-C", tmp, "config", "user.email", "t@t"], check=False,
                           capture_output=True)
            subprocess.run(["git", "-C", tmp, "config", "user.name", "t"], check=False,
                           capture_output=True)
            Path(tmp, "a.txt").write_text("v1\n", encoding="utf-8")
            subprocess.run(["git", "-C", tmp, "add", "."], check=False, capture_output=True)
            subprocess.run(["git", "-C", tmp, "commit", "-m", "init"], check=False,
                           capture_output=True)
            Path(tmp, "a.txt").write_text("v2\n", encoding="utf-8")
            Path(tmp, "new.txt").write_text("new\n", encoding="utf-8")
            mod, unt, err = git_working_tree(Path(tmp))
            self.assertEqual(err, "")
            self.assertEqual(mod, ["a.txt"])
            self.assertEqual(unt, ["new.txt"])


class ReplCompleterTest(unittest.TestCase):
    def _completions(self, text):
        try:
            from prompt_toolkit.document import Document
        except ImportError:
            self.skipTest("prompt_toolkit not installed")
        from servers.cli import _make_completer

        comp = _make_completer()
        self.assertIsNotNone(comp)
        doc = Document(text=text, cursor_position=len(text))
        return list(comp.get_completions(doc, None))

    def test_completes_fragment(self):
        found = {c.text for c in self._completions("/per")}
        self.assertIn("/persona ", found)
        self.assertIn("/personas ", found)

    def test_silent_off_slash(self):
        self.assertEqual(self._completions("hello model"), [])
        self.assertEqual(self._completions("/model x"), [])


class InitDiffTest(unittest.TestCase):
    def test_init_creates_and_never_overwrites(self):
        import tempfile

        from servers.commands import init_project_file

        with tempfile.TemporaryDirectory() as tmp:
            first = init_project_file(Path(tmp))
            self.assertIn("Wrote project memory", first)
            target = Path(tmp) / "CERBERUS.md"
            target.write_text("custom\n", encoding="utf-8")
            second = init_project_file(Path(tmp))
            self.assertIn("already exists", second)
            self.assertEqual(target.read_text(encoding="utf-8"), "custom\n")

    def test_diff_outside_git(self):
        import tempfile

        from servers.commands import workspace_diff_summary

        with tempfile.TemporaryDirectory() as tmp:
            self.assertIn("Not a git repo", workspace_diff_summary(Path(tmp)))

    def test_diff_shows_changes(self):
        import tempfile

        from servers.commands import workspace_diff_summary

        with tempfile.TemporaryDirectory() as tmp:
            r = subprocess.run(["git", "init", tmp], capture_output=True, text=True)
            if r.returncode != 0:
                self.skipTest("git not available")
            subprocess.run(
                ["git", "-C", tmp, "config", "user.email", "t@t"],
                capture_output=True, check=False,
            )
            subprocess.run(
                ["git", "-C", tmp, "config", "user.name", "t"],
                capture_output=True, check=False,
            )
            Path(tmp, "f.txt").write_text("v1\n", encoding="utf-8")
            subprocess.run(["git", "-C", tmp, "add", "."],
                           capture_output=True, check=False)
            subprocess.run(["git", "-C", tmp, "commit", "-m", "init"],
                           capture_output=True, check=False)
            Path(tmp, "f.txt").write_text("v2\n", encoding="utf-8")
            out = workspace_diff_summary(Path(tmp))
            self.assertIn("f.txt", out)


class SlashWiringTest(unittest.TestCase):
    def _run(self, line, tmpdir):
        from servers.cli import _handle_slash

        config = make_config(tmpdir)
        loop = StubLoop(config)
        ui = RecordingUI()
        _handle_slash(line, loop, ui, config)
        return config, loop, ui

    def test_slash_model_switches(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            config, _, ui = self._run("/model deepseek", tmp)
            self.assertEqual(config.provider.model, "deepseek")
            self.assertTrue(any("Switched model" in m for m in ui.texts("info")))

    def test_slash_model_bad_index_warns(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            _, _, ui = self._run("/model 999", tmp)
            self.assertTrue(any("No model" in m for m in ui.texts("warn")))

    def test_slash_add_and_compact(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "a.txt").write_text("ctx\n", encoding="utf-8")
            from servers.cli import _handle_slash

            config = make_config(tmp)
            loop = StubLoop(config)
            ui = RecordingUI()
            _handle_slash("/add a.txt", loop, ui, config)
            self.assertEqual(len(loop.messages), 1)
            for i in range(15):
                loop.messages.append(Message(role="user", content=f"m{i}"))
            _handle_slash("/compact", loop, ui, config)
            self.assertLess(len(loop.messages), 17)
            self.assertTrue(any("Compacted" in m for m in ui.texts("info")))

    def test_slash_diff_and_init(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            from servers.cli import _handle_slash

            config = make_config(tmp)
            loop = StubLoop(config)
            ui = RecordingUI()
            _handle_slash("/init", loop, ui, config)
            self.assertTrue((Path(tmp) / "CERBERUS.md").exists())
            _handle_slash("/diff", loop, ui, config)
            self.assertTrue(any("Not a git repo" in m for m in ui.texts("print")))


if __name__ == "__main__":
    unittest.main()
