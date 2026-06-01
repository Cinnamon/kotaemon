import threading
from typing import Any, Callable, Optional

from .base import BaseCache


class PyMemcacheCache(BaseCache):
    def __init__(self, servers, **kwargs):
        try:
            import pymemcache  # type: ignore
            import pymemcache.serde  # type: ignore # noqa: F401
        except ImportError:
            raise ImportError(
                "The pymemcache package is required to use the PyMemcacheCache. "
                "Please run: pip install pymemcache"
            )

        self._servers = servers
        self._kwargs = kwargs
        self._caches = {}

    @property
    def _cache(self):
        import pymemcache
        import pymemcache.serde

        ident = threading.get_ident()
        if ident not in self._caches:
            self._caches[ident] = pymemcache.Client(
                self._servers, serde=pymemcache.serde.pickle_serde, **self._kwargs
            )

        return self._caches[ident]

    def add(self, key: str, value: Any, timeout: Optional[int] = None) -> None:
        self._cache.add(key, value, expire=timeout or 0)

    def get(self, key: str, default: Any = None):
        return self._cache.get(key, default)

    def delete(self, key: str) -> None:
        self._cache.delete(key)

    def set(self, key: str, value: Any, timeout: Optional[int] = None) -> None:
        self._cache.set(key, value, expire=timeout or 0)

    def touch(self, key, timeout: Optional[int] = None) -> None:
        self._cache.touch(key, expire=timeout or 0)

    def clear(self) -> None:
        self._cache.flush_all()

    def close(self) -> None:
        self._cache.close()

    def incr(self, key, delta: int = 1) -> int:
        return self._cache.incr(key, delta)  # type: ignore

    def decr(self, key, delta: int = 1) -> int:
        return self._cache.decr(key, delta)  # type: ignore

    def __contains__(self, key: str) -> bool:
        return self._cache.get(key) is not None

    def __getitem__(self, key: str):
        return self._cache.get(key)

    def __setitem__(self, key: str, value: Any):
        self._cache.set(key, value)

    def __delitem__(self, key: str):
        self._cache.delete(key)

    def get_then_set(self, key: str, func: Callable[[Any], Any], default: Any = None):
        for _ in range(20):
            value, cas = self._cache.gets(key, default)
            value = func(value)
            if self._cache.cas(key, value, cas):
                return value

        raise RuntimeError("Key changes very frequently, please try again later")

    def __getstate__(self):
        state = self.__dict__.copy()
        del state["_caches"]
        return state

    def __setstate__(self, state):
        state["_caches"] = {}
        self.__dict__.update(state)
