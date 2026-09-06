"""
Shared workspace path resolution for Cerberus.

Writes are confined to the workspace when enforce_boundary is True.
Reads may leave the workspace (with a note) so docs outside the repo are usable.
"""

from __future__ import annotations

from pathlib import Path


class WorkspacePathError(ValueError):
    """Path escapes the configured workspace (writes)."""


_BLOCKED_DEVICES = frozenset(
    {
        "/dev/zero",
        "/dev/random",
        "/dev/urandom",
        "/dev/full",
        "/dev/stdin",
        "/dev/tty",
        "/dev/console",
        "/dev/stdout",
        "/dev/stderr",
        "/dev/fd/0",
        "/dev/fd/1",
        "/dev/fd/2",
    }
)


def is_blocked_device(path: Path | str) -> bool:
    try:
        p = Path(path).expanduser().resolve()
    except OSError:
        p = Path(str(path))
    return str(p) in _BLOCKED_DEVICES or str(path) in _BLOCKED_DEVICES


def resolve_workspace_path(
    path: str,
    workspace: Path,
    *,
    enforce_boundary: bool,
    for_write: bool,
) -> Path:
    """Resolve relative paths against workspace; optionally enforce boundary."""
    raw = Path(path).expanduser()
    if not raw.is_absolute():
        candidate = (workspace / raw).resolve()
    else:
        candidate = raw.resolve()

    if is_blocked_device(candidate):
        raise WorkspacePathError(f"Refusing device path: {candidate}")

    workspace_resolved = workspace.resolve()
    try:
        candidate.relative_to(workspace_resolved)
        inside = True
    except ValueError:
        inside = False

    if for_write and enforce_boundary and not inside:
        raise WorkspacePathError(
            f"Refusing write outside workspace.\n"
            f"  path: {candidate}\n"
            f"  workspace: {workspace_resolved}"
        )
    return candidate


def is_binary_sample(data: bytes) -> bool:
    return b"\x00" in data[:512]
