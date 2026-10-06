"""Small immutable contracts shared by knowledge retrieval policies."""

from __future__ import annotations

import math
import unicodedata
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from kotaemon.base import RetrievedDocument

RecallBranch = Literal["dense", "lexical"]
RecallStatus = Literal["available", "empty", "unavailable", "error"]


def _require_integer(name: str, value: int, *, minimum: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(
            f"{name} must be an integer greater than or equal to {minimum}"
        )


@dataclass(frozen=True)
class EnrichedQuery:
    original_query: str
    standalone_query: str
    variants: tuple[str, ...]
    reason: str

    def __post_init__(self) -> None:
        if not isinstance(self.original_query, str):
            raise TypeError("original_query must be a string")
        if not isinstance(self.standalone_query, str):
            raise TypeError("standalone_query must be a string")
        if not isinstance(self.reason, str) or not self.reason:
            raise ValueError("reason must be a non-empty string")
        if not isinstance(self.variants, tuple) or not self.variants:
            raise ValueError("variants must be a non-empty tuple")
        if any(not isinstance(variant, str) for variant in self.variants):
            raise TypeError("query variants must be strings")
        if self.variants[0] != self.standalone_query:
            raise ValueError("standalone_query must be the first variant")

        normalized = [
            " ".join(unicodedata.normalize("NFKC", variant).casefold().split())
            for variant in self.variants
        ]
        if len(normalized) != len(set(normalized)):
            raise ValueError("query variants must be unique after normalization")
        original_normalized = " ".join(
            unicodedata.normalize("NFKC", self.original_query).casefold().split()
        )
        if original_normalized not in normalized:
            raise ValueError("query variants must retain the original query")


@dataclass(frozen=True)
class RecallBatch:
    branch: RecallBranch
    query_index: int
    query: str
    documents: tuple[RetrievedDocument, ...]
    status: RecallStatus
    error_type: str | None = None

    def __post_init__(self) -> None:
        if self.branch not in ("dense", "lexical"):
            raise ValueError("branch must be 'dense' or 'lexical'")
        _require_integer("query_index", self.query_index, minimum=0)
        if not isinstance(self.query, str):
            raise TypeError("query must be a string")
        if not isinstance(self.documents, tuple):
            raise TypeError("documents must be a tuple")
        if self.status not in ("available", "empty", "unavailable", "error"):
            raise ValueError("unsupported recall status")
        if self.error_type is not None and not isinstance(self.error_type, str):
            raise TypeError("error_type must be a string or None")


@dataclass(frozen=True)
class RetrievalPolicy:
    enabled: bool = False
    candidate_k: int = 20
    max_fused_candidates: int = 40
    max_variants: int = 3
    dense_weight: float = 1.0
    lexical_weight: float = 1.0
    rrf_k: int = 60

    def __post_init__(self) -> None:
        if not isinstance(self.enabled, bool):
            raise ValueError("enabled must be a bool")
        _require_integer("candidate_k", self.candidate_k, minimum=1)
        _require_integer("max_fused_candidates", self.max_fused_candidates, minimum=1)
        _require_integer("max_variants", self.max_variants, minimum=1)
        _require_integer("rrf_k", self.rrf_k, minimum=0)
        for name in ("dense_weight", "lexical_weight"):
            value = getattr(self, name)
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
            ):
                raise ValueError(f"{name} must be a finite non-negative number")
            finite = isinstance(value, int) or math.isfinite(value)
            if not finite or value < 0:
                raise ValueError(f"{name} must be a finite non-negative number")
