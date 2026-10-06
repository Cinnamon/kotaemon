"""Serializable output produced by deterministic knowledge query planning."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class RetrievalPlan:
    """A query plus any exact, resolved source constraints.

    ``source_ids=None`` means the planner found no unambiguous source scope and
    the caller may search globally within its own visible-source boundary.
    ``source_ids=()`` is an explicit empty scope and must never be broadened.
    """

    query: str
    semantic_query: str
    source_types: tuple[str, ...] = ()
    virtual_paths: tuple[str, ...] = ()
    metadata_filters: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    reason: str = ""
    source_ids: tuple[str, ...] | None = None

    @property
    def is_scoped(self) -> bool:
        return self.source_ids is not None

    def to_dict(self) -> dict[str, Any]:
        """Return JSON-compatible values with tuple fields represented as lists."""
        return {
            "query": self.query,
            "semantic_query": self.semantic_query,
            "source_types": list(self.source_types),
            "virtual_paths": list(self.virtual_paths),
            "metadata_filters": dict(self.metadata_filters),
            "confidence": self.confidence,
            "reason": self.reason,
            "source_ids": None if self.source_ids is None else list(self.source_ids),
        }
