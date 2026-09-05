"""Fixed feeder registry and selection parsing."""

from .actionlint import ActionlintAdapter
from .gitleaks import GitleaksAdapter
from .osv_scanner import OsvScannerAdapter
from .scorecard import ScorecardAdapter
from .zizmor import ZizmorAdapter


_ADAPTERS = tuple(cls() for cls in (
    GitleaksAdapter, OsvScannerAdapter, ZizmorAdapter, ScorecardAdapter, ActionlintAdapter
))
_BY_NAME = {}
for _adapter in _ADAPTERS:
    _BY_NAME[_adapter.name] = _adapter
    for _alias in _adapter.aliases:
        _BY_NAME[_alias] = _adapter


def available_feeders():
    return tuple(adapter.name for adapter in _ADAPTERS)


def available_names():
    """Return the stable canonical names accepted by ``--feeders``."""
    return available_feeders()


def get_feeder(name):
    try:
        return _BY_NAME[name.strip().lower()]
    except KeyError as exc:
        raise ValueError("Unknown feeder {!r}; choose from {}".format(
            name, ", ".join(available_feeders()))) from exc


def resolve_feeders(selection="auto"):
    if selection is None or selection is True:
        selection = "auto"
    if isinstance(selection, str):
        names = [part.strip().lower() for part in selection.split(",") if part.strip()]
    else:
        names = [str(part).strip().lower() for part in selection]
    if not names or names in (["none"], ["off"]):
        return []
    if "auto" in names:
        if len(names) != 1:
            raise ValueError("'auto' cannot be combined with explicit feeder names")
        return list(_ADAPTERS)
    resolved = []
    seen = set()
    for name in names:
        adapter = get_feeder(name)
        if adapter.name not in seen:
            resolved.append(adapter)
            seen.add(adapter.name)
    return resolved


def parse_selection(value="auto"):
    """Validate a CLI selection and return canonical feeder names."""
    return [adapter.name for adapter in resolve_feeders(value)]
