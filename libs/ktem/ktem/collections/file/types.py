from __future__ import annotations

from typing import TypedDict

__all__ = ["IndexSettings"]


class IndexSettings(TypedDict, total=False):
    """Typed settings stored per-index (managed by the index, not the user).

    Both ``embedding`` and ``reranking`` are optional; callers fall
    back to the manager's default when a key is absent.
    """

    embedding: str
    reranking: str
