"""Zizmor GitHub Actions security adapter."""

import json

from .base import FeederAdapter
from .normalize import normalize_finding, redact


class ZizmorAdapter(FeederAdapter):
    name = "zizmor"
    executable_names = ("zizmor", "zizmor.exe")
    # 11-14 represent findings, ordered by the highest severity. Codes 1-3
    # remain actual audit/argument/input errors.
    accepted_exit_codes = frozenset({0, 11, 12, 13, 14})

    def applicable(self, root, files, target=None):
        return bool(self.workflow_files(files)), "No GitHub Actions workflow files were found."

    def build_argv(self, executable, root, files, work_dir, target=None):
        paths = [root + "/" + path for path in self.workflow_files(files)]
        # Pin the versioned JSON contract and prevent network-backed audits.
        return [executable, "--format=json-v1", "--offline"] + paths

    def parse(self, stdout, stderr, output, root):
        raw = json.loads(stdout)
        entries = raw if isinstance(raw, list) else raw.get("findings", raw.get("results", []))
        if not isinstance(entries, list):
            raise ValueError("Zizmor output does not contain a findings array")
        findings = []
        for item in entries:
            if not isinstance(item, dict):
                continue
            rule = item.get("ident") or item.get("rule_id") or item.get("ruleId") or "zizmor"
            message = item.get("desc") or item.get("message") or item.get("title") or rule
            determination = item.get("determinations") or {}
            if isinstance(determination, list):
                determination = determination[0] if determination else {}
            severity = (item.get("severity") or item.get("level")
                        or determination.get("severity") or "medium")
            confidence_name = str(determination.get("confidence") or "medium").lower()
            confidence = {"high": 0.95, "medium": 0.8, "low": 0.55}.get(
                confidence_name, 0.8)
            locations = item.get("locations") or [item.get("location") or item]
            for location in locations:
                if not isinstance(location, dict):
                    location = {}
                concrete = location.get("concrete") or {}
                location_range = concrete.get("location") or concrete
                point = location_range.get("start_point") or location.get("start") or location
                symbolic = location.get("symbolic") or {}
                local_key = (symbolic.get("key") or {}).get("Local") or {}
                row = point.get("row")
                line = (int(row) + 1) if isinstance(row, int) else point.get("line")
                column_value = point.get("column")
                column = (int(column_value) + 1) if isinstance(column_value, int) else 1
                findings.append(normalize_finding(
                    self.name, rule, severity,
                    local_key.get("verbatim_path") or location.get("path")
                    or item.get("path") or item.get("filename"),
                    line or location.get("line"), column, message, root,
                    remediation=item.get("remediation") or "Harden the affected workflow construct.",
                    confidence=confidence, agent="alignment",
                ))
        # Zizmor locations may embed workflow source. Keep only non-source audit
        # metadata in the preserved representation.
        safe_raw = [redact({
            "ident": item.get("ident") or item.get("rule_id") or item.get("ruleId"),
            "severity": item.get("severity") or item.get("level"),
            "desc": item.get("desc") or item.get("message") or item.get("title"),
            "determinations": item.get("determinations"),
        }) for item in entries if isinstance(item, dict)]
        return findings, safe_raw
