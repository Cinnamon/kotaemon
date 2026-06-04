"""Explicit registry for reasoning pipeline classes."""

from __future__ import annotations

from enum import Enum

from ktem.reasoning.base import BaseReasoning


class ReasoningKind(str, Enum):
    FULL_QA = "FullQAPipeline"
    FULL_DECOMPOSE_QA = "FullDecomposeQAPipeline"
    REACT = "ReactAgentPipeline"
    REWOO = "RewooAgentPipeline"


_LEGACY_PATH_MAP: dict[str, ReasoningKind] = {
    "ktem.reasoning.simple.FullQAPipeline": ReasoningKind.FULL_QA,
    "ktem.reasoning.simple.FullDecomposeQAPipeline": (ReasoningKind.FULL_DECOMPOSE_QA),
    "ktem.reasoning.react.ReactAgentPipeline": ReasoningKind.REACT,
    "ktem.reasoning.rewoo.RewooAgentPipeline": ReasoningKind.REWOO,
}


def _load_classes() -> dict[ReasoningKind, type[BaseReasoning]]:
    from ktem.reasoning.react import ReactAgentPipeline
    from ktem.reasoning.rewoo import RewooAgentPipeline
    from ktem.reasoning.simple import FullDecomposeQAPipeline, FullQAPipeline

    return {
        ReasoningKind.FULL_QA: FullQAPipeline,
        ReasoningKind.FULL_DECOMPOSE_QA: FullDecomposeQAPipeline,
        ReasoningKind.REACT: ReactAgentPipeline,
        ReasoningKind.REWOO: RewooAgentPipeline,
    }


def get_reasoning_cls(value: str | ReasoningKind) -> type[BaseReasoning]:
    """Resolve a reasoning class from enum value or legacy dotted path."""
    mp = _load_classes()
    if isinstance(value, ReasoningKind):
        return mp[value]
    if value in _LEGACY_PATH_MAP:
        return mp[_LEGACY_PATH_MAP[value]]
    try:
        return mp[ReasoningKind(value)]
    except ValueError as exc:
        raise ValueError(f"Unknown reasoning pipeline: {value!r}") from exc
