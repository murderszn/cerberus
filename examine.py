#!/usr/bin/env python3
"""Cerberus CLI scanner.

Loads the single-source-of-truth check catalog from checks.json (next to this
script) and evaluates a local directory or a GitHub repository against it,
emitting the cerberus.report/2 schema shared with the web app.

Python 3.9+, standard library only.
"""
from __future__ import annotations

import argparse
import datetime
import fnmatch
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.error
import urllib.request
from http.server import SimpleHTTPRequestHandler, HTTPServer

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CHECKS_JSON_PATH = os.path.join(SCRIPT_DIR, "checks.json")

ENGINE_VERSION = "2.0.0"
MAX_FILE_BYTES = 512 * 1024  # 512 KB
SCHEMA = "cerberus.report/2"

SEVERITY_ORDER = {"critical": 4, "high": 3, "medium": 2, "low": 1}

LICENSE_FILENAMES = {
    "license", "license.md", "license.txt", "license.rst",
    "copying", "copying.md", "copying.txt",
    "unlicense", "license-mit", "license-apache",
}

EXT_LANGUAGE = {
    ".py": "Python", ".js": "JavaScript", ".jsx": "JavaScript", ".ts": "TypeScript",
    ".tsx": "TypeScript", ".mjs": "JavaScript", ".cjs": "JavaScript", ".go": "Go",
    ".java": "Java", ".rb": "Ruby", ".php": "PHP", ".cs": "C#", ".rs": "Rust",
    ".kt": "Kotlin", ".swift": "Swift", ".scala": "Scala", ".sh": "Shell",
    ".bash": "Shell", ".html": "HTML", ".vue": "Vue", ".svelte": "Svelte",
    ".c": "C", ".cpp": "C++", ".h": "C",
}


# --------------------------------------------------------------------------
# Glob matching (supports ** the same way checks.json expects)
# --------------------------------------------------------------------------

_glob_cache = {}


def _glob_to_regex(pattern: str) -> re.Pattern:
    pat = pattern.replace("\\", "/")
    i, n = 0, len(pat)
    out = []
    while i < n:
        c = pat[i]
        if c == "*":
            if i + 1 < n and pat[i + 1] == "*":
                if i + 2 < n and pat[i + 2] == "/":
                    out.append("(?:.*/)?")
                    i += 3
                    continue
                else:
                    out.append(".*")
                    i += 2
                    continue
            out.append("[^/]*")
            i += 1
            continue
        elif c == "?":
            out.append("[^/]")
            i += 1
            continue
        else:
            out.append(re.escape(c))
            i += 1
            continue
    return re.compile("^" + "".join(out) + "$")


def glob_match(path: str, pattern: str) -> bool:
    key = pattern
    rx = _glob_cache.get(key)
    if rx is None:
        rx = _glob_to_regex(pattern)
        _glob_cache[key] = rx
    return rx.match(path) is not None


def any_glob_match(path: str, patterns) -> bool:
    return any(glob_match(path, p) for p in patterns)


def files_matching(all_files, patterns):
    return [f for f in all_files if any_glob_match(f, patterns)]


# --------------------------------------------------------------------------
# Target parsing / acquisition
# --------------------------------------------------------------------------

class TargetError(Exception):
    pass


GITHUB_RE = re.compile(
    r"^(?:https?://)?(?:www\.)?github\.com/([^/\s]+)/([^/\s#?]+?)(?:\.git)?"
    r"(?:/tree/([^/\s#?]+))?/?$"
)
BARE_REPO_RE = re.compile(r"^[\w.-]+/[\w.-]+$")


def parse_target(target: str):
    if os.path.isdir(target):
        return {"kind": "local", "path": os.path.abspath(target)}

    m = GITHUB_RE.match(target.strip())
    if m:
        owner, repo, ref = m.group(1), m.group(2), m.group(3)
        return {"kind": "github", "owner": owner, "repo": repo, "ref": ref}

    if BARE_REPO_RE.match(target.strip()) and not os.path.exists(target):
        owner, repo = target.strip().split("/", 1)
        return {"kind": "github", "owner": owner, "repo": repo, "ref": None}

    raise TargetError(
        f"'{target}' is not an existing local directory and does not look like "
        "a GitHub URL or 'owner/repo'."
    )


def _api_request(url, token=None):
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "cerberus-examine/2.0")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8")), dict(resp.headers)
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", "ignore")
        except Exception:
            pass
        raise TargetError(f"GitHub API error {e.code} for {url}: {body[:300]}") from e
    except urllib.error.URLError as e:
        raise TargetError(f"Network error contacting {url}: {e}") from e


def acquire_github(owner, repo, ref, token, notes):
    repo_meta_raw, headers = _api_request(
        f"https://api.github.com/repos/{owner}/{repo}", token
    )
    remaining = headers.get("X-RateLimit-Remaining")
    if remaining is not None:
        notes.append(f"GitHub API rate-limit remaining: {remaining}.")

    default_branch = repo_meta_raw.get("default_branch", "main")
    use_ref = ref or default_branch

    commit_raw, _ = _api_request(
        f"https://api.github.com/repos/{owner}/{repo}/commits/{urllib.request.quote(use_ref)}",
        token,
    )
    sha = commit_raw.get("sha")
    if not sha:
        raise TargetError(f"Could not resolve a commit SHA for ref '{use_ref}'.")

    tarball_url = f"https://codeload.github.com/{owner}/{repo}/tar.gz/{sha}"
    req = urllib.request.Request(tarball_url)
    req.add_header("User-Agent", "cerberus-examine/2.0")
    if token:
        req.add_header("Authorization", f"Bearer {token}")

    tmp_root = tempfile.mkdtemp(prefix="cerberus-cli-")
    tar_path = os.path.join(tmp_root, "repo.tar.gz")
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            with open(tar_path, "wb") as f:
                shutil.copyfileobj(resp, f)
    except urllib.error.HTTPError as e:
        shutil.rmtree(tmp_root, ignore_errors=True)
        raise TargetError(f"Failed to download tarball ({e.code}) from {tarball_url}") from e
    except urllib.error.URLError as e:
        shutil.rmtree(tmp_root, ignore_errors=True)
        raise TargetError(f"Network error downloading tarball: {e}") from e

    extract_dir = os.path.join(tmp_root, "extracted")
    os.makedirs(extract_dir, exist_ok=True)
    with tarfile.open(tar_path, "r:gz") as tf:
        def is_within(base, target_path):
            base = os.path.abspath(base)
            target_path = os.path.abspath(target_path)
            return os.path.commonpath([base, target_path]) == base

        members = tf.getmembers()
        for m in members:
            dest = os.path.join(extract_dir, m.name)
            if not is_within(extract_dir, dest):
                continue
        tf.extractall(extract_dir, members=members)
    os.remove(tar_path)

    entries = [e for e in os.listdir(extract_dir) if not e.startswith(".")]
    if len(entries) == 1 and os.path.isdir(os.path.join(extract_dir, entries[0])):
        root_dir = os.path.join(extract_dir, entries[0])
    else:
        root_dir = extract_dir

    repo_meta = {
        "description": repo_meta_raw.get("description"),
        "stars": repo_meta_raw.get("stargazers_count", 0),
        "license": (repo_meta_raw.get("license") or {}).get("spdx_id"),
        "archived": bool(repo_meta_raw.get("archived", False)),
        "pushedAt": repo_meta_raw.get("pushed_at"),
        "primaryLanguage": repo_meta_raw.get("language"),
    }
    return root_dir, sha, use_ref, repo_meta, tmp_root


# --------------------------------------------------------------------------
# Filesystem scanning
# --------------------------------------------------------------------------

def walk_tree(root_dir):
    out = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        dirnames[:] = [d for d in dirnames if d != ".git"]
        for fn in filenames:
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, root_dir).replace(os.sep, "/")
            out.append(rel)
    return sorted(out)


def is_binary_bytes(chunk: bytes) -> bool:
    if b"\x00" in chunk:
        return True
    return False


class FileCache:
    """Reads and caches text content with size/binary gating."""

    def __init__(self, root_dir):
        self.root_dir = root_dir
        self._text = {}
        self._skip_reason = {}

    def abspath(self, rel):
        return os.path.join(self.root_dir, rel)

    def size(self, rel):
        try:
            return os.path.getsize(self.abspath(rel))
        except OSError:
            return None

    def get_text(self, rel):
        """Returns text content, or None if binary/too large/unreadable.
        Populates self._skip_reason[rel] with the reason when None."""
        if rel in self._text:
            return self._text[rel]
        path = self.abspath(rel)
        try:
            size = os.path.getsize(path)
        except OSError as e:
            self._skip_reason[rel] = f"stat error: {e}"
            self._text[rel] = None
            return None
        if size > MAX_FILE_BYTES:
            self._skip_reason[rel] = "too_large"
            self._text[rel] = None
            return None
        try:
            with open(path, "rb") as f:
                raw = f.read()
        except OSError as e:
            self._skip_reason[rel] = f"read error: {e}"
            self._text[rel] = None
            return None
        if is_binary_bytes(raw[:8192]):
            self._skip_reason[rel] = "binary"
            self._text[rel] = None
            return None
        text = raw.decode("utf-8", errors="replace")
        self._text[rel] = text
        return text

    def skip_reason(self, rel):
        return self._skip_reason.get(rel)


# --------------------------------------------------------------------------
# Detector evaluation
# --------------------------------------------------------------------------

def compile_flags(flag_str):
    flags = 0
    flag_str = flag_str or ""
    if "i" in flag_str:
        flags |= re.IGNORECASE
    if "m" in flag_str:
        flags |= re.MULTILINE
    if "s" in flag_str:
        flags |= re.DOTALL
    return flags


def line_col(text, offset):
    line = text.count("\n", 0, offset) + 1
    last_nl = text.rfind("\n", 0, offset)
    col = offset - last_nl
    return line, col


CERBERUSIGNORE = ".cerberusignore"


def parse_cerberusignore(text):
    """Parse a .cerberusignore into glob patterns.

    Same spirit as .gitignore: one glob per line, `#` comments, blank lines ignored.
    A bare directory name is expanded to cover everything beneath it, and a pattern
    with no slash is anchored anywhere in the tree, so `secrets.json` works the way
    people expect without writing `**/secrets.json`.

    This exists because every scanner needs a suppression mechanism. Without one the
    only way to silence an unavoidable false positive is to weaken the rule for
    everybody, and rules that cannot be silenced get the whole tool switched off.
    """
    patterns = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        line = line.rstrip("/")
        if "/" not in line and not line.startswith("**"):
            patterns.append("**/" + line)
            patterns.append("**/" + line + "/**")
        else:
            patterns.append(line)
            patterns.append(line.rstrip("*").rstrip("/") + "/**")
    return patterns


def read_cerberusignore(cache):
    text = cache.get_text(CERBERUSIGNORE)
    return parse_cerberusignore(text) if text else []


# Keep in lockstep with COMMENT_LINE_RE in assets/scanner.js.
COMMENT_LINE_RE = re.compile(r"^\s*(#|//|/\*|\*(?!/)|\*/|<!--|--(?!\s*\[)|;|%)")


def line_text(text, offset):
    start = text.rfind("\n", 0, offset) + 1
    end = text.find("\n", offset)
    if end == -1:
        end = len(text)
    return text[start:end]


def truncate(s, n):
    s = s.strip()
    if len(s) > n:
        return s[: n - 1] + "…"
    return s


class Evaluator:
    def __init__(self, catalog, all_files, cache: FileCache, url_for_fn):
        self.catalog = catalog
        self.all_files = all_files
        self.cache = cache
        self.url_for = url_for_fn
        self.global_exclude = list(catalog["global_exclude"]) + read_cerberusignore(cache)
        self.test_paths = catalog["test_paths"]
        self.source_globs = catalog["source_globs"]
        self.placeholder_rx = re.compile(catalog["placeholder_pattern"], re.IGNORECASE)
        self.default_hit_cap = catalog["scoring"]["default_hit_cap"]
        self.per_hit = catalog["scoring"]["per_hit"]

        self.non_globally_excluded = [
            f for f in all_files if not any_glob_match(f, self.global_exclude)
        ]
        self.scannable = []
        self.skip_counts = {"too_large": 0, "binary": 0, "error": 0}
        for f in self.non_globally_excluded:
            text = self.cache.get_text(f)
            if text is None:
                reason = self.cache.skip_reason(f) or "error"
                if reason not in ("too_large", "binary"):
                    reason = "error"
                self.skip_counts[reason] += 1
            else:
                self.scannable.append(f)

        self.eligible_default = [
            f for f in self.scannable if any_glob_match(f, self.source_globs)
        ]

    def is_test_path(self, rel):
        return any_glob_match(rel, self.test_paths)

    def candidate_files(self, detector):
        if "include" in detector:
            pool = [f for f in self.scannable if any_glob_match(f, detector["include"])]
        else:
            pool = list(self.eligible_default)
        if "exclude" in detector:
            pool = [f for f in pool if not any_glob_match(f, detector["exclude"])]
        if detector.get("exclude_tests"):
            pool = [f for f in pool if not self.is_test_path(f)]
        return pool

    def applies(self, check):
        applies_if = check.get("applies_if")
        if not applies_if:
            return True, None
        any_path = applies_if.get("any_path", [])
        if any_path and any_glob_match_any(self.all_files, any_path):
            return True, None
        patterns_str = ", ".join(any_path)
        return False, f"No matching files found for this check (looked for: {patterns_str})."

    def eval_content(self, check):
        det = check["detector"]
        pattern = re.compile(det["pattern"], compile_flags(det.get("flags", "")))
        not_match = re.compile(det["not_match"], re.I) if det.get("not_match") else None
        not_match_window = det.get("not_match_window", 0)
        scan_comments = det.get("scan_comments", False)
        skip_placeholder = det.get("skip_if_placeholder", False)
        files = self.candidate_files(det)
        findings = []
        for rel in files:
            text = self.cache.get_text(rel)
            if text is None:
                continue
            for m in pattern.finditer(text):
                ln, col = line_col(text, m.start())
                lt = line_text(text, m.start())

                # Must mirror assets/scanner.js exactly — the CLI and the web app are
                # required to produce identical findings for the same commit.
                if not scan_comments and COMMENT_LINE_RE.match(lt):
                    continue
                if not_match:
                    if not_match_window > 0:
                        lines = text.splitlines()
                        window = "\n".join(lines[ln - 1: ln - 1 + not_match_window + 1])
                    else:
                        window = lt
                    if not_match.search(window):
                        continue
                if skip_placeholder and self.placeholder_rx.search(m.group(0)):
                    continue
                findings.append({
                    "path": rel,
                    "line": ln,
                    "column": col,
                    "snippet": truncate(lt, 300),
                    "match": truncate(m.group(0), 160),
                    "url": self.url_for(rel, ln),
                })
        return self._finalize_content(check, findings)

    def eval_content_required(self, check):
        det = check["detector"]
        pattern = re.compile(det["pattern"], compile_flags(det.get("flags", "")))
        paths = det["paths"]
        if paths == ["**/*"]:
            files = self.scannable
        else:
            files = [f for f in self.all_files if any_glob_match(f, paths)]
        found = False
        for rel in files:
            text = self.cache.get_text(rel)
            if text is None:
                continue
            if pattern.search(text):
                found = True
                break
        if found:
            return "pass", [], None
        reason = det.get("fail_message") or (check["name"] + ".")
        return "fail", [], reason

    def eval_path_required(self, check):
        det = check["detector"]
        matches = files_matching(self.all_files, det["paths"])
        if matches:
            return "pass", [], None
        return "fail", [], check["name"] + "."

    def eval_path_forbidden(self, check):
        det = check["detector"]
        matches = files_matching(self.all_files, det["paths"])
        exclude = det.get("exclude", [])
        if exclude:
            matches = [f for f in matches if not any_glob_match(f, exclude)]
        if det.get("exclude_tests"):
            matches = [f for f in matches if not self.is_test_path(f)]
        if not matches:
            return "pass", [], None
        hit_cap = det.get("hit_cap", self.default_hit_cap)
        findings = []
        for rel in matches[: max(hit_cap, 25)]:
            findings.append({
                "path": rel,
                "line": 1,
                "column": 1,
                "snippet": os.path.basename(rel),
                "match": rel,
                "url": self.url_for(rel, 1),
            })
        return "fail", findings, None

    def eval_meta_has_license(self, check, repo_meta):
        for f in self.all_files:
            if "/" not in f and f.lower() in LICENSE_FILENAMES:
                return "pass", [], None
        if repo_meta and repo_meta.get("license"):
            return "pass", [], None
        return "fail", [], check["name"] + "."

    def _finalize_content(self, check, findings):
        if not findings:
            return "pass", [], None
        return "fail", findings, None

    def evaluate(self, check, repo_meta):
        det = check["detector"]
        kind = det["kind"]
        applicable, reason = self.applies(check)
        if not applicable:
            return "not_applicable", [], reason
        try:
            if kind == "content":
                return self.eval_content(check)
            elif kind == "content_required":
                return self.eval_content_required(check)
            elif kind == "path_required":
                return self.eval_path_required(check)
            elif kind == "path_forbidden":
                return self.eval_path_forbidden(check)
            elif kind == "meta" and det.get("handler") == "has_license":
                return self.eval_meta_has_license(check, repo_meta)
            else:
                return "skipped", [], f"Unknown detector kind '{kind}'."
        except re.error as e:
            return "skipped", [], f"Regex error: {e}"
        except Exception as e:
            return "skipped", [], f"Evaluation error: {e}"


def any_glob_match_any(files, patterns):
    for f in files:
        if any_glob_match(f, patterns):
            return True
    return False


# --------------------------------------------------------------------------
# Report construction
# --------------------------------------------------------------------------

def load_catalog():
    with open(CHECKS_JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def grade_for(score):
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    return "F"


DISPLAY_FINDINGS_CAP = 25


def build_report(catalog, target_info, root_dir, repo_meta, only_agents, notes, engine_source="cli"):
    all_files = walk_tree(root_dir)
    cache = FileCache(root_dir)

    def url_for(rel, line):
        if target_info["kind"] == "github":
            return (
                f"https://github.com/{target_info['owner']}/{target_info['repo']}"
                f"/blob/{target_info['sha']}/{rel}#L{line}"
            )
        else:
            abspath = os.path.join(root_dir, rel)
            return f"file://{abspath}#L{line}"

    evaluator = Evaluator(catalog, all_files, cache, url_for)

    agents_meta = {a["id"]: a for a in catalog["agents"]}
    checks_by_agent = {a["id"]: [] for a in catalog["agents"]}
    for c in catalog["checks"]:
        checks_by_agent[c["agent"]].append(c)

    per_hit = catalog["scoring"]["per_hit"]
    default_hit_cap = catalog["scoring"]["default_hit_cap"]

    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0,
              "pass": 0, "fail": 0, "not_applicable": 0, "skipped": 0, "total": 0}

    agents_out = []
    total_score = 0.0

    for agent in catalog["agents"]:
        agent_id = agent["id"]
        include_agent = (only_agents is None) or (agent_id in only_agents)
        weight = agent["weight"]
        agent_score = float(weight)
        checks_out = []
        for check in checks_by_agent[agent_id]:
            counts["total"] += 1
            if not include_agent:
                # Still must appear in schema; treat as skipped-out-of-scope.
                status, findings, reason = "skipped", [], "Excluded by --only filter."
            else:
                status, findings, reason = evaluator.evaluate(check, repo_meta)

            counts[status] += 1

            deduction = 0.0
            total_findings = len(findings)
            display_findings = findings[:DISPLAY_FINDINGS_CAP]
            findings_truncated = total_findings > len(display_findings)

            if status == "fail":
                severity = check["severity"]
                counts[severity] += 1
                hit_cap = check["detector"].get("hit_cap", default_hit_cap)
                # Score distinct occurrences, not repetitions — mirrors the dedupe in
                # assets/scanner.js. The same line copy-pasted across 13 CI jobs is one
                # problem to fix. All occurrences remain in `findings`.
                distinct = len({
                    " ".join((f.get("snippet") or "").split())
                    for f in findings
                } - {""}) or total_findings
                hits = max(distinct, 1)  # structural fails count as 1 hit
                counted_hits = min(hits, hit_cap)
                deduction = round(per_hit[severity] * counted_hits, 4)
                agent_score -= deduction

            check_out = {
                "id": check["id"],
                "name": check["name"],
                "severity": check["severity"],
                "cwe": check.get("cwe", "N/A"),
                "summary": check.get("summary", ""),
                "risk": check.get("risk", ""),
                "remediation": check.get("remediation", ""),
                "status": status,
                "deduction": round(deduction, 2),
                "findings": display_findings,
                "findingsTruncated": findings_truncated,
                "totalFindings": total_findings,
            }
            if "fix" in check:
                check_out["fix"] = check["fix"]
            if status != "pass" and (status != "fail" or total_findings == 0):
                if reason:
                    check_out["reason"] = reason
            checks_out.append(check_out)

        agent_score = max(0.0, round(agent_score, 2))
        total_score += agent_score
        agents_out.append({
            "id": agent_id,
            "name": agent["name"],
            "domain": agent["domain"],
            "weight": weight,
            "score": round(agent_score, 1),
            "checks": checks_out,
        })

    total_score = max(0.0, min(100.0, round(total_score, 1)))
    grade = grade_for(total_score)

    if evaluator.skip_counts["too_large"]:
        notes.append(
            f"{evaluator.skip_counts['too_large']} file(s) exceeded the 512 KB limit and were not scanned."
        )
    if evaluator.skip_counts["binary"]:
        notes.append(f"{evaluator.skip_counts['binary']} binary file(s) were skipped.")

    lang = repo_meta.get("primaryLanguage") if repo_meta else None
    if not lang:
        ext_counts = {}
        for f in evaluator.eligible_default:
            ext = os.path.splitext(f)[1].lower()
            if ext in EXT_LANGUAGE:
                name = EXT_LANGUAGE[ext]
                ext_counts[name] = ext_counts.get(name, 0) + 1
        if ext_counts:
            lang = max(ext_counts.items(), key=lambda kv: kv[1])[0]

    report = {
        "schema": SCHEMA,
        "target": target_info["display_block"],
        "scannedAt": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "engine": {"version": ENGINE_VERSION, "checksVersion": catalog.get("version", ENGINE_VERSION),
                   "source": engine_source},
        "score": total_score,
        "grade": grade,
        "counts": counts,
        "repo": {
            "description": (repo_meta or {}).get("description"),
            "stars": (repo_meta or {}).get("stars", 0),
            "license": (repo_meta or {}).get("license"),
            "archived": (repo_meta or {}).get("archived", False),
            "pushedAt": (repo_meta or {}).get("pushedAt"),
            "primaryLanguage": lang,
        },
        "coverage": {
            "filesInTree": len(all_files),
            "filesEligible": len(evaluator.eligible_default),
            "filesScanned": len(evaluator.eligible_default),
            "filesSkipped": evaluator.skip_counts["too_large"] + evaluator.skip_counts["binary"] + evaluator.skip_counts["error"],
            "bytesScanned": sum((cache.size(f) or 0) for f in evaluator.eligible_default),
            "truncated": False,
            "skipReasons": {k: v for k, v in evaluator.skip_counts.items() if v},
        },
        "agents": agents_out,
        "notes": notes,
    }
    return report


# --------------------------------------------------------------------------
# Output renderers
# --------------------------------------------------------------------------

def severity_at_least(sev, minimum):
    return SEVERITY_ORDER.get(sev, 0) >= SEVERITY_ORDER.get(minimum, 0)


def render_sarif(report):
    rules = {}
    results = []
    level_for = {"critical": "error", "high": "error", "medium": "warning", "low": "note"}
    for agent in report["agents"]:
        for check in agent["checks"]:
            rules[check["id"]] = {
                "id": check["id"],
                "name": check["name"],
                "shortDescription": {"text": check["name"]},
                "fullDescription": {"text": check.get("summary", "")},
                "help": {"text": check.get("remediation", "")},
                "properties": {"cwe": check.get("cwe", "N/A"), "severity": check["severity"]},
            }
            if check["status"] != "fail":
                continue
            level = level_for.get(check["severity"], "warning")
            findings = check["findings"] or [{"path": ".", "line": 1}]
            for f in findings:
                results.append({
                    "ruleId": check["id"],
                    "level": level,
                    "message": {"text": check.get("reason") or check.get("summary", check["name"])},
                    "locations": [{
                        "physicalLocation": {
                            "artifactLocation": {"uri": f.get("path", ".")},
                            "region": {"startLine": max(1, f.get("line", 1))},
                        }
                    }],
                })
    sarif = {
        "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
        "version": "2.1.0",
        "runs": [{
            "tool": {
                "driver": {
                    "name": "Cerberus",
                    "version": report["engine"]["version"],
                    "informationUri": "https://github.com/",
                    "rules": list(rules.values()),
                }
            },
            "results": results,
        }],
    }
    return sarif


def html_escape(s):
    return html.escape(str(s), quote=True)


def render_html(report):
    import base64
    logo_base64 = ""
    try:
        logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logo.png")
        if os.path.exists(logo_path):
            with open(logo_path, "rb") as f:
                logo_base64 = base64.b64encode(f.read()).decode("utf-8")
    except Exception:
        pass

    logo_img = ""
    if logo_base64:
        logo_img = f'<img class="report-logo" src="data:image/png;base64,{logo_base64}" alt="Cerberus Labs Logo">'

    target = report["target"]
    display = html_escape(target.get("display", ""))
    
    def get_status_svg(status):
        if status == "pass":
            return '<svg class="status-icon icon-pass" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>'
        elif status == "fail":
            return '<svg class="status-icon icon-fail" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>'
        elif status == "not_applicable":
            return '<svg class="status-icon icon-na" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"></line></svg>'
        else: # skipped
            return '<svg class="status-icon icon-skipped" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="3"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="12" x2="12" y2="16"></line><line x1="12" y1="8" x2="12" y2="8"></line></svg>'

    agents_rows = []
    details = []
    for agent in report["agents"]:
        state_counts = {"pass": 0, "fail": 0, "not_applicable": 0, "skipped": 0}
        for c in agent["checks"]:
            state_counts[c["status"]] += 1
        agents_rows.append(
            f"<tr><td class='agent-name'>{html_escape(agent['name'])}"
            f"<span class='domain'>{html_escape(agent['domain'])}</span></td>"
            f"<td class='score-cell'>{agent['score']} / {agent['weight']}</td>"
            f"<td>{state_counts['pass']} pass / {state_counts['fail']} fail / "
            f"{state_counts['not_applicable']} n/a / {state_counts['skipped']} skip</td></tr>"
        )
        check_blocks = []
        for c in agent["checks"]:
            findings_html = ""
            if c["findings"]:
                items = []
                for fnd in c["findings"]:
                    items.append(
                        "<div class='finding'>"
                        f"<div class='finding-loc'><a href='{html_escape(fnd['url'])}'>"
                        f"{html_escape(fnd['path'])}:{fnd['line']}</a></div>"
                        f"<pre class='snippet'>{html_escape(fnd['snippet'])}</pre>"
                        "</div>"
                    )
                findings_html = "".join(items)
                if c["findingsTruncated"]:
                    findings_html += (
                        f"<div class='truncated'>Showing {len(c['findings'])} of "
                        f"{c['totalFindings']} findings.</div>"
                    )
            reason_html = (
                f"<div class='reason'>{html_escape(c.get('reason', ''))}</div>"
                if c.get("reason") else ""
            )
            
            status_svg = get_status_svg(c['status'])
            check_blocks.append(
                f"<div class='check status-{c['status']}'>"
                f"<div class='check-head'>"
                f"<span class='badge status-{c['status']}' title='{c['status']}'>{status_svg}</span>"
                f"<span class='badge sev-{c['severity']}'>{c['severity']}</span>"
                f"<span class='check-name'>{html_escape(c['name'])}</span>"
                f"<span class='check-id'>{html_escape(c['id'])}</span>"
                f"<span class='deduction'>-{c['deduction']}</span></div>"
                f"<div class='summary'>{html_escape(c.get('summary',''))}</div>"
                f"{reason_html}{findings_html}</div>"
            )
        details.append(
            f"<section class='agent-section'><h2>{html_escape(agent['name'])} "
            f"<small>{html_escape(agent['domain'])}</small></h2>{''.join(check_blocks)}</section>"
        )

    grade_class = f"grade-{str(report['grade']).lower()}"

    doc = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Cerberus Report - {display}</title>
<style>
:root {{
    --black: #0A0A0C;
    --white: #FFFFFF;
    --gray-100: #FAFAFC;
    --gray-200: #E2E2E8;
    --gray-300: #888894;
    --gray-400: #555560;
    --gray-500: #2C2C35;
    --accent-green: #39FF14;
    --accent-yellow: #DFFF00;
    --font-display: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    --font-body: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    --font-mono: SFMono-Regular, Consolas, Menlo, monospace;
}}
@media (prefers-color-scheme: dark) {{
    :root {{
        --white: #0A0A0C;
        --black: #FFFFFF;
        --gray-100: #141416;
        --gray-200: #2C2C35;
        --gray-300: #888894;
        --gray-400: #AAAAAB;
        --gray-500: #FAFAFC;
    }}
}}
body {{
    font-family: var(--font-body);
    max-width: 960px;
    margin: 2rem auto;
    padding: 0 1.5rem;
    background: var(--white);
    color: var(--black);
    line-height: 1.5;
}}
h1, h2, h3, h4, th, .report-title {{
    font-family: var(--font-display);
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: -0.02em;
}}
header {{
    display: flex;
    align-items: center;
    gap: 1rem;
    border-bottom: 3px solid var(--black);
    padding-bottom: 1.5rem;
    margin-bottom: 2rem;
    flex-wrap: wrap;
}}
.report-logo {{
    height: 48px;
    width: auto;
    display: block;
}}
.header-text {{
    flex: 1;
}}
.report-title {{
    font-size: 1.75rem;
    margin: 0;
    line-height: 1.1;
}}
.meta {{
    font-family: var(--font-mono);
    font-size: 0.75rem;
    color: var(--gray-300);
    margin-top: 0.5rem;
}}
.score-banner {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    border: 3px solid var(--black);
    box-shadow: 6px 6px 0px var(--black);
    padding: 1.5rem 2rem;
    margin-bottom: 2rem;
    background: var(--gray-100);
}}
.score-left {{
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
}}
.score-label {{
    font-family: var(--font-mono);
    font-size: 0.72rem;
    text-transform: uppercase;
    color: var(--gray-400);
    letter-spacing: 1px;
}}
.score-num {{
    font-family: var(--font-mono);
    font-size: 3.5rem;
    font-weight: 700;
    line-height: 1;
}}
.grade-box {{
    font-family: var(--font-display);
    font-size: 3rem;
    font-weight: 700;
    width: 72px;
    height: 72px;
    display: flex;
    align-items: center;
    justify-content: center;
    border: 3px solid var(--black);
    box-shadow: 4px 4px 0px var(--black);
}}
.grade-a {{ background: var(--accent-green); color: #0A0A0C; }}
.grade-b {{ background: var(--accent-yellow); color: #0A0A0C; }}
.grade-c {{ background: var(--accent-yellow); color: #0A0A0C; }}
.grade-d {{ background: var(--gray-300); color: var(--white); }}
.grade-f {{ background: var(--black); color: var(--white); }}

.progress-container {{
    width: 100%;
    height: 16px;
    background: var(--gray-200);
    border: 3px solid var(--black);
    box-shadow: 4px 4px 0px var(--black);
    margin: 1.5rem 0 2.5rem;
}}
.progress-bar {{
    height: 100%;
    background: linear-gradient(90deg, #DFFF00, #39FF14, #DFFF00);
}}
table {{
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 2.5rem;
    border: 3px solid var(--black);
    box-shadow: 6px 6px 0px var(--black);
}}
th, td {{
    padding: 1rem;
    text-align: left;
    border: 1px solid var(--gray-200);
}}
th {{
    background: var(--gray-100);
    border-bottom: 3px solid var(--black);
    font-size: 0.85rem;
}}
.agent-name {{
    font-weight: 700;
    font-size: 0.95rem;
}}
.domain {{
    display: block;
    font-family: var(--font-mono);
    font-size: 0.7rem;
    color: var(--gray-300);
    margin-top: 0.25rem;
    text-transform: uppercase;
}}
.score-cell {{
    font-family: var(--font-mono);
    font-weight: 700;
}}
.agent-section {{
    margin-bottom: 3rem;
}}
.agent-section h2 {{
    font-size: 1.35rem;
    border-bottom: 3px solid var(--black);
    padding-bottom: 0.5rem;
    margin-bottom: 1.5rem;
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
}}
.agent-section h2 small {{
    font-family: var(--font-mono);
    font-size: 0.75rem;
    color: var(--gray-300);
    font-weight: normal;
    text-transform: uppercase;
}}
.check {{
    border: 1px solid var(--gray-200);
    padding: 1.25rem;
    margin-bottom: 1.25rem;
    background: var(--white);
}}
.check-head {{
    display: flex;
    gap: 0.75rem;
    align-items: center;
    flex-wrap: wrap;
    margin-bottom: 0.75rem;
}}
.badge {{
    font-family: var(--font-mono);
    font-size: 0.65rem;
    font-weight: 700;
    padding: 0.2rem 0.5rem;
    text-transform: uppercase;
    border: 1px solid transparent;
}}
.badge.critical {{ background: var(--black); color: var(--white); }}
.badge.high {{ background: var(--gray-400); color: var(--white); }}
.badge.medium {{ background: var(--gray-300); color: var(--white); }}
.badge.low {{ background: var(--gray-100); color: var(--black); border-color: var(--gray-200); }}

.badge.status-pass, .badge.status-fail, .badge.status-not_applicable, .badge.status-skipped {{
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 22px;
    height: 22px;
    padding: 0;
    border-radius: 0;
    flex-shrink: 0;
}}
.badge.status-pass {{ background: transparent; color: var(--black); border: 2px solid var(--black); }}
.badge.status-fail {{ background: var(--black); color: var(--white); border: 2px solid var(--black); }}
.badge.status-not_applicable {{ background: transparent; color: var(--gray-300); border: 2px solid var(--gray-200); }}
.badge.status-skipped {{ background: transparent; color: var(--gray-300); border: 2px dashed var(--gray-200); }}
.status-icon {{
    width: 14px;
    height: 14px;
    display: block;
}}
.check-id {{
    font-family: var(--font-mono);
    color: var(--gray-300);
    font-size: 0.75rem;
}}
.check-name {{
    font-weight: 700;
    font-size: 0.95rem;
    flex: 1;
}}
.deduction {{
    font-family: var(--font-mono);
    color: var(--black);
    font-weight: 700;
    font-size: 0.85rem;
}}
.summary {{
    font-size: 0.88rem;
    color: var(--gray-400);
    margin: 0.5rem 0;
}}
.reason {{
    font-family: var(--font-mono);
    font-size: 0.72rem;
    font-style: italic;
    color: var(--gray-300);
    background: var(--gray-100);
    padding: 0.5rem 1rem;
    border-left: 3px solid var(--gray-300);
    margin: 0.5rem 0;
}}
.finding {{
    margin-top: 0.75rem;
    border: 1px solid var(--gray-200);
    background: var(--gray-100);
}}
.finding-loc {{
    padding: 0.5rem 0.75rem;
    border-bottom: 1px solid var(--gray-200);
    font-family: var(--font-mono);
    font-size: 0.78rem;
}}
.finding-loc a {{
    color: var(--black);
    text-decoration: none;
}}
.finding-loc a:hover {{
    text-decoration: underline;
}}
.snippet {{
    margin: 0;
    padding: 0.75rem;
    overflow-x: auto;
    font-family: var(--font-mono);
    font-size: 0.78rem;
    background: var(--white);
    color: var(--black);
}}
.truncated {{
    font-family: var(--font-mono);
    color: var(--gray-300);
    font-size: 0.72rem;
    margin-top: 0.5rem;
    text-transform: uppercase;
}}
</style></head><body>
<header>
    {logo_img}
    <div class="header-text">
        <h1 class="report-title">Cerberus Security Report</h1>
        <div class="meta">{display} &middot; scanned {html_escape(report['scannedAt'])} &middot; engine {html_escape(report['engine']['version'])} ({html_escape(report['engine']['source'])})</div>
    </div>
</header>
<div class="score-banner">
    <div class="score-left">
        <div class="score-label">Examination Score</div>
        <div class="score-num">{report['score']}/100</div>
    </div>
    <div class="grade-box {grade_class}">{report['grade']}</div>
</div>
<div class="progress-container">
    <div class="progress-bar" style="width: {report['score']}%"></div>
</div>
<table><thead><tr><th>Agent</th><th>Score</th><th>Checks</th></tr></thead>
<tbody>{''.join(agents_rows)}</tbody></table>
{''.join(details)}
</body></html>
"""
    return doc


def color(s, code, enabled):
    if not enabled:
        return s
    return f"\033[{code}m{s}\033[0m"


def print_terminal(report, quiet, use_color, severity_min, only_agents):
    def c(s, code):
        return color(s, code, use_color)

    if quiet:
        print(f"{report['score']}/100 ({report['grade']})")
        return

    target = report["target"]
    print(c("=" * 60, "90"))
    print(f"CERBERUS — {target.get('display', '')}")
    print(c("=" * 60, "90"))
    score = report["score"]
    grade = report["grade"]
    score_code = "92" if score >= 80 else "93" if score >= 60 else "91"
    print(f"Score: {c(f'{score}/100', score_code)}   Grade: {c(grade, score_code)}")
    counts = report["counts"]
    print(
        f"Checks: {counts['pass']} pass, {counts['fail']} fail, "
        f"{counts['not_applicable']} n/a, {counts['skipped']} skipped "
        f"(of {counts['total']})"
    )
    print(
        f"By severity (failed): critical={counts['critical']} high={counts['high']} "
        f"medium={counts['medium']} low={counts['low']}"
    )
    print()
    print(c("Per-agent scores:", "1"))
    for agent in report["agents"]:
        if only_agents and agent["id"] not in only_agents:
            continue
        print(f"  {agent['name']:<12} {agent['score']:>5.1f} / {agent['weight']:<4} {agent['domain']}")
    print()
    print(c("Failed checks:", "1"))
    any_failed = False
    for agent in report["agents"]:
        if only_agents and agent["id"] not in only_agents:
            continue
        for check in agent["checks"]:
            if check["status"] != "fail":
                continue
            if not severity_at_least(check["severity"], severity_min):
                continue
            any_failed = True
            sev_code = {"critical": "91", "high": "91", "medium": "93", "low": "94"}.get(
                check["severity"], "0"
            )
            print(
                f"  [{c(check['severity'].upper(), sev_code)}] {check['id']} "
                f"{check['name']} (-{check['deduction']})"
            )
            if check.get("reason"):
                print(f"      {check['reason']}")
            for fnd in check["findings"][:5]:
                print(f"      {fnd['path']}:{fnd['line']}  {fnd['snippet']}")
            if check["totalFindings"] > 5:
                print(f"      ... and {check['totalFindings'] - 5} more")
    if not any_failed:
        print("  (none at or above severity threshold)")
    if report["notes"]:
        print()
        print(c("Notes:", "1"))
        for n in report["notes"]:
            print(f"  - {n}")


# --------------------------------------------------------------------------
# Dev server (optional, --serve)
# --------------------------------------------------------------------------

class _Handler(SimpleHTTPRequestHandler):
    """Dev-only static handler bound to loopback.

    Deliberately does NOT send Access-Control-Allow-Origin. The app is served from the
    same origin as its assets, so it needs no CORS grant, and a wildcard here is exactly
    the C-01 finding this tool reports in other people's code.
    """

    def end_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        super().end_headers()


def run_dev_server(catalog, port=8080):
    print("[cerberus] --serve is a DEV-ONLY server, binding to 127.0.0.1 only.")
    server = HTTPServer(("127.0.0.1", port), _Handler)
    print(f"[cerberus] Serving static files at http://127.0.0.1:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[cerberus] Server stopped.")


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Cerberus security scanner (CLI)")
    parser.add_argument("target", nargs="?", default=".",
                         help="Local directory, GitHub URL, or owner/repo")
    parser.add_argument("--json", help="Write the full Report JSON to this path")
    parser.add_argument("--html", help="Write a standalone HTML report to this path")
    parser.add_argument("--sarif", help="Write a SARIF 2.1.0 file to this path")
    parser.add_argument("--fail-under", type=float, default=None,
                         help="Exit non-zero if the score is below N (for CI)")
    parser.add_argument("--only", help="Comma-separated list of agent ids to include")
    parser.add_argument("--severity", default="low",
                         choices=["critical", "high", "medium", "low"],
                         help="Minimum severity to show in the terminal summary")
    parser.add_argument("--quiet", action="store_true", help="Only print the final score line")
    parser.add_argument("--no-color", action="store_true", help="Disable ANSI colour output")
    parser.add_argument("--serve", action="store_true",
                         help="Start a dev-only static file server on 127.0.0.1 (drops scanning)")
    parser.add_argument("--port", type=int, default=8080, help="Port for --serve")
    args = parser.parse_args()

    catalog = load_catalog()

    if args.serve:
        run_dev_server(catalog, args.port)
        sys.exit(0)

    only_agents = None
    if args.only:
        only_agents = {a.strip() for a in args.only.split(",") if a.strip()}
        valid_ids = {a["id"] for a in catalog["agents"]}
        unknown = only_agents - valid_ids
        if unknown:
            print(f"error: unknown agent id(s) in --only: {', '.join(sorted(unknown))}",
                  file=sys.stderr)
            sys.exit(2)

    notes = []
    tmp_root = None
    token = os.environ.get("GITHUB_TOKEN")

    try:
        parsed = parse_target(args.target)
        if parsed["kind"] == "local":
            root_dir = parsed["path"]
            display = os.path.basename(root_dir.rstrip("/")) or root_dir
            git_ref = None
            try:
                git_ref = subprocess.check_output(
                    ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                    cwd=root_dir, stderr=subprocess.DEVNULL
                ).decode().strip()
            except Exception:
                pass
            target_info = {
                "kind": "local",
                "sha": None,
                "display_block": {
                    "kind": "local",
                    "display": display,
                    "path": root_dir,
                    "ref": git_ref,
                },
            }
            repo_meta = {}
        else:
            owner, repo, ref = parsed["owner"], parsed["repo"], parsed.get("ref")
            root_dir, sha, use_ref, repo_meta, tmp_root = acquire_github(
                owner, repo, ref, token, notes
            )
            target_info = {
                "kind": "github",
                "owner": owner,
                "repo": repo,
                "sha": sha,
                "display_block": {
                    "kind": "github",
                    "display": f"{owner}/{repo}",
                    "url": f"https://github.com/{owner}/{repo}",
                    "owner": owner,
                    "repo": repo,
                    "ref": use_ref,
                    "sha": sha,
                },
            }

        report = build_report(catalog, target_info, root_dir, repo_meta, only_agents, notes)
    except TargetError as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        if tmp_root:
            shutil.rmtree(tmp_root, ignore_errors=True)

    use_color = sys.stdout.isatty() and not args.no_color
    print_terminal(report, args.quiet, use_color, args.severity, only_agents)

    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        if not args.quiet:
            print(f"\nJSON report written to {args.json}")

    if args.html:
        with open(args.html, "w", encoding="utf-8") as f:
            f.write(render_html(report))
        if not args.quiet:
            print(f"HTML report written to {args.html}")

    if args.sarif:
        sarif = render_sarif(report)
        with open(args.sarif, "w", encoding="utf-8") as f:
            json.dump(sarif, f, indent=2)
        if not args.quiet:
            print(f"SARIF report written to {args.sarif}")

    if args.fail_under is not None and report["score"] < args.fail_under:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
