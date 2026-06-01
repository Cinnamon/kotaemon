import logging

from .base import BaseCache

logger = logging.getLogger(__name__)

_local_caches = {}


class FileCache(BaseCache):
    """A file-based cache

    A file-based case that persist the cache in to a directory on disk. Suitable for
    different runs in different times to share the same cache.
    """

    def __init__(self, path):
        try:
            import diskcache  # type: ignore
        except ImportError:
            raise ImportError(
                "The diskcache package is required to use the FileBasedCache. "
                "Please run: pip install diskcache"
            )

        path = str(path)
        if path not in _local_caches:
            _local_caches[path] = diskcache.Cache(path)

        self._cache = _local_caches[path]
        self._lock = diskcache.RLock(self._cache, "__lock__")

    def add(self, key, value, timeout=None):
        return self._cache.add(key, value, expire=timeout)

    def get(self, key, default=None):
        return self._cache.get(key, default=default)

    def delete(self, key):
        self._cache.delete(key)

    def set(self, key, value, timeout=None):
        self._cache.set(key, value, expire=timeout)

    def touch(self, key, timeout=None):
        self._cache.touch(key, expire=timeout)

    def clear(self):
        self._cache.clear()

    def close(self):
        self._cache.close()

    def incr(self, key, delta=1):
        return self._cache.incr(key, delta)

    def decr(self, key, delta=1):
        return self._cache.decr(key, delta)

    def __contains__(self, key):
        return key in self._cache

    def __getitem__(self, key):
        return self._cache[key]

    def __setitem__(self, key, value):
        self._cache[key] = value

    def __delitem__(self, key):
        del self._cache[key]

    @property
    def lock(self):
        return self._lock

    def __getstate__(self):
        state = self.__dict__.copy()
        state.pop("_lock")
        return state

    def __setstate__(self, state):
        import diskcache  # type: ignore

        self.__dict__.update(state)
        self._lock = diskcache.RLock(self._cache, "__lock__")

    def get_then_set(self, key, func, default=None):
        with self._lock:
            value = self._cache.get(key, default)
            value = func(value)
            self._cache.set(key, value)
        return value
