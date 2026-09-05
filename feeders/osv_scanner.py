"""OSV-Scanner adapter."""

import json

from .base import FeederAdapter
from .normalize import normalize_finding, normalize_severity, redact


MANIFEST_NAMES = {
    "package.json", "package-lock.json", "npm-shrinkwrap.json", "yarn.lock",
    "pnpm-lock.yaml", "requirements.txt", "requirements-dev.txt", "poetry.lock",
    "pipfile", "pipfile.lock", "pyproject.toml", "go.mod", "go.sum", "cargo.toml",
    "cargo.lock", "gemfile", "gemfile.lock", "composer.json", "composer.lock",
    "pom.xml", "build.gradle", "build.gradle.kts", "packages.lock.json",
}


class OsvScannerAdapter(FeederAdapter):
    name = "osv-scanner"
    executable_names = ("osv-scanner", "osv-scanner.exe")
    aliases = ("osv", "osv_scanner")
    # OSV-Scanner documents 1 as "vulnerabilities or findings were found".
    accepted_exit_codes = frozenset({0, 1})
    use_filtered_tree = True

    @staticmethod
    def _is_manifest(path):
        lowered = path.lower()
        return (lowered.rsplit("/", 1)[-1] in MANIFEST_NAMES
                or lowered.endswith((".spdx.json", ".cdx.json", ".spdx", ".cdx.xml")))

    def applicable(self, root, files, target=None):
        applicable = any(self._is_manifest(path) for path in files)
        return applicable, "No supported dependency manifest, lockfile, or SBOM was found."

    def staged_files(self, files):
        return [path for path in files if self._is_manifest(path)]

    def build_argv(self, executable, root, files, work_dir, target=None):
        return [executable, "scan", "source", "--format=json", "--recursive", root]

    @staticmethod
    def _severity(vuln):
        db = vuln.get("database_specific") or {}
        if db.get("severity"):
            return normalize_severity(db["severity"])
        for entry in vuln.get("severity") or []:
            score = str(entry.get("score", ""))
            match = __import__("re").search(r"(?:^|/)(\d+(?:\.\d+)?)$", score)
            if match:
                return normalize_severity(float(match.group(1)))
        return "high"

    def parse(self, stdout, stderr, output, root):
        raw = json.loads(stdout)
        if not isinstance(raw, dict):
            raise ValueError("OSV-Scanner output must be a JSON object")
        findings = []
        for result in raw.get("results") or []:
            source = result.get("source") or {}
            path = source.get("path") or result.get("path") or "."
            packages = result.get("packages") or []
            for package in packages:
                package_info = package.get("package") or package
                package_name = package_info.get("name") or "dependency"
                version = package_info.get("version") or "unknown version"
                for vuln in package.get("vulnerabilities") or package.get("vulns") or []:
                    rule = vuln.get("id") or vuln.get("aliases", ["OSV"])[0]
                    summary = vuln.get("summary") or vuln.get("details") or "Known vulnerable dependency"
                    findings.append(normalize_finding(
                        self.name, rule, self._severity(vuln), path, 1, 1,
                        f"{package_name} {version}: {summary}", root,
                        remediation="Upgrade to a fixed dependency version listed by OSV.",
                        confidence=0.99, agent="librarian",
                        evidence={"package": package_name, "version": version,
                                  "aliases": vuln.get("aliases", [])},
                    ))
        return findings, redact(raw)
