import unittest

import examine


class OrchestrationReportTest(unittest.TestCase):
    def _report(self):
        return {
            "schema": "cerberus.report/2",
            "target": {"display": "fixture"},
            "scannedAt": "2026-01-01T00:00:00Z",
            "engine": {"version": "2.0.0", "source": "cli"},
            "score": 100.0,
            "grade": "A",
            "counts": {"critical": 0, "high": 0, "medium": 0, "low": 0,
                       "pass": 0, "fail": 0, "not_applicable": 0,
                       "skipped": 0, "total": 0},
            "agents": [],
            "notes": [],
        }

    def test_external_findings_do_not_change_native_score(self):
        report = self._report()
        alignment = {
            "schema": "cerberus.alignment/1", "status": "completed",
            "score": 80, "grade": "B", "findings": [{
                "ruleId": "AL-TEST", "severity": "critical", "path": "AGENTS.md",
                "line": 1, "message": "unsafe instruction", "remediation": "remove it",
                "fingerprint": "sha256:test",
            }],
        }
        examine.enrich_report(report, alignment, [])
        self.assertEqual(report["score"], 100.0)
        self.assertEqual(report["native"]["score"], 100.0)
        self.assertFalse(report["policy"]["passed"])

    def test_strict_feeder_failure_is_policy_blocker(self):
        report = self._report()
        feeder = {"tool": "gitleaks", "status": "failed", "findings": []}
        examine.enrich_report(report, feeder_results=[feeder], strict_feeders=True)
        self.assertFalse(report["policy"]["passed"])
        self.assertEqual(report["feeders"]["summary"]["failed"], 1)

    def test_optional_unavailable_feeder_is_warning(self):
        report = self._report()
        feeder = {"tool": "zizmor", "status": "unavailable", "findings": []}
        examine.enrich_report(report, feeder_results=[feeder])
        self.assertTrue(report["policy"]["passed"])
        self.assertTrue(report["policy"]["warnings"])

    def test_strict_unavailable_feeder_is_blocker(self):
        report = self._report()
        feeder = {"tool": "zizmor", "status": "unavailable", "findings": []}
        examine.enrich_report(report, feeder_results=[feeder], strict_feeders=True)
        self.assertFalse(report["policy"]["passed"])

    def test_sarif_contains_provenance_and_fingerprint(self):
        report = self._report()
        feeder = {"tool": "actionlint", "toolVersion": "1.0", "status": "completed",
                  "findings": [{"ruleId": "syntax", "severity": "high",
                                "path": ".github/workflows/ci.yml", "line": 2,
                                "message": "bad workflow", "remediation": "fix syntax",
                                "fingerprint": "sha256:stable"}]}
        examine.enrich_report(report, feeder_results=[feeder])
        sarif = examine.render_sarif(report)
        self.assertEqual(sarif["runs"][1]["tool"]["driver"]["name"], "actionlint")
        self.assertEqual(sarif["runs"][1]["results"][0]["partialFingerprints"]["cerberus/v1"],
                         "sha256:stable")

    def test_html_renders_with_zero_feeders(self):
        report = self._report()
        examine.enrich_report(report)
        output = examine.render_html(report)
        self.assertIn("Native Cerberus Score", output)
        self.assertIn("No feeder tools were selected", output)


if __name__ == "__main__":
    unittest.main()
