"""
GitHub PR automation tool for Cerberus.

Supports:
  1. Branch creation: cerberus/{agent}-{task-slug}
  2. Staging and committing modified workspace files
  3. Pushing branch to remote
  4. Invoking `gh pr create` with report attachment
  5. Dry-run mode for safe execution preview
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Optional

from servers.logging_setup import get_logger
from servers.tools.git import _is_git_repo, _run_git

log = get_logger("tools.pr")


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[-\s]+", "-", text)
    return text[:40].strip("-") or "patch"


def create_pull_request(
    title: str,
    *,
    workspace: Path,
    agent_name: str = "agent",
    body: str = "",
    base_branch: str = "main",
    branch_name: str = "",
    task_slug: str = "",
    report_path: Optional[str] = None,
    dry_run: bool = False,
) -> str:
    """
    Create a branch, commit modified files, push, and open a GitHub PR via `gh`.

    If dry_run is True, previews all actions without executing remote changes.
    """
    if not _is_git_repo(workspace):
        return "ERROR: not a git repository"

    if not title or not title.strip():
        return "ERROR: PR title must not be empty"

    title = title.strip()
    slug = task_slug or slugify(title)
    target_branch = branch_name or f"cerberus/{agent_name}-{slug}"

    # Verify changes exist
    exit_code, status_out, _ = _run_git(["status", "--porcelain"], workspace)
    if exit_code != 0:
        return f"ERROR: failed to check git status: {status_out}"
    if not status_out.strip():
        return "ERROR: no modified files in workspace to commit or create a PR for"

    # Report attachment
    report_summary = ""
    candidate_report = Path(report_path) if report_path else (workspace / "cerberus-report.json")
    if not candidate_report.is_absolute():
        candidate_report = workspace / candidate_report

    if candidate_report.exists() and candidate_report.is_file():
        try:
            raw_rep = json.loads(candidate_report.read_text(encoding="utf-8"))
            score = raw_rep.get("score")
            findings = raw_rep.get("findings", [])
            report_summary = (
                f"\n\n### Cerberus Audit Summary\n"
                f"- **Native Score:** {score if score is not None else 'N/A'}/100\n"
                f"- **Findings Detected:** {len(findings)}\n"
                f"- **Auditing Agent:** `{agent_name}`\n"
            )
        except Exception:
            pass

    full_body = (body.strip() or f"Automated security remediation by Cerberus `{agent_name}` agent.") + report_summary

    if dry_run:
        return (
            f"[DRY RUN] GitHub PR Preview:\n"
            f"  Target Branch: {target_branch}\n"
            f"  Base Branch:   {base_branch}\n"
            f"  Title:         {title}\n"
            f"  Body:\n"
            f"{full_body}\n"
            f"  Changes to stage:\n"
            f"{status_out.strip()}"
        )

    # 1. Create or checkout branch
    code, out, err = _run_git(["checkout", "-b", target_branch], workspace)
    if code != 0:
        # Branch might already exist, try checkout
        code, out, err = _run_git(["checkout", target_branch], workspace)
        if code != 0:
            return f"ERROR: failed to checkout branch {target_branch}: {err}"

    # 2. Stage all changes
    code, out, err = _run_git(["add", "-A"], workspace)
    if code != 0:
        return f"ERROR: failed to stage files: {err}"

    # 3. Commit
    commit_msg = f"fix({agent_name}): {title}\n\n{full_body}"
    code, out, err = _run_git(["commit", "-m", commit_msg], workspace)
    if code != 0:
        return f"ERROR: commit failed: {err}"

    # 4. Push to remote
    code, out, err = _run_git(["push", "-u", "origin", target_branch], workspace, timeout=60)
    if code != 0:
        return f"ERROR: git push failed: {err}"

    # 5. Open PR via gh CLI
    gh = shutil.which("gh")
    if not gh:
        return (
            f"SUCCESS: branch {target_branch} pushed to origin.\n"
            f"NOTE: `gh` CLI not found in PATH — please open PR manually via GitHub UI."
        )

    try:
        proc = subprocess.run(
            [gh, "pr", "create", "--base", base_branch, "--title", title, "--body", full_body],
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        if proc.returncode != 0:
            return f"Branch pushed, but `gh pr create` failed: {proc.stderr.strip()}"
        pr_url = proc.stdout.strip()
        return f"SUCCESS: PR created: {pr_url}"
    except Exception as exc:
        return f"Branch pushed, but error running `gh pr create`: {exc}"
