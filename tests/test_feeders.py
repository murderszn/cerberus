"""Focused unit tests for feeder selection, safety, and normalization."""

import json
import os
import stat
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from feeders.base import FeederAdapter
from feeders.gitleaks import GitleaksAdapter
from feeders.osv_scanner import OsvScannerAdapter
from feeders.zizmor import ZizmorAdapter
from feeders.normalize import deduplicate, normalize_finding, normalize_severity, redact
from feeders.registry import available_feeders, available_names, parse_selection, resolve_feeders
from feeders.runner import FeederRunner, _make_filtered_tree, _repository_files, summarize_results


class _FakeAdapter(FeederAdapter):
    name = "fake"
    executable_names = ("fake",)

    def __init__(self, args=None):
        self.args = args or []

    def build_argv(self, executable, root, files, work_dir, target=None):
        return [executable] + self.args

    def parse(self, stdout, stderr, output, root):
        raw = json.loads(stdout)
        return [normalize_finding(
            self.name, raw.get("rule"), raw.get("severity"), raw.get("path"),
            raw.get("line"), 1, raw.get("message"), root,
        )], redact(raw)


def _script(root, body):
    path = os.path.join(root, "fake")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("#!/usr/bin/env python3\nimport sys, time\n")
        handle.write("if '--version' in sys.argv:\n print('fake 1.2.3'); raise SystemExit(0)\n")
        handle.write(body)
    os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR)
    return path


class RegistryTest(unittest.TestCase):
    def test_all_phase_one_feeders_registered(self):
        self.assertEqual(available_feeders(), (
            "gitleaks", "osv-scanner", "zizmor", "scorecard", "actionlint"
        ))
        self.assertEqual(available_names(), available_feeders())
        self.assertEqual(parse_selection("osv,gitleaks"), ["osv-scanner", "gitleaks"])

    def test_alias_and_deduplication(self):
        selected = resolve_feeders("osv,osv-scanner,gitleaks")
        self.assertEqual([item.name for item in selected], ["osv-scanner", "gitleaks"])

    def test_unknown_rejected(self):
        with self.assertRaises(ValueError):
            resolve_feeders("made-up-tool")

    def test_applicability(self):
        by_name = {item.name: item for item in resolve_feeders("auto")}
        self.assertTrue(by_name["osv-scanner"].applicable(".", ["package-lock.json"])[0])
        self.assertFalse(by_name["osv-scanner"].applicable(".", ["README.md"])[0])
        self.assertTrue(by_name["zizmor"].applicable(".", [".github/workflows/ci.yml"])[0])
        self.assertTrue(by_name["actionlint"].applicable(".", [".github/workflows/ci.yaml"])[0])


class NormalizeTest(unittest.TestCase):
    def test_severity_mapping(self):
        expected = {"CRITICAL": "critical", "error": "high", "warning": "medium",
                    "moderate": "medium", "note": "info", 9.1: "critical", 7.2: "high"}
        for value, severity in expected.items():
            self.assertEqual(normalize_severity(value), severity)

    def test_fingerprint_stability_and_deduplication(self):
        one = normalize_finding("fake", "R1", "high", "src/a.py", 2, 1, "problem", ".")
        two = normalize_finding("fake", "R1", "high", "src/a.py", 2, 1, "problem", ".")
        self.assertEqual(one["fingerprint"], two["fingerprint"])
        self.assertEqual(len(deduplicate([one, two])), 1)

    def test_secret_redaction(self):
        value = redact({"Secret": "do-not-show", "message": "token=do-not-show"})
        self.assertNotIn("do-not-show", json.dumps(value))
        self.assertEqual(value["Secret"], "[REDACTED]")

    def test_gitleaks_raw_drops_secret_and_match(self):
        payload = json.dumps([{
            "RuleID": "generic", "File": "a.txt", "StartLine": 1,
            "Secret": "opaque-value", "Match": "opaque-value",
        }])
        findings, raw = GitleaksAdapter().parse("", "", payload, ".")
        serialized = json.dumps({"findings": findings, "raw": raw})
        self.assertNotIn("opaque-value", serialized)
        self.assertNotIn("Secret", raw[0])
        self.assertNotIn("Match", raw[0])

    def test_documented_finding_exit_codes_are_accepted(self):
        self.assertIn(1, OsvScannerAdapter.accepted_exit_codes)
        self.assertTrue({11, 12, 13, 14}.issubset(ZizmorAdapter.accepted_exit_codes))

    def test_zizmor_v1_location_and_determination(self):
        payload = json.dumps([{
            "ident": "template-injection", "desc": "unsafe expansion",
            "determinations": {"confidence": "High", "severity": "High"},
            "locations": [{
                "symbolic": {"key": {"Local": {"verbatim_path": "./.github/workflows/ci.yml"}}},
                "concrete": {"location": {"start_point": {"row": 4, "column": 2}}},
            }],
        }])
        findings, _ = ZizmorAdapter().parse(payload, "", None, ".")
        self.assertEqual(findings[0]["path"], ".github/workflows/ci.yml")
        self.assertEqual(findings[0]["line"], 5)
        self.assertEqual(findings[0]["column"], 3)
        self.assertEqual(findings[0]["severity"], "high")

    def test_path_traversal_is_not_reported(self):
        finding = normalize_finding("fake", "R", "low", "../../etc/passwd", 1, 1, "x", ".")
        self.assertEqual(finding["path"], ".")


class RunnerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_unavailable(self):
        runner = FeederRunner(which=lambda name: None)
        result = runner.run(_FakeAdapter(), self.tmp.name, ["README.md"])
        self.assertEqual(result["status"], "unavailable")

    def test_not_applicable_precedes_availability(self):
        adapter = resolve_feeders("actionlint")[0]
        runner = FeederRunner(which=lambda name: None)
        result = runner.run(adapter, self.tmp.name, ["README.md"])
        self.assertEqual(result["status"], "not_applicable")

    def test_completed_and_version(self):
        executable = _script(self.tmp.name,
            'print(\'{"rule":"R1","severity":"high","path":"a.py","line":2,"message":"bad"}\')\n')
        runner = FeederRunner(which=lambda name: executable)
        result = runner.run(_FakeAdapter(), self.tmp.name, ["a.py"])
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["toolVersion"], "fake 1.2.3")
        self.assertEqual(len(result["findings"]), 1)

    def test_timeout(self):
        executable = _script(self.tmp.name, "time.sleep(2)\n")
        result = FeederRunner(timeout=0.05, which=lambda name: executable).run(
            _FakeAdapter(), self.tmp.name, ["a.py"])
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["errors"][0]["kind"], "timeout")

    def test_malformed_json(self):
        executable = _script(self.tmp.name, "print('not json')\n")
        result = FeederRunner(which=lambda name: executable).run(
            _FakeAdapter(), self.tmp.name, ["a.py"])
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["errors"][0]["kind"], "malformed_output")

    def test_nonzero_exit(self):
        executable = _script(self.tmp.name, "print('boom', file=sys.stderr)\nraise SystemExit(7)\n")
        result = FeederRunner(which=lambda name: executable).run(
            _FakeAdapter(), self.tmp.name, ["a.py"])
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["errors"][0]["kind"], "exit_code")

    def test_bounded_output(self):
        executable = _script(self.tmp.name, "print('x' * 10000)\n")
        result = FeederRunner(capture_limit=100, which=lambda name: executable).run(
            _FakeAdapter(), self.tmp.name, ["a.py"])
        self.assertEqual(result["status"], "failed")

    def test_summary(self):
        summary = summarize_results([
            {"status": "completed"}, {"status": "not_applicable"},
            {"status": "unavailable"}, {"status": "failed"},
        ])
        self.assertEqual(summary, {"completed": 1, "not_applicable": 1,
                                   "unavailable": 1, "failed": 1})

    def test_cerberusignore_excludes_nested_scanner_checkout(self):
        os.makedirs(os.path.join(self.tmp.name, ".cerberus"))
        with open(os.path.join(self.tmp.name, ".cerberusignore"), "w") as handle:
            handle.write(".cerberus/\n")
        with open(os.path.join(self.tmp.name, "app.py"), "w") as handle:
            handle.write("print('ok')\n")
        with open(os.path.join(self.tmp.name, ".cerberus", "package-lock.json"), "w") as handle:
            handle.write("{}\n")
        files = _repository_files(self.tmp.name)
        self.assertIn("app.py", files)
        self.assertFalse(any(path.startswith(".cerberus/") for path in files))

    def test_filtered_tree_contains_only_selected_safe_files(self):
        with open(os.path.join(self.tmp.name, "package-lock.json"), "w") as handle:
            handle.write("{}\n")
        with open(os.path.join(self.tmp.name, "README.md"), "w") as handle:
            handle.write("docs\n")
        destination = os.path.join(self.tmp.name, "stage")
        os.makedirs(destination)
        adapter = OsvScannerAdapter()
        _make_filtered_tree(
            self.tmp.name, destination, adapter, ["package-lock.json", "README.md"])
        self.assertTrue(os.path.isfile(os.path.join(destination, "package-lock.json")))
        self.assertFalse(os.path.exists(os.path.join(destination, "README.md")))


if __name__ == "__main__":
    unittest.main()
