"""Base types shared by external scanner adapters."""

from __future__ import annotations

import abc
import os
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


FEEDER_SCHEMA = "cerberus.feeder/1"


class FeederAdapter(abc.ABC):
    """A fixed, allowlisted external tool invocation and output parser."""

    name = ""
    executable_names: Sequence[str] = ()
    aliases: Sequence[str] = ()
    output_filename: Optional[str] = None
    accepted_exit_codes = frozenset({0})
    use_filtered_tree = False

    def applicable(
        self, root: str, files: Sequence[str], target: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, str]:
        return bool(files), "Repository contains no files."

    @abc.abstractmethod
    def build_argv(
        self,
        executable: str,
        root: str,
        files: Sequence[str],
        work_dir: str,
        target: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """Return an argv list. Values from repository content must never be commands."""

    @abc.abstractmethod
    def parse(
        self,
        stdout: str,
        stderr: str,
        output: Optional[str],
        root: str,
    ) -> Tuple[List[Dict[str, Any]], Any]:
        """Return tool-shaped findings and sanitized raw evidence."""

    def version_argv(self, executable: str) -> List[str]:
        return [executable, "--version"]

    def staged_files(self, files: Sequence[str]) -> Sequence[str]:
        """Select files copied into an isolated scan tree, when requested."""
        return files

    @staticmethod
    def workflow_files(files: Iterable[str]) -> List[str]:
        return [
            path for path in files
            if path.startswith(".github/workflows/")
            and os.path.splitext(path)[1].lower() in (".yml", ".yaml")
        ]
