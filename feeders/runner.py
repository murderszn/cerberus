"""Safe subprocess runner for allowlisted feeder adapters."""

from __future__ import annotations

import os
import json
import shutil
import subprocess
import tempfile
import time

from .base import FEEDER_SCHEMA
from .normalize import deduplicate, redact_text
from .registry import resolve_feeders


DEFAULT_CAPTURE_LIMIT = 4 * 1024 * 1024


def _bounded_read(handle, limit):
    handle.seek(0)
    data = handle.read(limit + 1)
    truncated = len(data) > limit
    data = data[:limit]
    return data.decode("utf-8", errors="replace"), truncated


class FeederRunner:
    def __init__(self, timeout=60, capture_limit=DEFAULT_CAPTURE_LIMIT, which=shutil.which):
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        if capture_limit <= 0:
            raise ValueError("capture_limit must be positive")
        self.timeout = timeout
        self.capture_limit = capture_limit
        self.which = which

    def _execute(self, argv, cwd, timeout):
        if not isinstance(argv, list) or not argv or not all(isinstance(v, str) for v in argv):
            raise ValueError("feeder command must be a non-empty argv list")
        with tempfile.TemporaryFile() as stdout_file, tempfile.TemporaryFile() as stderr_file:
            process = subprocess.Popen(
                argv, cwd=cwd, stdin=subprocess.DEVNULL,
                stdout=stdout_file, stderr=stderr_file, shell=False,
            )
            timed_out = False
            try:
                returncode = process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                timed_out = True
                process.kill()
                returncode = process.wait()
            stdout, stdout_truncated = _bounded_read(stdout_file, self.capture_limit)
            stderr, stderr_truncated = _bounded_read(stderr_file, self.capture_limit)
        return {
            "returncode": returncode, "timed_out": timed_out,
            "stdout": stdout, "stderr": stderr,
            "stdout_truncated": stdout_truncated, "stderr_truncated": stderr_truncated,
        }

    def _version(self, adapter, executable, root):
        try:
            result = self._execute(adapter.version_argv(executable), root, min(5, self.timeout))
            if result["timed_out"]:
                return None
            first = (result["stdout"] or result["stderr"]).strip().splitlines()
            return redact_text(first[0])[:200] if first else None
        except (OSError, ValueError):
            return None

    def run(self, adapter, root, files, target=None):
        started = time.monotonic()
        base = {
            "schema": FEEDER_SCHEMA, "tool": adapter.name, "toolVersion": None,
            "source": "external", "status": "failed", "target": root,
            "durationMs": 0, "findings": [], "errors": [],
        }
        applicable, reason = adapter.applicable(root, files, target)
        if not applicable:
            base["status"] = "not_applicable"
            base["errors"] = []
            base["reason"] = reason
            return base

        executable = None
        for executable_name in adapter.executable_names:
            executable = self.which(executable_name)
            if executable:
                break
        if not executable:
            base["status"] = "unavailable"
            base["errors"] = [{"kind": "not_installed", "message": (
                "{} was not found on PATH; Cerberus did not install it.".format(adapter.name)
            )}]
            return base

        base["toolVersion"] = self._version(adapter, executable, root)
        try:
            with tempfile.TemporaryDirectory(prefix="cerberus-feeder-") as work_dir:
                argv = adapter.build_argv(executable, root, files, work_dir, target)
                if os.path.realpath(argv[0]) != os.path.realpath(executable):
                    raise ValueError("adapter attempted to invoke a non-allowlisted executable")
                result = self._execute(argv, root, self.timeout)
                if result["timed_out"]:
                    base["errors"].append({"kind": "timeout", "message": (
                        "{} exceeded the {} second timeout.".format(adapter.name, self.timeout)
                    )})
                    return base
                output = None
                if adapter.output_filename:
                    output_path = os.path.realpath(os.path.join(work_dir, adapter.output_filename))
                    if os.path.commonpath((os.path.realpath(work_dir), output_path)) != os.path.realpath(work_dir):
                        raise ValueError("feeder output path escaped its temporary directory")
                    if os.path.isfile(output_path):
                        with open(output_path, "rb") as handle:
                            output = handle.read(self.capture_limit + 1)
                        if len(output) > self.capture_limit:
                            raise ValueError("feeder report exceeded capture limit")
                        output = output.decode("utf-8", errors="replace")
                if result["returncode"] not in adapter.accepted_exit_codes:
                    base["errors"].append({
                        "kind": "exit_code", "message": "{} exited with code {}.".format(
                            adapter.name, result["returncode"]),
                        "stderr": redact_text(result["stderr"])[:2000],
                    })
                    return base
                if result["stdout_truncated"] or result["stderr_truncated"]:
                    raise ValueError("captured feeder output exceeded the size limit")
                findings, raw = adapter.parse(result["stdout"], result["stderr"], output, root)
                base["findings"] = deduplicate(findings)
                base["raw"] = raw
                base["status"] = "completed"
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
            base["errors"].append({"kind": "malformed_output", "message": redact_text(exc)[:1000]})
        finally:
            base["durationMs"] = max(0, round((time.monotonic() - started) * 1000))
        return base


def _repository_files(root):
    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [name for name in dirnames if name != ".git"]
        for filename in filenames:
            files.append(os.path.relpath(
                os.path.join(dirpath, filename), root
            ).replace(os.sep, "/"))
    return sorted(files)


def run_feeders(root_dir, selection="auto", timeout=60, target=None, capture_limit=DEFAULT_CAPTURE_LIMIT):
    """Run selected feeders and return ``cerberus.feeder/1`` contract dicts.

    ``selection`` accepts ``auto``, ``none``, or comma-separated canonical names.
    Repository file discovery is internal so the CLI integration remains small.
    """
    runner = FeederRunner(timeout=timeout, capture_limit=capture_limit)
    files = _repository_files(root_dir)
    return [runner.run(adapter, root_dir, files, target) for adapter in resolve_feeders(selection)]


def summarize_results(results):
    summary = {"completed": 0, "not_applicable": 0, "unavailable": 0, "failed": 0}
    for result in results:
        status = result.get("status", "failed")
        summary[status if status in summary else "failed"] += 1
    return summary
