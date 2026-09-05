"""actionlint GitHub Actions validation adapter."""

import json

from .base import FeederAdapter
from .normalize import normalize_finding, redact


class ActionlintAdapter(FeederAdapter):
    name = "actionlint"
    executable_names = ("actionlint", "actionlint.exe")
    accepted_exit_codes = frozenset({0, 1})

    def applicable(self, root, files, target=None):
        return bool(self.workflow_files(files)), "No GitHub Actions workflow files were found."

    def build_argv(self, executable, root, files, work_dir, target=None):
        json_format = "{{json .}}"
        paths = [root + "/" + path for path in self.workflow_files(files)]
        return [executable, "-format", json_format] + paths

    def parse(self, stdout, stderr, output, root):
        stripped = stdout.strip()
        if not stripped:
            raw = []
        else:
            try:
                decoded = json.loads(stripped)
                raw = decoded if isinstance(decoded, list) else [decoded]
            except json.JSONDecodeError:
                raw = [json.loads(line) for line in stripped.splitlines() if line.strip()]
        findings = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            rule = item.get("kind") or item.get("rule") or "actionlint"
            findings.append(normalize_finding(
                self.name, rule, item.get("severity") or "medium",
                item.get("filepath") or item.get("path"), item.get("line"), item.get("column"),
                item.get("message") or "GitHub Actions workflow validation error", root,
                remediation="Correct the workflow syntax or expression reported by actionlint.",
                confidence=0.98, agent="alignment",
            ))
        # Source snippets can contain credentials embedded in a workflow. Preserve
        # only diagnostic metadata; the normalized finding already retains location.
        safe_raw = [redact({
            key: value for key, value in item.items()
            if key.lower() not in {"snippet", "content", "source"}
        }) for item in raw if isinstance(item, dict)]
        return findings, safe_raw
