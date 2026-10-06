"""Synthetic integration tests for the controlled local retrieval experiment."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from kotaemon.base import Document, DocumentWithEmbedding
from kotaemon.embeddings import BaseEmbeddings
from kotaemon.indices.knowledge.evaluation import local_experiment
from kotaemon.indices.knowledge.evaluation.local_experiment import (
    _AuditedReranker,
    _HashedFeatureEmbeddings,
    _SnapshotCatalog,
    _build_chunk_documents,
    _make_bundle,
    _run_arm,
    _service,
    run_local_experiment,
)
from kotaemon.indices.knowledge.evaluation.local_models import (
    LocalModelMetadata,
    LocalModelPaths,
)
from kotaemon.indices.knowledge.evaluation.local_ingest import DraftChunk
from kotaemon.indices.knowledge.evaluation.local_snapshot import load_local_snapshot
from kotaemon.indices.knowledge.planning.query_planner import KnowledgeSource
from kotaemon.indices.rankings import BaseReranking
from kotaemon.storages import InMemoryDocumentStore, InMemoryVectorStore


def _json_bytes(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode() + b"\n"


def _jsonl_bytes(rows):
    return b"".join(_json_bytes(row) for row in rows)


def _write_reviewed_snapshot(
    root: Path,
    *,
    path: str | None = None,
    filters: dict[str, str] | None = None,
    splitter_configuration: dict | None = None,
    source0_text: str | None = None,
    source_types: list[str] | None = None,
) -> tuple[Path, tuple[str, ...]]:
    root.mkdir()
    sources = []
    units = []
    chunks = []
    provenance = []
    source_ids = []
    for index in range(7):
        relative_path = f"collection/doc-{index}.md"
        source_bytes = f"generated synthetic source {index}".encode()
        source_id = hashlib.sha256(source_bytes).hexdigest()
        source_ids.append(source_id)
        text = source0_text or (
            "alpha unique target phrase"
            if index == 0
            else f"unrelated synthetic source content {index}"
        )
        unit_id = f"unit-{index}"
        locator = {"page_label": "1"}
        sources.append(
            {
                "source_id": source_id,
                "relative_path": relative_path,
                "sha256": source_id,
                "suffix": ".md",
                "byte_size": len(source_bytes),
                "duplicate_of": None,
                "selected_reader": "TxtReader",
                "reader_attempts": ["TxtReader"],
                "reader_fallback_used": False,
                "reader_granularity": "document",
                "status": "parsed",
            }
        )
        units.append(
            {
                "unit_id": unit_id,
                "source_id": source_id,
                "relative_path": relative_path,
                "unit_ordinal": 0,
                "locator": locator,
                "text": text,
                "normalized_text": text,
            }
        )
        chunks.append(
            {
                "chunk_id": f"snapshot-chunk-{index}",
                "source_id": source_id,
                "relative_path": relative_path,
                "unit_id": unit_id,
                "unit_ordinal": 0,
                "chunk_ordinal": 0,
                "locator": locator,
                "text": text,
                "char_start": 0,
                "char_end": len(text),
            }
        )
        provenance.append(
            {
                "source_id": source_id,
                "repository_path": f"synthetic-sources/{relative_path}",
                "sha256": source_id,
            }
        )

    splitter_configuration = splitter_configuration or {
        "version": "main-token-only-v1",
        "name": "TokenSplitter",
        "chunk_size": 1024,
        "chunk_overlap": 256,
        "separator": "\n\n",
        "backup_separators": ["\n", ".", " ", "\u200b"],
    }
    records = {
        "schema_version": 1,
        "parser_configuration": {".md": "TxtReader"},
        "splitter_configuration": splitter_configuration,
        "sources": sources,
        "source_units": units,
        "chunks": chunks,
        "topic_candidates": [],
        "topic_review_source_ids": [],
        "quality": {
            "empty_locators": [],
            "unusable_locators": [],
            "reader_diagnostics": [],
            "extraction_failures": [],
            "chunk_mapping_issues": [],
            "pages": [],
            "sheets": [],
        },
        "excluded_inputs": [],
    }
    judgment = {
        "schema_version": 1,
        "id": "q-alpha",
        "query": "alpha unique target phrase",
        "judgment_level": "source",
        "relevant_ids": [source_ids[0]],
        "disallowed_source_ids": source_ids[1:],
        "allowed_source_ids": None,
        "path": path,
        "source_types": ["markdown"] if source_types is None else source_types,
        "filters": filters,
        "case_kind": "named",
    }
    anchor = {
        "schema_version": 1,
        "id": "anchor-alpha",
        "query_id": "q-alpha",
        "source_id": source_ids[0],
        "source_sha256": source_ids[0],
        "unit_id": "unit-0",
        "locator": {"page_label": "1"},
        "char_start": 0,
        "char_end": len("alpha unique target phrase"),
        "evidence_sha256": hashlib.sha256(b"alpha unique target phrase").hexdigest(),
    }
    payloads = {
        "records.json": _json_bytes(records),
        "judgments.jsonl": _jsonl_bytes([judgment]),
        "anchors.jsonl": _jsonl_bytes([anchor]),
    }
    for name, data in payloads.items():
        (root / name).write_bytes(data)
    manifest = {
        "schema_version": 1,
        "snapshot_version": root.name,
        "schema_versions": {"records": 1, "judgments": 1, "anchors": 1},
        "payload_sha256": {
            name: hashlib.sha256(data).hexdigest() for name, data in payloads.items()
        },
        "review_status": "approved",
        "review_date": "2026-10-03",
        "source_root": "synthetic-sources",
        "source_provenance": provenance,
        "parser_configuration": records["parser_configuration"],
        "splitter_configuration": records["splitter_configuration"],
        "counts": {
            "source_paths": len(sources),
            "documents": len(sources),
            "source_units": len(units),
            "chunks": len(chunks),
            "queries": 1,
            "anchors": 1,
        },
    }
    (root / "manifest.json").write_bytes(_json_bytes(manifest))
    return root, tuple(source_ids)


@pytest.fixture
def synthetic_snapshot(tmp_path):
    root, source_ids = _write_reviewed_snapshot(tmp_path / "reviewed-v1")
    return load_local_snapshot(root), source_ids


@pytest.fixture
def fake_local_models(monkeypatch, tmp_path):
    paths = LocalModelPaths(
        embedding_model_dir=tmp_path / "fake-embedding",
        reranker_model_dir=tmp_path / "fake-reranker",
        embedding_revision="synthetic-embedding-revision",
        embedding_weight_source="downloaded",
        reranker_revision="synthetic-reranker-revision",
        reranker_weight_source="cached",
    )
    paths.embedding_model_dir.mkdir()
    paths.reranker_model_dir.mkdir()

    class Embedding(BaseEmbeddings):
        def run(self, text, *args, **kwargs):
            documents = self.prepare_input(text)
            return [
                DocumentWithEmbedding(content=document, embedding=[1.0, 0.0, 0.0])
                for document in documents
            ]

    class Reranker(BaseReranking):
        def __init__(self):
            super().__init__()
            object.__setattr__(self, "inputs", [])
            object.__setattr__(
                self,
                "metadata",
                LocalModelMetadata(
                    model_id="synthetic/reranker",
                    revision="synthetic-reranker-revision",
                    weights_sha256=(("model.safetensors", "a" * 64),),
                    device="cpu",
                    flag_embedding_version="synthetic-version",
                    query_max_length=64,
                    passage_max_length=128,
                    weight_source="cached",
                ),
            )

        def run(self, documents, query):
            ids = [document.doc_id for document in documents]
            self.inputs.append(ids)
            return list(reversed(documents))

    embedding = Embedding()
    reranker = Reranker()
    object.__setattr__(
        embedding,
        "metadata",
        LocalModelMetadata(
            model_id="synthetic/embedding",
            revision="synthetic-embedding-revision",
            weights_sha256=(("model.safetensors", "b" * 64),),
            device="cpu",
            flag_embedding_version="synthetic-version",
            query_max_length=64,
            passage_max_length=128,
            weight_source="downloaded",
        ),
    )
    monkeypatch.setattr(
        "kotaemon.indices.knowledge.evaluation.local_experiment._create_embedding",
        lambda model_dir, *, revision, weight_source: (
            embedding
            if model_dir == paths.embedding_model_dir
            and revision == paths.embedding_revision
            and weight_source == paths.embedding_weight_source
            else pytest.fail("embedding provenance was not forwarded")
        ),
    )
    monkeypatch.setattr(
        "kotaemon.indices.knowledge.evaluation.local_experiment._create_reranker",
        lambda model_dir, *, revision, weight_source: (
            reranker
            if model_dir == paths.reranker_model_dir
            and revision == paths.reranker_revision
            and weight_source == paths.reranker_weight_source
            else pytest.fail("reranker provenance was not forwarded")
        ),
    )
    return paths, embedding, reranker


def test_four_arm_runner_preserves_source_scoring_and_reranker_candidates(
    synthetic_snapshot, fake_local_models, tmp_path
):
    snapshot, source_ids = synthetic_snapshot
    paths, _, fake_reranker = fake_local_models
    artifact_dir = tmp_path / "run"

    report = run_local_experiment(
        snapshot,
        model_paths=paths,
        artifact_dir=artifact_dir,
    )

    assert set(report.arms) == {"baseline", "chunking", "embedding", "reranker"}
    assert report.k == 5
    assert report.candidate_k == 20
    assert report.query_count == 1
    assert all(arm.query_count == 1 for arm in report.arms.values())
    assert all(arm.metrics.k == 5 for arm in report.arms.values())
    assert all(arm.metrics.judged_query_count == 1 for arm in report.arms.values())
    assert all(
        arm.vector_candidate_counts["q-alpha"] == 7
        and arm.vector_candidate_counts["q-alpha"] < report.candidate_k
        for arm in report.arms.values()
    )

    baseline = report.arms["baseline"]
    reranker = report.arms["reranker"]
    candidate_ids = baseline.vector_candidate_ids["q-alpha"]
    assert len(candidate_ids) == len(set(candidate_ids))
    assert reranker.vector_candidate_ids["q-alpha"] == candidate_ids
    assert reranker.input_candidate_ids["q-alpha"] == candidate_ids
    assert fake_reranker.inputs == [list(candidate_ids)]
    assert reranker.final_result_ids["q-alpha"] == tuple(reversed(candidate_ids))

    # The report's source metric is a distinct-source projection at K=5.
    assert len(baseline.metrics.per_query[0].result_ids) <= 5
    assert baseline.metrics.hit_at_k == 1.0
    assert baseline.metrics.recall_at_k == 1.0
    assert baseline.metrics.per_query[0].wrong_scope_denominator == 5
    assert baseline.metrics.per_query[0].wrong_scope_numerator == 4
    assert report.wrong_scope_numerators["baseline"] == 4
    assert report.wrong_scope_denominators["baseline"] == 5
    assert report.metric_deltas["reranker"]["hit_at_k"] == -1.0
    assert baseline.anchor_coverage.total_anchors == 1
    assert baseline.anchor_coverage.covered_anchors == 1
    assert baseline.anchor_coverage.rate == 1.0
    assert all(arm.anchor_coverage.total_anchors == 1 for arm in report.arms.values())
    assert reranker.anchor_coverage.total_anchors == 1
    assert reranker.anchor_coverage.covered_anchors == 0
    assert all(
        arm.anchor_coverage_cutoff == "top_5_distinct_sources_per_query"
        for arm in report.arms.values()
    )

    expected_components = {
        "chunking": "chunking",
        "embedding": "embedding",
        "reranker": "reranker",
    }
    base_config = baseline.component_config
    for arm_name, changed_component in expected_components.items():
        candidate_config = report.arms[arm_name].component_config
        differences = {
            key for key in base_config if base_config[key] != candidate_config[key]
        }
        assert differences == {changed_component}
    assert all(arm.config_fingerprint for arm in report.arms.values())
    assert report.metric_deltas["baseline"]["hit_at_k"] == 0.0

    for arm in report.arms.values():
        trace_path = artifact_dir / arm.trace_artifacts["q-alpha"]
        trace = json.loads(trace_path.read_text(encoding="utf-8"))
        assert trace["original_query"] == "alpha unique target phrase"
        assert trace["explicit_filters"] == {
            "path": None,
            "source_types": ["markdown"],
            "metadata_filters": {},
        }
        assert trace["plan"]["virtual_paths"] == []
        assert trace["plan"]["source_ids"] is None
        assert trace["plan"]["source_types"] == ["markdown"]
        assert "collection" not in trace_path.read_text(encoding="utf-8")
        assert trace["scope_fallback"] is False
        attempts = trace["attempts"]
        assert len(attempts) == 1
        traced_candidates = tuple(
            item["id"] for item in attempts[0]["vector_candidates"]
        )
        assert traced_candidates == arm.vector_candidate_ids["q-alpha"]
        assert trace["merged_ids"] == list(arm.vector_candidate_ids["q-alpha"])

    assert report.artifact_manifest
    assert all(
        (artifact_dir / item["path"]).is_file() for item in report.artifact_manifest
    )
    serialized_report = json.loads(
        (artifact_dir / "report.json").read_text(encoding="utf-8")
    )
    assert serialized_report["arms"]["baseline"]["vector_candidate_counts"] == {
        "q-alpha": 7
    }
    assert serialized_report["arms"]["baseline"]["anchor_coverage"] == {
        "cutoff": "top_5_distinct_sources_per_query",
        "total_anchors": 1,
        "covered_anchors": 1,
        "uncovered_anchors": 0,
        "unresolved_anchors": 0,
        "coverage_denominator": 1,
        "uncovered_anchor_ids": [],
        "unresolved_anchor_ids": [],
        "denominator_semantics": "covered / (covered + uncovered); unresolved excluded",
        "rate": 1.0,
    }
    assert serialized_report["arms"]["embedding"]["component_config"]["embedding"][
        "metadata"
    ]["weights_sha256"] == [["model.safetensors", "b" * 64]]
    assert (
        serialized_report["arms"]["embedding"]["component_config"]["embedding"][
            "metadata"
        ]["revision"]
        == paths.embedding_revision
    )
    assert (
        serialized_report["arms"]["embedding"]["component_config"]["embedding"][
            "metadata"
        ]["weight_source"]
        == paths.embedding_weight_source
    )
    assert (
        "model_dir"
        not in serialized_report["arms"]["embedding"]["component_config"]["embedding"]
    )
    assert (
        serialized_report["arms"]["reranker"]["component_config"]["reranker"][
            "metadata"
        ]["query_max_length"]
        == 64
    )
    serialized_manifest = json.loads(
        (artifact_dir / "artifact-manifest.json").read_text(encoding="utf-8")
    )
    assert serialized_manifest["arm_configurations"]["embedding"]["component_config"][
        "embedding"
    ]["metadata"]["weights_sha256"] == [["model.safetensors", "b" * 64]]


def test_anchor_coverage_reports_ambiguous_repeated_chunk_offsets_as_unresolved(
    tmp_path,
):
    repeated_text = "alpha unique target phrase " * 1500
    snapshot_root, _ = _write_reviewed_snapshot(
        tmp_path / "reviewed-ambiguous-chunk",
        source0_text=repeated_text,
    )
    snapshot = load_local_snapshot(snapshot_root)
    chunks, chunk_to_source, _, _, draft_chunks, unresolved_offsets = (
        _build_chunk_documents(snapshot, chunking_arm=False)
    )
    source_chunks = [
        chunk
        for chunk in chunks
        if chunk_to_source[chunk.doc_id] == snapshot.anchors[0].source_id
    ]

    coverage = local_experiment._anchor_coverage_for_results(
        snapshot.anchors,
        source_chunks,
        chunk_to_source,
        draft_chunks,
        unresolved_offsets,
    )

    assert coverage.total_anchors == 1
    assert coverage.covered_anchors == 0
    assert coverage.uncovered_anchor_ids == ()
    assert coverage.unresolved_anchor_ids == ("anchor-alpha",)
    assert coverage.rate is None


def test_anchor_coverage_checks_later_chunks_in_top_five_sources(synthetic_snapshot):
    snapshot, source_ids = synthetic_snapshot
    anchor = snapshot.anchors[0]
    ranked_chunks = [
        Document(text="first chunk", id_="source-0-first"),
        Document(text="later chunk", id_="source-0-later"),
        *[
            Document(text=f"source {index}", id_=f"source-{index}")
            for index in range(1, 6)
        ],
    ]
    chunk_to_source = {
        "source-0-first": source_ids[0],
        "source-0-later": source_ids[0],
        **{f"source-{index}": source_ids[index] for index in range(1, 6)},
    }
    draft_chunks = {
        "source-0-first": DraftChunk(
            chunk_id="source-0-first",
            source_id=source_ids[0],
            relative_path="collection/doc-0.md",
            unit_id="unit-0",
            unit_ordinal=0,
            chunk_ordinal=0,
            locator=dict(anchor.locator),
            text="first chunk",
            char_start=anchor.char_end + 5,
            char_end=anchor.char_end + 16,
        ),
        "source-0-later": DraftChunk(
            chunk_id="source-0-later",
            source_id=source_ids[0],
            relative_path="collection/doc-0.md",
            unit_id="unit-0",
            unit_ordinal=0,
            chunk_ordinal=1,
            locator=dict(anchor.locator),
            text="later chunk",
            char_start=0,
            char_end=anchor.char_end,
        ),
    }

    coverage = local_experiment._anchor_coverage_for_results(
        (anchor,),
        ranked_chunks,
        chunk_to_source,
        draft_chunks,
        {},
    )

    assert coverage.covered_anchors == 1
    assert coverage.uncovered_anchor_ids == ()
    assert coverage.unresolved_anchor_ids == ()


def test_empty_vector_attempt_is_a_valid_zero_candidate_trace():
    trace_data = {
        "events": [],
        "scope_fallback": False,
        "candidate_k": 20,
        "attempts": [
            {
                "vector_status": "empty",
                "lexical_status": "not_used",
                "vector_candidates": [],
            }
        ],
        "merged_ids": [],
    }

    assert local_experiment._trace_candidate_ids(trace_data, "q-empty") == ()


@pytest.mark.parametrize("include_empty_call", [False, True])
def test_empty_vector_attempt_allows_optional_reranker_call(
    synthetic_snapshot, tmp_path, include_empty_call
):
    snapshot, source_ids = synthetic_snapshot
    source_id = source_ids[0]
    reranker_delegate = type(
        "RerankerDelegate",
        (),
        {"run": lambda self, documents, query: documents},
    )()
    audited_reranker = _AuditedReranker(reranker_delegate)
    bundle = {
        "vector_store": InMemoryVectorStore(),
        "doc_store": InMemoryDocumentStore(),
        "embedding": _HashedFeatureEmbeddings(),
        "catalog": _SnapshotCatalog(
            [
                KnowledgeSource(
                    source_id=source_id,
                    source_type="markdown",
                    virtual_path="/",
                    entity={},
                )
            ],
            {source_id: ("not-indexed-chunk",)},
        ),
    }

    arm = _run_arm(
        "empty-window",
        {},
        _service(
            bundle,
            rerankers=(audited_reranker,) if include_empty_call else (),
        ),
        [snapshot.judgments.cases[0]],
        {"not-indexed-chunk": source_id},
        {},
        {},
        (),
        artifact_dir=tmp_path / "empty-attempt-run",
        audited_reranker=audited_reranker,
    )

    assert arm.vector_candidate_counts["q-alpha"] == 0
    assert arm.input_candidate_ids["q-alpha"] == ()
    expected_calls = [("alpha unique target phrase", ())] if include_empty_call else []
    assert audited_reranker.calls == expected_calls
    trace = json.loads(
        (tmp_path / "empty-attempt-run" / arm.trace_artifacts["q-alpha"]).read_text(
            encoding="utf-8"
        )
    )
    assert trace["attempts"][0]["vector_status"] == "empty"
    assert trace["attempts"][0]["vector_candidates"] == []


def test_explicit_no_match_is_scored_as_zero_without_reranking(
    tmp_path, fake_local_models
):
    snapshot_root, _ = _write_reviewed_snapshot(
        tmp_path / "reviewed-no-match",
        source_types=["pdf"],
    )
    snapshot = load_local_snapshot(snapshot_root)
    paths, _, fake_reranker = fake_local_models
    artifact_dir = tmp_path / "no-match-run"

    report = run_local_experiment(
        snapshot,
        model_paths=paths,
        artifact_dir=artifact_dir,
    )

    assert report.query_count == 1
    for arm in report.arms.values():
        assert arm.vector_candidate_counts["q-alpha"] == 0
        assert arm.final_result_ids["q-alpha"] == ()
        assert arm.metrics.hit_at_k == 0.0
        trace = json.loads(
            (artifact_dir / arm.trace_artifacts["q-alpha"]).read_text(encoding="utf-8")
        )
        assert trace["search_status"] == "not_run"
        assert trace["no_search_reason"] == "explicit_filters_no_match"
        assert [
            event for event in trace["events"] if event["stage"] == "no_search"
        ] == [{"stage": "no_search", "reason": "explicit_filters_no_match"}]
    assert report.arms["reranker"].input_candidate_ids["q-alpha"] == ()
    assert fake_reranker.inputs == []


def test_local_model_factories_forward_verified_provenance_without_loading_weights(
    monkeypatch, tmp_path
):
    calls = {}

    class CaptureEmbeddingAdapter:
        def __init__(self, **kwargs):
            calls["embedding"] = kwargs

    class CaptureRerankerAdapter:
        def __init__(self, **kwargs):
            calls["reranker"] = kwargs

    monkeypatch.setattr(local_experiment, "BgeM3Embeddings", CaptureEmbeddingAdapter)
    monkeypatch.setattr(local_experiment, "BgeM3Reranking", CaptureRerankerAdapter)
    embedding_dir = tmp_path / "embedding"
    reranker_dir = tmp_path / "reranker"

    local_experiment._create_embedding(
        embedding_dir,
        revision="embedding-commit-sha",
        weight_source="downloaded",
    )
    local_experiment._create_reranker(
        reranker_dir,
        revision="reranker-commit-sha",
        weight_source="cached",
    )

    assert calls["embedding"] == {
        "model_path": embedding_dir,
        "revision": "embedding-commit-sha",
        "weight_source": "downloaded",
    }
    assert calls["reranker"] == {
        "model_path": reranker_dir,
        "revision": "reranker-commit-sha",
        "weight_source": "cached",
    }


def test_missing_model_provenance_fails_before_factory_or_artifacts(
    synthetic_snapshot, monkeypatch, tmp_path
):
    snapshot, _ = synthetic_snapshot
    calls = []
    monkeypatch.setattr(
        local_experiment,
        "_create_embedding",
        lambda *args, **kwargs: calls.append("embedding"),
    )
    monkeypatch.setattr(
        local_experiment,
        "_create_reranker",
        lambda *args, **kwargs: calls.append("reranker"),
    )
    artifact_dir = tmp_path / "missing-provenance"

    with pytest.raises(ValueError, match="verified model revision and weight source"):
        run_local_experiment(
            snapshot,
            model_paths=LocalModelPaths(
                embedding_model_dir=tmp_path / "embedding",
                reranker_model_dir=tmp_path / "reranker",
            ),
            artifact_dir=artifact_dir,
        )

    assert calls == []
    assert not artifact_dir.exists()


def test_failed_run_does_not_publish_staged_trace_artifacts(
    synthetic_snapshot, fake_local_models, monkeypatch, tmp_path
):
    snapshot, _ = synthetic_snapshot
    paths, _, _ = fake_local_models
    artifact_dir = tmp_path / "atomic-run"
    staged_trace_paths = []
    original_run_arm = local_experiment._run_arm

    def fail_after_staging_trace(name, *args, **kwargs):
        arm = original_run_arm(name, *args, **kwargs)
        if name == "baseline":
            stage_dir = kwargs["artifact_dir"]
            staged_trace_paths.append(stage_dir / arm.trace_artifacts["q-alpha"])
            assert staged_trace_paths[-1].is_file()
            raise RuntimeError("synthetic failure after trace staging")
        return arm

    monkeypatch.setattr(local_experiment, "_run_arm", fail_after_staging_trace)

    with pytest.raises(RuntimeError, match="after trace staging"):
        run_local_experiment(
            snapshot,
            model_paths=paths,
            artifact_dir=artifact_dir,
        )

    assert staged_trace_paths and not staged_trace_paths[0].exists()
    assert not artifact_dir.exists()
    assert not list(tmp_path.glob(".atomic-run.staging-*"))


def test_physical_source_directories_do_not_become_virtual_paths(
    synthetic_snapshot,
):
    snapshot, _ = synthetic_snapshot
    bundle = _make_bundle(
        snapshot,
        embedding=_HashedFeatureEmbeddings(),
        chunking_arm=False,
    )

    assert all(
        source.virtual_path == "/" for source in bundle["catalog"].list_sources()
    )
    assert all(
        document.metadata["virtual_path"] == "/" for document in bundle["chunks"]
    )
    assert all("collection" not in document.metadata for document in bundle["chunks"])


@pytest.mark.parametrize(
    ("path", "filters"),
    [("/collection", None), (None, {"topic": "alpha"})],
)
def test_runner_rejects_unreviewed_path_or_metadata_filters_before_artifacts(
    tmp_path, path, filters
):
    snapshot_root, _ = _write_reviewed_snapshot(
        tmp_path / "reviewed-with-unreviewed-scope",
        path=path,
        filters=filters,
    )
    snapshot = load_local_snapshot(snapshot_root)
    artifact_dir = tmp_path / "must-not-be-created"
    model_paths = LocalModelPaths(
        embedding_model_dir=tmp_path / "unread-embedding",
        reranker_model_dir=tmp_path / "unread-reranker",
    )

    with pytest.raises(ValueError, match="reviewed logical metadata"):
        run_local_experiment(
            snapshot,
            model_paths=model_paths,
            artifact_dir=artifact_dir,
        )

    assert not artifact_dir.exists()


@pytest.mark.parametrize(
    "splitter_configuration",
    [
        {
            "version": "different-v1",
            "name": "TokenSplitter",
            "chunk_size": 1024,
            "chunk_overlap": 256,
            "separator": "\n\n",
            "backup_separators": ["\n", ".", " ", "\u200b"],
        },
        {
            "version": "main-token-only-v1",
            "name": "TokenSplitter",
            "chunk_size": 512,
            "chunk_overlap": 256,
            "separator": "\n\n",
            "backup_separators": ["\n", ".", " ", "\u200b"],
        },
        {
            "version": "main-token-only-v1",
            "name": "TokenSplitter",
            "chunk_size": 1024,
            "chunk_overlap": 128,
            "separator": "\n\n",
            "backup_separators": ["\n", ".", " ", "\u200b"],
        },
        {
            "version": "main-token-only-v1",
            "name": "TokenSplitter",
            "chunk_size": 1024,
            "chunk_overlap": 256,
            "separator": " ",
            "backup_separators": ["\n", ".", " ", "\u200b"],
        },
    ],
)
def test_runner_rejects_baseline_splitter_config_mismatch_before_artifacts(
    tmp_path, splitter_configuration
):
    snapshot_root, _ = _write_reviewed_snapshot(
        tmp_path / "reviewed-with-other-splitter",
        splitter_configuration=splitter_configuration,
    )
    snapshot = load_local_snapshot(snapshot_root)
    artifact_dir = tmp_path / "must-not-be-created"

    with pytest.raises(ValueError, match="baseline splitter configuration"):
        run_local_experiment(
            snapshot,
            model_paths=LocalModelPaths(
                embedding_model_dir=tmp_path / "unused-embedding",
                reranker_model_dir=tmp_path / "unused-reranker",
            ),
            artifact_dir=artifact_dir,
        )

    assert not artifact_dir.exists()
