"""Local storage shim replacing theflow.storage for promptui."""

from __future__ import annotations

from pathlib import Path
from typing import IO


class PromptUIStorage:
    """Filesystem-backed storage for promptui logs."""

    def url(self, path: str) -> str:
        if path.startswith("file://"):
            return path[7:]
        return path

    def open(self, path: str, mode: str = "r") -> IO:
        return open(self.url(path), mode)


storage = PromptUIStorage()
