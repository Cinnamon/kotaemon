import abc
from typing import Any, Callable, Optional


class BaseCache(abc.ABC):
    @abc.abstractmethod
    def __init__(self, *args, **kwargs):
        """Initialize the cache"""
        ...

    @abc.abstractmethod
    def add(self, key: str, value: Any, timeout: Optional[int] = None) -> None:
        """Add a key/value pair to the cache if it doesn't already exist

        If the key already exists, this method will do nothing.

        Args:
            key: the name of the key to add
            value: the value to add
            timeout: the number of seconds to keep the key in the cache
        """
        ...

    @abc.abstractmethod
    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from the cache

        Args:
            key: the name of the key to get
            default: the value to return if the key doesn't exist

        Returns:
            The value of the key, or the default value if the key doesn't exist
        """
        ...

    @abc.abstractmethod
    def delete(self, key: str) -> None:
        """Delete a key from the cache

        Args:
            key: the name of the key to delete
        """
        ...

    @abc.abstractmethod
    def set(self, key: str, value: Any, timeout: Optional[int] = None) -> None:
        """Set a key/value pair in the cache

        If the key already exists, its value will be overwritten.

        Args:
            key: the name of the key to set
            value: the value to set
            timeout: the number of seconds to keep the key in the cache
        """
        ...

    @abc.abstractmethod
    def touch(self, key: str, timeout: Optional[int] = None) -> None:
        """Update the timeout for a key

        Args:
            key: the name of the key to update
            timeout: the number of seconds to keep the key in the cache
        """
        ...

    @abc.abstractmethod
    def clear(self) -> None:
        """Clear all keys from the cache"""
        ...

    @abc.abstractmethod
    def close(self) -> None:
        """Close the cache"""
        ...

    @abc.abstractmethod
    def incr(self, key: str, delta: int = 1) -> int:
        """Increment a key's value

        Args:
            key: the name of the key to increment
            delta: the amount to increment the key's value by
        """
        ...

    @abc.abstractmethod
    def decr(self, key: str, delta: int = 1) -> int:
        """Decrement a key's value

        Args:
            key: the name of the key to decrement
            delta: the amount to decrement the key's value by

        Returns:
            The new value of the key
        """
        ...

    @abc.abstractmethod
    def __contains__(self, key: str) -> bool:
        """Check if a key exists in the cache

        Args:
            key: the name of the key to check

        Returns:
            True if the key exists, False otherwise
        """
        ...

    @abc.abstractmethod
    def __getitem__(self, key: str) -> Any:
        """Get a value from the cache

        Args:
            key: the name of the key to get

        Returns:
            The value of the key
        """
        ...

    @abc.abstractmethod
    def __setitem__(self, key: str, value: Any) -> None:
        """Set a key/value pair in the cache

        If the key already exists, its value will be overwritten.

        Args:
            key: the name of the key to set
            value: the value to set
        """
        ...

    @abc.abstractmethod
    def __delitem__(self, key: str) -> None:
        """Delete a key from the cache

        Args:
            key: the name of the key to delete
        """
        ...

    @abc.abstractmethod
    def get_then_set(self, key: str, func: Callable[[Any], Any], default: Any = None):
        """Get a value from the cache, and then set the value, avoiding race conditions

        Args:
            key: the name of the key to get
            func: a function to call to get the updated value
            default: the value to return if the key doesn't exist

        Returns:
            The value of the key, updated to cache
        """
        ...
