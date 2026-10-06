"""Snapshot-level arm orchestration and atomic run artifact publication."""

from __future__ import annotations

import os
import math
import json
import shutil
import stat
import tempfile
import time
import uuid
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from statistics import median
from typing import Any, Mapping

from kotaemon.base import Document
from kotaemon.indices.knowledge.evaluation.local_models import LocalModelPaths
from kotaemon.indices.knowledge.evaluation.local_snapshot import (
    EvidenceAnchor,
    LocalSnapshot,
)
from kotaemon.indices.knowledge.evaluation.retrieval_eval import (
    IndexedCatalog,
    resolve_judgments,
)
from kotaemon.indices.knowledge.evaluation.source_metrics import (
    final_context_anchor_coverage,
    score_candidate_recall,
    score_source_run,
)
from kotaemon.indices.knowledge.retrieval.contracts import RetrievalPolicy

from . import local_experiment
from .combination_arms import (
    CANDIDATE_K,
    MAX_FUSED_CANDIDATES,
    MAX_QUERY_VARIANTS,
    SOURCE_K,
    get_arm_configurations,
)
from .combination_artifacts import (
    CombinationArmReport,
    CombinationReport,
    _canonical_json,
    _fingerprint,
    _report_to_dict,
    _sha256,
)
from .combination_checkpoint import (
    RunCheckpoint,
    _atomic_write as _checkpoint_atomic_write,
)
from .combination_runtime import (
    _GENERATION_NOT_RUN,
    _aggregate_anchor_coverage,
    _counter_and_budget,
    _doc_id,
    _evaluate_conversations,
    _evaluate_single_query,
    _generation_system_prompt,
    _percentile_summary,
    _repack_single_query_from_trace,
    _verify_zero_invariants,
)
from .conversation_fixtures import (
    ConversationFixture,
    _reject_label_leaking_source_metadata,
    _validate_conversation_fixture_snapshot,
    _validate_snapshot_constraints,
    load_conversation_fixture,
)
from .snapshot_adapter import (
    SnapshotRuntime,
    build_snapshot_replay_runtime,
    build_snapshot_runtime,
)

_CONTEXT_PACKING_VERSION = "serialized-full-message-v1"


def _snapshot_file_hashes(snapshot_root: Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for path in sorted(Path(snapshot_root).iterdir(), key=lambda item: item.name):
        mode = path.lstat().st_mode
        if stat.S_ISLNK(mode):
            raise ValueError("Approved snapshot contains a symlink")
        if stat.S_ISREG(mode):
            hashes[path.name] = _sha256(path.read_bytes())
        elif stat.S_ISDIR(mode):
            raise ValueError("Approved snapshot contains an unexpected subdirectory")
    return hashes


def _model_manifest(model_paths: LocalModelPaths, embedding: Any, reranker: Any):
    embedding_data = local_experiment._model_metadata(embedding, "embedding")
    reranker_data = local_experiment._model_metadata(reranker, "reranker")
    return {
        "embedding": embedding_data,
        "reranker": reranker_data,
        "weight_source": {
            "embedding": model_paths.embedding_weight_source,
            "reranker": model_paths.reranker_weight_source,
        },
    }


def _build_policy() -> RetrievalPolicy:
    return RetrievalPolicy(
        enabled=True,
        candidate_k=CANDIDATE_K,
        max_fused_candidates=MAX_FUSED_CANDIDATES,
        max_variants=MAX_QUERY_VARIANTS,
        dense_weight=1.0,
        lexical_weight=1.0,
        rrf_k=60,
    )


def _runtime_for_arm(
    snapshot: LocalSnapshot,
    *,
    embedding: Any,
    reranker: Any,
    components: Mapping[str, Any],
) -> SnapshotRuntime:
    use_reranker = bool(components["reranker"])
    return build_snapshot_runtime(
        snapshot,
        embedding=embedding,
        reranker=reranker if use_reranker else None,
        policy=_build_policy(),
        chunking_mode=components["chunking_mode"],
        lexical=bool(components["lexical_rrf"]),
    )


def _effective_arm_config(
    config: Mapping[str, Any],
    *,
    lexical_status: str,
    model_device: str | None,
    context_packing_version: str | None,
) -> dict[str, Any]:
    components = config["components"]
    result = {
        **config,
        "reranker_status": ("available" if components["reranker"] else "not_used"),
        "lexical_status": lexical_status,
        "expansion_score_gate": (
            "relative_bge_reranker_floor"
            if components["evidence_expansion"] and components["reranker"]
            else "scorer_unavailable"
            if components["evidence_expansion"]
            else "not_used"
        ),
        "device": model_device,
    }
    if context_packing_version is not None:
        result["context_packing_version"] = context_packing_version
    return result


def _global_config(
    *,
    arm_configs: Mapping[str, Any],
    generation_budget: Any,
    counter_id: str,
    conversation_fixture_digest: str | None,
    context_packing_version: str | None,
    system_prompt_sha256: str | None = None,
    repack_source: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    result = {
        "schema_version": 1,
        "candidate_k_per_route": CANDIDATE_K,
        "max_fused_candidates": MAX_FUSED_CANDIDATES,
        "source_k": SOURCE_K,
        "retrieval_policy": asdict(_build_policy()),
        "generation_budget": asdict(generation_budget),
        "token_counter": counter_id,
        "arms": arm_configs,
        "conversation_fixture_sha256": conversation_fixture_digest,
        "comparison_semantics": "incremental_and_combined; no_significance_claim",
    }
    if context_packing_version is not None:
        result["context_packing_version"] = context_packing_version
    if system_prompt_sha256 is not None:
        result["system_prompt_sha256"] = system_prompt_sha256
    if repack_source is not None:
        result["repack_source"] = dict(repack_source)
    return result


def _lexical_status_for_replay() -> str:
    from kotaemon.storages.docstores.sqlite_fts import SQLiteFTSDocumentStore

    store = SQLiteFTSDocumentStore()
    try:
        return (
            "available"
            if getattr(store, "supports_lexical_search", False)
            else "unavailable"
        )
    finally:
        close = getattr(store, "close", None)
        if callable(close):
            close()


def _validate_snapshot(snapshot: LocalSnapshot) -> None:
    if not isinstance(snapshot, LocalSnapshot):
        raise TypeError("snapshot must be a validated LocalSnapshot")
    local_experiment._verify_snapshot(snapshot)
    local_experiment._validate_baseline_splitter(snapshot)
    if not snapshot.judgments.cases:
        raise ValueError("The approved snapshot has no judged queries")
    if any(case.judgment_level != "source" for case in snapshot.judgments.cases):
        raise ValueError("Combination evaluation requires source-level judgments")
    for case in snapshot.judgments.cases:
        _validate_snapshot_constraints(case, snapshot)
    _reject_label_leaking_source_metadata(snapshot)


def _snapshot_catalog(snapshot: LocalSnapshot, runtime: SnapshotRuntime):
    return IndexedCatalog(
        (source["source_id"] for source in snapshot.selected_sources),
        runtime.chunk_to_source,
    )


def _collect_case_anchors(
    snapshot: LocalSnapshot,
) -> dict[str, tuple[EvidenceAnchor, ...]]:
    result: dict[str, list[EvidenceAnchor]] = {}
    for anchor in snapshot.anchors:
        result.setdefault(anchor.query_id, []).append(anchor)
    return {key: tuple(value) for key, value in result.items()}


def _query_checkpoint_summary(case: Any, result: Mapping[str, Any]) -> dict[str, Any]:
    generation_input = {
        "case_id": case.case_id,
        "question": case.query,
        "payload": result["payload"],
        "trace_context_ids": list(result["trace_context_ids"]),
        "payload_context_ids": list(result["payload_context_ids"]),
        "generation": result["generation"],
        "human_judgment": {
            "answer_support": None,
            "citation_precision": None,
            "no_answer_correctness": None,
            "status": "not_reviewed",
        },
    }
    return {
        "case_id": case.case_id,
        "candidate_ids": list(result["candidate_ids"]),
        "final_ids": [_doc_id(item) for item in result["ranked"]],
        "trace_context_ids": list(result["trace_context_ids"]),
        "payload_context_ids": list(result["payload_context_ids"]),
        "context_tokens": result["packed"].token_count,
        "timings": dict(result["timings"]),
        "route_statuses": dict(result["route_statuses"]),
        "invariants": dict(result["invariants"]),
        "generation_input": generation_input,
    }


def _query_result_from_checkpoint(
    case: Any,
    trace: Mapping[str, Any],
    summary: Mapping[str, Any],
) -> dict[str, Any]:
    if (
        summary.get("case_id") != case.case_id
        or trace.get("original_query") != case.query
        or not isinstance(summary.get("generation_input"), Mapping)
        or summary["generation_input"].get("case_id") != case.case_id
        or summary["generation_input"].get("question") != case.query
    ):
        raise ValueError("Resume checkpoint trace does not match the reviewed query")
    combination = trace.get("combination_evaluation")
    if not isinstance(combination, Mapping):
        raise ValueError("Resume checkpoint trace is missing combination metadata")
    fields = {
        "candidate_ids": combination.get("candidate_ids"),
        "trace_context_ids": combination.get("packed_context_ids"),
        "payload_context_ids": combination.get("payload_context_ids"),
    }
    for name, value in fields.items():
        if (
            not isinstance(value, list)
            or any(not isinstance(item, str) or not item for item in value)
            or len(value) != len(set(value))
            or list(summary.get(name, ())) != value
        ):
            raise ValueError("Resume checkpoint trace metadata is inconsistent")
    final_ids = trace.get("final_chunk_ids")
    if (
        not isinstance(final_ids, list)
        or any(not isinstance(item, str) or not item for item in final_ids)
        or len(final_ids) != len(set(final_ids))
        or list(summary.get("final_ids", ())) != final_ids
    ):
        raise ValueError("Resume checkpoint final result IDs are inconsistent")
    timings = summary.get("timings")
    route_statuses = summary.get("route_statuses")
    invariants = summary.get("invariants")
    if (
        not isinstance(timings, Mapping)
        or not isinstance(route_statuses, Mapping)
        or not isinstance(invariants, Mapping)
        or isinstance(summary.get("context_tokens"), bool)
        or not isinstance(summary.get("context_tokens"), int)
        or summary["context_tokens"] < 0
    ):
        raise ValueError("Resume checkpoint query summary is invalid")
    generation_input = summary["generation_input"]
    if (
        generation_input.get("trace_context_ids") != fields["trace_context_ids"]
        or generation_input.get("payload_context_ids") != fields["payload_context_ids"]
    ):
        raise ValueError("Resume checkpoint generation input IDs are inconsistent")
    return {
        "ranked": tuple(Document(id_=item, text="") for item in final_ids),
        "candidate_ids": tuple(fields["candidate_ids"]),
        "trace": trace,
        "trace_context_ids": tuple(fields["trace_context_ids"]),
        "payload_context_ids": tuple(fields["payload_context_ids"]),
        "token_count": summary["context_tokens"],
        "timings": dict(timings),
        "route_statuses": dict(route_statuses),
        "invariants": dict(invariants),
        "generation_input": dict(generation_input),
    }


def _run_in_directory(
    snapshot: LocalSnapshot,
    *,
    model_paths: LocalModelPaths,
    embedding: Any,
    reranker: Any,
    artifact_dir: Path,
    conversation_fixture: ConversationFixture | None,
    conversation_fixture_path: Path | None,
    verified_model_manifest_bytes: bytes | None,
    resume: bool,
    replay_only: bool = False,
    repack_source: Mapping[str, Any] | None = None,
) -> CombinationReport:
    snapshot_hashes_before = _snapshot_file_hashes(snapshot.root)
    model_manifest = _model_manifest(model_paths, embedding, reranker)
    model_fingerprint = _fingerprint(model_manifest)
    generation_budget, count_tokens, counter_id = _counter_and_budget()
    system_prompt = _generation_system_prompt()
    arm_configs = get_arm_configurations()
    global_config = _global_config(
        arm_configs=arm_configs,
        generation_budget=generation_budget,
        counter_id=counter_id,
        conversation_fixture_digest=(
            None if conversation_fixture is None else conversation_fixture.digest
        ),
        context_packing_version=_CONTEXT_PACKING_VERSION,
        system_prompt_sha256=_sha256(system_prompt.encode("utf-8")),
        repack_source=repack_source,
    )
    config_fingerprint = _fingerprint(global_config)
    gold_hashes = {
        name: snapshot_hashes_before[name]
        for name in ("judgments.jsonl", "anchors.jsonl")
    }
    gold_fingerprint = _fingerprint(gold_hashes)
    checkpoint_fingerprints = {
        "snapshot": snapshot.fingerprint,
        "gold": gold_fingerprint,
        "model": model_fingerprint,
        "model_manifest": (
            _sha256(verified_model_manifest_bytes)
            if verified_model_manifest_bytes is not None
            else _fingerprint(model_manifest)
        ),
        "config": config_fingerprint,
    }
    arm_config_fingerprints = {
        name: _fingerprint(config) for name, config in arm_configs.items()
    }
    case_ids = tuple(case.case_id for case in snapshot.judgments.cases)
    if resume:
        checkpoint = RunCheckpoint.resume(
            artifact_dir,
            expected_fingerprints=checkpoint_fingerprints,
            expected_case_ids=case_ids,
            expected_arm_config_fingerprints=arm_config_fingerprints,
        )
    else:
        checkpoint = RunCheckpoint.create(
            artifact_dir,
            run_id=f"{snapshot.fingerprint[:12]}-{uuid.uuid4().hex[:12]}",
            fingerprints=checkpoint_fingerprints,
            case_ids=case_ids,
            arm_config_fingerprints=arm_config_fingerprints,
        )
    if replay_only:
        expected_keys = {
            (arm, index)
            for arm in arm_configs
            for index in range(len(snapshot.judgments.cases))
        }
        if not resume or checkpoint.completed_keys != expected_keys:
            raise ValueError("Replay checkpoint does not contain every arm/query trace")
    run_id = checkpoint.run_id
    anchors_by_query = _collect_case_anchors(snapshot)
    runtimes: dict[tuple[str, bool, bool], SnapshotRuntime] = {}
    arms: dict[str, CombinationArmReport] = {}
    trace_entries: list[dict[str, Any]] = []
    generation_input_files: list[Path] = []
    conversation_metrics = None
    conversation_artifact = None
    arm_stage_durations: dict[str, Mapping[str, tuple[float, ...]]] = {}
    arm_latency: dict[str, Mapping[str, Mapping[str, float | int | None]]] = {}
    arm_tokens: dict[str, Mapping[str, Any]] = {}
    arm_routes: dict[str, Mapping[str, Any]] = {}
    global_invariants = Counter()
    unresolved_anchor_ids = set()
    model_device = model_manifest["embedding"].get("device")
    query_count = len(snapshot.judgments.cases)
    final_runtime = None
    replay_lexical_status = (
        _lexical_status_for_replay() if replay_only else None
    )

    for arm_name, config in arm_configs.items():
        components = config["components"]
        runtime_key = (
            components["chunking_mode"],
            bool(components["lexical_rrf"]),
            bool(components["reranker"]),
        )
        runtime = runtimes.get(runtime_key)
        index_duration_ms = 0.0
        if runtime is None:
            index_started = time.perf_counter()
            if replay_only:
                runtime = build_snapshot_replay_runtime(
                    snapshot,
                    policy=_build_policy(),
                    chunking_mode=components["chunking_mode"],
                    lexical=bool(components["lexical_rrf"]),
                    lexical_status=(
                        replay_lexical_status
                        if components["lexical_rrf"]
                        else "not_used"
                    ),
                    reranker_available=bool(components["reranker"]),
                )
            else:
                runtime = _runtime_for_arm(
                    snapshot,
                    embedding=embedding,
                    reranker=reranker,
                    components=components,
                )
            index_duration_ms = (time.perf_counter() - index_started) * 1000
            runtimes[runtime_key] = runtime
        if arm_name == "registry_expansion":
            final_runtime = runtime

        catalog = _snapshot_catalog(snapshot, runtime)
        resolved_cases = resolve_judgments(snapshot.judgments, catalog)
        if len(resolved_cases) != query_count:
            raise ValueError("A combination arm changed the reviewed query order")
        if tuple(item.case_id for item in resolved_cases) != tuple(
            item.case_id for item in snapshot.judgments.cases
        ):
            raise ValueError("A combination arm changed the reviewed query IDs")

        arm_config = _effective_arm_config(
            config,
            lexical_status=runtime.config.get("lexical_status", "unknown"),
            model_device=model_device,
            context_packing_version=_CONTEXT_PACKING_VERSION,
        )
        checkpoint.bind_arm_config(arm_name, _fingerprint(arm_config))

        retrieval_policy = _build_policy()
        result_map: dict[str, tuple[Document, ...]] = {}
        candidates_map: dict[str, tuple[str, ...]] = {}
        final_ids: dict[str, tuple[str, ...]] = {}
        context_ids: dict[str, tuple[str, ...]] = {}
        context_counts: dict[str, int] = {}
        anchor_coverages = []
        duration_values: dict[str, list[float]] = {
            "index_build": [index_duration_ms] if index_duration_ms else [],
            "query_enrichment": [],
            "retrieval": [],
            "evidence_expansion": [],
            "context_packing": [],
            "overall": [],
        }
        route_counts: Counter[str] = Counter()
        arm_invariants = Counter()
        token_counts = []
        query_trace_paths: dict[str, str] = {}
        generation_rows = []

        for index, case in enumerate(resolved_cases):
            checkpoint_key = (arm_name, index)
            if checkpoint_key in checkpoint.completed_keys:
                trace_data, summary = checkpoint.read(arm_name, index)
                result = _query_result_from_checkpoint(case, trace_data, summary)
            else:
                checkpoint.begin(arm_name, index, case.case_id)
                result = _evaluate_single_query(
                    runtime,
                    case,
                    components=components,
                    retrieval_policy=retrieval_policy,
                    history=(),
                    generation_budget=generation_budget,
                    count_tokens=count_tokens,
                    counter_id=counter_id,
                    system_prompt=system_prompt,
                )
                summary = _query_checkpoint_summary(case, result)
                checkpoint.complete(
                    arm_name,
                    index,
                    case.case_id,
                    trace=result["trace"],
                    summary=summary,
                )

            result_map[case.case_id] = result["ranked"]
            candidates_map[case.case_id] = result["candidate_ids"]
            final_ids[case.case_id] = tuple(_doc_id(item) for item in result["ranked"])
            context_ids[case.case_id] = result["trace_context_ids"]
            context_counts[case.case_id] = len(result["trace_context_ids"])
            token_count = (
                result["token_count"]
                if "token_count" in result
                else result["packed"].token_count
            )
            token_counts.append(token_count)
            for stage_name, value in result["timings"].items():
                duration_values.setdefault(stage_name, []).append(value)
            for status, count in result["route_statuses"].items():
                route_counts[status] += count
            for key, value in result["invariants"].items():
                arm_invariants[key] += value
                global_invariants[key] += value
            query_anchors = anchors_by_query.get(case.case_id, ())
            coverage = final_context_anchor_coverage(
                query_anchors,
                context_chunk_ids=result["trace_context_ids"],
                chunks_by_id=runtime.draft_chunks,
                unresolved_offsets=runtime.unresolved_offsets,
            )
            anchor_coverages.append(coverage)
            unresolved_anchor_ids.update(coverage.unresolved_anchor_ids)

            trace_relative = Path("traces") / arm_name / f"query-{index:04d}.json"
            query_trace_paths[case.case_id] = trace_relative.as_posix()
            generation_rows.append(summary["generation_input"])

        generation_relative = Path("generation-inputs") / f"{arm_name}.jsonl"
        generation_path = artifact_dir / generation_relative
        generation_bytes = b"".join(
            _canonical_json(row) + b"\n" for row in generation_rows
        )
        _checkpoint_atomic_write(generation_path, generation_bytes)
        generation_input_files.append(generation_path)
        trace_entries.append(
            {
                "path": generation_relative.as_posix(),
                "sha256": _sha256(generation_bytes),
                "size_bytes": len(generation_bytes),
                "kind": "private_generation_input_and_judgment_template",
            }
        )

        metrics = score_source_run(
            resolved_cases,
            result_map,
            k=SOURCE_K,
            chunk_to_source=runtime.chunk_to_source,
        )
        candidate_recall = score_candidate_recall(
            resolved_cases,
            candidates_map,
            runtime.chunk_to_source,
            candidate_k=MAX_FUSED_CANDIDATES,
        )
        combined_coverage = _aggregate_anchor_coverage(anchor_coverages)
        invariants = {
            **dict(arm_invariants),
            "source_metric_k": metrics.k,
            "candidate_recall_stage": "pre_rerank_fusion",
            "packed_context_counter": counter_id,
            "snapshot_hashes_unchanged": True,
        }
        stage_summaries = {
            name: _percentile_summary(values)
            for name, values in duration_values.items()
        }
        token_summary = {
            "counter": counter_id,
            "estimated": generation_budget.estimated,
            "sample_count": len(token_counts),
            "total_context_tokens": sum(token_counts),
            "mean_context_tokens": (
                None if not token_counts else sum(token_counts) / len(token_counts)
            ),
            "p50_context_tokens": (None if not token_counts else median(token_counts)),
            "p95_context_tokens": (
                None
                if not token_counts
                else sorted(token_counts)[
                    max(0, math.ceil(0.95 * len(token_counts)) - 1)
                ]
            ),
            "packed_context_chunks": sum(context_counts.values()),
            "source_k": SOURCE_K,
        }
        route_summary = {
            "counts": dict(sorted(route_counts.items())),
            "lexical_status": runtime.config.get("lexical_status", "unknown"),
            "reranker_status": arm_config["reranker_status"],
            "expansion_score_gate": arm_config["expansion_score_gate"],
        }
        arms[arm_name] = CombinationArmReport(
            component_config=arm_config,
            config_fingerprint=_fingerprint(arm_config),
            source_metrics=metrics,
            candidate_recall=candidate_recall,
            final_context_anchor_coverage=combined_coverage,
            candidate_chunk_ids=candidates_map,
            final_result_ids=final_ids,
            packed_context_ids=context_ids,
            packed_context_chunk_counts=context_counts,
            stage_durations_ms={
                key: tuple(value) for key, value in duration_values.items()
            },
            latency_percentiles_ms=stage_summaries,
            token_usage=token_summary,
            route_statuses=route_summary,
            invariants=invariants,
            trace_artifacts=query_trace_paths,
        )
        arm_stage_durations[arm_name] = arms[arm_name].stage_durations_ms
        arm_latency[arm_name] = stage_summaries
        arm_tokens[arm_name] = token_summary
        arm_routes[arm_name] = route_summary

        if arm_name == "registry_expansion" and conversation_fixture is not None:
            assert conversation_fixture_path is not None
            _validate_conversation_fixture_snapshot(conversation_fixture, snapshot)
            conversation_metrics, conversation_artifact = _evaluate_conversations(
                conversation_fixture,
                snapshot,
                runtime,
                final_components=components,
                retrieval_policy=retrieval_policy,
                generation_budget=generation_budget,
                count_tokens=count_tokens,
                counter_id=counter_id,
                system_prompt=system_prompt,
                artifact_dir=artifact_dir,
            )
            conversation_metrics["fixture_digest"] = conversation_fixture.digest
            conversation_metrics["fixture_name"] = conversation_fixture.source_name

    if final_runtime is None:
        raise ValueError("The final combined configuration was not evaluated")
    snapshot_hashes_after = _snapshot_file_hashes(snapshot.root)
    snapshot_unchanged = snapshot_hashes_before == snapshot_hashes_after
    global_invariants["v2_snapshot_hash_changes"] = 0 if snapshot_unchanged else 1
    global_invariants["v2_snapshot_inputs_unchanged"] = snapshot_unchanged
    if not snapshot_unchanged:
        raise ValueError(
            "Approved v2 snapshot files changed during combination evaluation"
        )
    _verify_zero_invariants(global_invariants)
    checkpoint.finish()

    metric_names = ("hit_at_k", "recall_at_k", "mrr_at_k", "wrong_scope_at_k")
    incremental_deltas = {}
    predecessor = {
        "registry_chunking": "dense_baseline",
        "registry_lexical_rrf": "registry_chunking",
        "registry_reranking": "registry_lexical_rrf",
        "registry_enrichment": "registry_reranking",
        "registry_expansion": "registry_enrichment",
    }
    for current, previous in predecessor.items():
        incremental_deltas[current] = {
            metric: (
                None
                if getattr(arms[current].source_metrics, metric) is None
                or getattr(arms[previous].source_metrics, metric) is None
                else getattr(arms[current].source_metrics, metric)
                - getattr(arms[previous].source_metrics, metric)
            )
            for metric in metric_names
        }
    ablation_deltas = {}
    for name in get_arm_configurations():
        if name.startswith("ablation_"):
            ablation_deltas[name] = {
                metric: (
                    None
                    if getattr(arms[name].source_metrics, metric) is None
                    or getattr(arms["registry_expansion"].source_metrics, metric)
                    is None
                    else getattr(arms[name].source_metrics, metric)
                    - getattr(arms["registry_expansion"].source_metrics, metric)
                )
                for metric in metric_names
            }

    fixture_input = None
    if conversation_fixture is not None:
        assert conversation_fixture_path is not None
        fixture_input = {
            "path_label": conversation_fixture.source_name,
            "sha256": conversation_fixture.digest,
            "kind": "reviewed_conversation_fixture_input",
        }
    artifact_entries = [*trace_entries, *checkpoint.artifact_entries()]
    model_manifest_sha256 = None
    if verified_model_manifest_bytes is not None:
        model_manifest_path = artifact_dir / "model-manifest.json"
        _checkpoint_atomic_write(model_manifest_path, verified_model_manifest_bytes)
        model_manifest_sha256 = _sha256(verified_model_manifest_bytes)
        artifact_entries.append(
            {
                "path": "model-manifest.json",
                "sha256": model_manifest_sha256,
                "size_bytes": len(verified_model_manifest_bytes),
                "kind": "verified_model_manifest",
            }
        )
    if conversation_artifact is not None:
        payload = (artifact_dir / conversation_artifact).read_bytes()
        entry = {
            "path": conversation_artifact.as_posix(),
            "sha256": _sha256(payload),
            "size_bytes": len(payload),
            "kind": "private_conversation_trace",
        }
        artifact_entries.append(entry)
    if fixture_input is not None:
        artifact_entries.append(fixture_input)
    generation_metrics = {
        "status": "not_run",
        "answer_support": None,
        "citation_precision": None,
        "no_answer_correctness": None,
        "model_failures": None,
        "not_run_reason": _GENERATION_NOT_RUN,
        "judgment_template": "generation-inputs/*.jsonl",
    }
    report = CombinationReport(
        run_id=run_id,
        snapshot_fingerprint=snapshot.fingerprint,
        gold_fingerprint=gold_fingerprint,
        model_fingerprint=model_fingerprint,
        config_fingerprint=config_fingerprint,
        model_manifest=model_manifest,
        candidate_k_per_route=CANDIDATE_K,
        max_fused_candidates=MAX_FUSED_CANDIDATES,
        source_k=SOURCE_K,
        query_count=query_count,
        arms=arms,
        incremental_deltas=incremental_deltas,
        ablation_deltas=ablation_deltas,
        generation_metrics=generation_metrics,
        conversation_metrics=conversation_metrics,
        conversation_fixture_digest=(
            None if conversation_fixture is None else conversation_fixture.digest
        ),
        stage_durations_ms=arm_stage_durations,
        latency_percentiles_ms=arm_latency,
        token_usage=arm_tokens,
        route_statuses=arm_routes,
        invariants=dict(global_invariants),
        artifact_digest_manifest=tuple(artifact_entries),
    )
    report_bytes = _canonical_json(_report_to_dict(report)) + b"\n"
    report_path = artifact_dir / "report.json"
    _checkpoint_atomic_write(report_path, report_bytes)
    sidecar = {
        "schema_version": 1,
        "run_id": run_id,
        "snapshot_fingerprint": snapshot.fingerprint,
        "gold_fingerprint": gold_fingerprint,
        "model_fingerprint": model_fingerprint,
        "config_fingerprint": config_fingerprint,
        "inputs": {
            "approved_snapshot_files": snapshot_hashes_before,
            "gold_files": gold_hashes,
            "model_manifest_sha256": model_manifest_sha256,
            "conversation_fixture": fixture_input,
            "repack_source": (
                None if repack_source is None else dict(repack_source)
            ),
        },
        "artifacts": [
            *artifact_entries,
            {
                "path": "report.json",
                "sha256": _sha256(report_bytes),
                "size_bytes": len(report_bytes),
                "kind": "aggregate_combination_report",
            },
        ],
    }
    _checkpoint_atomic_write(
        artifact_dir / "artifact-manifest.json",
        _canonical_json(sidecar) + b"\n",
    )
    return report


def _reject_symlink_path(path: Path) -> None:
    current = Path(os.path.abspath(path))
    while True:
        try:
            if stat.S_ISLNK(current.lstat().st_mode):
                raise ValueError(f"Artifact path contains a symlink: {current}")
        except FileNotFoundError:
            pass
        if current.parent == current:
            break
        current = current.parent


def run_combination_experiment(
    snapshot: LocalSnapshot,
    *,
    model_paths: LocalModelPaths,
    artifact_dir: Path,
    conversation_fixture: Path | None = None,
    staging_dir: Path | None = None,
    resume: bool = False,
    verified_model_manifest_bytes: bytes | None = None,
) -> CombinationReport:
    """Run or safely resume all fixed combination/ablation arms."""
    _validate_snapshot(snapshot)
    if not isinstance(model_paths, LocalModelPaths):
        raise TypeError("model_paths must be LocalModelPaths")
    if conversation_fixture is not None:
        fixture = load_conversation_fixture(conversation_fixture)
        _validate_conversation_fixture_snapshot(fixture, snapshot)
    else:
        fixture = None
    local_experiment._validate_model_provenance(model_paths)

    destination = Path(os.path.abspath(Path(artifact_dir).expanduser()))
    _reject_symlink_path(destination)
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(
            f"Combination artifact destination already exists: {destination}"
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    _reject_symlink_path(destination.parent)
    if resume and staging_dir is None:
        raise ValueError("Resuming requires an explicit staging directory")
    if staging_dir is None:
        staging = Path(
            tempfile.mkdtemp(
                prefix=f".{destination.name}.staging-", dir=destination.parent
            )
        )
    else:
        staging = Path(os.path.abspath(Path(staging_dir).expanduser()))
        _reject_symlink_path(staging)
        if staging == destination or staging.parent != destination.parent:
            raise ValueError("Combination staging directory must be beside its output")
        if not staging.name.startswith(f".{destination.name}.staging-"):
            raise ValueError("Combination staging directory name does not match output")
        if resume:
            if not staging.is_dir():
                raise ValueError("Combination staging directory does not exist")
        elif staging.exists() or staging.is_symlink():
            raise FileExistsError("Combination staging directory already exists")
    try:
        embedding = local_experiment._create_embedding(
            model_paths.embedding_model_dir,
            revision=model_paths.embedding_revision,
            weight_source=model_paths.embedding_weight_source,
        )
        reranker = local_experiment._create_reranker(
            model_paths.reranker_model_dir,
            revision=model_paths.reranker_revision,
            weight_source=model_paths.reranker_weight_source,
        )
        report = _run_in_directory(
            snapshot,
            model_paths=model_paths,
            embedding=embedding,
            reranker=reranker,
            artifact_dir=staging,
            conversation_fixture=fixture,
            conversation_fixture_path=(
                None if conversation_fixture is None else Path(conversation_fixture)
            ),
            verified_model_manifest_bytes=verified_model_manifest_bytes,
            resume=resume,
        )
        if destination.exists() or destination.is_symlink():
            raise FileExistsError(
                f"Combination artifact destination appeared during the run: {destination}"
            )
        os.rename(staging, destination)
        return report
    except BaseException:
        # Keep checkpointed staging data intact so a local run can be resumed.
        raise


def repack_completed_combination_experiment(
    snapshot: LocalSnapshot,
    *,
    model_paths: LocalModelPaths,
    source_staging_dir: Path,
    artifact_dir: Path,
    verified_model_manifest_bytes: bytes | None = None,
) -> CombinationReport:
    """Repack a complete authenticated retrieval run without query inference."""
    _validate_snapshot(snapshot)
    if not isinstance(model_paths, LocalModelPaths):
        raise TypeError("model_paths must be LocalModelPaths")
    local_experiment._validate_model_provenance(model_paths)

    destination = Path(os.path.abspath(Path(artifact_dir).expanduser()))
    source_root = Path(os.path.abspath(Path(source_staging_dir).expanduser()))
    _reject_symlink_path(destination)
    _reject_symlink_path(source_root)
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(
            f"Combination repack destination already exists: {destination}"
        )
    if not source_root.is_dir() or source_root == destination:
        raise ValueError("Repack source must be a distinct checkpoint directory")
    if source_root.parent != destination.parent:
        raise ValueError("Repack source and destination must share the local runs directory")

    checkpoint_path = source_root / "run-checkpoint.json"
    _reject_symlink_path(checkpoint_path)
    try:
        source_control = json.loads(checkpoint_path.read_bytes())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("Repack source checkpoint control file is invalid") from error
    if (
        not isinstance(source_control, dict)
        or source_control.get("status") not in {"running", "complete"}
        or source_control.get("pending") is not None
    ):
        raise ValueError("Repack source checkpoint is incomplete or has a pending query")

    embedding = local_experiment._create_embedding(
        model_paths.embedding_model_dir,
        revision=model_paths.embedding_revision,
        weight_source=model_paths.embedding_weight_source,
    )
    reranker = local_experiment._create_reranker(
        model_paths.reranker_model_dir,
        revision=model_paths.reranker_revision,
        weight_source=model_paths.reranker_weight_source,
    )
    model_manifest = _model_manifest(model_paths, embedding, reranker)
    model_fingerprint = _fingerprint(model_manifest)
    generation_budget, count_tokens, counter_id = _counter_and_budget()
    system_prompt = _generation_system_prompt()
    arm_configs = get_arm_configurations()
    case_ids = tuple(case.case_id for case in snapshot.judgments.cases)
    snapshot_hashes = _snapshot_file_hashes(snapshot.root)
    gold_hashes = {
        name: snapshot_hashes[name]
        for name in ("judgments.jsonl", "anchors.jsonl")
    }
    gold_fingerprint = _fingerprint(gold_hashes)
    old_config = _global_config(
        arm_configs=arm_configs,
        generation_budget=generation_budget,
        counter_id=counter_id,
        conversation_fixture_digest=None,
        context_packing_version=None,
    )
    old_fingerprints = {
        "snapshot": snapshot.fingerprint,
        "gold": gold_fingerprint,
        "model": model_fingerprint,
        "model_manifest": (
            _sha256(verified_model_manifest_bytes)
            if verified_model_manifest_bytes is not None
            else _fingerprint(model_manifest)
        ),
        "config": _fingerprint(old_config),
    }
    baseline_arm_fingerprints = {
        name: _fingerprint(config) for name, config in arm_configs.items()
    }
    source_checkpoint = RunCheckpoint.resume(
        source_root,
        expected_fingerprints=old_fingerprints,
        expected_case_ids=case_ids,
        expected_arm_config_fingerprints=baseline_arm_fingerprints,
    )
    expected_keys = {
        (arm, index)
        for arm in arm_configs
        for index in range(len(case_ids))
    }
    if source_checkpoint.completed_keys != expected_keys:
        raise ValueError("Repack source does not contain every arm/query trace")

    model_device = model_manifest["embedding"].get("device")
    replay_lexical_status = _lexical_status_for_replay()
    expected_effective = {
        name: _fingerprint(
            _effective_arm_config(
                config,
                lexical_status=(
                    replay_lexical_status
                    if config["components"]["lexical_rrf"]
                    else "not_used"
                ),
                model_device=model_device,
                context_packing_version=None,
            )
        )
        for name, config in arm_configs.items()
    }
    if source_checkpoint.effective_arm_config_fingerprints != expected_effective:
        raise ValueError("Repack source effective arm fingerprints do not match")

    source_records = sorted(
        (
            {
                key: record[key]
                for key in (
                    "arm",
                    "query_index",
                    "case_id",
                    "trace_sha256",
                    "trace_size_bytes",
                    "summary_sha256",
                    "summary_size_bytes",
                )
            }
            for record in source_checkpoint.completed_records
        ),
        key=lambda item: (item["arm"], item["query_index"]),
    )
    repack_source = {
        "run_id": source_checkpoint.run_id,
        "checkpoint_sha256": _sha256(checkpoint_path.read_bytes()),
        "query_record_manifest_sha256": _fingerprint(source_records),
        "trace_count": len(source_records),
        "mode": "trace-repack-v1",
    }
    new_global_config = _global_config(
        arm_configs=arm_configs,
        generation_budget=generation_budget,
        counter_id=counter_id,
        conversation_fixture_digest=None,
        context_packing_version=_CONTEXT_PACKING_VERSION,
        system_prompt_sha256=_sha256(system_prompt.encode("utf-8")),
        repack_source=repack_source,
    )
    new_fingerprints = {
        "snapshot": snapshot.fingerprint,
        "gold": gold_fingerprint,
        "model": model_fingerprint,
        "model_manifest": old_fingerprints["model_manifest"],
        "config": _fingerprint(new_global_config),
    }

    destination.parent.mkdir(parents=True, exist_ok=True)
    _reject_symlink_path(destination.parent)
    staging = Path(
        tempfile.mkdtemp(
            prefix=f".{destination.name}.staging-", dir=destination.parent
        )
    )
    checkpoint = RunCheckpoint.create(
        staging,
        run_id=f"{snapshot.fingerprint[:12]}-{uuid.uuid4().hex[:12]}",
        fingerprints=new_fingerprints,
        case_ids=case_ids,
        arm_config_fingerprints=baseline_arm_fingerprints,
    )
    runtimes: dict[tuple[str, bool, bool], SnapshotRuntime] = {}
    for arm_name, config in arm_configs.items():
        components = config["components"]
        runtime_key = (
            components["chunking_mode"],
            bool(components["lexical_rrf"]),
            bool(components["reranker"]),
        )
        runtime = runtimes.get(runtime_key)
        if runtime is None:
            runtime = build_snapshot_replay_runtime(
                snapshot,
                policy=_build_policy(),
                chunking_mode=components["chunking_mode"],
                lexical=bool(components["lexical_rrf"]),
                lexical_status=(
                    replay_lexical_status
                    if components["lexical_rrf"]
                    else "not_used"
                ),
                reranker_available=bool(components["reranker"]),
            )
            runtimes[runtime_key] = runtime
        arm_config = _effective_arm_config(
            config,
            lexical_status=runtime.config["lexical_status"],
            model_device=model_device,
            context_packing_version=_CONTEXT_PACKING_VERSION,
        )
        checkpoint.bind_arm_config(arm_name, _fingerprint(arm_config))
        resolved_cases = resolve_judgments(
            snapshot.judgments, _snapshot_catalog(snapshot, runtime)
        )
        if tuple(case.case_id for case in resolved_cases) != case_ids:
            raise ValueError("Repack changed the reviewed query order")
        for index, case in enumerate(resolved_cases):
            source_trace, source_summary = source_checkpoint.read(arm_name, index)
            _query_result_from_checkpoint(case, source_trace, source_summary)
            result = _repack_single_query_from_trace(
                runtime,
                case,
                trace_data=source_trace,
                summary=source_summary,
                components=components,
                generation_budget=generation_budget,
                count_tokens=count_tokens,
                counter_id=counter_id,
                system_prompt=system_prompt,
                context_packing_version=_CONTEXT_PACKING_VERSION,
            )
            if any(result["invariants"].values()):
                raise ValueError("Repack query invariants did not pass")
            checkpoint.begin(arm_name, index, case.case_id)
            checkpoint.complete(
                arm_name,
                index,
                case.case_id,
                trace=result["trace"],
                summary=_query_checkpoint_summary(case, result),
            )
    checkpoint.finish()

    report = _run_in_directory(
        snapshot,
        model_paths=model_paths,
        embedding=embedding,
        reranker=reranker,
        artifact_dir=staging,
        conversation_fixture=None,
        conversation_fixture_path=None,
        verified_model_manifest_bytes=verified_model_manifest_bytes,
        resume=True,
        replay_only=True,
        repack_source=repack_source,
    )
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(
            f"Combination repack destination appeared during run: {destination}"
        )
    os.rename(staging, destination)
    return report
