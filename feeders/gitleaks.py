"""Gitleaks adapter."""

import json
import os

from .base import FeederAdapter
from .normalize import normalize_finding, redact


class GitleaksAdapter(FeederAdapter):
    name = "gitleaks"
    executable_names = ("gitleaks",)
    aliases = ("git-leaks",)
    output_filename = "gitleaks.json"
    accepted_exit_codes = frozenset({0, 1})
    # Gitleaks has no general path-exclusion CLI flag. Scan a filtered copy so
    # .cerberusignore and the scanner checkout exclusion are authoritative.
    use_filtered_tree = True

    def build_argv(self, executable, root, files, work_dir, target=None):
        return [executable, "detect", "--source", root, "--no-git", "--no-banner", "--no-color",
                "--report-format", "json", "--report-path",
                os.path.join(work_dir, self.output_filename)]

    def parse(self, stdout, stderr, output, root):
        raw = json.loads(output if output and output.strip() else "[]")
        if not isinstance(raw, list):
            raise ValueError("Gitleaks output must be a JSON array")
        findings = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            rule = item.get("RuleID") or item.get("ruleId") or "secret"
            findings.append(normalize_finding(
                self.name, rule, item.get("Severity") or "high",
                item.get("File") or item.get("Source"),
                item.get("StartLine"), item.get("StartColumn"),
                item.get("Description") or f"Potential secret detected by {rule}", root,
                remediation="Revoke exposed credentials and move secrets to an approved secret store.",
                confidence=0.95,
                agent="vault",
                evidence={k: v for k, v in item.items() if k not in {
                    "Secret", "Match", "Entropy", "Fingerprint"
                }},
            ))
        # Gitleaks' Secret and Match fields contain the credential itself. They
        # are omitted (not merely pattern-redacted) because arbitrary secrets
        # cannot be recognized reliably from their shape.
        safe_raw = []
        for item in raw:
            if isinstance(item, dict):
                safe_raw.append(redact({
                    key: value for key, value in item.items()
                    if key.lower() not in {"secret", "match"}
                }))
        return findings, safe_raw
