"""OpenSSF Scorecard adapter."""

import json
import os

from .base import FeederAdapter
from .normalize import normalize_finding, redact


class ScorecardAdapter(FeederAdapter):
    name = "scorecard"
    executable_names = ("scorecard", "scorecard.exe")
    aliases = ("openssf-scorecard", "openssf_scorecard")

    def applicable(self, root, files, target=None):
        github = bool(target and target.get("kind") == "github")
        return os.path.isdir(os.path.join(root, ".git")) or github, \
            "Scorecard requires Git metadata or GitHub repository context."

    def build_argv(self, executable, root, files, work_dir, target=None):
        if target and target.get("kind") == "github" and target.get("owner") and target.get("repo"):
            repository = "github.com/{}/{}".format(target["owner"], target["repo"])
            return [executable, "--repo", repository, "--format", "json"]
        return [executable, "--local", root, "--format", "json"]

    def parse(self, stdout, stderr, output, root):
        raw = json.loads(stdout)
        if not isinstance(raw, dict) or not isinstance(raw.get("checks", []), list):
            raise ValueError("Scorecard output must contain a checks array")
        findings = []
        for check in raw.get("checks", []):
            score = check.get("score", -1)
            try:
                numeric_score = float(score)
            except (TypeError, ValueError):
                numeric_score = -1
            if numeric_score >= 10 or numeric_score < 0:
                continue
            severity = "high" if numeric_score <= 3 else "medium" if numeric_score <= 7 else "low"
            rule = "scorecard-" + str(check.get("name") or "check").lower().replace(" ", "-")
            details = check.get("details") or []
            message = check.get("reason") or (details[0] if details else "Scorecard check did not pass")
            findings.append(normalize_finding(
                self.name, rule, severity, ".", 1, 1, message, root,
                remediation=f"Improve the OpenSSF Scorecard {check.get('name', 'check')} score.",
                confidence=0.9, agent="librarian",
                evidence={"score": score, "documentation": check.get("documentation")},
            ))
        return findings, redact(raw)
