"""
browse_web_content for Cerberus (gated for Librarian / research).
"""

from __future__ import annotations

import re
from typing import Optional
from urllib.parse import urlparse

import httpx

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

_STRIP_TAGS = re.compile(
    r"<(script|style|noscript|svg|iframe)[^>]*>.*?</\1>",
    re.I | re.S,
)
_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"[ \t]+\n")
_MULTI_NL = re.compile(r"\n{3,}")


def _html_to_text_regex(html: str) -> str:
    cleaned = _STRIP_TAGS.sub("", html)
    cleaned = re.sub(r"<br\s*/?>", "\n", cleaned, flags=re.I)
    cleaned = re.sub(r"</(p|div|h[1-6]|li|tr|section|article)>", "\n", cleaned, flags=re.I)
    cleaned = re.sub(r"<li[^>]*>", "- ", cleaned, flags=re.I)
    cleaned = _TAG.sub("", cleaned)
    cleaned = (
        cleaned.replace("&nbsp;", " ")
        .replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&quot;", '"')
        .replace("&#39;", "'")
    )
    cleaned = _WS.sub("\n", cleaned)
    cleaned = _MULTI_NL.sub("\n\n", cleaned)
    return cleaned.strip()


def _html_to_text_bs(html: str) -> str:
    assert BeautifulSoup is not None
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg", "iframe", "nav", "footer", "header"]):
        tag.decompose()

    root = soup.find("main") or soup.find("article") or soup.body or soup
    lines: list[str] = []
    for el in root.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "pre", "code", "td", "th"]):
        text = el.get_text(" ", strip=True)
        if not text:
            continue
        name = el.name.lower()
        if name.startswith("h"):
            level = int(name[1])
            lines.append("#" * level + " " + text)
        elif name == "li":
            lines.append(f"- {text}")
        elif name == "pre":
            lines.append("```\n" + el.get_text("\n", strip=False).strip() + "\n```")
        else:
            lines.append(text)

    if not lines:
        text = root.get_text("\n", strip=True)
        return _MULTI_NL.sub("\n\n", text).strip()

    return _MULTI_NL.sub("\n\n", "\n\n".join(lines)).strip()


def browse_web_content(
    url: str,
    *,
    timeout: float = 30.0,
    max_chars: int = 50_000,
    user_agent: str = "Cerberus/2.0 (+security-agent)",
) -> str:
    if not url or not url.strip():
        return "ERROR: empty url"

    url = url.strip()
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return f"ERROR: only http/https URLs are allowed, got scheme={parsed.scheme!r}"

    headers = {
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,text/plain;q=0.8,*/*;q=0.5",
    }

    try:
        with httpx.Client(timeout=timeout, follow_redirects=True, headers=headers) as client:
            resp = client.get(url)
    except httpx.TimeoutException:
        return f"ERROR: request timed out after {timeout}s for {url}"
    except httpx.HTTPError as exc:
        return f"ERROR: HTTP failure for {url}: {exc}"

    if resp.status_code >= 400:
        return f"ERROR: HTTP {resp.status_code} for {url}\nbody_preview: {resp.text[:500]}"

    content_type = (resp.headers.get("content-type") or "").lower()
    body = resp.text

    if "application/json" in content_type or url.rstrip("/").endswith(".json"):
        text = body
    elif "text/plain" in content_type or "markdown" in content_type:
        text = body
    else:
        if BeautifulSoup is not None:
            try:
                text = _html_to_text_bs(body)
            except Exception:
                text = _html_to_text_regex(body)
        else:
            text = _html_to_text_regex(body)

    truncated = False
    if len(text) > max_chars:
        text = text[:max_chars]
        truncated = True

    header = [
        f"url: {resp.url}",
        f"status: {resp.status_code}",
        f"chars: {len(text)}" + (" (truncated)" if truncated else ""),
        "---",
    ]
    return "\n".join(header + [text])
