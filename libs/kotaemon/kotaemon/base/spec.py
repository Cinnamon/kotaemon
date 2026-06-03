"""Serialization helpers replacing theflow.utils.modules.serialize."""

from __future__ import annotations

from typing import Any


def spec_value(value: Any) -> Any:
    """Return a JSON-friendly value for runtime spec dicts."""
    if isinstance(value, (str, int, float, bool, type(None))):
        return value
    if isinstance(value, dict):
        return {str(k): spec_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [spec_value(v) for v in value]
    raise TypeError(f"Cannot serialize value of type {type(value)!r}")
