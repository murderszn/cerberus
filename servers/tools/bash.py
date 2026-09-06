"""
execute_bash_command for Cerberus — local subprocess tool with timeout, safety gates, and secret redaction.
"""

from __future__ import annotations

import subprocess
import time
from typing import Any, Callable, Optional

from servers.logging_setup import get_logger
from servers.tools.safety import is_destructive, redact_text

log = get_logger("tools.bash")

# Approval answer: True/"once" allows one run, "session" allows (callers with
# session memory record the kind), False/"deny"/None denies. Any truthy value
# executes, so tri-state callbacks stay compatible with this gate.
ConfirmCallback = Callable[[str, str], Any]


def run_bash(
    command: str,
    *,
    timeout: int = 45,
    cwd: Optional[str] = None,
    confirm: Optional[ConfirmCallback] = None,
    extra_destructive_patterns: Optional[list[str]] = None,
    redact_output: bool = True,
) -> str:
    """
    Execute a shell command via subprocess.Popen.
    Returns structured output with secret redaction applied.
    """
    if not command or not command.strip():
        return "ERROR: empty command"

    destructive, reason = is_destructive(command, extra_destructive_patterns)
    if destructive:
        log.warning("destructive command gated: %s (%s)", command[:120], reason)
        allowed = False
        if confirm is not None:
            allowed = confirm(command, reason)
        if not allowed:
            log.warning("destructive command BLOCKED by user")
            return (
                "BLOCKED: command flagged as potentially destructive.\n"
                f"Reason: {reason}\n"
                f"Command: {command}\n"
                "User denied execution (or no confirmation callback was available)."
            )
        log.info("destructive command APPROVED by user")

    log.info("shell exec  timeout=%ss  cwd=%s  cmd=%r", timeout, cwd, command[:200])
    t0 = time.monotonic()
    try:
        proc = subprocess.Popen(
            ["bash", "-lc", command],
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=cwd,
            text=True,
        )
        try:
            stdout, stderr = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            stdout, stderr = proc.communicate()
            log.error("shell TIMEOUT after %ss  cmd=%r", timeout, command[:120])
            out_s = redact_text(stdout or "") if redact_output else (stdout or "")
            err_s = redact_text(stderr or "") if redact_output else (stderr or "")
            return (
                f"TIMEOUT: command exceeded {timeout}s and was killed.\n"
                f"--- stdout ---\n{out_s.strip()}\n"
                f"--- stderr ---\n{err_s.strip()}"
            )
    except OSError as exc:
        log.error("shell spawn failed: %s", exc)
        return f"ERROR: failed to spawn process: {exc}"

    exit_code = proc.returncode if proc.returncode is not None else -1
    out = (stdout or "").rstrip()
    err = (stderr or "").rstrip()

    if redact_output:
        out = redact_text(out)
        err = redact_text(err)

    elapsed = time.monotonic() - t0
    log.info(
        "shell done  exit=%s  %.2fs  stdout_chars=%d  stderr_chars=%d",
        exit_code,
        elapsed,
        len(out),
        len(err),
    )

    max_chars = 40_000
    if len(out) > max_chars:
        out = out[:max_chars] + f"\n... [stdout truncated at {max_chars} chars]"
    if len(err) > max_chars:
        err = err[:max_chars] + f"\n... [stderr truncated at {max_chars} chars]"

    parts = [f"exit_code: {exit_code}"]
    parts.append("--- stdout ---")
    parts.append(out if out else "(empty)")
    parts.append("--- stderr ---")
    parts.append(err if err else "(empty)")
    return "\n".join(parts)
