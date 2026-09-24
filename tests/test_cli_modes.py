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

    def test_report_notices_go_to_stderr(self):
        with tempfile.TemporaryDirectory() as repo, tempfile.TemporaryDirectory() as output:
            Path(repo, "README.md").write_text("safe fixture\n", encoding="utf-8")
            report_path = Path(output, "report.json")
            result = subprocess.run(
                [sys.executable, str(EXAMINE), repo, "--native-only",
                 "--json", str(report_path)],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn("written to", result.stdout)
            self.assertIn("JSON report written to", result.stderr)

    def test_fail_under_prints_reason_on_stderr(self):
        with tempfile.TemporaryDirectory() as repo:
            Path(repo, "README.md").write_text("safe fixture\n", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(EXAMINE), repo, "--native-only", "--quiet",
                 "--fail-under", "100"],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("FAIL", result.stderr)

    def test_fail_under_range_rejected(self):
        with tempfile.TemporaryDirectory() as repo:
            Path(repo, "README.md").write_text("safe fixture\n", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(EXAMINE), repo, "--native-only",
                 "--fail-under", "101"],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("--fail-under", result.stderr)

    def test_unknown_only_suggests_valid_ids(self):
        with tempfile.TemporaryDirectory() as repo:
            Path(repo, "README.md").write_text("safe fixture\n", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(EXAMINE), repo, "--native-only",
                 "--only", "no-such-agent"],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("no-such-agent", result.stderr)
            self.assertIn("valid:", result.stderr)

    def test_color_precedence_no_color_flag_over_env_over_tty(self):
        with tempfile.TemporaryDirectory() as repo:
            Path(repo, "README.md").write_text("safe fixture\n", encoding="utf-8")
            env = dict(os.environ)
            env["NO_COLOR"] = "1"
            # NO_COLOR alone suppresses ANSI even when piped (non-TTY anyway).
            plain = subprocess.run(
                [sys.executable, str(EXAMINE), repo, "--native-only"],
                capture_output=True, text=True, check=False, env=env,
            )
            # Explicit --color always overrides NO_COLOR.
            forced = subprocess.run(
                [sys.executable, str(EXAMINE), repo, "--native-only",
                 "--color", "always"],
                capture_output=True, text=True, check=False, env=env,
            )
            # Explicit --no-color wins over --color always.
            off = subprocess.run(
                [sys.executable, str(EXAMINE), repo, "--native-only",
                 "--color", "always", "--no-color"],
                capture_output=True, text=True, check=False, env=env,
            )
            self.assertEqual(plain.returncode, 0, plain.stderr)
            self.assertNotIn("\033[", plain.stdout)
            self.assertEqual(forced.returncode, 0, forced.stderr)
            self.assertIn("\033[", forced.stdout)
            self.assertEqual(off.returncode, 0, off.stderr)
            self.assertNotIn("\033[", off.stdout)

    def test_version_flag(self):
        result = subprocess.run(
            [sys.executable, str(EXAMINE), "--version"],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 0)
        self.assertRegex(result.stdout.strip(), r"\d+\.\d+\.\d+")

    def test_progress_phases_on_stderr_when_forced(self):
        with tempfile.TemporaryDirectory() as repo:
            Path(repo, "README.md").write_text("safe fixture\n", encoding="utf-8")
            shown = subprocess.run(
                [sys.executable, str(EXAMINE), repo, "--native-only", "--progress"],
                capture_output=True, text=True, check=False,
            )
            hidden = subprocess.run(
                [sys.executable, str(EXAMINE), repo, "--native-only", "--progress",
                 "--no-progress"],
                capture_output=True, text=True, check=False,
            )
            quiet = subprocess.run(
                [sys.executable, str(EXAMINE), repo, "--native-only", "--quiet",
                 "--progress"],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(shown.returncode, 0, shown.stderr)
            self.assertIn("cerberus: scanning", shown.stderr)
            self.assertIn("--native-only", shown.stderr)
            self.assertNotIn("cerberus:", shown.stdout)
            self.assertEqual(hidden.returncode, 0, hidden.stderr)
            self.assertNotIn("cerberus:", hidden.stderr)
            self.assertEqual(quiet.returncode, 0, quiet.stderr)
            self.assertNotIn("cerberus:", quiet.stderr)

    def test_severity_filter_echo_and_limit(self):
        with tempfile.TemporaryDirectory() as repo:
            Path(repo, "deploy.py").write_text(
                'import subprocess\nsubprocess.run(f"deploy {target}", shell=True)\n',
                encoding="utf-8",
            )
            filtered = subprocess.run(
                [sys.executable, str(EXAMINE), repo, "--native-only",
                 "--severity", "high"],
                capture_output=True, text=True, check=False,
            )
            unfiltered = subprocess.run(
                [sys.executable, str(EXAMINE), repo, "--native-only"],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(filtered.returncode, 0, filtered.stderr)
            self.assertIn("showing high and above", filtered.stdout)
            self.assertNotIn("showing low and above", unfiltered.stdout)
            limited = subprocess.run(
                [sys.executable, str(EXAMINE), repo, "--native-only", "--limit", "0"],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(limited.returncode, 0, limited.stderr)
            bad = subprocess.run(
                [sys.executable, str(EXAMINE), repo, "--native-only", "--limit", "-1"],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(bad.returncode, 2)
            self.assertIn("--limit", bad.stderr)


if __name__ == "__main__":
    unittest.main()
