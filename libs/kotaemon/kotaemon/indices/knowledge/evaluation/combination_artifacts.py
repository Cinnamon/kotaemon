"""Stable report models, canonical fingerprints, and artifact readers."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .source_metrics import CandidateRecall, FinalContextAnchorCoverage


@dataclass(frozen=True)
class CombinationArmReport:
    component_config: Mapping[str, Any]
    config_fingerprint: str
    source_metrics: Any
    candidate_recall: CandidateRecall
    final_context_anchor_coverage: FinalContextAnchorCoverage
    candidate_chunk_ids: Mapping[str, tuple[str, ...]]
    final_result_ids: Mapping[str, tuple[str, ...]]
    packed_context_ids: Mapping[str, tuple[str, ...]]
    packed_context_chunk_counts: Mapping[str, int]
    stage_durations_ms: Mapping[str, tuple[float, ...]]
    latency_percentiles_ms: Mapping[str, Mapping[str, float | int | None]]
    token_usage: Mapping[str, Any]
    route_statuses: Mapping[str, Any]
    invariants: Mapping[str, Any]
    trace_artifacts: Mapping[str, str]


@dataclass(frozen=True)
class CombinationReport:
    run_id: str
    snapshot_fingerprint: str
    gold_fingerprint: str
    model_fingerprint: str
    config_fingerprint: str
    model_manifest: Mapping[str, Any]
    candidate_k_per_route: int
    max_fused_candidates: int
    source_k: int
    query_count: int
    arms: Mapping[str, CombinationArmReport]
    incremental_deltas: Mapping[str, Mapping[str, float | None]]
    ablation_deltas: Mapping[str, Mapping[str, float | None]]
    generation_metrics: Mapping[str, Any]
    conversation_metrics: Mapping[str, Any] | None
    conversation_fixture_digest: str | None
    stage_durations_ms: Mapping[str, Mapping[str, tuple[float, ...]]]
    latency_percentiles_ms: Mapping[str, Mapping[str, Mapping[str, float | int | None]]]
    token_usage: Mapping[str, Any]
    route_statuses: Mapping[str, Any]
    invariants: Mapping[str, Any]
    artifact_digest_manifest: tuple[Mapping[str, Any], ...]


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        allow_nan=False,
        separators=(",", ":"),
    ).encode("utf-8")


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _fingerprint(value: Any) -> str:
    return _sha256(_canonical_json(value))


def _coverage_to_dict(value: FinalContextAnchorCoverage) -> dict[str, Any]:
    return {
        "cutoff": "exact_final_packed_context_ids",
        "total_anchors": value.total_anchors,
        "eligible_anchors": value.eligible_anchors,
        "covered_anchors": value.covered_anchors,
        "uncovered_anchors": value.uncovered_anchors,
        "unresolved_anchors": value.unresolved_anchors,
        "context_chunk_count": value.context_chunk_count,
        "denominator_semantics": "covered / (covered + uncovered); unresolved excluded",
        "rate": value.rate,
        "covered_anchor_ids": list(value.covered_anchor_ids),
        "uncovered_anchor_ids": list(value.uncovered_anchor_ids),
        "unresolved_anchor_ids": list(value.unresolved_anchor_ids),
    }


def _arm_to_dict(arm: CombinationArmReport) -> dict[str, Any]:
    return {
        "component_config": dict(arm.component_config),
        "config_fingerprint": arm.config_fingerprint,
        "source_metrics": arm.source_metrics.to_dict(),
        "source_metric_denominators": {
            "judged_query_count": arm.source_metrics.judged_query_count,
            "scope_labeled_query_count": arm.source_metrics.scope_labeled_query_count,
            "wrong_scope_numerator": sum(
                row.wrong_scope_numerator for row in arm.source_metrics.per_query
            ),
            "wrong_scope_denominator": sum(
                row.wrong_scope_denominator for row in arm.source_metrics.per_query
            ),
        },
        "candidate_recall": asdict(arm.candidate_recall),
        "final_context_anchor_coverage": _coverage_to_dict(
            arm.final_context_anchor_coverage
        ),
        "candidate_chunk_ids": {
            key: list(value) for key, value in arm.candidate_chunk_ids.items()
        },
        "final_result_ids": {
            key: list(value) for key, value in arm.final_result_ids.items()
        },
        "packed_context_ids": {
            key: list(value) for key, value in arm.packed_context_ids.items()
        },
        "packed_context_chunk_counts": dict(arm.packed_context_chunk_counts),
        "stage_durations_ms": {
            key: list(values) for key, values in arm.stage_durations_ms.items()
        },
        "latency_percentiles_ms": {
            key: dict(value) for key, value in arm.latency_percentiles_ms.items()
        },
        "token_usage": dict(arm.token_usage),
        "route_statuses": dict(arm.route_statuses),
        "invariants": dict(arm.invariants),
        "trace_artifacts": dict(arm.trace_artifacts),
    }


def _report_to_dict(report: CombinationReport) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "run_id": report.run_id,
        "snapshot_fingerprint": report.snapshot_fingerprint,
        "gold_fingerprint": report.gold_fingerprint,
        "model_fingerprint": report.model_fingerprint,
        "config_fingerprint": report.config_fingerprint,
        "model_manifest": dict(report.model_manifest),
        "candidate_cutoff": {
            "stage": "pre_rerank_fusion",
            "candidate_k_per_route": report.candidate_k_per_route,
            "max_fused_candidates": report.max_fused_candidates,
        },
        "metric_units": {
            "candidate_recall": {
                "stage": "pre_rerank_fusion",
                "unit": "distinct_source_ids",
                "candidate_ids_unit": "chunk_id",
                "k": report.max_fused_candidates,
            },
            "source_metrics": {
                "stage": "post_rerank_results",
                "unit": "distinct_source_ids",
                "k": report.source_k,
            },
            "final_context_anchor_coverage": {
                "stage": "exact_final_packed_context",
                "unit": "reviewed_evidence_anchor",
                "context_ids_unit": "chunk_id",
            },
            "candidate_chunk_ids": "chunk_id",
            "final_result_ids": "chunk_id",
            "packed_context_ids": "chunk_id",
        },
        "source_k": report.source_k,
        "query_count": report.query_count,
        "arms": {name: _arm_to_dict(arm) for name, arm in report.arms.items()},
        "incremental_deltas": {
            name: dict(values) for name, values in report.incremental_deltas.items()
        },
        "ablation_deltas": {
            name: dict(values) for name, values in report.ablation_deltas.items()
        },
        "generation_metrics": dict(report.generation_metrics),
        "conversation_metrics": (
            None
            if report.conversation_metrics is None
            else dict(report.conversation_metrics)
        ),
        "conversation_fixture_digest": report.conversation_fixture_digest,
        "stage_durations_ms": {
            arm: {stage: list(values) for stage, values in stages.items()}
            for arm, stages in report.stage_durations_ms.items()
        },
        "latency_percentiles_ms": {
            arm: {stage: dict(value) for stage, value in stages.items()}
            for arm, stages in report.latency_percentiles_ms.items()
        },
        "token_usage": dict(report.token_usage),
        "route_statuses": dict(report.route_statuses),
        "invariants": dict(report.invariants),
        "artifact_digest_manifest": [
            dict(entry) for entry in report.artifact_digest_manifest
        ],
        "interpretation": {
            "combination_deltas": "incremental and combined configuration comparisons; not isolated single-factor effects",
            "answer_support": "not measured without generated answers and reviewed human judgments",
            "citation_precision": "not measured without generated answers and reviewed human judgments",
            "significance": "no inferential or significance claim is made",
        },
    }


def read_generation_inputs(artifact_dir: str | Path) -> dict[str, list[dict[str, Any]]]:
    """Read local generation inputs by arm for invariant checks and later review."""
    root = Path(artifact_dir)
    result = {}
    inputs_root = root / "generation-inputs"
    if not inputs_root.exists():
        return result
    for path in sorted(inputs_root.glob("*.jsonl")):
        rows = []
        for line_number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), 1
        ):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(
                    f"Invalid generation input at {path.name}:{line_number}"
                ) from error
            if not isinstance(row, dict):
                raise ValueError(
                    f"Invalid generation input at {path.name}:{line_number}"
                )
            rows.append(row)
        result[path.stem] = rows
    return result
