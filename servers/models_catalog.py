"""
Model catalog with selectable sections for the Cerberus interactive picker.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional


@dataclass(frozen=True)
class ModelSection:
    title: str
    models: tuple[str, ...]
    blurb: str = ""


# Curated defaults — strong tool-callers first (Cerberus agent sweet spot)
DEFAULT_SECTIONS: tuple[ModelSection, ...] = (
    ModelSection(
        title="Recommended · tool calling",
        blurb="Best defaults for coding & security agents on Pollinations",
        models=("kimi", "deepseek", "openai"),
    ),
    ModelSection(
        title="Local · Ollama / hermes",
        blurb="Point --base-url at localhost:11434/v1",
        models=("hermes", "llama3.1", "qwen2.5-coder", "codellama"),
    ),
    ModelSection(
        title="General · chat & reasoning",
        blurb="Broader models when available on your endpoint",
        models=("mistral", "gemma", "claude", "gpt-4o", "gpt-4.1"),
    ),
)


@dataclass
class CatalogEntry:
    """Flat selectable row with section metadata for display."""

    index: int
    model: str
    section: str
    is_current: bool = False


def build_catalog(
    *,
    current: str,
    configured: Optional[Iterable[str]] = None,
    extra_sections: Optional[list[ModelSection]] = None,
) -> list[CatalogEntry]:
    """
    Build a numbered catalog for the picker.
    """
    rows: list[CatalogEntry] = []
    seen: set[str] = set()
    n = 1

    cfg = [m.strip() for m in (configured or []) if m and str(m).strip()]
    if cfg:
        for m in cfg:
            if m in seen:
                continue
            seen.add(m)
            rows.append(
                CatalogEntry(
                    index=n,
                    model=m,
                    section="Your config",
                    is_current=(m == current),
                )
            )
            n += 1

    sections = list(extra_sections or DEFAULT_SECTIONS)
    for sec in sections:
        for m in sec.models:
            if m in seen:
                continue
            seen.add(m)
            rows.append(
                CatalogEntry(
                    index=n,
                    model=m,
                    section=sec.title,
                    is_current=(m == current),
                )
            )
            n += 1

    # Always ensure current model appears even if unknown
    if current and current not in seen:
        rows.insert(
            0,
            CatalogEntry(
                index=0,
                model=current,
                section="Active",
                is_current=True,
            ),
        )
        for i, row in enumerate(rows, start=1):
            rows[i - 1] = CatalogEntry(
                index=i,
                model=row.model,
                section=row.section,
                is_current=row.is_current,
            )

    return rows


def find_by_index(catalog: list[CatalogEntry], index: int) -> Optional[str]:
    for row in catalog:
        if row.index == index:
            return row.model
    return None


def find_by_name(catalog: list[CatalogEntry], name: str) -> Optional[str]:
    name_l = name.strip().lower()
    for row in catalog:
        if row.model.lower() == name_l:
            return row.model
    if name.strip():
        return name.strip()
    return None
