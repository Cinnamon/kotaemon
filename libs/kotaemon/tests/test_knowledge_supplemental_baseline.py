"""Focused tests for the supplemental legacy hybrid baseline."""

from __future__ import annotations

from pathlib import Path

import pytest
from kotaemon.indices.knowledge.evaluation.retrieval_eval import (
    EvaluationCase,
    EvaluationFixture,
    resolve_judgments,
)


def _implementation():
    package_root = Path(__file__).parents[1] / "kotaemon"
    assert (package_root / "indices/knowledge/evaluation/supplemental_baseline.py").is_file(), (
        "supplemental baseline evaluator is not implemented"
    )
    from kotaemon.indices.knowledge.evaluation import supplemental_baseline

    return supplemental_baseline


def test_legacy_merge_is_lexical_first_stable_id_deduplication():
    baseline = _implementation()

    result = baseline.legacy_lexical_first_merge(
        ["shared", "lexical-a", "shared", "lexical-b"],
        ["dense-a", "shared", "dense-b"],
        limit=5,
    )

    assert result == ["shared", "lexical-a", "lexical-b", "dense-a", "dense-b"]


def test_supplemental_arms_exclude_rrf_reranking_and_query_expansion():
    baseline = _implementation()

    arms = baseline.supplemental_arm_configs()

    assert set(arms) == {"token_legacy_hybrid", "registry_legacy_hybrid"}
    assert arms["token_legacy_hybrid"]["chunking_mode"] == "token"
    assert arms["registry_legacy_hybrid"]["chunking_mode"] == "registry"
    assert arms["token_legacy_hybrid"]["chunk_size_tokens"] == 1024
    assert arms["token_legacy_hybrid"]["chunk_overlap_tokens"] == 256
    assert arms["registry_legacy_hybrid"]["fallback_chunk_size_tokens"] == 1024
    assert arms["registry_legacy_hybrid"]["fallback_chunk_overlap_tokens"] == 256
    for config in arms.values():
        assert config["merge"] == "lexical_first_stable_id_dedup"
        assert config["candidate_k_per_route"] == 20
        assert config["max_merged_candidates"] == 40
        assert config["source_k"] == 5
        assert config["lexical_backend"] == "sqlite_fts5"
        assert config["embedding_model"] == "BAAI/bge-m3"
        assert config["rrf"] is False
        assert config["reranker"] is False
        assert config["query_enrichment"] is False
        assert config["evidence_expansion"] is False


def test_reference_identity_mismatch_is_rejected():
    baseline = _implementation()
    report = {
        "run_id": "ref-run",
        "snapshot_fingerprint": "snapshot-a",
        "gold_fingerprint": "gold-a",
        "model_fingerprint": "model-a",
    }
    checkpoint = {
        "run_id": "ref-run",
        "fingerprints": {
            "snapshot": "snapshot-a",
            "gold": "gold-a",
            "model": "model-a",
        },
    }
    artifact_manifest = {
        "run_id": "ref-run",
        "snapshot_fingerprint": "snapshot-a",
        "gold_fingerprint": "gold-a",
        "model_fingerprint": "model-a",
        "inputs": {"model_manifest_sha256": "manifest-a"},
    }

    with pytest.raises(ValueError, match="snapshot fingerprint"):
        baseline._validate_reference_identity(
            report,
            checkpoint,
            artifact_manifest,
            expected_snapshot_fingerprint="different-snapshot",
            expected_gold_fingerprint="gold-a",
            expected_model_manifest_sha256="manifest-a",
        )


def test_reference_artifact_digest_mismatch_is_rejected(tmp_path: Path):
    baseline = _implementation()
    artifact = tmp_path / "report.json"
    artifact.write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="digest mismatch"):
        baseline._verify_artifact_entries(
            tmp_path,
            [{"path": "report.json", "sha256": "0" * 64, "size_bytes": 2}],
        )


def test_snapshot_query_resolution_uses_source_and_chunk_relations():
    baseline = _implementation()
    catalog = baseline._indexed_catalog(
        [{"source_id": "source-a"}], {"chunk-a": "source-a"}
    )
    fixture = EvaluationFixture(
        schema_version=1,
        cases=(
            EvaluationCase(
                case_id="q-1",
                query="find source",
                judgment_level="source",
                relevant_ids=("source-a",),
            ),
        ),
    )

    resolved = resolve_judgments(fixture, catalog)

    assert resolved[0].relevant_ids == ("source-a",)
