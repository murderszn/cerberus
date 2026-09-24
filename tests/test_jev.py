import base64
import json
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from servers import jev


SHA = "a" * 40
BLOB = "b" * 40


def result(path="app.py", probability=.85):
    return {"path": path, "status": "analyzed", "analysis": {
        "model": "jev-1.13.0", "answers": {
            "risk_0": {"type": "noul", "noul": probability}}}}


class JevTests(unittest.TestCase):
    def test_env_file_key_loading(self):
        for line in ['jev_api_key=test-value', 'export JEV_API_KEY="test-value" # comment']:
            with patch.dict(jev.os.environ, {}, clear=True), patch("pathlib.Path.read_text", return_value=line):
                self.assertEqual(jev.load_api_key(), "test-value")

    def test_environment_precedes_file(self):
        with patch.dict(jev.os.environ, {"JEV_API_KEY": "env-value"}, clear=True), patch("pathlib.Path.read_text") as read:
            self.assertEqual(jev.load_api_key(), "env-value")
            read.assert_not_called()

    def test_end_to_end_contract(self):
        responses = [
            {"default_branch": "main"}, {"sha": SHA},
            {"tree": [
                {"path": "app.py", "mode": "100644", "type": "blob", "size": 20, "sha": BLOB},
                {"path": ".env", "mode": "100644", "type": "blob", "size": 20, "sha": BLOB}]},
            {"encoding": "base64", "content": base64.b64encode(b'api_key = "private"').decode()},
            result()["analysis"],
        ]
        with patch.object(jev, "_request", side_effect=responses) as request:
            files = jev.integrate_jev_with_cerberus("https://github.com/example/project",
                {"api_key": "test-key", "api_secret": "never-send", "github_token": "github-key"},
                ["vulnerabilities"])
        self.assertEqual(files[0]["path"], "app.py")
        self.assertEqual(files[0]["priority"], "high")
        self.assertEqual(files[1]["priority"], "unassessed")
        call = request.call_args_list[-1]
        self.assertEqual(call.args[:2], (jev.ENDPOINT, "test-key"))
        payload = call.args[2]
        self.assertEqual(payload["model"], "jev-latest")
        self.assertEqual(payload["questions"]["risk_0"]["type"], "noul")
        self.assertNotIn("private", json.dumps(payload))
        self.assertNotIn("never-send", str(request.call_args_list))
        self.assertIn(SHA, request.call_args_list[2].args[0])

    def test_order_and_native_score_unchanged(self):
        files = jev.categorize_and_prioritize_files(
            [result("low.py", .1), result("high.py", .9), result("middle.py", .5)],
            ["vulnerabilities"])
        self.assertEqual([f["priority"] for f in files], ["high", "medium", "low"])
        report = {"score": 84, "grade": "B", "policy": {"passed": True}}
        self.assertIs(jev.integrate_with_cerberus(files, report), files)
        self.assertEqual(report["score"], 84)
        self.assertTrue(report["policy"]["passed"])
        self.assertEqual(report["triage"]["analyzed"], 3)

    def test_bad_probabilities(self):
        for probability in [None, True, "0.5", -1, 1.01, float("nan"), float("inf")]:
            with self.subTest(probability=probability), self.assertRaises(jev.JevError):
                jev.categorize_and_prioritize_files([result(probability=probability)], ["vulnerabilities"])

    def test_input_validation_before_network(self):
        with patch.object(jev, "_request") as request:
            for url in ["http://github.com/a/b", "https://github.com.evil/a/b", "https://github.com/a/b/tree/main"]:
                with self.assertRaises(jev.JevError):
                    jev.integrate_jev_with_cerberus(url, {"api_key": "test"}, ["vulnerabilities"])
            with self.assertRaises(jev.JevError):
                jev.integrate_jev_with_cerberus("https://github.com/a/b",
                    {"api_key": "test", "api_endpoint": "https://evil.test"}, ["vulnerabilities"])
            request.assert_not_called()

    def test_sensitive_and_ignored_files(self):
        for path in [".env.production", "config/credentials.json", "key.pem", "node_modules/a.js", "src/private.py", "../escape.py"]:
            self.assertIsNotNone(jev._skip_reason({"path": path, "size": 10, "mode": "100644"}, ["src/*"]))
        self.assertEqual(jev._skip_reason({"path": "link.py", "mode": "120000"}, []), "not_regular_file")

    def test_truncated_tree_fails(self):
        with patch.object(jev, "_request", side_effect=[{"default_branch": "main"}, {"sha": SHA}, {"truncated": True}]), self.assertRaises(jev.JevError):
            jev.integrate_jev_with_cerberus("https://github.com/a/b", {"api_key": "test"}, ["vulnerabilities"])

    def test_commit_mismatch_rejected(self):
        with self.assertRaises(jev.JevError):
            jev.integrate_with_cerberus([{"sha": SHA}], {"target": {"sha": BLOB}})

    def test_nested_ignore(self):
        self.assertEqual(jev._skip_reason(
            {"path": "src/internal/a.py", "mode": "100644", "size": 20},
            ["internal/"]), "cerberusignore")

    def test_live_events_are_ordered_and_pinned(self):
        responses = [{"default_branch": "main"}, {"sha": SHA}, {"tree": [
            {"path": "app.py", "type": "blob", "mode": "100644", "size": 10, "sha": BLOB}]},
            {"encoding": "base64", "content": base64.b64encode(b"print(1)").decode()}, result()["analysis"]]
        events = []
        with patch.object(jev, "_request", side_effect=responses) as request:
            jev.jev_api_fetch_and_analyze("https://github.com/a/b", {"api_key": "test", "commit_sha": SHA}, ["vulnerabilities"], events.append)
        self.assertEqual([e["type"] for e in events], ["phase", "inventory", "evaluating", "categorized"])
        self.assertTrue(request.call_args_list[1].args[0].endswith(SHA))
        self.assertEqual(events[1]["candidates"], ["app.py"])
        self.assertGreaterEqual(events[-1]["latencyMs"], 0)
        self.assertNotIn("analysis", events[-1]["file"])

    def test_file_budget_is_visible(self):
        tree = {"tree": [{"path": "app.py", "type": "blob", "mode": "100644", "size": 10}]}
        with patch.object(jev, "MAX_FILES", 0), patch.object(jev, "_request", side_effect=[{"default_branch": "main"}, {"sha": SHA}, tree]):
            files = jev.integrate_jev_with_cerberus("https://github.com/a/b", {"api_key": "test"}, ["vulnerabilities"])
        self.assertEqual(files[0]["reason"], "file_count_limit")
        self.assertIsNone(files[0]["riskScore"])

    def test_http_errors_do_not_leak_remote_body(self):
        with patch.object(jev, "build_opener") as opener:
            opener.return_value.open.side_effect = HTTPError(jev.ENDPOINT, 401, "secret response", {}, None)
            with self.assertRaisesRegex(jev.JevError, r"HTTP 401") as error:
                jev._request(jev.ENDPOINT, "private-key", {})
        self.assertNotIn("secret", str(error.exception))

    def test_retry_is_bounded(self):
        with patch.object(jev, "build_opener") as opener, patch.object(jev.time, "sleep") as sleep:
            opener.return_value.open.side_effect = HTTPError(jev.ENDPOINT, 429, "rate limit", {}, None)
            with self.assertRaises(jev.JevError):
                jev._request(jev.ENDPOINT, "test", {})
        self.assertEqual(opener.return_value.open.call_count, 3)
        self.assertEqual(sleep.call_count, 2)

    def test_digest_includes_advisory(self):
        from servers.scan_context import build_scan_digest
        report = {}
        jev.integrate_with_cerberus(jev.categorize_and_prioritize_files([result()], ["vulnerabilities"]), report)
        self.assertIn("Jev advisory triage", build_scan_digest(report))


if __name__ == "__main__":
    unittest.main()
