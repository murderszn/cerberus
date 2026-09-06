"""
Pollinations BYOP (Bring Your Own Pollen) — device authorization flow for Cerberus.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Callable, Optional

POLLINATIONS_ENTER_URL = "https://enter.pollinations.ai"
DEFAULT_BYOP_CLIENT_ID = "pk_AixR2lSZdrdT17l7"


@dataclass
class DeviceCodeResponse:
    device_code: str
    user_code: str
    verification_uri: str
    expires_in: Optional[int] = None
    interval: Optional[int] = None


@dataclass
class DeviceUserInfo:
    sub: str
    preferred_username: Optional[str] = None
    picture: Optional[str] = None
    name: Optional[str] = None
    email: Optional[str] = None


def resolve_byop_client_id() -> Optional[str]:
    for env in (
        "CERBERUS_BYOP_KEY",
        "POLLINATIONS_BYOP_KEY",
        "OPENCODE_HARNESS_BYOP_KEY",
        "SPROUT_BYOP_KEY",
    ):
        val = os.environ.get(env, "").strip()
        if val:
            return val
    return DEFAULT_BYOP_CLIENT_ID


def device_verification_url(verification_uri: str) -> str:
    if verification_uri.startswith("http://") or verification_uri.startswith("https://"):
        return verification_uri
    base = POLLINATIONS_ENTER_URL.rstrip("/")
    path = verification_uri if verification_uri.startswith("/") else f"/{verification_uri}"
    return f"{base}{path}"


def _post_json(url: str, payload: dict, *, timeout: float = 30.0) -> tuple[int, dict]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Cerberus/2.0 (BYOP)",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            status = resp.status
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        status = exc.code
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Network error contacting Pollinations: {exc.reason}") from exc

    try:
        parsed = json.loads(body) if body.strip() else {}
    except json.JSONDecodeError:
        parsed = {"raw": body}
    if not isinstance(parsed, dict):
        parsed = {"raw": body}
    return status, parsed


def _get_json(url: str, *, bearer: str, timeout: float = 30.0) -> tuple[int, dict]:
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {bearer}",
            "Accept": "application/json",
            "User-Agent": "Cerberus/2.0 (BYOP)",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            status = resp.status
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        status = exc.code
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Network error contacting Pollinations: {exc.reason}") from exc

    try:
        parsed = json.loads(body) if body.strip() else {}
    except json.JSONDecodeError:
        parsed = {}
    if not isinstance(parsed, dict):
        parsed = {}
    return status, parsed


def request_device_code(client_id: str) -> DeviceCodeResponse:
    status, data = _post_json(
        f"{POLLINATIONS_ENTER_URL}/api/device/code",
        {"client_id": client_id},
    )
    if status >= 400:
        raise RuntimeError(f"Could not start Pollen sign-in ({status}). {data}".strip())
    device_code = data.get("device_code")
    user_code = data.get("user_code")
    verification_uri = data.get("verification_uri") or "/device"
    if not device_code or not user_code:
        raise RuntimeError("Pollinations returned an incomplete device authorization response.")
    return DeviceCodeResponse(
        device_code=str(device_code),
        user_code=str(user_code),
        verification_uri=str(verification_uri),
        expires_in=int(data["expires_in"]) if data.get("expires_in") is not None else None,
        interval=int(data["interval"]) if data.get("interval") is not None else None,
    )


def poll_device_token_once(device_code: str) -> dict:
    status, body = _post_json(
        f"{POLLINATIONS_ENTER_URL}/api/device/token",
        {"device_code": device_code},
    )
    if status < 400 and body.get("access_token"):
        return {"ok": True, "access_token": str(body["access_token"])}

    err = body.get("error")
    if err == "authorization_pending":
        return {"ok": False, "error": "authorization_pending"}
    if err == "slow_down":
        retry = body.get("retry_after")
        retry_ms = int(retry) * 1000 if isinstance(retry, (int, float)) else 10_000
        return {"ok": False, "error": "slow_down", "retry_after_ms": retry_ms}
    if err in {"expired_token", "access_denied", "invalid_grant"}:
        return {"ok": False, "error": err}

    raise RuntimeError(f"Pollen sign-in failed ({status})" + (f": {err}" if err else ""))


def poll_device_token(
    device_code: str,
    *,
    interval_ms: int = 5000,
    timeout_ms: int = 10 * 60 * 1000,
    on_pending: Optional[Callable[[int], None]] = None,
    sleep: Optional[Callable[[float], None]] = None,
) -> str:
    _sleep = sleep or time.sleep
    started = time.time()
    interval = max(1.0, interval_ms / 1000.0)
    timeout_s = timeout_ms / 1000.0

    while time.time() - started < timeout_s:
        result = poll_device_token_once(device_code)
        if result.get("ok") and result.get("access_token"):
            return str(result["access_token"])

        err = result.get("error")
        if err == "expired_token":
            raise RuntimeError("Pollen sign-in code expired — run `cerberus login` again.")
        if err == "access_denied":
            raise RuntimeError("Pollen sign-in was denied.")
        if err == "invalid_grant":
            raise RuntimeError("Pollen sign-in grant is no longer valid — run `cerberus login` again.")
        if err == "slow_down" and result.get("retry_after_ms"):
            interval = max(interval, float(result["retry_after_ms"]) / 1000.0)

        elapsed_ms = int((time.time() - started) * 1000)
        if on_pending:
            on_pending(elapsed_ms)
        _sleep(interval)

    raise RuntimeError("Pollen sign-in timed out — approve in the browser, then run `cerberus login` again.")


def fetch_device_userinfo(access_token: str) -> Optional[DeviceUserInfo]:
    try:
        status, data = _get_json(
            f"{POLLINATIONS_ENTER_URL}/api/device/userinfo",
            bearer=access_token,
        )
        if status >= 400 or not data.get("sub"):
            return None
        return DeviceUserInfo(
            sub=str(data["sub"]),
            preferred_username=data.get("preferred_username"),
            picture=data.get("picture"),
            name=data.get("name"),
            email=data.get("email"),
        )
    except Exception:
        return None


def open_browser(url: str) -> bool:
    try:
        if sys.platform == "darwin":
            subprocess.run(["open", url], check=False, capture_output=True)
            return True
        if sys.platform == "win32":
            subprocess.run(["cmd", "/c", "start", "", url], check=False, shell=False, capture_output=True)
            return True
        subprocess.run(["xdg-open", url], check=False, capture_output=True)
        return True
    except Exception:
        return False


@dataclass
class ByopLoginResult:
    access_token: str
    user: Optional[DeviceUserInfo] = None
    user_code: str = ""
    verify_url: str = ""


def run_byop_login(
    client_id: str,
    *,
    on_device_code: Optional[Callable[[str, str, bool], None]] = None,
    on_waiting: Optional[Callable[[int], None]] = None,
    on_authorized: Optional[Callable[[Optional[DeviceUserInfo]], None]] = None,
) -> ByopLoginResult:
    device = request_device_code(client_id)
    verify_url = device_verification_url(device.verification_uri)
    opened = open_browser(verify_url)
    if on_device_code:
        on_device_code(device.user_code, verify_url, opened)

    interval_ms = (device.interval or 5) * 1000
    access_token = poll_device_token(
        device.device_code,
        interval_ms=interval_ms,
        on_pending=on_waiting,
    )
    user = fetch_device_userinfo(access_token)
    if on_authorized:
        on_authorized(user)

    return ByopLoginResult(
        access_token=access_token,
        user=user,
        user_code=device.user_code,
        verify_url=verify_url,
    )
