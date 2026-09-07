"""Tests for layered config: global < project < CERBERUS.md < env < CLI."""

import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from servers.config import (  # noqa: E402
    _coerce_value,
    _normalize_models,
    config_get,
    config_set,
    load_config,
    scaffold_project,
)


class ModelsMapTest(unittest.TestCase):
    def test_string_list(self):
        ids, meta = _normalize_models(["a", "b"])
        self.assertEqual(ids, ["a", "b"])
        self.assertEqual(meta, {})

    def test_list_of_maps(self):
        ids, meta = _normalize_models([
            {"id": "kimi", "base_url": "https://x/v1", "api_key_env": "KIMI_KEY", "temperature": 0.1},
            "deepseek",
        ])
        self.assertEqual(ids, ["kimi", "deepseek"])
        self.assertEqual(meta["kimi"]["api_key_env"], "KIMI_KEY")
        self.assertEqual(meta["kimi"]["temperature"], 0.1)

    def test_dict_form(self):
        ids, meta = _normalize_models({"openai": {"base_url": "https://y"}})
        self.assertEqual(ids, ["openai"])
        self.assertEqual(meta, {"openai": {"base_url": "https://y"}})

    def test_empty_falls_back(self):
        ids, _ = _normalize_models(None)
        self.assertIn("kimi", ids)


class LayeredLoadTest(unittest.TestCase):
    def _write(self, path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def test_project_overrides_global(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            glob = tmpdir / "global.json"
            self._write(glob, '{"provider": {"model": "kimi"}, "agent_mode": "plan"}')
            projdir = tmpdir / "proj"
            self._write(
                projdir / ".cerberus" / "cerberus.json",
                '{"provider": {"model": "deepseek"}}',
            )
            cfg = load_config(glob, project_dir=projdir)
            self.assertEqual(cfg.provider.model, "deepseek")
            self.assertEqual(cfg.agent_mode, "plan")

    def test_memory_appends_instructions(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            glob = tmpdir / "global.json"
            self._write(glob, '{"system_prompt_extra": "be brief"}')
            (tmpdir / "CERBERUS.md").write_text("project rules\n", encoding="utf-8")
            cfg = load_config(glob, project_dir=tmpdir)
            self.assertIn("be brief", cfg.system_prompt_extra)
            self.assertIn("project rules", cfg.system_prompt_extra)

    def test_env_beats_files(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            glob = tmpdir / "global.json"
            self._write(glob, '{"provider": {"model": "kimi"}}')
            old = os.environ.get("CERBERUS_MODEL")
            os.environ["CERBERUS_MODEL"] = "openai"
            try:
                cfg = load_config(glob, project_dir=tmpdir)
            finally:
                if old is None:
                    del os.environ["CERBERUS_MODEL"]
                else:
                    os.environ["CERBERUS_MODEL"] = old
            self.assertEqual(cfg.provider.model, "openai")


class ConfigGetSetTest(unittest.TestCase):
    def test_get_dotted(self):
        from servers.config import AppConfig

        cfg = AppConfig()
        self.assertEqual(config_get(cfg, "provider.model"), cfg.provider.model)
        self.assertEqual(config_get(cfg, "agent_mode"), "plan")
        with self.assertRaises(KeyError):
            config_get(cfg, "provider.nope")

    def test_set_json_roundtrip_and_coercion(self):
        import json
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "c.json"
            config_set(path, "provider.model", "deepseek")
            config_set(path, "tools.approve_external", "false")
            config_set(path, "tools.max_tool_rounds", "12")
            raw = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(raw["provider"]["model"], "deepseek")
            self.assertIs(raw["tools"]["approve_external"], False)
            self.assertEqual(raw["tools"]["max_tool_rounds"], 12)

    def test_set_refuses_secrets(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "c.json"
            with self.assertRaises(ValueError):
                config_set(path, "provider.api_key", "sk-123")

    def test_coerce(self):
        self.assertIs(_coerce_value("true"), True)
        self.assertIs(_coerce_value("off"), False)
        self.assertEqual(_coerce_value("42"), 42)
        self.assertEqual(_coerce_value("1.5"), 1.5)
        self.assertEqual(_coerce_value('"hi"'), "hi")
        self.assertEqual(_coerce_value("kimi"), "kimi")


class ScaffoldTest(unittest.TestCase):
    def test_creates_and_never_overwrites(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            cfg_path, mem_path, cfg_new, mem_new = scaffold_project(tmpdir)
            self.assertTrue(cfg_new and mem_new)
            self.assertTrue(cfg_path.is_file() and mem_path.is_file())
            cfg_path.write_text("custom\n", encoding="utf-8")
            _, _, cfg_new2, mem_new2 = scaffold_project(tmpdir)
            self.assertFalse(cfg_new2 or mem_new2)
            self.assertEqual(cfg_path.read_text(encoding="utf-8"), "custom\n")


if __name__ == "__main__":
    unittest.main()
