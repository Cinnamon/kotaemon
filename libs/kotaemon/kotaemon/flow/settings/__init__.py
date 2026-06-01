"""Settings access for TheFlow runtime."""
from __future__ import annotations

from typing import Any


class _SettingsProxy:
    """Lazy proxy delegating to kotaemon_settings.get_settings()."""

    def __getattr__(self, item: str) -> Any:
        from kotaemon_settings import get_settings

        settings = get_settings()
        if hasattr(type(settings), item):
            return getattr(settings, item)
        extra = getattr(settings, "__pydantic_extra__", None) or {}
        if item in extra:
            return extra[item]
        return getattr(settings, item)


settings = _SettingsProxy()
