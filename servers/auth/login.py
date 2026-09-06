"""
Interactive login UX for Cerberus — Pollen BYOP device flow + manual key paste.
"""

from __future__ import annotations

import getpass
import sys
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from servers.auth.byop import (
    ByopLoginResult,
    resolve_byop_client_id,
    run_byop_login,
)
from servers.auth.store import (
    clear_stored_key,
    credentials_path,
    mask_key,
    resolve_api_key,
    save_api_key,
)

_C_WHITE = "#FFFFFF"
_C_GRAY = "#9A9A9A"
_C_DIM = "#5A5A5A"
_C_LIME = _C_WHITE
_C_JADE = _C_GRAY
_C_MINT = _C_WHITE


def is_interactive() -> bool:
    try:
        return bool(sys.stdin.isatty() and sys.stdout.isatty())
    except Exception:
        return False


def _read_choice(console: Console, prompt: str) -> str:
    try:
        return console.input(prompt).strip().lower()
    except (EOFError, KeyboardInterrupt):
        raise
    except Exception:
        try:
            sys.stdout.write(prompt.replace("[", "").replace("]", ""))
            sys.stdout.flush()
            return input().strip().lower()
        except (EOFError, KeyboardInterrupt):
            raise


def perform_byop_login(*, save: bool = True, console: Optional[Console] = None) -> str:
    console = console or Console()
    client_id = resolve_byop_client_id()
    if not client_id:
        raise RuntimeError(
            "BYOP is not configured — set POLLINATIONS_BYOP_KEY or ship a publishable pk_ App Key."
        )

    console.print()
    console.print(
        Panel(
            Text.from_markup(
                f"[bold {_C_LIME}]Sign in with Pollen[/]\n"
                f"[{_C_MINT}]CERBERUS[/] uses [bold]your[/] Pollinations balance for inference —\n"
                "nothing is charged to the app author.\n\n"
                f"[{_C_DIM}]Browser opens enter.pollinations.ai · approve · come back here.[/]"
            ),
            border_style=_C_JADE,
            title="◈  Pollen · BYOP",
            title_align="left",
            padding=(1, 2),
        )
    )

    def on_device_code(user_code: str, verify_url: str, opened: bool) -> None:
        console.print()
        console.print(f"  [bold]Enter this code[/] at [{_C_MINT} underline]{verify_url}[/]")
        console.print(f"  [bold {_C_LIME}]{user_code}[/]\n")
        if opened:
            console.print(
                f"  [{_C_DIM}]Opened your browser — approve access, then come back here.[/]\n"
            )
        else:
            console.print(
                f"  [{_C_DIM}]Could not open a browser automatically — visit the URL above.[/]\n"
            )

    def on_waiting(elapsed_ms: int) -> None:
        secs = round(elapsed_ms / 1000)
        console.print(f"  [{_C_DIM}]waiting for approval… {secs}s[/]", end="\r")

    def on_authorized(user) -> None:
        console.print()
        if user and user.preferred_username:
            console.print(f"  [bold {_C_LIME}]✓[/] authorized as [bold]{user.preferred_username}[/]")
        else:
            console.print(f"  [bold {_C_LIME}]✓[/] authorized")

    result: ByopLoginResult = run_byop_login(
        client_id,
        on_device_code=on_device_code,
        on_waiting=on_waiting,
        on_authorized=on_authorized,
    )

    if save:
        username = result.user.preferred_username if result.user else None
        path = save_api_key(result.access_token, kind="byop", username=username)
        console.print(
            f"\n[{_C_JADE}]Saved[/] (masked: [bold]{mask_key(result.access_token)}[/]) "
            f"to [{_C_DIM}]{path}[/]"
        )

    return result.access_token


def prompt_manual_key(*, save: bool = True, console: Optional[Console] = None) -> str:
    console = console or Console()
    console.print()
    console.print(
        Panel(
            Text.from_markup(
                f"[bold {_C_LIME}]Paste API key[/]\n"
                f"[{_C_DIM}]Pollinations sk_… · OpenAI · Ollama dummy · any OpenAI-compatible key[/]"
            ),
            border_style=_C_JADE,
            title="◈  Manual key",
            title_align="left",
            padding=(0, 2),
        )
    )
    try:
        key = getpass.getpass("  API key: ").strip()
    except (EOFError, KeyboardInterrupt) as exc:
        raise RuntimeError("Login cancelled.") from exc
    if not key:
        raise RuntimeError("Empty API key.")

    if save:
        path = save_api_key(key, kind="manual")
        console.print(
            f"  [{_C_JADE}]Saved[/] (masked: [bold]{mask_key(key)}[/]) to [{_C_DIM}]{path}[/]"
        )
    return key


def interactive_login(
    *,
    save: bool = True,
    console: Optional[Console] = None,
    allow_cancel: bool = True,
) -> str:
    console = console or Console()
    client_id = resolve_byop_client_id()

    console.print()
    console.print(
        Panel(
            Text.from_markup(
                f"[bold {_C_LIME}]CERBERUS login[/]\n\n"
                f"  [bold]1[/]  Sign in with Pollen  [{_C_DIM}](recommended · enter.pollinations.ai)[/]\n"
                f"  [bold]2[/]  Paste an API key     [{_C_DIM}](sk_… / OpenAI / local)[/]\n"
                + (
                    f"  [bold]3[/]  Cancel\n"
                    if allow_cancel
                    else ""
                )
            ),
            border_style=_C_JADE,
            title="◈  Auth",
            title_align="left",
            padding=(1, 2),
        )
    )

    default = "1" if client_id else "2"
    prompt = f"  [{_C_LIME}]choice[/] [{_C_DIM}](default {default})[/] › "
    try:
        raw = _read_choice(console, prompt)
    except (EOFError, KeyboardInterrupt) as exc:
        raise RuntimeError("Login cancelled.") from exc

    if not raw:
        raw = default

    if allow_cancel and raw in {"3", "c", "cancel", "q", "quit", "n", "no"}:
        raise RuntimeError("Login cancelled.")

    if raw in {"1", "p", "pollen", "byop", "y", "yes"}:
        if not client_id:
            console.print(
                f"  [bold #FFFFFF]BYOP App Key missing[/] — falling back to paste key.\n"
                f"  [{_C_DIM}]Set POLLINATIONS_BYOP_KEY to enable Pollen device login.[/]"
            )
            return prompt_manual_key(save=save, console=console)
        return perform_byop_login(save=save, console=console)

    if raw in {"2", "k", "key", "paste", "manual"}:
        return prompt_manual_key(save=save, console=console)

    raise RuntimeError(
        f"Unknown choice {raw!r} — pick 1 (Pollen), 2 (paste key)"
        + (", or 3 (cancel)" if allow_cancel else "")
        + "."
    )


def require_api_key(
    *,
    config_file_key: str = "",
    console: Optional[Console] = None,
    force_login: bool = False,
) -> str:
    console = console or Console()
    if not force_login:
        resolved = resolve_api_key(config_file_key=config_file_key)
        if resolved:
            return resolved.key

    if not is_interactive():
        raise RuntimeError(
            "No API key found. Set CERBERUS_API_KEY, run `cerberus login` in a TTY, or add provider.api_key to config."
        )

    console.print()
    console.print(
        Text.from_markup(
            f"[bold {_C_LIME}]No API key found[/]  [{_C_DIM}]— sign in to continue[/]"
        )
    )
    return interactive_login(save=True, console=console, allow_cancel=False)


def perform_logout(*, console: Optional[Console] = None) -> bool:
    console = console or Console()
    if clear_stored_key():
        console.print(
            f"[{_C_JADE}]Cleared stored key[/] from [{_C_DIM}]{credentials_path()}[/]"
        )
        return True
    console.print(f"[{_C_DIM}]No stored credentials to clear.[/]")
    console.print(
        f"[{_C_DIM}]If you use an env var (CERBERUS_API_KEY / POLLINATIONS_API_KEY), unset it in your shell.[/]"
    )
    return False
