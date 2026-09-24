import http.client
import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from servers import jev_live


class LiveBridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), jev_live.Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def request(self, origin="http://127.0.0.1:8765", host="127.0.0.1:8766", method="POST", body=None, path="/triage"):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=3)
        connection.request(method, path, json.dumps(body or {"repo_url": "https://github.com/a/b", "sha": "a" * 40}),
                           {"Host": host, "Origin": origin, "Content-Type": "application/json"})
        response = connection.getresponse()
        status, headers, data = response.status, dict(response.getheaders()), response.read().decode()
        connection.close()
        return status, headers, data

    def test_rejects_other_origins_and_dns_rebinding(self):
        for origin, host in [("https://evil.test", "127.0.0.1:8766"),
                             ("http://127.0.0.1:8765", "evil.test:8766")]:
            self.assertEqual(self.request(origin=origin, host=host)[0], 403)

    def test_preflight(self):
        status, headers, _ = self.request(method="OPTIONS")
        self.assertEqual(status, 204)
        self.assertEqual(headers["Access-Control-Allow-Origin"], "http://127.0.0.1:8765")

    def test_stream_and_credentials_stay_server_side(self):
        def scan(repo, credentials, criteria, emit):
            self.assertEqual(credentials["api_key"], "never-expose")
            self.assertEqual(credentials["commit_sha"], "a" * 40)
            emit({"type": "phase", "message": "Reading repository"})
            emit({"type": "inventory", "files": [], "candidates": [], "sha": "a" * 40})
            return {"data": []}
        with patch.object(jev_live, "load_api_key", return_value="never-expose"), patch.object(jev_live, "jev_api_fetch_and_analyze", side_effect=scan):
            status, headers, data = self.request()
        self.assertEqual(status, 200)
        self.assertEqual(headers["Content-Type"], "application/x-ndjson")
        events = [json.loads(line) for line in data.splitlines()]
        self.assertEqual([event["type"] for event in events], ["phase", "inventory", "done"])
        self.assertNotIn("never-expose", data)

    def test_error_does_not_claim_completion(self):
        with patch.object(jev_live, "load_api_key", side_effect=jev_live.JevError("Missing key")):
            _, _, data = self.request()
        self.assertEqual(json.loads(data)["type"], "error")

    def test_concurrent_scan_rejected(self):
        with jev_live.BUSY:
            self.assertEqual(self.request()[0], 409)

    def test_pollinations_synthesis_is_local_and_returns_report(self):
        with patch.object(jev_live, "pollinations_synthesis", return_value="Review the native evidence first.") as synthesize:
            status, headers, data = self.request(path="/synthesis", body={"prompt": "Native findings and Jev priorities"})
        self.assertEqual(status, 200)
        self.assertEqual(headers["Access-Control-Allow-Origin"], "http://127.0.0.1:8765")
        self.assertEqual(json.loads(data)["response"], "Review the native evidence first.")
        synthesize.assert_called_once_with("Native findings and Jev priorities")

    def test_pollinations_synthesis_rejects_empty_prompt(self):
        self.assertEqual(self.request(path="/synthesis", body={"prompt": ""})[0], 400)

    def test_pollinations_response_contract(self):
        response = MagicMock()
        response.read.return_value = b'{"choices":[{"message":{"content":"Prioritize the verified finding."}}]}'
        response.__enter__.return_value = response
        with patch.object(jev_live, "resolve_api_key", return_value=SimpleNamespace(key="test-key")), \
             patch.object(jev_live.urllib.request, "urlopen", return_value=response) as urlopen:
            answer = jev_live.pollinations_synthesis("Same commit, native findings, Jev priorities")
        self.assertEqual(answer, "Prioritize the verified finding.")
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, jev_live.POLLINATIONS_URL)
        self.assertIn(b"Jev priorities", request.data)


if __name__ == "__main__":
    unittest.main()
