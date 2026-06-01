from abc import ABC, abstractmethod
from typing import Optional


class BaseStorage(ABC):
    @abstractmethod
    def __init__(self, *args, **kwargs):
        ...

    @abstractmethod
    def open(self, path: str, mode: str, encoding: Optional[str] = None):
        """Open file in storage. Support context manager"""
        ...

    @abstractmethod
    def exists(self, path: str) -> bool:
        """Check if a path exists in storage"""
        ...

    @abstractmethod
    def rm(self, path: str):
        """Remove a path"""
        ...

    @abstractmethod
    def join(self, *paths: str) -> str:
        """Join paths"""
        ...

    @abstractmethod
    def url(self, *paths: str) -> str:
        """Get url of a path"""
        ...
