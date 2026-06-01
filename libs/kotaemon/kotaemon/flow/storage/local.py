from pathlib import Path
from typing import Optional

from .base import BaseStorage


class LocalStorage(BaseStorage):
    """Local on-disk file storage

    Args:
        prefix: the prefix of the storage
    """

    def __init__(self, prefix: str):
        self._prefix: Path = Path(prefix)
        if not self._prefix.exists():
            self._prefix.mkdir(parents=True)

    def open(self, path: str, mode="rb", encoding: Optional[str] = None):
        parent = (self._prefix / path).parent
        if not parent.exists():
            parent.mkdir(parents=True)
        return open(self._prefix / path, mode=mode, encoding=encoding)

    def exists(self, path: str) -> bool:
        return (self._prefix / path).exists()

    def rm(self, path: str):
        (self._prefix / path).unlink()

    def join(self, *paths: str) -> str:
        return str(Path(*paths))

    def url(self, *paths: str) -> str:
        return str(self._prefix.joinpath(*paths))
