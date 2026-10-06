"""Versioned offline retrieval fixtures, scoring, and paired-run comparison.

All scores produced here describe the supplied judgments and indexed catalog.
The module deliberately knows nothing about a vector database or query model;
``compare_runs`` accepts two retrieval callables so both can use one fixture and
one real retrieval stack.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any

from kotaemon.indices.knowledge.planning.query_planner import normalize_logical_path
from kotaemon.indices.knowledge.schema import SUPPORTED_SOURCE_TYPES

SCHEMA_VERSION = 1
_CASE_KINDS = {"named", "ambiguous", "legacy", "zero_result"}
_FIELDS = {
    "schema_version",
    "id",
    "query",
    "judgment_level",
    "relevant_ids",
    "disallowed_source_ids",
    "allowed_source_ids",
    "path",
    "source_types",
    "filters",
    "case_kind",
}


@dataclass(frozen=True)
class EvaluationCase:
    """One versioned query judgment as stored in JSONL."""

    case_id: str
    query: str
    judgment_level: str
    relevant_ids: tuple[str, ...]
    disallowed_source_ids: tuple[str, ...] | None = None
    allowed_source_ids: tuple[str, ...] | None = None
    path: str | None = None
    source_types: tuple[str, ...] | None = None
    filters: Mapping[str, str] | None = None
    case_kind: str | None = None


@dataclass(frozen=True)
class EvaluationFixture:
    schema_version: int
    cases: tuple[EvaluationCase, ...]
    source_path: str | None = None


@dataclass(frozen=True)
class IndexedCatalog:
    """Immutable canonical ID relations used to resolve fixture judgments."""

    source_ids: frozenset[str]
    chunk_to_source: Mapping[str, str]

    def __init__(self, source_ids: Iterable[str], chunk_to_source: Mapping[str, str]):
        normalized_sources = frozenset(
            _nonempty_id(value, "Source ID") for value in source_ids
        )
        normalized_chunks: dict[str, str] = {}
        for chunk_id, source_id in chunk_to_source.items():
            chunk = _nonempty_id(chunk_id, "chunk ID")
            source = _nonempty_id(source_id, f"Source relation for chunk {chunk!r}")
            if source not in normalized_sources:
                raise ValueError(
                    f"Chunk {chunk!r} points to unknown Source ID {source!r}"
                )
            normalized_chunks[chunk] = source
        object.__setattr__(self, "source_ids", normalized_sources)
        object.__setattr__(self, "chunk_to_source", MappingProxyType(normalized_chunks))


@dataclass(frozen=True)
class ResolvedCase:
    """A fixture case whose judgments have been checked against the index."""

    case_id: str
    query: str
    judgment_level: str
    relevant_ids: tuple[str, ...]
    disallowed_source_ids: tuple[str, ...] | None
    allowed_source_ids: tuple[str, ...] | None
    path: str | None
    source_types: tuple[str, ...] | None
    filters: Mapping[str, str] | None
    case_kind: str | None

    def to_dict(self) -> dict[str, Any]:
        """Export the frozen canonical judgment used by both comparison arms."""
        return {
            "schema_version": SCHEMA_VERSION,
            "id": self.case_id,
            "query": self.query,
            "judgment_level": self.judgment_level,
            "relevant_ids": list(self.relevant_ids),
            "disallowed_source_ids": (
                None
                if self.disallowed_source_ids is None
                else list(self.disallowed_source_ids)
            ),
            "allowed_source_ids": (
                None
                if self.allowed_source_ids is None
                else list(self.allowed_source_ids)
            ),
            "path": self.path,
            "source_types": (
                None if self.source_types is None else list(self.source_types)
            ),
            "filters": None if self.filters is None else dict(self.filters),
            "case_kind": self.case_kind,
        }


@dataclass(frozen=True)
class QueryMetrics:
    case_id: str
    hit_at_k: float
    recall_at_k: float
    reciprocal_rank_at_k: float
    result_ids: tuple[str, ...]
    relevant_retrieved_ids: tuple[str, ...]
    first_relevant_rank: int | None
    raw_result_count: int
    unique_result_count: int
    duplicate_result_count: int
    wrong_scope_numerator: int
    wrong_scope_denominator: int
    wrong_scope_rate: float | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.case_id,
            "hit_at_k": self.hit_at_k,
            "recall_at_k": self.recall_at_k,
            "reciprocal_rank_at_k": self.reciprocal_rank_at_k,
            "result_ids": list(self.result_ids),
            "relevant_retrieved_ids": list(self.relevant_retrieved_ids),
            "first_relevant_rank": self.first_relevant_rank,
            "raw_result_count": self.raw_result_count,
            "unique_result_count": self.unique_result_count,
            "duplicate_result_count": self.duplicate_result_count,
            "wrong_scope_numerator": self.wrong_scope_numerator,
            "wrong_scope_denominator": self.wrong_scope_denominator,
            "wrong_scope_rate": self.wrong_scope_rate,
        }


@dataclass(frozen=True)
class RunMetrics:
    k: int
    per_query: tuple[QueryMetrics, ...]
    hit_at_k: float
    recall_at_k: float
    mrr_at_k: float
    wrong_scope_at_k: float | None
    judged_query_count: int
    scope_labeled_query_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "k": self.k,
            "hit_at_k": self.hit_at_k,
            "recall_at_k": self.recall_at_k,
            "mrr_at_k": self.mrr_at_k,
            "wrong_scope_at_k": self.wrong_scope_at_k,
            "judged_query_count": self.judged_query_count,
            "scope_labeled_query_count": self.scope_labeled_query_count,
            "per_query": [metric.to_dict() for metric in self.per_query],
        }


@dataclass(frozen=True)
class CaseObservation:
    case_id: str
    result_ids: tuple[str, ...]
    planner_status: str | None = None
    fallback_reason: str | None = None
    candidate_k: int | None = None
    vector_statuses: tuple[str, ...] = ()
    lexical_statuses: tuple[str, ...] = ()
    trace_artifact_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.case_id,
            "result_ids": list(self.result_ids),
            "planner_status": self.planner_status,
            "fallback_reason": self.fallback_reason,
            "candidate_k": self.candidate_k,
            "vector_statuses": list(self.vector_statuses),
            "lexical_statuses": list(self.lexical_statuses),
            "trace_artifact_path": self.trace_artifact_path,
        }


@dataclass(frozen=True)
class Comparison:
    baseline: RunMetrics
    planned: RunMetrics
    config_fingerprint: str
    baseline_config: Mapping[str, Any]
    planned_config: Mapping[str, Any]
    baseline_observations: tuple[CaseObservation, ...] = field(default_factory=tuple)
    planned_observations: tuple[CaseObservation, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "config_fingerprint": self.config_fingerprint,
            "baseline_config": dict(self.baseline_config),
            "planned_config": dict(self.planned_config),
            "baseline": self.baseline.to_dict(),
            "planned": self.planned.to_dict(),
            "baseline_observations": [
                observation.to_dict() for observation in self.baseline_observations
            ],
            "planned_observations": [
                observation.to_dict() for observation in self.planned_observations
            ],
        }


def _nonempty_id(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


def _string_id_list(
    value: Any, label: str, *, allow_none: bool
) -> tuple[str, ...] | None:
    if value is None and allow_none:
        return None
    if not isinstance(value, list):
        raise ValueError(f"{label} must be a list" + (" or null" if allow_none else ""))
    result = tuple(_nonempty_id(item, label) for item in value)
    if len(result) != len(set(result)):
        duplicate_label = "relevant ID" if label == "relevant_ids" else "ID"
        raise ValueError(f"{label} contains a duplicate {duplicate_label}")
    return result


def _parse_case(row: Any, line_number: int) -> EvaluationCase:
    if not isinstance(row, Mapping):
        raise ValueError(f"Line {line_number}: each JSONL value must be an object")
    unknown = set(row) - _FIELDS
    if unknown:
        raise ValueError(
            f"Line {line_number}: unsupported fixture field(s): {sorted(unknown)}"
        )
    version = row.get("schema_version")
    if isinstance(version, bool) or version != SCHEMA_VERSION:
        raise ValueError(
            f"Line {line_number}: unsupported schema_version {version!r}; "
            f"expected {SCHEMA_VERSION}"
        )
    case_id = _nonempty_id(row.get("id"), f"Line {line_number} query ID")
    query = _nonempty_id(row.get("query"), f"Query {case_id!r} query")
    level = row.get("judgment_level")
    if level not in {"chunk", "source"}:
        raise ValueError(
            f"Query {case_id!r}: judgment_level must be 'chunk' or 'source'"
        )
    relevant = _string_id_list(
        row.get("relevant_ids"), "relevant_ids", allow_none=False
    )
    if not relevant:
        raise ValueError(f"Query {case_id!r}: at least one relevant ID is required")

    disallowed = _string_id_list(
        row.get("disallowed_source_ids"), "disallowed_source_ids", allow_none=True
    )
    allowed = _string_id_list(
        row.get("allowed_source_ids"), "allowed_source_ids", allow_none=True
    )

    raw_path = row.get("path")
    if raw_path is not None:
        path = normalize_logical_path(raw_path)
    else:
        path = None

    raw_types = row.get("source_types")
    if raw_types is None:
        source_types = None
    else:
        source_types = _string_id_list(raw_types, "source_types", allow_none=False)
        normalized_types = tuple(
            sorted({item.strip().lower() for item in source_types})
        )
        unsupported = sorted(set(normalized_types) - set(SUPPORTED_SOURCE_TYPES))
        if unsupported:
            raise ValueError(
                f"Query {case_id!r}: unsupported source type(s): {unsupported}"
            )
        source_types = normalized_types

    raw_filters = row.get("filters")
    if raw_filters is None:
        filters = None
    elif not isinstance(raw_filters, Mapping):
        raise ValueError(f"Query {case_id!r}: filters must be an object")
    else:
        filters = {}
        for key, value in raw_filters.items():
            normalized_key = key.strip() if isinstance(key, str) else ""
            if not normalized_key:
                raise ValueError(
                    f"Query {case_id!r}: filter keys must be non-empty strings"
                )
            if not isinstance(value, (str, int, float, bool)) or value == "":
                raise ValueError(
                    f"Query {case_id!r}: filter values must be scalar values"
                )
            filters[normalized_key] = str(value).strip()
            if not filters[normalized_key]:
                raise ValueError(f"Query {case_id!r}: filter values must be non-empty")

    case_kind = row.get("case_kind")
    if case_kind is not None and case_kind not in _CASE_KINDS:
        raise ValueError(f"Query {case_id!r}: unsupported case_kind {case_kind!r}")

    return EvaluationCase(
        case_id=case_id,
        query=query,
        judgment_level=level,
        relevant_ids=relevant,
        disallowed_source_ids=disallowed,
        allowed_source_ids=allowed,
        path=path,
        source_types=source_types,
        filters=filters,
        case_kind=case_kind,
    )


def load_fixture(path: str | Path) -> EvaluationFixture:
    """Load and structurally validate a UTF-8, version 1 JSONL fixture."""
    source_path = Path(path)
    cases: list[EvaluationCase] = []
    try:
        with source_path.open("r", encoding="utf-8") as fixture_file:
            for line_number, line in enumerate(fixture_file, 1):
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError as error:
                    raise ValueError(
                        f"Line {line_number}: invalid JSON: {error.msg}"
                    ) from error
                cases.append(_parse_case(row, line_number))
    except UnicodeDecodeError as error:
        raise ValueError("Fixture must be valid UTF-8 JSONL") from error
    if not cases:
        raise ValueError("Fixture must contain at least one judged query")
    ids = [case.case_id for case in cases]
    if len(ids) != len(set(ids)):
        raise ValueError("Fixture contains a duplicate query ID")
    levels = {case.judgment_level for case in cases}
    if len(levels) > 1:
        raise ValueError("Fixture cannot contain mixed judgment levels")
    return EvaluationFixture(
        schema_version=SCHEMA_VERSION,
        cases=tuple(cases),
        source_path=str(source_path),
    )


def resolve_judgments(
    fixture: EvaluationFixture, indexed_catalog: IndexedCatalog
) -> tuple[ResolvedCase, ...]:
    """Check all labels against one immutable index before any retrieval runs."""
    if not isinstance(indexed_catalog, IndexedCatalog):
        raise TypeError("indexed_catalog must be an IndexedCatalog")
    resolved: list[ResolvedCase] = []
    for case in fixture.cases:
        if case.judgment_level == "chunk":
            for chunk_id in case.relevant_ids:
                if chunk_id not in indexed_catalog.chunk_to_source:
                    raise ValueError(
                        f"Query {case.case_id!r}: Unknown chunk ID {chunk_id!r}"
                    )
        else:
            for source_id in case.relevant_ids:
                if source_id not in indexed_catalog.source_ids:
                    raise ValueError(
                        f"Query {case.case_id!r}: Unknown Source ID {source_id!r}"
                    )

        for label, source_ids in (
            ("disallowed", case.disallowed_source_ids),
            ("allowed", case.allowed_source_ids),
        ):
            if source_ids is None:
                continue
            for source_id in source_ids:
                if source_id not in indexed_catalog.source_ids:
                    raise ValueError(
                        f"Query {case.case_id!r}: Unknown {label} Source ID "
                        f"{source_id!r}"
                    )

        resolved.append(
            ResolvedCase(
                case_id=case.case_id,
                query=case.query,
                judgment_level=case.judgment_level,
                relevant_ids=case.relevant_ids,
                disallowed_source_ids=case.disallowed_source_ids,
                allowed_source_ids=case.allowed_source_ids,
                path=case.path,
                source_types=case.source_types,
                filters=(
                    None
                    if case.filters is None
                    else MappingProxyType(dict(case.filters))
                ),
                case_kind=case.case_kind,
            )
        )
    return tuple(resolved)


def _validate_k(k: int) -> int:
    if isinstance(k, bool) or not isinstance(k, int) or k <= 0:
        raise ValueError("k must be a positive integer")
    return k


def _result_id(item: Any) -> str:
    if isinstance(item, str):
        return _nonempty_id(item, "result chunk ID")
    value = getattr(item, "doc_id", None)
    if value is None:
        value = getattr(item, "id_", None)
    return _nonempty_id(value, "result chunk ID")


def score_case(
    case: ResolvedCase | EvaluationCase,
    ranked_chunk_ids: Sequence[Any],
    *,
    k: int,
    chunk_to_source: Mapping[str, str],
) -> QueryMetrics:
    """Score one case over the raw first-K result window.

    Duplicate IDs are removed for Hit/Recall/Wrong-scope counts, while MRR uses
    the original one-based rank. Thus a duplicate result cannot move a later
    relevant ID toward the front.
    """
    k = _validate_k(k)
    if isinstance(ranked_chunk_ids, (str, bytes)) or not isinstance(
        ranked_chunk_ids, Sequence
    ):
        raise ValueError("ranked_chunk_ids must be a sequence of chunk IDs")
    raw_ids = [_result_id(item) for item in ranked_chunk_ids]
    for chunk_id in raw_ids:
        if chunk_id not in chunk_to_source:
            raise ValueError(
                f"Returned chunk {chunk_id!r} has no indexed Source relationship"
            )
        source_id = chunk_to_source[chunk_id]
        if not isinstance(source_id, str) or not source_id:
            raise ValueError(
                f"Returned chunk {chunk_id!r} has no indexed Source relationship"
            )

    window = raw_ids[:k]
    unique_window = tuple(dict.fromkeys(window))
    if case.judgment_level == "chunk":
        retrieved_units = unique_window
        relevant_set = set(case.relevant_ids)
    elif case.judgment_level == "source":
        retrieved_units = tuple(
            dict.fromkeys(chunk_to_source[chunk_id] for chunk_id in unique_window)
        )
        relevant_set = set(case.relevant_ids)
    else:
        raise ValueError(f"Unsupported judgment level {case.judgment_level!r}")

    relevant_retrieved = tuple(unit for unit in retrieved_units if unit in relevant_set)
    relevant_rank = next(
        (
            index
            for index, chunk_id in enumerate(window, 1)
            if (
                chunk_id in relevant_set
                if case.judgment_level == "chunk"
                else chunk_to_source[chunk_id] in relevant_set
            )
        ),
        None,
    )
    denominator = len(case.relevant_ids)
    wrong_scope_numerator = 0
    wrong_scope_denominator = 0
    wrong_scope_rate: float | None = None
    if case.disallowed_source_ids is not None:
        disallowed = set(case.disallowed_source_ids)
        wrong_scope_denominator = len(unique_window)
        wrong_scope_numerator = sum(
            chunk_to_source[chunk_id] in disallowed for chunk_id in unique_window
        )
        if wrong_scope_denominator:
            wrong_scope_rate = wrong_scope_numerator / wrong_scope_denominator

    return QueryMetrics(
        case_id=case.case_id,
        hit_at_k=float(bool(relevant_retrieved)),
        recall_at_k=len(relevant_retrieved) / denominator,
        reciprocal_rank_at_k=(0.0 if relevant_rank is None else 1 / relevant_rank),
        result_ids=unique_window,
        relevant_retrieved_ids=relevant_retrieved,
        first_relevant_rank=relevant_rank,
        raw_result_count=len(window),
        unique_result_count=len(unique_window),
        duplicate_result_count=len(window) - len(unique_window),
        wrong_scope_numerator=wrong_scope_numerator,
        wrong_scope_denominator=wrong_scope_denominator,
        wrong_scope_rate=wrong_scope_rate,
    )


def score_run(
    cases: Sequence[ResolvedCase | EvaluationCase],
    results_by_query_id: Mapping[str, Sequence[Any]],
    *,
    k: int,
    chunk_to_source: Mapping[str, str],
) -> RunMetrics:
    """Score all judged cases using macro Hit/Recall/MRR and pooled scope rate."""
    k = _validate_k(k)
    case_ids = [case.case_id for case in cases]
    if not case_ids:
        raise ValueError("At least one judged case is required")
    if len(case_ids) != len(set(case_ids)):
        raise ValueError("Cases contain a duplicate query ID")
    missing = set(case_ids) - set(results_by_query_id)
    extra = set(results_by_query_id) - set(case_ids)
    if missing:
        raise ValueError(
            f"Missing retrieval results for query ID(s): {sorted(missing)}"
        )
    if extra:
        raise ValueError(f"Unexpected retrieval result query ID(s): {sorted(extra)}")
    per_query = tuple(
        score_case(
            case,
            results_by_query_id[case.case_id],
            k=k,
            chunk_to_source=chunk_to_source,
        )
        for case in cases
    )
    count = len(per_query)
    scope_queries = sum(case.disallowed_source_ids is not None for case in cases)
    scope_numerator = sum(metric.wrong_scope_numerator for metric in per_query)
    scope_denominator = sum(metric.wrong_scope_denominator for metric in per_query)
    return RunMetrics(
        k=k,
        per_query=per_query,
        hit_at_k=sum(metric.hit_at_k for metric in per_query) / count,
        recall_at_k=sum(metric.recall_at_k for metric in per_query) / count,
        mrr_at_k=sum(metric.reciprocal_rank_at_k for metric in per_query) / count,
        wrong_scope_at_k=(
            scope_numerator / scope_denominator if scope_denominator else None
        ),
        judged_query_count=count,
        scope_labeled_query_count=scope_queries,
    )


def _json_config(config: Mapping[str, Any], arm: str) -> dict[str, Any]:
    if not isinstance(config, Mapping):
        raise ValueError(f"{arm}_config must be a mapping")
    try:
        # A JSON round trip also prevents a later caller mutation from changing
        # the fingerprint or the reviewable configuration snapshot.
        encoded = json.dumps(
            config, sort_keys=True, ensure_ascii=False, allow_nan=False
        )
        return json.loads(encoded)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{arm}_config must contain finite JSON values") from error


def _case_observation(
    case: EvaluationCase, result_ids: tuple[str, ...], trace: Any
) -> CaseObservation:
    if trace is None:
        return CaseObservation(case_id=case.case_id, result_ids=result_ids)
    snapshot = trace.to_dict() if callable(getattr(trace, "to_dict", None)) else {}
    plan = snapshot.get("plan")
    if isinstance(plan, Mapping) and "source_ids" in plan:
        planner_status = (
            "global"
            if plan["source_ids"] is None
            else ("empty" if not plan["source_ids"] else "scoped")
        )
    else:
        planner_status = None
    attempts = snapshot.get("attempts", ())
    vector_statuses = tuple(
        str(attempt["vector_status"])
        for attempt in attempts
        if isinstance(attempt, Mapping) and attempt.get("vector_status") is not None
    )
    lexical_statuses = tuple(
        str(attempt["lexical_status"])
        for attempt in attempts
        if isinstance(attempt, Mapping) and attempt.get("lexical_status") is not None
    )
    trace_path = getattr(trace, "artifact_path", None)
    return CaseObservation(
        case_id=case.case_id,
        result_ids=result_ids,
        planner_status=planner_status,
        fallback_reason=snapshot.get("scope_fallback_reason"),
        candidate_k=snapshot.get("candidate_k"),
        vector_statuses=vector_statuses,
        lexical_statuses=lexical_statuses,
        trace_artifact_path=(str(trace_path) if trace_path is not None else None),
    )


def _returned_ids(result: Any, case_id: str, arm: str) -> tuple[str, ...]:
    if result is None or isinstance(result, (str, bytes)):
        raise ValueError(f"{arm} search returned no result sequence for {case_id!r}")
    if not isinstance(result, Sequence):
        raise ValueError(f"{arm} search returned a non-sequence for {case_id!r}")
    return tuple(_result_id(item) for item in result)


def compare_runs(
    cases: Sequence[ResolvedCase | EvaluationCase],
    *,
    search_baseline: Callable[..., Sequence[Any]],
    search_planned: Callable[..., Sequence[Any]],
    k: int,
    chunk_to_source: Mapping[str, str],
    baseline_config: Mapping[str, Any],
    planned_config: Mapping[str, Any],
    trace_factory: Callable[[str, EvaluationCase], Any] | None = None,
) -> Comparison:
    """Run the same cases in order through two matching retrieval configs.

    The only permitted configuration difference is the injected planner.
    Actual candidate-k values and branch statuses are captured from each trace
    so callers can review backend behavior alongside the synthetic metrics.
    """
    k = _validate_k(k)
    if not cases:
        raise ValueError("At least one judged case is required")
    baseline_snapshot = _json_config(baseline_config, "baseline")
    planned_snapshot = _json_config(planned_config, "planned")
    baseline_shared = dict(baseline_snapshot)
    planned_shared = dict(planned_snapshot)
    if "planner" not in baseline_shared or "planner" not in planned_shared:
        raise ValueError("Both run configs must declare planner")
    baseline_planner = baseline_shared.pop("planner")
    planned_planner = planned_shared.pop("planner")
    if baseline_planner == planned_planner:
        raise ValueError(
            "Baseline and planned configs must identify different planners"
        )
    if baseline_shared != planned_shared:
        raise ValueError("baseline/planned configuration differs outside planner")

    baseline_results: dict[str, tuple[str, ...]] = {}
    planned_results: dict[str, tuple[str, ...]] = {}
    baseline_observations: list[CaseObservation] = []
    planned_observations: list[CaseObservation] = []
    for case in cases:
        baseline_trace = trace_factory("baseline", case) if trace_factory else None
        baseline_output = search_baseline(case, trace=baseline_trace)
        baseline_ids = _returned_ids(baseline_output, case.case_id, "baseline")
        baseline_results[case.case_id] = baseline_ids
        baseline_observations.append(
            _case_observation(case, baseline_ids, baseline_trace)
        )

        planned_trace = trace_factory("planned", case) if trace_factory else None
        planned_output = search_planned(case, trace=planned_trace)
        planned_ids = _returned_ids(planned_output, case.case_id, "planned")
        planned_results[case.case_id] = planned_ids
        planned_observations.append(_case_observation(case, planned_ids, planned_trace))

    expected_candidate_k = baseline_shared.get("candidate_k")
    if trace_factory is not None:
        for case, before, after in zip(
            cases, baseline_observations, planned_observations
        ):
            if expected_candidate_k is not None:
                for arm, observation in (
                    ("baseline", before),
                    ("planned", after),
                ):
                    if observation.candidate_k is None:
                        raise ValueError(
                            f"Missing observed candidate_k for {arm} query "
                            f"{case.case_id!r}"
                        )
                    if observation.candidate_k != expected_candidate_k:
                        raise ValueError(
                            f"Observed candidate_k does not match shared config "
                            f"for {arm} query {case.case_id!r}"
                        )
            if before.candidate_k is not None and after.candidate_k is not None:
                if before.candidate_k != after.candidate_k:
                    raise ValueError(
                        f"Observed candidate_k differs for query {case.case_id!r}"
                    )

    fingerprint_payload = {
        "baseline": baseline_snapshot,
        "planned": planned_snapshot,
    }
    fingerprint = hashlib.sha256(
        json.dumps(
            fingerprint_payload,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    return Comparison(
        baseline=score_run(
            cases, baseline_results, k=k, chunk_to_source=chunk_to_source
        ),
        planned=score_run(cases, planned_results, k=k, chunk_to_source=chunk_to_source),
        config_fingerprint=fingerprint,
        baseline_config=MappingProxyType(baseline_snapshot),
        planned_config=MappingProxyType(planned_snapshot),
        baseline_observations=tuple(baseline_observations),
        planned_observations=tuple(planned_observations),
    )


__all__ = [
    "CaseObservation",
    "Comparison",
    "EvaluationCase",
    "EvaluationFixture",
    "IndexedCatalog",
    "QueryMetrics",
    "ResolvedCase",
    "RunMetrics",
    "compare_runs",
    "load_fixture",
    "resolve_judgments",
    "score_case",
    "score_run",
]
