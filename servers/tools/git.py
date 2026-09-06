"""
Git intelligence tools for Cerberus — status, diff, log, branch with secret redaction.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional

from servers.logging_setup import get_logger
from servers.tools.safety import redact_text

log = get_logger("tools.git")


def _run_git(args: list[str], cwd: Path, timeout: int = 15) -> tuple[int, str, str]:
    cmd = ["git", "-C", str(cwd)] + args
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return proc.returncode, proc.stdout, proc.stderr
    except FileNotFoundError:
        return -1, "", "ERROR: git not found in PATH"
    except subprocess.TimeoutExpired:
        return -1, "", f"ERROR: git command timed out after {timeout}s"
    except Exception as exc:
        return -1, "", f"ERROR: {exc}"


def _is_git_repo(cwd: Path) -> bool:
    exit_code, _, _ = _run_git(["rev-parse", "--git-dir"], cwd)
    return exit_code == 0


def git_status(
    workspace: Path,
    *,
    short: bool = False,
) -> str:
    """Show git working tree status."""
    if not _is_git_repo(workspace):
        return "ERROR: not a git repository"

    exit_code, stdout, stderr = _run_git(
        ["status", "--porcelain", "-b"], workspace
    )
    if exit_code != 0:
        return f"ERROR: git status failed: {stderr.strip()}"

    lines = stdout.strip().splitlines()
    if not lines:
        return "Working tree clean — no changes."

    branch_line = ""
    file_lines = []
    for line in lines:
        if line.startswith("##"):
            branch_line = line[2:].strip()
        else:
            file_lines.append(line)

    staged = []
    unstaged = []
    untracked = []
    conflicted = []

    for line in file_lines:
        if len(line) < 3:
            continue
        xy = line[:2]
        path_part = line[3:]

        if xy == "??":
            untracked.append(path_part)
        elif xy.startswith("U") or xy.endswith("U") or xy == "DD" or xy == "AA":
            conflicted.append(f"{path_part} [{xy}]")
        elif xy[0] != " " and xy[0] != "?":
            staged.append(f"{path_part} [{xy[0]}]")
        if xy[1] != " " and xy[1] != "?":
            unstaged.append(f"{path_part} [{xy[1]}]")

    parts = []
    if branch_line:
        parts.append(f"branch: {branch_line}")
    if staged:
        parts.append(f"\nstaged ({len(staged)}):")
        parts.extend(f"  + {f}" for f in staged)
    if unstaged:
        parts.append(f"\nunstaged ({len(unstaged)}):")
        parts.extend(f"  ~ {f}" for f in unstaged)
    if untracked:
        parts.append(f"\nuntracked ({len(untracked)}):")
        parts.extend(f"  ? {f}" for f in untracked)
    if conflicted:
        parts.append(f"\nconflicted ({len(conflicted)}):")
        parts.extend(f"  ! {f}" for f in conflicted)

    if short:
        return "\n".join(parts)

    exit_code, ahead_behind, _ = _run_git(
        ["rev-list", "--left-right", "--count", "HEAD...@{upstream}"], workspace
    )
    if exit_code == 0:
        try:
            ahead, behind = ahead_behind.strip().split("\t")
            if ahead != "0" or behind != "0":
                parts.append(f"\nahead {ahead}, behind {behind} (vs upstream)")
        except ValueError:
            pass

    return "\n".join(parts)


def git_diff(
    workspace: Path,
    *,
    staged: bool = False,
    path: str = "",
    max_lines: int = 500,
    redact: bool = True,
) -> str:
    """Show git diff with secret redaction."""
    if not _is_git_repo(workspace):
        return "ERROR: not a git repository"

    args = ["diff"]
    if staged:
        args.append("--staged")
    args.append("--")
    if path:
        args.append(path)

    exit_code, stdout, stderr = _run_git(args, workspace)
    if exit_code != 0:
        return f"ERROR: git diff failed: {stderr.strip()}"

    if not stdout.strip():
        scope = "staged" if staged else "unstaged"
        filter_note = f" for '{path}'" if path else ""
        return f"No {scope} changes{filter_note}."

    diff_text = redact_text(stdout) if redact else stdout
    lines = diff_text.splitlines()
    if len(lines) > max_lines:
        truncated = "\n".join(lines[:max_lines])
        return f"{truncated}\n... [diff truncated at {max_lines} lines, {len(lines)} total]"
    return diff_text


def git_log(
    workspace: Path,
    *,
    n: int = 10,
    oneline: bool = True,
    path: str = "",
) -> str:
    """Show recent commit history."""
    if not _is_git_repo(workspace):
        return "ERROR: not a git repository"

    args = ["log", f"-{n}"]
    if oneline:
        args.append("--oneline")
    else:
        args.extend(["--format=medium", "--stat"])
    args.append("--")
    if path:
        args.append(path)

    exit_code, stdout, stderr = _run_git(args, workspace)
    if exit_code != 0:
        return f"ERROR: git log failed: {stderr.strip()}"

    if not stdout.strip():
        return "No commits found."

    return stdout


def git_branch(workspace: Path) -> str:
    """Show current branch and list all branches."""
    if not _is_git_repo(workspace):
        return "ERROR: not a git repository"

    exit_code, stdout, stderr = _run_git(["branch", "-vv"], workspace)
    if exit_code != 0:
        return f"ERROR: git branch failed: {stderr.strip()}"

    if not stdout.strip():
        return "No branches found."

    return stdout
