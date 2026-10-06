"""Whole-unit seed-first packing against an explicit generator budget."""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Literal

from kotaemon.base import RetrievedDocument

from .expansion import EvidenceBundle


def serialize_chat_messages(messages: Sequence[dict]) -> str:
    """Serialize role/content messages in the canonical compact request form."""
    return json.dumps(
        list(messages),
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    )


def _require_integer(name: str, value: int, *, minimum: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(
            f"{name} must be an integer greater than or equal to {minimum}"
        )


@dataclass(frozen=True)
class GenerationBudget:
    model_context: int
    output_reserve: int
    format_reserve: int
    estimated: bool = False

    def __post_init__(self) -> None:
        _require_integer("model_context", self.model_context, minimum=1)
        _require_integer("output_reserve", self.output_reserve, minimum=0)
        _require_integer("format_reserve", self.format_reserve, minimum=0)
        if not isinstance(self.estimated, bool):
            raise ValueError("estimated must be a bool")
        if self.output_reserve + self.format_reserve > self.model_context:
            raise ValueError("output and format reserves exceed model_context")


@dataclass(frozen=True)
class PackedContext:
    documents: tuple[RetrievedDocument, ...]
    token_count: int
    available_tokens: int
    status: Literal["ready", "insufficient_evidence"]
    omitted_ids: tuple[str, ...]
    omission_reasons: tuple[dict, ...] = ()
    request_token_count: int | None = None
    request_tokens_available: int | None = None


def _count_tokens(count_tokens: Callable[[str], int], text: str) -> int:
    value = count_tokens(text)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError("token counter must return a non-negative integer")
    return value


def _document_id(document: RetrievedDocument) -> str | None:
    value = getattr(document, "doc_id", None)
    return value if isinstance(value, str) and value else None


def _omitted_id(document: RetrievedDocument) -> str:
    document_id = _document_id(document)
    return document_id if document_id is not None else ""


def pack_evidence(
    bundle: EvidenceBundle,
    *,
    budget: GenerationBudget,
    count_tokens: Callable[[str], int],
    base_prompt: str,
    render_context: Callable[[Sequence[RetrievedDocument]], str],
    render_budgeted_request: Callable[[str], str] | None = None,
) -> PackedContext:
    """Pack complete rendered units, considering every seed before any neighbor."""
    if not isinstance(bundle, EvidenceBundle):
        raise TypeError("bundle must be an EvidenceBundle")
    if not isinstance(budget, GenerationBudget):
        raise TypeError("budget must be a GenerationBudget")
    if not callable(count_tokens):
        raise TypeError("count_tokens must be callable")
    if not isinstance(base_prompt, str):
        raise TypeError("base_prompt must be a string")
    if not callable(render_context):
        raise TypeError("render_context must be callable")
    if render_budgeted_request is not None and not callable(render_budgeted_request):
        raise TypeError("render_budgeted_request must be callable")

    prompt_tokens = _count_tokens(count_tokens, base_prompt)
    available_tokens = (
        budget.model_context
        - prompt_tokens
        - budget.output_reserve
        - budget.format_reserve
    )
    if available_tokens < 0:
        raise ValueError("base prompt and reserves exceed model_context")
    request_tokens_available = budget.model_context - (
        budget.output_reserve + budget.format_reserve
    )

    def request_token_count(rendered_context: str) -> int | None:
        if render_budgeted_request is None:
            return None
        rendered_request = render_budgeted_request(rendered_context)
        if not isinstance(rendered_request, str):
            raise TypeError("render_budgeted_request must return a string")
        return _count_tokens(count_tokens, rendered_request)

    def fits_budget(rendered_context: str, context_tokens: int) -> bool:
        if context_tokens > available_tokens:
            return False
        request_tokens = request_token_count(rendered_context)
        return (
            request_tokens is None
            or request_tokens <= request_tokens_available
        )

    included: list[RetrievedDocument] = []
    included_seed_ids: set[str] = set()
    included_ids: set[str] = set()
    omitted_ids: list[str] = []
    omission_reasons: list[dict] = []

    def omit(document: RetrievedDocument, reason: str) -> None:
        document_id = _omitted_id(document)
        if document_id and document_id not in omitted_ids:
            omitted_ids.append(document_id)
        omission_reasons.append({"document_id": document_id or None, "reason": reason})

    def try_include(document: RetrievedDocument, *, is_seed: bool) -> None:
        document_id = _document_id(document)
        if document_id is None:
            omit(document, "missing_document_id")
            return
        if document_id in included_ids:
            omit(document, "duplicate_id")
            return

        candidate_documents = (*included, document)
        rendered = render_context(candidate_documents)
        if not isinstance(rendered, str):
            raise TypeError("render_context must return a string")
        candidate_tokens = _count_tokens(count_tokens, rendered)
        if not fits_budget(rendered, candidate_tokens):
            omit(document, "rendered_unit_exceeds_available_tokens")
            return

        included.append(document)
        included_ids.add(document_id)
        if is_seed:
            included_seed_ids.add(document_id)

    for seed in bundle.seeds:
        try_include(seed, is_seed=True)

    if not included_seed_ids:
        for neighbor in bundle.expansions:
            omit(neighbor, "no_seed_fits")
        empty_rendered = render_context(())
        if not isinstance(empty_rendered, str):
            raise TypeError("render_context must return a string")
        empty_token_count = _count_tokens(count_tokens, empty_rendered)
        empty_request_tokens = request_token_count(empty_rendered)
        if empty_token_count > available_tokens or (
            empty_request_tokens is not None
            and empty_request_tokens > request_tokens_available
        ):
            raise ValueError(
                "empty rendered evidence exceeds the available token budget"
            )
        return PackedContext(
            documents=(),
            token_count=empty_token_count,
            available_tokens=available_tokens,
            status="insufficient_evidence",
            omitted_ids=tuple(omitted_ids),
            omission_reasons=tuple(omission_reasons),
            request_token_count=empty_request_tokens,
            request_tokens_available=(
                request_tokens_available
                if render_budgeted_request is not None
                else None
            ),
        )

    for neighbor in bundle.expansions:
        try_include(neighbor, is_seed=False)

    final_rendered = render_context(tuple(included))
    if not isinstance(final_rendered, str):
        raise TypeError("render_context must return a string")
    final_token_count = _count_tokens(count_tokens, final_rendered)
    final_request_tokens = request_token_count(final_rendered)
    if final_token_count > available_tokens or (
        final_request_tokens is not None
        and final_request_tokens > request_tokens_available
    ):
        raise ValueError("final rendered evidence exceeds the available token budget")

    return PackedContext(
        documents=tuple(included),
        token_count=final_token_count,
        available_tokens=available_tokens,
        status="ready",
        omitted_ids=tuple(omitted_ids),
        omission_reasons=tuple(omission_reasons),
        request_token_count=final_request_tokens,
        request_tokens_available=(
            request_tokens_available if render_budgeted_request is not None else None
        ),
    )
