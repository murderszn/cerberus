import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXAMINE = ROOT / "examine.py"


class CliModeTest(unittest.TestCase):
    def test_native_only_emits_empty_orchestration_sections(self):
        with tempfile.TemporaryDirectory() as repo, tempfile.TemporaryDirectory() as output:
            Path(repo, "README.md").write_text("safe fixture\n", encoding="utf-8")
            report_path = Path(output, "report.json")
            result = subprocess.run(
                [sys.executable, str(EXAMINE), repo, "--native-only", "--quiet",
                 "--json", str(report_path)], capture_output=True, text=True, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(report["alignment"]["status"], "not_run")
            self.assertEqual(report["feeders"]["tools"], [])
            self.assertEqual(report["native"]["score"], report["score"])

    def test_strict_feeder_failure_changes_exit_only_when_requested(self):
        with tempfile.TemporaryDirectory() as repo, tempfile.TemporaryDirectory() as binaries:
            workflow = Path(repo, ".github", "workflows", "ci.yml")
            workflow.parent.mkdir(parents=True)
            workflow.write_text("jobs: {}\n", encoding="utf-8")
            fake = Path(binaries, "actionlint")
            fake.write_text("#!/bin/sh\nexit 2\n", encoding="utf-8")
            fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
            env = dict(os.environ)
            env["PATH"] = binaries + os.pathsep + env.get("PATH", "")
            base = [sys.executable, str(EXAMINE), repo, "--feeders", "actionlint", "--quiet"]
            optional = subprocess.run(base, env=env, capture_output=True, text=True, check=False)
            strict = subprocess.run(base + ["--strict-feeders"], env=env,
                                    capture_output=True, text=True, check=False)
            self.assertEqual(optional.returncode, 0, optional.stderr)
            self.assertEqual(strict.returncode, 1, strict.stderr)


if __name__ == "__main__":
    unittest.main()
