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

    def test_fail_on_severity_gate(self):
        with tempfile.TemporaryDirectory() as repo:
            # S-05 (critical): shell execution with interpolated input.
            Path(repo, "deploy.py").write_text(
                'import subprocess\nsubprocess.run(f"deploy {target}", shell=True)\n',
                encoding="utf-8",
            )
            base = [sys.executable, str(EXAMINE), repo, "--native-only", "--quiet"]
            noisy = subprocess.run(base, capture_output=True, text=True, check=False)
            self.assertEqual(noisy.returncode, 0, noisy.stderr)
            gated = subprocess.run(base + ["--fail-on", "critical"],
                                   capture_output=True, text=True, check=False)
            self.assertEqual(gated.returncode, 1, gated.stderr)
            # At-or-above semantics: --fail-on high also trips on a critical.
            gated_high = subprocess.run(base + ["--fail-on", "high"],
                                        capture_output=True, text=True, check=False)
            self.assertEqual(gated_high.returncode, 1, gated_high.stderr)

    def test_fail_on_passes_for_clean_repo(self):
        with tempfile.TemporaryDirectory() as repo:
            Path(repo, "README.md").write_text("safe fixture\n", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(EXAMINE), repo, "--native-only", "--quiet",
                 "--fail-on", "critical"],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

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
