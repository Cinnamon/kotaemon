"""Distinct-source retrieval metrics and evidence-anchor coverage helpers."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from .retrieval_eval import (
    EvaluationCase,
    ResolvedCase,
    RunMetrics,
    _result_id,
    _validate_k,
    score_run,
)

if TYPE_CHECKING:
    from kotaemon.base import Document

    from .local_ingest import DraftChunk
    from .local_snapshot import EvidenceAnchor


@dataclass(frozen=True)
class AnchorCoverage:
    """Coverage counts for the supplied reviewed evidence anchors."""

    total_anchors: int
    covered_anchors: int
    unmapped_anchor_ids: tuple[str, ...]
    rate: float | None


@dataclass(frozen=True)
class FinalContextAnchorCoverage:
    """Anchor coverage over exactly the evidence chunks packed for generation."""

    total_anchors: int
    eligible_anchors: int
    covered_anchors: int
    uncovered_anchors: int
    unresolved_anchors: int
    context_chunk_count: int
    rate: float | None
    covered_anchor_ids: tuple[str, ...]
    uncovered_anchor_ids: tuple[str, ...]
    unresolved_anchor_ids: tuple[str, ...]


@dataclass(frozen=True)
class CandidateRecall:
    """Micro-averaged relevant-source recall at a declared candidate cutoff."""

    numerator: int
    denominator: int
    rate: float | None
    candidate_k: int
    query_count: int
    per_query: Mapping[str, Mapping[str, Any]]


def _nonempty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _validate_span(start: Any, end: Any, label: str) -> None:
    if (
        isinstance(start, bool)
        or not isinstance(start, int)
        or isinstance(end, bool)
        or not isinstance(end, int)
        or start < 0
        or end <= start
    ):
        raise ValueError(f"{label} must be a non-empty half-open character span")


def _validate_limit(limit: Any) -> int:
    if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
        raise ValueError("limit must be a positive integer")
    return limit


def _validate_sequence(value: Any, label: str) -> Sequence[Any]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise ValueError(f"{label} must be a sequence")
    return value


def source_ranked_chunks(
    ranked_chunks: Sequence[Document],
    chunk_to_source: Mapping[str, str],
    *,
    limit: int,
) -> tuple[Document, ...]:
    """Keep the first representative chunk for each of the first ``limit`` sources.

    Every candidate is checked before the source window is returned, including
    candidates after the window has filled. This prevents malformed indexed
    relationships from being silently hidden in a result tail.
    """
    _validate_limit(limit)
    chunks = _validate_sequence(ranked_chunks, "ranked_chunks")
    if not isinstance(chunk_to_source, Mapping):
        raise ValueError("chunk_to_source must be a mapping")

    validated: list[tuple[Document, str]] = []
    for chunk in chunks:
        chunk_id = _result_id(chunk)
        try:
            source_id = chunk_to_source[chunk_id]
        except (KeyError, TypeError) as error:
            raise ValueError(
                f"Returned chunk {chunk_id!r} has no indexed Source relationship"
            ) from error
        if not isinstance(source_id, str) or not source_id.strip():
            raise ValueError(
                f"Returned chunk {chunk_id!r} has no indexed Source relationship"
            )
        validated.append((chunk, source_id))

    selected: list[Document] = []
    seen_sources: set[str] = set()
    for chunk, source_id in validated:
        if source_id in seen_sources:
            continue
        seen_sources.add(source_id)
        selected.append(chunk)
        if len(selected) == limit:
            break
    return tuple(selected)


def score_source_run(
    cases: Sequence[ResolvedCase | EvaluationCase],
    results_by_query_id: Mapping[str, Sequence[Document]],
    *,
    k: int,
    chunk_to_source: Mapping[str, str],
) -> RunMetrics:
    """Score source-level judgments over the first ``k`` distinct sources."""
    _validate_k(k)
    if any(case.judgment_level != "source" for case in cases):
        raise ValueError("score_source_run requires source-level cases")

    case_ids = [case.case_id for case in cases]
    if not case_ids:
        raise ValueError("At least one judged case is required")
    if len(case_ids) != len(set(case_ids)):
        raise ValueError("Cases contain a duplicate query ID")
    if not isinstance(results_by_query_id, Mapping):
        raise ValueError("results_by_query_id must be a mapping")
    missing = set(case_ids) - set(results_by_query_id)
    extra = set(results_by_query_id) - set(case_ids)
    if missing:
        raise ValueError(
            f"Missing retrieval results for query ID(s): {sorted(missing)}"
        )
    if extra:
        raise ValueError(f"Unexpected retrieval result query ID(s): {sorted(extra)}")

    projected = {
        case.case_id: source_ranked_chunks(
            results_by_query_id[case.case_id], chunk_to_source, limit=k
        )
        for case in cases
    }
    return score_run(cases, projected, k=k, chunk_to_source=chunk_to_source)


def anchor_coverage(
    anchors: Sequence[EvidenceAnchor], chunks: Sequence[DraftChunk]
) -> AnchorCoverage:
    """Count anchors contained by at least one chunk with matching provenance.

    A chunk must match the anchor's source, source unit, and complete locator,
    and contain its entire non-empty half-open span. Spans split across several
    chunks do not count as covered. Anchor IDs must be non-empty and unique;
    all anchor and chunk spans and provenance IDs are validated before matching.
    """
    anchor_items = _validate_sequence(anchors, "anchors")
    chunk_items = _validate_sequence(chunks, "chunks")

    validated_anchors: list[tuple[str, str, str, Mapping[str, Any], int, int]] = []
    seen_anchor_ids: set[str] = set()
    for anchor in anchor_items:
        anchor_id = _nonempty_string(getattr(anchor, "id", None), "anchor ID")
        if anchor_id in seen_anchor_ids:
            raise ValueError(f"Duplicate anchor ID {anchor_id!r}")
        seen_anchor_ids.add(anchor_id)
        _nonempty_string(getattr(anchor, "query_id", None), "anchor query ID")
        source_id = _nonempty_string(
            getattr(anchor, "source_id", None), "anchor source ID"
        )
        unit_id = _nonempty_string(getattr(anchor, "unit_id", None), "anchor unit ID")
        locator = getattr(anchor, "locator", None)
        if not isinstance(locator, Mapping):
            raise ValueError(f"Anchor {anchor_id!r} locator must be a mapping")
        char_start = getattr(anchor, "char_start", None)
        char_end = getattr(anchor, "char_end", None)
        _validate_span(char_start, char_end, f"Anchor {anchor_id!r} span")
        validated_anchors.append(
            (anchor_id, source_id, unit_id, locator, char_start, char_end)
        )

    validated_chunks: list[tuple[str, str, Mapping[str, Any], int, int]] = []
    seen_chunk_ids: set[str] = set()
    for chunk in chunk_items:
        chunk_id = _nonempty_string(getattr(chunk, "chunk_id", None), "chunk ID")
        if chunk_id in seen_chunk_ids:
            raise ValueError(f"Duplicate chunk ID {chunk_id!r}")
        seen_chunk_ids.add(chunk_id)
        source_id = _nonempty_string(
            getattr(chunk, "source_id", None), "chunk source ID"
        )
        unit_id = _nonempty_string(getattr(chunk, "unit_id", None), "chunk unit ID")
        locator = getattr(chunk, "locator", None)
        if not isinstance(locator, Mapping):
            raise ValueError(f"Chunk {chunk_id!r} locator must be a mapping")
        char_start = getattr(chunk, "char_start", None)
        char_end = getattr(chunk, "char_end", None)
        _validate_span(char_start, char_end, f"Chunk {chunk_id!r} span")
        validated_chunks.append((source_id, unit_id, locator, char_start, char_end))

    unmapped: list[str] = []
    for anchor_id, source_id, unit_id, locator, start, end in validated_anchors:
        covered = any(
            chunk_source == source_id
            and chunk_unit == unit_id
            and chunk_locator == locator
            and chunk_start <= start < end <= chunk_end
            for chunk_source, chunk_unit, chunk_locator, chunk_start, chunk_end in validated_chunks
        )
        if not covered:
            unmapped.append(anchor_id)

    total = len(validated_anchors)
    covered_count = total - len(unmapped)
    return AnchorCoverage(
        total_anchors=total,
        covered_anchors=covered_count,
        unmapped_anchor_ids=tuple(unmapped),
        rate=None if total == 0 else covered_count / total,
    )


def final_context_anchor_coverage(
    anchors: Sequence[EvidenceAnchor],
    *,
    context_chunk_ids: Sequence[str],
    chunks_by_id: Mapping[str, DraftChunk],
    unresolved_offsets: Mapping[str, Any],
) -> FinalContextAnchorCoverage:
    """Measure anchor coverage only against chunks in the final packed payload.

    ``unresolved_offsets`` entries may be ``UnresolvedChunkOffsets`` objects or
    mappings with ``source_id``, ``unit_id``, ``locator``, and ``candidate_spans``.
    An anchor whose location cannot be resolved is reported separately and
    excluded from the coverage denominator.
    """
    anchor_items = _validate_sequence(anchors, "anchors")
    context_items = _validate_sequence(context_chunk_ids, "context_chunk_ids")
    if not isinstance(chunks_by_id, Mapping):
        raise ValueError("chunks_by_id must be a mapping")
    if not isinstance(unresolved_offsets, Mapping):
        raise ValueError("unresolved_offsets must be a mapping")
    normalized_ids = tuple(
        _nonempty_string(value, "context chunk ID") for value in context_items
    )
    if len(normalized_ids) != len(set(normalized_ids)):
        raise ValueError("context_chunk_ids contains duplicate IDs")
    missing = set(normalized_ids) - set(chunks_by_id) - set(unresolved_offsets)
    if missing:
        raise ValueError(
            "Final context contains chunk IDs without reviewed anchor metadata: "
            f"{sorted(missing)}"
        )

    known_chunks = tuple(
        chunks_by_id[chunk_id]
        for chunk_id in normalized_ids
        if chunk_id in chunks_by_id
    )
    known_coverage = anchor_coverage(anchor_items, known_chunks)
    uncovered_candidates = set(known_coverage.unmapped_anchor_ids)
    unresolved_ids: set[str] = set()
    anchors_by_id = {anchor.id: anchor for anchor in anchor_items}
    for anchor_id in uncovered_candidates:
        anchor = anchors_by_id[anchor_id]
        for chunk_id in normalized_ids:
            value = unresolved_offsets.get(chunk_id)
            if value is None:
                continue
            if isinstance(value, Mapping):
                source_id = value.get("source_id")
                unit_id = value.get("unit_id")
                locator = value.get("locator")
                spans = value.get("candidate_spans", ())
            else:
                source_id = getattr(value, "source_id", None)
                unit_id = getattr(value, "unit_id", None)
                locator = getattr(value, "locator", None)
                spans = getattr(value, "candidate_spans", ())
            if (
                source_id != anchor.source_id
                or unit_id != anchor.unit_id
                or locator != anchor.locator
            ):
                continue
            if not isinstance(spans, Sequence) or isinstance(spans, (str, bytes)):
                raise ValueError("candidate_spans must be a sequence of spans")
            if not spans or any(
                isinstance(span, Sequence)
                and not isinstance(span, (str, bytes))
                and len(span) == 2
                and isinstance(span[0], int)
                and isinstance(span[1], int)
                and span[0] <= anchor.char_start < anchor.char_end <= span[1]
                for span in spans
            ):
                unresolved_ids.add(anchor_id)
                break

    covered_ids = tuple(
        anchor.id for anchor in anchor_items if anchor.id not in uncovered_candidates
    )
    unresolved_anchor_ids = tuple(
        anchor.id for anchor in anchor_items if anchor.id in unresolved_ids
    )
    uncovered_ids = tuple(
        anchor.id
        for anchor in anchor_items
        if anchor.id in uncovered_candidates and anchor.id not in unresolved_ids
    )
    covered_count = len(covered_ids)
    uncovered_count = len(uncovered_ids)
    eligible_count = covered_count + uncovered_count
    return FinalContextAnchorCoverage(
        total_anchors=len(anchor_items),
        eligible_anchors=eligible_count,
        covered_anchors=covered_count,
        uncovered_anchors=uncovered_count,
        unresolved_anchors=len(unresolved_anchor_ids),
        context_chunk_count=len(normalized_ids),
        rate=(None if eligible_count == 0 else covered_count / eligible_count),
        covered_anchor_ids=covered_ids,
        uncovered_anchor_ids=uncovered_ids,
        unresolved_anchor_ids=unresolved_anchor_ids,
    )


def score_candidate_recall(
    cases: Sequence[ResolvedCase | EvaluationCase],
    candidate_ids_by_query: Mapping[str, Sequence[str]],
    chunk_to_source: Mapping[str, str],
    *,
    candidate_k: int,
) -> CandidateRecall:
    """Score source recall in the pre-rerank candidate pool at ``candidate_k``."""
    _validate_limit(candidate_k)
    if any(case.judgment_level != "source" for case in cases):
        raise ValueError("score_candidate_recall requires source-level cases")
    case_ids = [case.case_id for case in cases]
    if not case_ids or len(case_ids) != len(set(case_ids)):
        raise ValueError("Candidate recall requires unique, non-empty judged cases")
    if not isinstance(candidate_ids_by_query, Mapping):
        raise ValueError("candidate_ids_by_query must be a mapping")
    if not isinstance(chunk_to_source, Mapping):
        raise ValueError("chunk_to_source must be a mapping")
    missing = set(case_ids) - set(candidate_ids_by_query)
    extra = set(candidate_ids_by_query) - set(case_ids)
    if missing or extra:
        raise ValueError(
            f"Candidate query IDs differ from judgments (missing={sorted(missing)}, "
            f"extra={sorted(extra)})"
        )

    numerator = denominator = 0
    per_query: dict[str, Mapping[str, Any]] = {}
    for case in cases:
        raw_candidates = _validate_sequence(
            candidate_ids_by_query[case.case_id],
            f"candidate IDs for query {case.case_id!r}",
        )
        candidates = raw_candidates[:candidate_k]
        for chunk_id in candidates:
            if not isinstance(chunk_id, str) or not chunk_id.strip():
                raise ValueError("candidate IDs must be non-empty strings")
        unique_candidates = tuple(dict.fromkeys(candidates))
        candidate_sources = []
        for chunk_id in unique_candidates:
            source_id = chunk_to_source.get(chunk_id)
            if not isinstance(source_id, str) or not source_id:
                raise ValueError(
                    f"Candidate chunk {chunk_id!r} has no indexed Source relationship"
                )
            candidate_sources.append(source_id)
        candidate_source_set = set(candidate_sources)
        relevant = set(case.relevant_ids)
        found = tuple(sorted(candidate_source_set & relevant))
        query_numerator = len(found)
        query_denominator = len(relevant)
        numerator += query_numerator
        denominator += query_denominator
        per_query[case.case_id] = {
            "numerator": query_numerator,
            "denominator": query_denominator,
            "rate": (
                None if query_denominator == 0 else query_numerator / query_denominator
            ),
            "candidate_chunk_count": len(unique_candidates),
            "candidate_source_count": len(candidate_source_set),
            "relevant_retrieved_source_ids": list(found),
        }
    return CandidateRecall(
        numerator=numerator,
        denominator=denominator,
        rate=None if denominator == 0 else numerator / denominator,
        candidate_k=candidate_k,
        query_count=len(cases),
        per_query=per_query,
    )
