"""External scanner adapters for Cerberus.

The package is intentionally independent from ``examine.py`` so native scans do
not import or execute third-party tools unless the CLI explicitly asks for them.
"""

from .registry import available_feeders, available_names, get_feeder, parse_selection, resolve_feeders
from .runner import FeederRunner, run_feeders, summarize_results

__all__ = [
    "FeederRunner",
    "available_feeders",
    "available_names",
    "get_feeder",
    "parse_selection",
    "resolve_feeders",
    "run_feeders",
    "summarize_results",
]
