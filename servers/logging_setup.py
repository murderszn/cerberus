"""
Activity logging for Cerberus Agent Server.

Default log path: ~/.cerberus/logs/cerberus.log
"""

from __future__ import annotations

import logging
import sys
import threading
from collections import deque
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Callable, Deque, Optional

from servers.config import DEFAULT_CONFIG_DIR

LOG_DIR = DEFAULT_CONFIG_DIR / "logs"
DEFAULT_LOG_FILE = LOG_DIR / "cerberus.log"
LOGGER_NAME = "cerberus"

_listeners: list[Callable[[str, str], None]] = []
_listener_lock = threading.Lock()
_activity: Deque[str] = deque(maxlen=200)
_activity_lock = threading.Lock()
_configured = False


class _ActivityHandler(logging.Handler):
    """Push formatted records into the ring buffer + optional listeners."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            with _activity_lock:
                _activity.append(msg)
            with _listener_lock:
                listeners = list(_listeners)
            for cb in listeners:
                try:
                    cb(record.levelname, record.getMessage())
                except Exception:
                    pass
        except Exception:
            self.handleError(record)


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Return a child logger under cerberus.*"""
    if name and not name.startswith(LOGGER_NAME):
        return logging.getLogger(f"{LOGGER_NAME}.{name}")
    return logging.getLogger(name or LOGGER_NAME)


def setup_logging(
    *,
    level: str = "INFO",
    log_file: Optional[Path] = None,
    console: bool = False,
    quiet: bool = False,
) -> Path:
    global _configured

    path = Path(log_file) if log_file else DEFAULT_LOG_FILE
    path.parent.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger(LOGGER_NAME)
    root.handlers.clear()
    root.setLevel(logging.DEBUG)
    root.propagate = False

    numeric = getattr(logging, level.upper(), logging.INFO)
    if quiet:
        numeric = logging.WARNING

    fmt = logging.Formatter(
        fmt="%(asctime)s │ %(levelname)-5s │ %(name)s │ %(message)s",
        datefmt="%H:%M:%S",
    )
    file_fmt = logging.Formatter(
        fmt="%(asctime)s │ %(levelname)-5s │ %(name)s │ %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    fh = RotatingFileHandler(
        path,
        maxBytes=2_000_000,
        backupCount=5,
        encoding="utf-8",
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(file_fmt)
    root.addHandler(fh)

    ah = _ActivityHandler()
    ah.setLevel(numeric)
    ah.setFormatter(fmt)
    root.addHandler(ah)

    if console:
        sh = logging.StreamHandler(sys.stderr)
        sh.setLevel(numeric)
        sh.setFormatter(fmt)
        root.addHandler(sh)

    _configured = True
    root.info("logging started  level=%s  file=%s", level.upper(), path)
    return path


def ensure_logging(**kwargs) -> Path:  # type: ignore[no-untyped-def]
    if not _configured:
        return setup_logging(**kwargs)
    return Path(kwargs.get("log_file") or DEFAULT_LOG_FILE)


def add_activity_listener(cb: Callable[[str, str], None]) -> None:
    with _listener_lock:
        if cb not in _listeners:
            _listeners.append(cb)


def remove_activity_listener(cb: Callable[[str, str], None]) -> None:
    with _listener_lock:
        try:
            _listeners.remove(cb)
        except ValueError:
            pass


def recent_activity(n: int = 30) -> list[str]:
    with _activity_lock:
        return list(_activity)[-n:]


def log_path() -> Path:
    return DEFAULT_LOG_FILE


def heartbeat(label: str) -> str:
    ts = datetime.now(timezone.utc).astimezone().strftime("%H:%M:%S")
    return f"{ts}  {label}"
