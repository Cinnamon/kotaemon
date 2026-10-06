"""Supplemental evaluation of the pre-RRF lexical-first hybrid baseline."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import tempfile
import uuid
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

from kotaemon.base import RetrievedDocument
from kotaemon.indices.knowledge.evaluation.local_snapshot import LocalSnapshot
from kotaemon.indices.knowledge.evaluation.retrieval_eval import (
    IndexedCatalog,
    resolve_judgments,
)
from kotaemon.indices.knowledge.evaluation.source_metrics import (
    score_candidate_recall,
    score_source_run,
    source_ranked_chunks,
)
from kotaemon.indices.knowledge.retrieval.contracts import RetrievalPolicy
from kotaemon.storages.docstores.sqlite_fts import SQLiteFTSDocumentStore

from .combination_arms import CANDIDATE_K, MAX_FUSED_CANDIDATES, SOURCE_K
from .combination_runner import _snapshot_file_hashes
from .snapshot_adapter import build_snapshot_replay_runtime


_ARM_TEMPLATE = {
    "merge": "lexical_first_stable_id_dedup",
    "candidate_k_per_route": CANDIDATE_K,
    "max_merged_candidates": MAX_FUSED_CANDIDATES,
    "source_k": SOURCE_K,
    "lexical_backend": "sqlite_fts5",
    "embedding_model": "BAAI/bge-m3",
    "rrf": False,
    "reranker": False,
    "query_enrichment": False,
    "evidence_expansion": False,
}


def legacy_lexical_first_merge(
    lexical_ids: Sequence[str], vector_ids: Sequence[str], *, limit: int
) -> list[str]:
    """Preserve pre-v3 lexical-first order and stable ID deduplication."""
    if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
        raise ValueError("limit must be a positive integer")
    if any(not isinstance(value, str) or not value for value in (*lexical_ids, *vector_ids)):
        raise ValueError("candidate IDs must be non-empty strings")
    return list(dict.fromkeys((*lexical_ids, *vector_ids)))[:limit]


def supplemental_arm_configs() -> dict[str, dict[str, Any]]:
    """Return the original-chunking baseline and one chunking bridge arm."""
    return {
        "token_legacy_hybrid": {
            **_ARM_TEMPLATE,
            "chunking_mode": "token",
            "chunk_size_tokens": 1024,
            "chunk_overlap_tokens": 256,
            "comparison": "original_system_baseline",
        },
        "registry_legacy_hybrid": {
            **_ARM_TEMPLATE,
            "chunking_mode": "registry",
            "fallback_chunk_size_tokens": 1024,
            "fallback_chunk_overlap_tokens": 256,
            "comparison": "chunking_bridge_vs_token_legacy_hybrid",
        },
    }


def _fingerprint(value: Any) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, allow_nan=False, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _validate_reference_identity(
    report: Mapping[str, Any],
    checkpoint: Mapping[str, Any],
    artifact_manifest: Mapping[str, Any],
    *,
    expected_snapshot_fingerprint: str,
    expected_gold_fingerprint: str,
    expected_model_manifest_sha256: str,
) -> None:
    """Fail closed unless report, checkpoint, manifest, and current inputs agree."""
    for name, expected in (
        ("snapshot", expected_snapshot_fingerprint),
        ("gold", expected_gold_fingerprint),
    ):
        report_value = report.get(f"{name}_fingerprint")
        checkpoint_value = (checkpoint.get("fingerprints") or {}).get(name)
        manifest_value = artifact_manifest.get(f"{name}_fingerprint")
        if report_value != expected or checkpoint_value != expected or manifest_value != expected:
            raise ValueError(f"reference {name} fingerprint does not match the approved inputs")

    report_model = report.get("model_fingerprint")
    checkpoint_model = (checkpoint.get("fingerprints") or {}).get("model")
    manifest_model = artifact_manifest.get("model_fingerprint")
    if not report_model or report_model != checkpoint_model or report_model != manifest_model:
        raise ValueError("reference model fingerprint is inconsistent")
    model_manifest = report.get("model_manifest")
    if not isinstance(model_manifest, Mapping) or _fingerprint(model_manifest) != report_model:
        raise ValueError("reference model manifest fingerprint is inconsistent")
    if (artifact_manifest.get("inputs") or {}).get("model_manifest_sha256") != expected_model_manifest_sha256:
        raise ValueError("reference model-manifest digest does not match the verified local manifest")
    if artifact_manifest.get("run_id") != report.get("run_id") or checkpoint.get("run_id") != report.get("run_id"):
        raise ValueError("reference run identity is inconsistent")


def _verify_artifact_entries(root: Path, entries: Sequence[Mapping[str, Any]]) -> None:
    """Verify every listed reference artifact without following links or escapes."""
    resolved_root = Path(root).resolve(strict=True)
    seen_paths: set[str] = set()
    for item in entries:
        relative = item.get("path")
        if not isinstance(relative, str) or not relative or "\\" in relative:
            raise ValueError("reference artifact path is invalid")
        pure = PurePosixPath(relative)
        if pure.is_absolute() or any(part in {"", ".", ".."} for part in relative.split("/")):
            raise ValueError("reference artifact path escapes its root")
        if relative in seen_paths:
            raise ValueError("reference artifact manifest contains a duplicate path")
        seen_paths.add(relative)
        path = resolved_root
        for part in pure.parts:
            path = path / part
            try:
                mode = path.lstat().st_mode
            except OSError as error:
                raise ValueError("reference artifact is missing") from error
            if stat.S_ISLNK(mode):
                raise ValueError("reference artifact path contains a symlink")
        if not stat.S_ISREG(mode):
            raise ValueError("reference artifact must be a regular file")
        payload = path.read_bytes()
        digest = item.get("sha256")
        size = item.get("size_bytes")
        if (
            isinstance(size, bool)
            or not isinstance(size, int)
            or size < 0
            or len(payload) != size
            or not isinstance(digest, str)
            or hashlib.sha256(payload).hexdigest() != digest
        ):
            raise ValueError("reference artifact size or digest mismatch")


def _legacy_hybrid_query(
    runtime,
    docstore: SQLiteFTSDocumentStore,
    case,
    *,
    vector_candidate_ids: Sequence[str],
    candidate_k: int,
    max_candidates: int,
):
    """Return lexical-first ID-deduplicated candidates, without post-fusion ranking."""
    allowed_ids = runtime.service.authorized_chunk_ids(
        path=case.path,
        source_types=case.source_types,
        filters=case.filters,
        allowed_source_ids=case.allowed_source_ids,
    )
    if not allowed_ids:
        return (), (), (), ()
    scope = sorted(allowed_ids)
    scope_ids = set(scope)
    selected_vector_ids: list[str] = []
    seen_vector_ids: set[str] = set()
    for chunk_id in vector_candidate_ids:
        if chunk_id not in runtime.chunk_to_source:
            raise ValueError("frozen dense arm returned an unknown chunk ID")
        if chunk_id in scope_ids and chunk_id not in seen_vector_ids:
            selected_vector_ids.append(chunk_id)
            seen_vector_ids.add(chunk_id)
        if len(selected_vector_ids) == candidate_k:
            break
    vector_docs = [
        RetrievedDocument(**document.to_dict(), score=-1.0)
        for document in docstore.get(selected_vector_ids)
    ]
    lexical_results = docstore.query(
        case.query,
        top_k=candidate_k,
        doc_ids=scope,
    )
    lexical_docs = [
        RetrievedDocument(**document.to_dict(), score=-1.0)
        for document in lexical_results
    ]
    merged_ids = legacy_lexical_first_merge(
        [document.doc_id for document in lexical_docs],
        [document.doc_id for document in vector_docs],
        limit=max_candidates,
    )
    documents_by_id = {
        document.doc_id: document for document in (*lexical_docs, *vector_docs)
    }
    merged = [documents_by_id[chunk_id] for chunk_id in merged_ids]
    return (
        tuple(lexical_docs),
        tuple(vector_docs),
        tuple(merged),
        tuple(merged_ids),
    )


def _indexed_catalog(
    sources: Sequence[Mapping[str, Any]], chunk_to_source: Mapping[str, str]
) -> IndexedCatalog:
    """Build the immutable evaluation catalog from the authorized snapshot index."""
    return IndexedCatalog(
        (source["source_id"] for source in sources),
        chunk_to_source,
    )


def _metric_values(metrics: Mapping[str, Any], denominators: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "query_count": metrics["judged_query_count"],
        "hit_at_5": metrics["hit_at_k"],
        "recall_at_5": metrics["recall_at_k"],
        "mrr_at_5": metrics["mrr_at_k"],
        "wrong_scope_at_5": metrics["wrong_scope_at_k"],
        "wrong_scope_numerator": denominators["wrong_scope_numerator"],
        "wrong_scope_denominator": denominators["wrong_scope_denominator"],
    }


def _metric_delta(before: Mapping[str, Any], after: Mapping[str, Any]) -> dict[str, float | None]:
    result: dict[str, float | None] = {}
    for key in ("hit_at_5", "recall_at_5", "mrr_at_5", "wrong_scope_at_5"):
        left, right = before.get(key), after.get(key)
        result[key] = None if left is None or right is None else right - left
    return result


def _read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"reference {label} is unavailable or invalid JSON") from error
    if not isinstance(value, dict):
        raise ValueError(f"reference {label} must be a JSON object")
    return value


def _write_json(path: Path, value: Any) -> bytes:
    payload = (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            allow_nan=False,
            separators=(",", ":"),
        ).encode("utf-8")
        + b"\n"
    )
    path.write_bytes(payload)
    return payload


def run_supplemental_baseline(
    snapshot: LocalSnapshot,
    *,
    reference_report: Mapping[str, Any],
    reference_artifact_dir: Path,
    verified_model_manifest_sha256: str,
    artifact_dir: Path,
) -> dict[str, Any]:
    """Measure the two added arms and compare identities to frozen v3 artifacts.

    Model and snapshot loading/verification remain the caller's responsibility.
    Dense IDs are replayed from the exact frozen v3 dense-only arms, avoiding
    re-embedding and ensuring both arms reuse the same vector candidates.
    """
    if not isinstance(snapshot, LocalSnapshot):
        raise TypeError("snapshot must be a validated LocalSnapshot")
    if (
        not isinstance(verified_model_manifest_sha256, str)
        or len(verified_model_manifest_sha256) != 64
        or any(character not in "0123456789abcdef" for character in verified_model_manifest_sha256)
    ):
        raise ValueError("verified model-manifest SHA-256 is invalid")
    output = Path(artifact_dir).expanduser().resolve(strict=False)
    reference_root = Path(reference_artifact_dir).expanduser().resolve(strict=True)
    if output.exists() or output.is_symlink():
        raise FileExistsError(f"supplemental baseline output already exists: {output}")
    reference_report = dict(reference_report)
    checkpoint = _read_json(reference_root / "run-checkpoint.json", "checkpoint")
    artifact_manifest = _read_json(reference_root / "artifact-manifest.json", "artifact manifest")
    _verify_artifact_entries(reference_root, artifact_manifest.get("artifacts", ()))

    snapshot_hashes = _snapshot_file_hashes(snapshot.root)
    expected_gold = _fingerprint(
        {name: snapshot_hashes[name] for name in ("judgments.jsonl", "anchors.jsonl")}
    )
    _validate_reference_identity(
        reference_report,
        checkpoint,
        artifact_manifest,
        expected_snapshot_fingerprint=snapshot.fingerprint,
        expected_gold_fingerprint=expected_gold,
        expected_model_manifest_sha256=verified_model_manifest_sha256,
    )
    if checkpoint.get("status") != "complete":
        raise ValueError("reference combination run is not complete")
    case_ids = [case.case_id for case in snapshot.judgments.cases]
    if checkpoint.get("case_ids") != case_ids or reference_report.get("query_count") != len(case_ids):
        raise ValueError("reference run does not use the same frozen query set")
    reference_inputs = artifact_manifest.get("inputs", {})
    if reference_inputs.get("approved_snapshot_files") != snapshot_hashes:
        raise ValueError("reference run did not use the same complete snapshot")
    if not isinstance(reference_report.get("arms"), Mapping):
        raise ValueError("reference report has no experiment arms")
    expected_reference_arms = (
        "dense_baseline",
        "registry_chunking",
        "registry_lexical_rrf",
        "registry_reranking",
        "registry_enrichment",
        "registry_expansion",
    )
    for arm_name in expected_reference_arms:
        if arm_name not in reference_report["arms"]:
            raise ValueError(f"reference report is missing the {arm_name} arm")
    if (
        reference_report.get("candidate_cutoff", {}).get("candidate_k_per_route")
        != CANDIDATE_K
        or reference_report.get("candidate_cutoff", {}).get("max_fused_candidates")
        != MAX_FUSED_CANDIDATES
        or reference_report.get("source_k") != SOURCE_K
    ):
        raise ValueError("reference run uses incompatible retrieval cutoffs")

    # The checked-in v2 snapshot declares the same fixed TokenSplitter settings.
    from .local_experiment import _validate_baseline_splitter

    _validate_baseline_splitter(snapshot)

    report_model_path = reference_root / "model-manifest.json"
    try:
        model_manifest_bytes = report_model_path.read_bytes()
    except OSError as error:
        raise ValueError("reference model manifest is missing") from error
    if hashlib.sha256(model_manifest_bytes).hexdigest() != verified_model_manifest_sha256:
        raise ValueError("reference model manifest digest mismatch")

    dense_candidate_ids = {
        "token": reference_report["arms"]["dense_baseline"].get(
            "candidate_chunk_ids", {}
        ),
        "registry": reference_report["arms"]["registry_chunking"].get(
            "candidate_chunk_ids", {}
        ),
    }
    for mode, rows in dense_candidate_ids.items():
        if set(rows) != set(case_ids) or any(
            not isinstance(ids, list)
            or len(ids) > CANDIDATE_K
            or any(not isinstance(chunk_id, str) or not chunk_id for chunk_id in ids)
            for ids in rows.values()
        ):
            raise ValueError(f"frozen {mode} dense arm has invalid candidate IDs")

    configs = supplemental_arm_configs()
    results: dict[str, dict[str, tuple[RetrievedDocument, ...]]] = {}
    candidate_ids: dict[str, dict[str, tuple[str, ...]]] = {}
    details: dict[str, dict[str, Any]] = {}
    arm_summaries: dict[str, dict[str, Any]] = {}
    for arm_name, config in configs.items():
        mode = config["chunking_mode"]
        vector_arm = "dense_baseline" if mode == "token" else "registry_chunking"
        runtime = build_snapshot_replay_runtime(
            snapshot,
            policy=RetrievalPolicy(
                enabled=False,
                candidate_k=CANDIDATE_K,
                max_fused_candidates=MAX_FUSED_CANDIDATES,
            ),
            chunking_mode=mode,
            lexical=True,
            lexical_status="available",
            reranker_available=False,
        )
        docstore = SQLiteFTSDocumentStore()
        try:
            if not getattr(docstore, "supports_lexical_search", False):
                reason = getattr(docstore, "capability_reason", None)
                raise RuntimeError(
                    "SQLite FTS5 lexical search is unavailable"
                    if not reason
                    else f"SQLite FTS5 lexical search is unavailable: {reason}"
                )
            docstore.add(list(runtime.documents))
            resolved_cases = resolve_judgments(
                snapshot.judgments,
                _indexed_catalog(snapshot.selected_sources, runtime.chunk_to_source),
            )
            if tuple(case.case_id for case in resolved_cases) != tuple(case_ids):
                raise ValueError("supplemental arm changed the frozen query order")

            arm_results: dict[str, tuple[RetrievedDocument, ...]] = {}
            arm_candidates: dict[str, tuple[str, ...]] = {}
            arm_details: dict[str, Any] = {}
            for case in resolved_cases:
                lexical_docs, vector_docs, merged_docs, merged_ids = _legacy_hybrid_query(
                    runtime,
                    docstore,
                    case,
                    vector_candidate_ids=dense_candidate_ids[mode][case.case_id],
                    candidate_k=CANDIDATE_K,
                    max_candidates=MAX_FUSED_CANDIDATES,
                )
                if len(merged_ids) != len(set(merged_ids)):
                    raise ValueError("legacy lexical-first merge emitted duplicate IDs")
                arm_results[case.case_id] = merged_docs
                arm_candidates[case.case_id] = merged_ids
                selected_sources = source_ranked_chunks(
                    merged_docs,
                    runtime.chunk_to_source,
                    limit=SOURCE_K,
                )
                arm_details[case.case_id] = {
                    "lexical_ids": [item.doc_id for item in lexical_docs],
                    "vector_ids": [item.doc_id for item in vector_docs],
                    "merged_ids": list(merged_ids),
                    "top_source_chunk_ids": [item.doc_id for item in selected_sources],
                    "top_source_ids": [runtime.chunk_to_source[item.doc_id] for item in selected_sources],
                }

            metrics = score_source_run(
                resolved_cases,
                arm_results,
                k=SOURCE_K,
                chunk_to_source=runtime.chunk_to_source,
            )
            candidate_recall = score_candidate_recall(
                resolved_cases,
                arm_candidates,
                runtime.chunk_to_source,
                candidate_k=MAX_FUSED_CANDIDATES,
            )
            denominators = {
                "wrong_scope_numerator": sum(
                    row.wrong_scope_numerator for row in metrics.per_query
                ),
                "wrong_scope_denominator": sum(
                    row.wrong_scope_denominator for row in metrics.per_query
                ),
            }
            serialized_metrics = metrics.to_dict()
            serialized_metrics.pop("per_query", None)
            arm_summaries[arm_name] = {
                "config": {**config, "vector_candidate_source_arm": vector_arm},
                "source_metrics": _metric_values(serialized_metrics, denominators),
                "candidate_recall_at_40": {
                    "numerator": candidate_recall.numerator,
                    "denominator": candidate_recall.denominator,
                    "rate": candidate_recall.rate,
                    "query_count": candidate_recall.query_count,
                },
                "candidate_count": {
                    "indexed_chunk_count": len(runtime.documents),
                    "source_count": len(snapshot.selected_sources),
                    "mean_merged_candidates": sum(map(len, arm_candidates.values()))
                    / len(arm_candidates),
                    "queries_with_lexical_hits": sum(
                        bool(row["lexical_ids"]) for row in arm_details.values()
                    ),
                    "queries_with_vector_hits": sum(
                        bool(row["vector_ids"]) for row in arm_details.values()
                    ),
                },
            }
            results[arm_name] = arm_results
            candidate_ids[arm_name] = arm_candidates
            details[arm_name] = arm_details
        finally:
            docstore.close()

    reference_summaries: dict[str, dict[str, Any]] = {}
    for arm_name in expected_reference_arms:
        arm = reference_report["arms"][arm_name]
        reference_summaries[arm_name] = _metric_values(
            arm["source_metrics"],
            arm["source_metric_denominators"],
        )
    baseline = arm_summaries["token_legacy_hybrid"]["source_metrics"]
    stages = [
        ("baseline", "token_legacy_hybrid", baseline),
        (
            "chunking_1024_256",
            "registry_legacy_hybrid",
            arm_summaries["registry_legacy_hybrid"]["source_metrics"],
        ),
        ("fusion_rrf", "registry_lexical_rrf", reference_summaries["registry_lexical_rrf"]),
        ("cross_encoder_reranker", "registry_reranking", reference_summaries["registry_reranking"]),
        ("query_enrichment", "registry_enrichment", reference_summaries["registry_enrichment"]),
        ("evidence_expansion", "registry_expansion", reference_summaries["registry_expansion"]),
    ]
    stage_rows = []
    for index, (label, name, values) in enumerate(stages):
        previous = None if index == 0 else stages[index - 1][2]
        stage_rows.append(
            {
                "stage": label,
                "arm": name,
                "metrics": values,
                "delta_from_previous": None if previous is None else _metric_delta(previous, values),
                "delta_from_legacy_baseline": _metric_delta(baseline, values),
            }
        )

    final_coverage = reference_report["arms"]["registry_expansion"].get(
        "final_context_anchor_coverage", {}
    )
    report = {
        "schema_version": 1,
        "run_id": f"supplemental-{uuid.uuid4().hex[:12]}",
        "description": "Fixed-token lexical-first hybrid baseline and bridge compared with the frozen v3 pipeline.",
        "evaluation": {
            "snapshot_fingerprint": snapshot.fingerprint,
            "gold_fingerprint": expected_gold,
            "query_count": len(case_ids),
            "document_count": len(snapshot.selected_sources),
            "anchor_count": len(snapshot.anchors),
            "reference_v3_run_id": reference_report["run_id"],
            "reference_v3_report_sha256": hashlib.sha256(
                (reference_root / "report.json").read_bytes()
            ).hexdigest(),
            "model_manifest_sha256": verified_model_manifest_sha256,
            "embedding_model_fingerprint": reference_report["model_fingerprint"],
            "metrics_unit": "distinct source documents at source-level top-5",
        },
        "baseline_definition": {
            **_ARM_TEMPLATE,
            "chunk_size_tokens": 1024,
            "chunk_overlap_tokens": 256,
            "route_order": ["full_text", "vector"],
            "deduplication": "stable chunk ID; retain first occurrence",
            "post_merge_reranking": False,
            "post_merge_text_or_overlap_deduplication": False,
            "source_metric_projection": "first 5 distinct source IDs in merged order",
            "vector_route": "exact candidate IDs replayed from the frozen v3 dense-only arm using the same local BGE-M3 model and same chunking mode",
            "implementation_note": "Controlled replay of the pre-RRF lexical-first merge semantics using the project's current local SQLite FTS5 backend; not a byte-for-byte replay of the historical production FTS engine.",
        },
        "arms": arm_summaries,
        "optimized_v3_arms": reference_summaries,
        "comparison_stages": stage_rows,
        "overall_optimized_delta_from_legacy_baseline": _metric_delta(
            baseline, reference_summaries["registry_expansion"]
        ),
        "final_context_anchor_coverage_v3": {
            key: value
            for key, value in final_coverage.items()
            if key in ("total_anchors", "eligible_anchors", "covered_anchors", "uncovered_anchors", "unresolved_anchors", "context_chunk_count", "rate", "denominator_semantics")
        },
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.staging-", dir=output.parent))
    try:
        details_bytes = _write_json(staging / "private-results.json", details)
        report_bytes = _write_json(staging / "report.json", report)
        entries = []
        for name, payload, kind in (
            ("private-results.json", details_bytes, "private_per_query_chunk_ids"),
            ("report.json", report_bytes, "aggregate_comparison_report"),
        ):
            entries.append(
                {
                    "path": name,
                    "kind": kind,
                    "size_bytes": len(payload),
                    "sha256": hashlib.sha256(payload).hexdigest(),
                }
            )
        _write_json(
            staging / "artifact-manifest.json",
            {
                "run_id": report["run_id"],
                "inputs": {
                    "snapshot_fingerprint": snapshot.fingerprint,
                    "gold_fingerprint": expected_gold,
                    "reference_run_id": reference_report["run_id"],
                    "reference_report_sha256": report["evaluation"]["reference_v3_report_sha256"],
                    "model_manifest_sha256": verified_model_manifest_sha256,
                },
                "artifacts": entries,
            },
        )
        os.replace(staging, output)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return report
