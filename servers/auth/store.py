"""
Secure local key storage for Cerberus.

Resolution order:
  1. Env: CERBERUS_API_KEY / POLLINATIONS_API_KEY / OPENAI_API_KEY / OPENCODE_HARNESS_API_KEY / SPROUT_API_KEY
  2. Credentials file: ~/.cerberus/credentials.json  (mode 0o600)
  3. provider.api_key inside config.yaml (discouraged)
"""

from __future__ import annotations

import json
import os
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional

from servers.config import DEFAULT_CONFIG_DIR

ApiKeyKind = Literal["byop", "manual", "env"]

CREDENTIALS_PATH = DEFAULT_CONFIG_DIR / "credentials.json"


@dataclass
class ResolvedKey:
    key: str
    source: Literal["env", "credentials", "config"]
    kind: ApiKeyKind


def mask_key(key: str) -> str:
    """sk_abc...xyz -> sk_a****xyz — only form ever printed."""
    if not key:
        return "(empty)"
    if len(key) <= 8:
        return "*" * len(key)
    stars = min(len(key) - 7, 20)
    return f"{key[:4]}{'*' * stars}{key[-3:]}"


def _ensure_private_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    if os.name != "nt":
        try:
            path.chmod(0o700)
        except OSError:
            pass


def _chmod_private(path: Path) -> None:
    if os.name != "nt" and path.exists():
        try:
            path.chmod(0o600)
        except OSError:
            pass


def read_credentials() -> dict:
    if not CREDENTIALS_PATH.exists():
        return {}
    try:
        data = json.loads(CREDENTIALS_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def save_api_key(key: str, kind: ApiKeyKind = "byop", *, username: Optional[str] = None) -> Path:
    """Persist access token to credentials.json with restrictive permissions."""
    _ensure_private_dir(DEFAULT_CONFIG_DIR)
    payload = {
        "api_key": key,
        "api_key_kind": kind,
    }
    if username:
        payload["username"] = username
    existing = read_credentials()
    existing.update(payload)
    CREDENTIALS_PATH.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")
    _chmod_private(CREDENTIALS_PATH)
    return CREDENTIALS_PATH


def clear_stored_key() -> bool:
    """Remove stored api_key from credentials. Returns True if something was cleared."""
    data = read_credentials()
    if "api_key" not in data and "api_key_kind" not in data:
        return False
    data.pop("api_key", None)
    data.pop("api_key_kind", None)
    data.pop("username", None)
    if data:
        CREDENTIALS_PATH.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        _chmod_private(CREDENTIALS_PATH)
    elif CREDENTIALS_PATH.exists():
        CREDENTIALS_PATH.unlink()
    return True


def resolve_api_key(*, config_file_key: str = "") -> Optional[ResolvedKey]:
    """Resolve a usable API key without prompting."""
    for env_name in (
        "CERBERUS_API_KEY",
        "POLLINATIONS_API_KEY",
        "OPENAI_API_KEY",
        "OPENCODE_HARNESS_API_KEY",
        "SPROUT_API_KEY",
    ):
        val = os.environ.get(env_name, "").strip()
        if val:
            return ResolvedKey(key=val, source="env", kind="env")

    creds = read_credentials()
    file_key = str(creds.get("api_key") or "").strip()
    if file_key:
        kind_raw = str(creds.get("api_key_kind") or "manual")
        kind: ApiKeyKind = kind_raw if kind_raw in {"byop", "manual", "env"} else "manual"
        return ResolvedKey(key=file_key, source="credentials", kind=kind)

    cfg_key = (config_file_key or "").strip()
    if cfg_key:
        return ResolvedKey(key=cfg_key, source="config", kind="manual")

    return None


def credentials_path() -> Path:
    return CREDENTIALS_PATH


def credentials_is_private() -> bool:
    """True if credentials file mode is owner-only (or on Windows)."""
    if os.name == "nt":
        return True
    if not CREDENTIALS_PATH.exists():
        return True
    mode = CREDENTIALS_PATH.stat().st_mode
    return (mode & (stat.S_IRWXG | stat.S_IRWXO)) == 0
