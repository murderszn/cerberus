"""Loopback-only streaming bridge for the Cerberus browser preview.

Run: python -m servers.jev_live. Never serves repository files or credentials.
"""
import json
import threading
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from servers.jev import (JevError, load_api_key, jev_api_fetch_and_analyze,
                         categorize_and_prioritize_files)
from servers.auth.store import resolve_api_key
from servers.config import load_config

ORIGINS = {"http://127.0.0.1:8765", "http://localhost:8765"}
BUSY = threading.Lock()
CRITERIA = ["vulnerabilities", "quality issues", "maintainability"]
POLLINATIONS_URL = "https://gen.pollinations.ai/v1/chat/completions"


def pollinations_synthesis(prompt):
    key = resolve_api_key()
    if not key:
        try:
            key = resolve_api_key(config_file_key=load_config().provider.api_key)
        except RuntimeError:
            pass  # A missing optional YAML parser must not break env or saved credentials.
    if not key:
        raise ValueError("Connect Pollinations in the Cerberus CLI first, or set POLLINATIONS_API_KEY.")
    payload = json.dumps({"model": "kimi", "messages": [
        {"role": "system", "content": "Summarize only the supplied Cerberus findings and Jev advisory triage. Never invent evidence or treat Jev probabilities as confirmed findings."},
        {"role": "user", "content": prompt}], "stream": False, "temperature": 0.2}).encode()
    request = urllib.request.Request(POLLINATIONS_URL, data=payload, headers={
        "Authorization": "Bearer " + key.key, "Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            data = json.loads(response.read(262145))
    except urllib.error.HTTPError as exc:
        if exc.code == 401:
            raise ValueError("Pollinations rejected the saved API key. Refresh your Cerberus Pollinations login or set POLLINATIONS_API_KEY.") from exc
        raise ValueError("Pollinations returned HTTP " + str(exc.code)) from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise ValueError("Pollinations is unreachable right now.") from exc
    answer = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    if not isinstance(answer, str) or not answer.strip():
        raise ValueError("Pollinations returned no report text.")
    return answer


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def allowed(self):
        return (self.headers.get("Host") in {"127.0.0.1:8766", "localhost:8766"}
                and self.headers.get("Origin") in ORIGINS)

    def send_headers(self, status=200, content_type="application/json"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        if status in (400, 403):
            self.send_header("Content-Length", "0")
        if self.allowed():
            self.send_header("Access-Control-Allow-Origin", self.headers["Origin"])
            self.send_header("Vary", "Origin")
        self.end_headers()

    def do_OPTIONS(self):
        if not self.allowed():
            self.send_headers(403)
            return
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", self.headers["Origin"])
        self.send_header("Access-Control-Allow-Methods", "POST")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        if not self.allowed() or self.path not in {"/triage", "/synthesis"}:
            self.send_headers(403)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            limit = 65536 if self.path == "/synthesis" else 4096
            if not 0 < length <= limit or self.headers.get("Content-Type") != "application/json":
                raise ValueError()
            body = json.loads(self.rfile.read(length))
            if not isinstance(body, dict):
                raise ValueError()
        except (ValueError, OSError):
            self.send_headers(400)
            return
        if self.path == "/synthesis":
            prompt = body.get("prompt", "")
            if not isinstance(prompt, str) or not 0 < len(prompt) <= 50000:
                self.send_headers(400)
                return
            try:
                result = {"response": pollinations_synthesis(prompt), "model": "kimi"}
                self.send_headers(200)
            except ValueError as exc:
                result = {"error": str(exc)}
                self.send_headers(503)
            self.wfile.write(json.dumps(result).encode())
            return
        if not BUSY.acquire(blocking=False):
            self.send_headers(409)
            self.wfile.write(b'{"error":"Another Jev scan is active. Try again shortly."}')
            return
        try:
            self.send_headers(200, "application/x-ndjson")

            def emit(event):
                self.wfile.write((json.dumps(event) + "\n").encode())
                self.wfile.flush()  # A disconnected browser stops work at the next event.

            try:
                credentials = {"api_key": load_api_key(), "commit_sha": body.get("sha")}
                if body.get("githubToken"):
                    credentials["github_token"] = body["githubToken"]
                result = jev_api_fetch_and_analyze(body.get("repo_url"), credentials, CRITERIA, emit)
                files = categorize_and_prioritize_files(result["data"], CRITERIA)
                emit({"type": "done", "triage": {"schema": "cerberus.triage/1",
                      "source": "jev", "advisory": True, "files": files,
                      "analyzed": sum(f["status"] == "analyzed" for f in files),
                      "skipped": sum(f["status"] == "skipped" for f in files)}})
            except JevError as exc:
                emit({"type": "error", "message": str(exc)})
            except (BrokenPipeError, ConnectionResetError):
                pass
            except Exception:
                emit({"type": "error", "message": "Jev triage failed. Native results remain available."})
        finally:
            BUSY.release()


if __name__ == "__main__":
    print("Jev live bridge: http://127.0.0.1:8766 (local preview only)", flush=True)
    ThreadingHTTPServer(("127.0.0.1", 8766), Handler).serve_forever()
