"""
Session persistence — save/load conversation transcripts for Cerberus.

Storage: JSONL files in ~/.cerberus/sessions/
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Optional

from servers.config import DEFAULT_CONFIG_DIR
from servers.logging_setup import get_logger

log = get_logger("session_store")

SESSIONS_DIR = DEFAULT_CONFIG_DIR / "sessions"


@dataclass
class SessionMeta:
    name: str
    created_at: float
    updated_at: float
    model: str = ""
    workspace: str = ""
    message_count: int = 0


def _ensure_dir() -> Path:
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    return SESSIONS_DIR


def _session_path(name: str) -> Path:
    safe = name.replace("/", "_").replace("\\", "_")
    return _ensure_dir() / f"{safe}.jsonl"


def list_sessions() -> list[SessionMeta]:
    """Return all saved sessions sorted by most recently updated."""
    sessions = []
    if not SESSIONS_DIR.exists():
        return sessions
    for path in sorted(SESSIONS_DIR.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            with path.open("r", encoding="utf-8") as f:
                first = json.loads(f.readline())
            meta = first.get("_meta", {})
            with path.open("r", encoding="utf-8") as f:
                count = sum(1 for line in f if line.strip()) - 1
            sessions.append(
                SessionMeta(
                    name=path.stem,
                    created_at=float(meta.get("created_at") or path.stat().st_ctime),
                    updated_at=float(meta.get("updated_at") or path.stat().st_mtime),
                    model=str(meta.get("model") or ""),
                    workspace=str(meta.get("workspace") or ""),
                    message_count=max(0, count),
                )
            )
        except Exception as exc:
            log.debug("could not read session %s: %s", path, exc)
    return sessions


def save_session(
    name: str,
    messages: list[dict[str, Any]],
    *,
    model: str = "",
    workspace: str = "",
) -> Path:
    """Save conversation history to a JSONL file."""
    path = _session_path(name)
    now = time.time()
    created_at = now
    if path.exists():
        try:
            with path.open("r", encoding="utf-8") as rf:
                first = json.loads(rf.readline() or "{}")
            created_at = float(first.get("_meta", {}).get("created_at") or now)
        except Exception:
            created_at = now
    meta = {
        "_meta": {
            "created_at": created_at,
            "updated_at": now,
            "model": model,
            "workspace": workspace,
        }
    }
    with path.open("w", encoding="utf-8") as f:
        f.write(json.dumps(meta, ensure_ascii=False) + "\n")
        for msg in messages:
            f.write(json.dumps(msg, ensure_ascii=False) + "\n")
    log.info("saved session %s (%d messages) -> %s", name, len(messages), path)
    return path


def load_session(name: str) -> list[dict[str, Any]]:
    """Load a transcript from JSONL."""
    path = _session_path(name)
    if not path.exists():
        raise FileNotFoundError(f"Session not found: {name}")
    messages = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if "_meta" in obj:
                continue
            messages.append(obj)
    log.info("loaded session %s (%d messages) from %s", name, len(messages), path)
    return messages


def delete_session(name: str) -> bool:
    """Delete a saved session."""
    path = _session_path(name)
    if path.exists():
        path.unlink()
        log.info("deleted session %s", name)
        return True
    return False
