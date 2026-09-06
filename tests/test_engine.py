"""Offline engine tests for the Cerberus CLI scanner.

These test the *real* evaluation logic (examine.build_report) against synthetic
local directories — no network, no GitHub API. They assert structural invariants
of the cerberus.report/2 schema plus targeted check outcomes, so they stay green
when individual catalog severities/weights are tuned without breaking the shape.
"""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import examine  # noqa: E402

CATALOG = examine.load_catalog()


def _write_files(root, files):
    for rel, content in files.items():
        path = os.path.join(root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)


def _build_report(root, files, extra=()):
    _write_files(root, files)
    target_info = {
        "kind": "local",
        "sha": None,
        "display_block": {"kind": "local", "display": os.path.basename(root), "path": root, "ref": None},
    }
    return examine.build_report(CATALOG, target_info, root, {}, None, list(extra))


def _find_check(report, check_id):
    for agent in report["agents"]:
        for check in agent["checks"]:
            if check["id"] == check_id:
                return check
    raise AssertionError(f"check {check_id} not found in report")


CRED_SOURCE = """
import os
def connect():
    client = boto3.client('s3')
    print('connecting')
"""

VULN_SOURCE = """
import boto3

def init():
    client = boto3.client(
        's3',
        aws_access_key_id='AKIAQ7XK4M2XYZABC12',
        aws_secret_access_key='k8Lm2pQ4rT6vW8xZ0aB3cD5eF7gH9iJ1'
    )
    return client
"""


class CatalogIntegrityTest(unittest.TestCase):
    def test_agent_weights_sum_to_100(self):
        total = sum(a["weight"] for a in CATALOG["agents"])
        self.assertEqual(total, 100)

    def test_agent_ids_unique(self):
        ids = [a["id"] for a in CATALOG["agents"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_check_ids_unique(self):
        ids = [c["id"] for c in CATALOG["checks"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_every_check_refers_to_defined_agent(self):
        agent_ids = {a["id"] for a in CATALOG["agents"]}
        for c in CATALOG["checks"]:
            self.assertIn(c["agent"], agent_ids, c["id"])

    def test_checks_have_valid_severity(self):
        valid = {"critical", "high", "medium", "low"}
        for c in CATALOG["checks"]:
            self.assertIn(c["severity"], valid, c["id"])

    def test_all_nine_agents_present(self):
        ids = {a["id"] for a in CATALOG["agents"]}
        expected = {"sentinel", "vault", "gatekeeper", "librarian", "conduit",
                    "watchtower", "shield", "auditor", "architect"}
        self.assertEqual(ids, expected)


class ReportShapeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.report = _build_report(self.tmp.name, {
            "app.py": CRED_SOURCE,
            "README.md": "# demo\n",
        })

    def test_schema_is_report_v2(self):
        self.assertEqual(self.report["schema"], "cerberus.report/2")

    def test_counts_sum_to_total(self):
        c = self.report["counts"]
        summed = c["pass"] + c["fail"] + c["not_applicable"] + c["skipped"]
        self.assertEqual(summed, c["total"])
        self.assertEqual(c["total"], len(CATALOG["checks"]))

    def test_all_agents_present_with_matching_weights(self):
        agent_ids = {a["id"] for a in self.report["agents"]}
        self.assertEqual(len(agent_ids), 9)
        for agent in self.report["agents"]:
            definition = next(a for a in CATALOG["agents"] if a["id"] == agent["id"])
            self.assertEqual(agent["weight"], definition["weight"], agent["id"])

    def test_coverage_is_present(self):
        cov = self.report["coverage"]
        for key in ("filesInTree", "filesEligible", "filesScanned", "filesSkipped",
                    "bytesScanned", "truncated", "skipReasons"):
            self.assertIn(key, cov)

    def test_local_findings_use_file_url(self):
        # Local scans must produce file:// permalinks, not github URLs.
        for agent in self.report["agents"]:
            for check in agent["checks"]:
                for finding in check["findings"]:
                    self.assertTrue(finding["url"].startswith("file://"), finding["url"])


class TargetedOutcomeTest(unittest.TestCase):
    def test_vulnerable_repo_fails_hardcoded_credential(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = _build_report(tmp, {"src/app.py": VULN_SOURCE})
            check = _find_check(report, "S-01")
            self.assertEqual(check["status"], "fail")
            self.assertGreaterEqual(len(check["findings"]), 1)
            first = check["findings"][0]
            self.assertTrue(
                "aws_secret_access_key" in first["snippet"] or "aws_access_key_id" in first["snippet"],
                first["snippet"],
            )
            self.assertIsInstance(first["line"], int)
            self.assertGreaterEqual(first["line"], 1)

    def test_clean_repo_scores_high(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = _build_report(tmp, {
                "app.py": CRED_SOURCE,
                "README.md": "# demo\n",
                "LICENSE": "MIT\n",
                "SECURITY.md": "# Security\n",
                ".gitignore": "node_modules/\n",
                "requirements.txt": "requests==2.31.0\n",
                ".github/workflows/ci.yml": "on: push\njobs:\n  build:\n    runs-on: ubuntu\n    steps:\n      - uses: actions/checkout@v4\n",
                "tests/test_app.py": "def test_ok():\n    assert True\n",
            })
            # A small, tidy repo should not score in the failure range.
            self.assertGreater(report["score"], 60)
            s = _find_check(report, "S-01")
            self.assertEqual(s["status"], "pass")


if __name__ == "__main__":
    unittest.main()
