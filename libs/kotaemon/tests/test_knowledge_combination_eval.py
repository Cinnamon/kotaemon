"""Synthetic invariants for versioned combination and ablation evaluation."""

from __future__ import annotations

import runpy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest


def _combination_eval():
    from kotaemon.indices.knowledge.evaluation import combination_eval

    return combination_eval


def _fake_local_models(monkeypatch, tmp_path):
    helpers = runpy.run_path(
        str(Path(__file__).with_name("test_knowledge_eval_local_experiment.py"))
    )
    fake_local_models = helpers["fake_local_models"]
    return fake_local_models.__wrapped__(monkeypatch, tmp_path)


def _write_synthetic_snapshot(root):
    helpers = runpy.run_path(
        str(Path(__file__).with_name("test_knowledge_eval_local_experiment.py"))
    )
    return helpers["_write_reviewed_snapshot"](root)


def test_v2_inputs_unchanged_after_combination(tmp_path, monkeypatch):
    combination_eval = _combination_eval()
    snapshot_root = tmp_path / "reviewed-v2"
    _write_synthetic_snapshot(snapshot_root)
    from kotaemon.indices.knowledge.evaluation.local_snapshot import (
        load_local_snapshot,
    )

    snapshot = load_local_snapshot(snapshot_root)
    before = {
        path.name: combination_eval._sha256(path.read_bytes())
        for path in snapshot_root.iterdir()
        if path.is_file()
    }
    model_paths, _embedding, _reranker = _fake_local_models(monkeypatch, tmp_path)

    combination_eval.run_combination_experiment(
        snapshot,
        model_paths=model_paths,
        artifact_dir=tmp_path / "run",
    )

    after = {
        path.name: combination_eval._sha256(path.read_bytes())
        for path in snapshot_root.iterdir()
        if path.is_file()
    }
    assert after == before


def test_arm_configurations_express_only_declared_changes():
    arms = _combination_eval().get_arm_configurations()

    baseline = arms["dense_baseline"]["components"]
    declared = {
        "registry_chunking": "chunking_mode",
        "registry_lexical_rrf": "lexical_rrf",
        "registry_reranking": "reranker",
        "registry_enrichment": "query_enrichment",
        "registry_expansion": "evidence_expansion",
    }
    previous = baseline
    for arm_name, changed_component in declared.items():
        current = arms[arm_name]["components"]
        changed = {key for key in previous if previous[key] != current[key]}
        assert changed == {changed_component}
        previous = current


def test_ablations_disable_exactly_one_final_component():
    arms = _combination_eval().get_arm_configurations()
    final = arms["registry_expansion"]["components"]
    disabled = {
        "ablation_no_chunking": "chunking_mode",
        "ablation_dense_only": "lexical_rrf",
        "ablation_no_reranker": "reranker",
        "ablation_no_enrichment": "query_enrichment",
        "ablation_no_expansion": "evidence_expansion",
    }
    for arm_name, component in disabled.items():
        ablation = arms[arm_name]["components"]
        changed = {key for key in final if final[key] != ablation[key]}
        assert changed == {component}
        assert arms[arm_name]["ablation_of"] == "registry_expansion"
    assert arms["ablation_no_reranker"]["coupled_dependencies"] == [
        "expansion_score_gate_unavailable"
    ]


def test_candidate_recall_precedes_rerank():
    score_candidate_recall = _combination_eval().score_candidate_recall
    case = SimpleNamespace(
        case_id="q1", judgment_level="source", relevant_ids=("source-good",)
    )

    recall = score_candidate_recall(
        (case,),
        {"q1": ("chunk-good", "chunk-other")},
        {"chunk-good": "source-good", "chunk-other": "source-other"},
        candidate_k=20,
    )

    assert recall.numerator == 1
    assert recall.denominator == 1
    assert recall.rate == 1.0


def test_replay_reconstructs_final_document_scores_from_route_trace():
    from kotaemon.indices.knowledge.evaluation.combination_runtime import (
        _ranked_document_scores_from_trace,
    )

    trace = {
        "events": [
            {
                "stage": "recall_route",
                "branch": "dense",
                "candidates": [
                    {"id": "dense-id", "score": 0.25, "score_available": True}
                ],
            },
            {
                "stage": "recall_route",
                "branch": "lexical",
                "candidates": [
                    {"id": "lexical-id", "score": None, "score_available": False}
                ],
            },
        ],
        "final_chunk_ids": ["dense-id", "lexical-id"],
    }

    assert _ranked_document_scores_from_trace(trace) == {
        "dense-id": 0.25,
        "lexical-id": -1.0,
    }


def test_replay_rejects_ambiguous_final_dense_score():
    from kotaemon.indices.knowledge.evaluation.combination_runtime import (
        _ranked_document_scores_from_trace,
    )

    trace = {
        "events": [
            {
                "stage": "recall_route",
                "branch": "dense",
                "candidates": [
                    {"id": "dense-id", "score": None, "score_available": False}
                ],
            }
        ],
        "final_chunk_ids": ["dense-id"],
    }

    with pytest.raises(ValueError, match="score cannot be reconstructed"):
        _ranked_document_scores_from_trace(trace)


def test_repack_uses_trace_rankings_and_applies_exact_request_budget():
    from kotaemon.base import RetrievedDocument
    from kotaemon.indices.knowledge.evaluation.combination_runtime import (
        _repack_single_query_from_trace,
    )
    from kotaemon.indices.knowledge.retrieval.context_budget import GenerationBudget

    document = RetrievedDocument(
        id_="chunk-a",
        text="approved snapshot text",
        metadata={"source_id": "source-a"},
        score=0.25,
    )
    runtime = SimpleNamespace(
        documents=(document,),
        chunk_to_source={"chunk-a": "source-a"},
        source_labels={"source-a": "label"},
        locators={"chunk-a": {"page_label": "1"}},
        service=SimpleNamespace(
            authorized_chunk_ids=lambda **_kwargs: frozenset({"chunk-a"})
        ),
    )
    case = SimpleNamespace(
        case_id="query-a",
        query="synthetic question",
        path=None,
        source_types=None,
        filters=None,
        allowed_source_ids=None,
    )
    trace = {
        "original_query": case.query,
        "final_chunk_ids": ["chunk-a"],
        "events": [
            {
                "stage": "recall_route",
                "branch": "dense",
                "candidates": [
                    {"id": "chunk-a", "score": 0.25, "score_available": True}
                ],
            },
            {"stage": "fusion", "ids": ["chunk-a"]},
        ],
        "combination_evaluation": {
            "candidate_ids": ["chunk-a"],
            "seed_chunk_ids": ["chunk-a"],
            "expanded_chunk_ids": [],
            "expansion_decisions": [],
        },
    }

    result = _repack_single_query_from_trace(
        runtime,
        case,
        trace_data=trace,
        summary={"timings": {}},
        components={"evidence_expansion": False},
        generation_budget=GenerationBudget(10000, 5, 0),
        count_tokens=len,
        counter_id="synthetic_utf8",
        system_prompt="system prompt",
        context_packing_version="serialized-full-message-v1",
    )

    packed_trace = result["trace"]["combination_evaluation"]
    assert result["trace_context_ids"] == ("chunk-a",)
    assert result["payload_context_ids"] == ("chunk-a",)
    assert result["invariants"] == {
        "unauthorized_candidates": 0,
        "unauthorized_results": 0,
        "unauthorized_expansions": 0,
        "unauthorized_context": 0,
        "token_budget_violations": 0,
        "trace_payload_id_mismatches": 0,
    }
    assert packed_trace["full_message_tokens"] <= packed_trace[
        "request_tokens_available"
    ]
    assert packed_trace["context_packing_version"] == "serialized-full-message-v1"


def test_anchor_coverage_uses_final_packed_context():
    source_metrics = __import__(
        "kotaemon.indices.knowledge.evaluation.source_metrics",
        fromlist=["final_context_anchor_coverage"],
    )
    anchor = SimpleNamespace(
        id="anchor-a",
        query_id="q1",
        source_id="source-a",
        unit_id="unit-a",
        locator={"page_label": "1"},
        char_start=0,
        char_end=4,
    )
    chunk = SimpleNamespace(
        chunk_id="chunk-a",
        source_id="source-a",
        unit_id="unit-a",
        locator={"page_label": "1"},
        char_start=0,
        char_end=4,
    )

    included = source_metrics.final_context_anchor_coverage(
        (anchor,),
        context_chunk_ids=("chunk-a",),
        chunks_by_id={"chunk-a": chunk},
        unresolved_offsets={},
    )
    omitted = source_metrics.final_context_anchor_coverage(
        (anchor,),
        context_chunk_ids=(),
        chunks_by_id={"chunk-a": chunk},
        unresolved_offsets={},
    )

    assert included.covered_anchors == 1
    assert omitted.covered_anchors == 0
    assert omitted.uncovered_anchors == 1


def test_generation_not_run_has_no_answer_score(tmp_path, monkeypatch):
    from kotaemon.indices.knowledge.evaluation.local_snapshot import (
        load_local_snapshot,
    )

    combination_eval = _combination_eval()
    snapshot_root = tmp_path / "reviewed-v2"
    _write_synthetic_snapshot(snapshot_root)
    model_paths, _embedding, _reranker = _fake_local_models(monkeypatch, tmp_path)
    report = combination_eval.run_combination_experiment(
        load_local_snapshot(snapshot_root),
        model_paths=model_paths,
        artifact_dir=tmp_path / "run",
    )

    assert report.generation_metrics["status"] == "not_run"
    assert report.generation_metrics["answer_support"] is None
    assert report.generation_metrics["citation_precision"] is None
    assert report.generation_metrics["no_answer_correctness"] is None
    assert report.generation_metrics["not_run_reason"]


def test_source_k_not_confused_with_expanded_chunks():
    from kotaemon.indices.knowledge.evaluation.retrieval_eval import EvaluationCase
    from kotaemon.indices.knowledge.evaluation.source_metrics import score_source_run
    from kotaemon.base import Document

    case = EvaluationCase(
        case_id="q1",
        query="synthetic query",
        judgment_level="source",
        relevant_ids=("source-a",),
    )
    docs = [Document(id_=f"chunk-{index}", text="synthetic") for index in range(8)]
    chunk_to_source = {
        **{f"chunk-{index}": "source-a" for index in range(4)},
        **{f"chunk-{index}": f"source-{index}" for index in range(4, 8)},
    }

    metrics = score_source_run(
        (case,), {"q1": docs}, k=5, chunk_to_source=chunk_to_source
    )

    assert metrics.k == 5
    assert len(metrics.per_query[0].result_ids) == 5
    assert metrics.per_query[0].result_ids[0] == "chunk-0"


def test_evidence_allowlist_preserves_explicit_metadata_filters():
    combination_eval = _combination_eval()
    case = SimpleNamespace(
        case_id="q1",
        query="synthetic",
        path="/team/a",
        source_types=("markdown",),
        filters={"region": "west"},
        allowed_source_ids=("source-a",),
    )

    class Service:
        def search(self, query, **kwargs):
            self.received = (query, kwargs)
            return []

    service = Service()
    combination_eval._search_case(service, case, trace=None)

    query, received = service.received
    assert query == "synthetic"
    assert received["path"] == "/team/a"
    assert received["source_types"] == ("markdown",)
    assert received["filters"] == {"region": "west"}
    assert received["allowed_source_ids"] == ("source-a",)


def test_trace_context_ids_equal_payload(tmp_path, monkeypatch):
    from kotaemon.indices.knowledge.evaluation.local_snapshot import (
        load_local_snapshot,
    )

    combination_eval = _combination_eval()
    snapshot_root = tmp_path / "reviewed-v2"
    _write_synthetic_snapshot(snapshot_root)
    model_paths, _embedding, _reranker = _fake_local_models(monkeypatch, tmp_path)
    run_dir = tmp_path / "run"
    combination_eval.run_combination_experiment(
        load_local_snapshot(snapshot_root),
        model_paths=model_paths,
        artifact_dir=run_dir,
    )

    payloads = combination_eval.read_generation_inputs(run_dir)
    for arm in payloads.values():
        for row in arm:
            assert row["trace_context_ids"] == row["payload_context_ids"]


def test_rejects_artifact_overwrite(tmp_path, monkeypatch):
    from kotaemon.indices.knowledge.evaluation.local_snapshot import (
        load_local_snapshot,
    )

    combination_eval = _combination_eval()
    snapshot_root = tmp_path / "reviewed-v2"
    _write_synthetic_snapshot(snapshot_root)
    model_paths, _embedding, _reranker = _fake_local_models(monkeypatch, tmp_path)
    artifact_dir = tmp_path / "run"
    artifact_dir.mkdir()
    marker = artifact_dir / "keep.txt"
    marker.write_text("preserve", encoding="utf-8")

    with pytest.raises(FileExistsError):
        combination_eval.run_combination_experiment(
            load_local_snapshot(snapshot_root),
            model_paths=model_paths,
            artifact_dir=artifact_dir,
        )
    assert marker.read_text(encoding="utf-8") == "preserve"


def test_report_records_unavailable_generation_and_measured_run_fingerprints(
    tmp_path, monkeypatch
):
    from kotaemon.indices.knowledge.evaluation.local_snapshot import (
        load_local_snapshot,
    )

    combination_eval = _combination_eval()
    snapshot_root = tmp_path / "reviewed-v2"
    _write_synthetic_snapshot(snapshot_root)
    model_paths, _embedding, _reranker = _fake_local_models(monkeypatch, tmp_path)
    report = combination_eval.run_combination_experiment(
        load_local_snapshot(snapshot_root),
        model_paths=model_paths,
        artifact_dir=tmp_path / "run",
    )

    assert report.snapshot_fingerprint
    assert report.model_fingerprint
    assert report.config_fingerprint
    assert report.artifact_digest_manifest
    final_arm = report.arms["registry_expansion"]
    assert final_arm.candidate_recall.candidate_k == 40
    assert final_arm.source_metrics.k == 5
    report_data = json.loads((tmp_path / "run" / "report.json").read_text())
    assert report_data["metric_units"]["candidate_recall"]["k"] == 40
    assert report_data["metric_units"]["source_metrics"]["k"] == 5


def test_combination_runner_resumes_from_manifest_bound_completed_query_rows(
    tmp_path, monkeypatch
):
    from kotaemon.indices.knowledge.evaluation.local_snapshot import (
        load_local_snapshot,
    )
    from kotaemon.indices.knowledge.evaluation import combination_runner

    combination_eval = _combination_eval()
    snapshot_root = tmp_path / "reviewed-v2"
    _write_synthetic_snapshot(snapshot_root)
    snapshot = load_local_snapshot(snapshot_root)
    model_paths, _embedding, _reranker = _fake_local_models(monkeypatch, tmp_path)
    artifact_dir = tmp_path / "resumed-run"
    staging_dir = tmp_path / ".resumed-run.staging-synthetic"
    manifest_bytes = b'{"verified":"synthetic model manifest"}\n'
    original_evaluate = combination_runner._evaluate_single_query
    initial_attempts = 0

    def interrupt_after_three(*args, **kwargs):
        nonlocal initial_attempts
        if initial_attempts == 3:
            raise RuntimeError("synthetic interruption")
        initial_attempts += 1
        return original_evaluate(*args, **kwargs)

    monkeypatch.setattr(
        combination_runner, "_evaluate_single_query", interrupt_after_three
    )
    with pytest.raises(RuntimeError, match="synthetic interruption"):
        combination_runner.run_combination_experiment(
            snapshot,
            model_paths=model_paths,
            artifact_dir=artifact_dir,
            staging_dir=staging_dir,
            verified_model_manifest_bytes=manifest_bytes,
        )

    checkpoint = json.loads((staging_dir / "run-checkpoint.json").read_text())
    assert len(checkpoint["completed"]) == 3
    assert checkpoint["pending"] is not None

    forbidden_calls = []

    def should_not_run(*args, **kwargs):
        forbidden_calls.append(True)
        raise AssertionError("fingerprint mismatch must stop before query inference")

    monkeypatch.setattr(combination_runner, "_evaluate_single_query", should_not_run)
    with pytest.raises(ValueError, match="fingerprint mismatch"):
        combination_runner.run_combination_experiment(
            snapshot,
            model_paths=model_paths,
            artifact_dir=artifact_dir,
            staging_dir=staging_dir,
            resume=True,
            verified_model_manifest_bytes=b'{"verified":"different model manifest"}\n',
        )
    assert forbidden_calls == []

    resumed_attempts = 0

    def count_resumed(*args, **kwargs):
        nonlocal resumed_attempts
        resumed_attempts += 1
        return original_evaluate(*args, **kwargs)

    monkeypatch.setattr(combination_runner, "_evaluate_single_query", count_resumed)
    report = combination_runner.run_combination_experiment(
        snapshot,
        model_paths=model_paths,
        artifact_dir=artifact_dir,
        staging_dir=staging_dir,
        resume=True,
        verified_model_manifest_bytes=manifest_bytes,
    )

    arm_count = len(combination_runner.get_arm_configurations())
    expected_queries = arm_count * len(snapshot.judgments.cases)
    assert resumed_attempts == expected_queries - 3
    assert report.query_count == len(snapshot.judgments.cases)
    assert len(report.arms) == arm_count
    assert not staging_dir.exists()
    checkpoint_bytes = (artifact_dir / "run-checkpoint.json").read_bytes()
    final_checkpoint = json.loads(checkpoint_bytes)
    assert final_checkpoint["status"] == "complete"
    assert len(final_checkpoint["completed"]) == expected_queries
    assert len(
        {
            (row["arm"], row["query_index"])
            for row in final_checkpoint["completed"]
        }
    ) == expected_queries
    assert final_checkpoint["fingerprints"]["snapshot"] == snapshot.fingerprint
    gold_hashes = {
        name: combination_eval._sha256((snapshot_root / name).read_bytes())
        for name in ("judgments.jsonl", "anchors.jsonl")
    }
    assert final_checkpoint["fingerprints"]["gold"] == combination_eval._fingerprint(
        gold_hashes
    )
    assert final_checkpoint["fingerprints"]["model_manifest"] == combination_eval._sha256(
        manifest_bytes
    )
    assert final_checkpoint["fingerprints"]["model"] == report.model_fingerprint
    assert final_checkpoint["fingerprints"]["config"] == report.config_fingerprint

    sidecar = json.loads((artifact_dir / "artifact-manifest.json").read_text())
    assert sidecar["gold_fingerprint"] == report.gold_fingerprint
    assert sidecar["inputs"]["model_manifest_sha256"] == combination_eval._sha256(
        manifest_bytes
    )
    for entry in sidecar["artifacts"]:
        path = artifact_dir / entry["path"]
        payload = path.read_bytes()
        assert len(payload) == entry["size_bytes"]
        assert combination_eval._sha256(payload) == entry["sha256"]


def test_conversation_run_keeps_allowlists_history_and_inline_anchor_digest(
    tmp_path, monkeypatch
):
    from kotaemon.indices.knowledge.evaluation.local_snapshot import (
        load_local_snapshot,
    )

    combination_eval = _combination_eval()
    snapshot_root = tmp_path / "reviewed-v2"
    _snapshot_path, source_ids = _write_synthetic_snapshot(snapshot_root)
    first_span = "alpha"
    fixture = {
        "schema_version": 1,
        "reviewed": True,
        "cases": [
            {
                "case_id": "conversation-a",
                "turns": [
                    {
                        "turn_id": "conversation-a-1",
                        "question": "alpha unique target phrase",
                        "allowed_source_ids": [source_ids[0]],
                        "expected_relevant_source_ids": [source_ids[0]],
                        "expected_anchors": [
                            {
                                "id": "conversation-anchor-a",
                                "source_id": source_ids[0],
                                "unit_id": "unit-0",
                                "locator": {"page_label": "1"},
                                "char_start": 0,
                                "char_end": len(first_span),
                                "evidence_sha256": hashlib.sha256(
                                    first_span.encode("utf-8")
                                ).hexdigest(),
                            }
                        ],
                        "topic_switch": False,
                        "no_answer": False,
                        "path": None,
                        "source_types": ["markdown"],
                        "filters": None,
                    },
                    {
                        "turn_id": "conversation-a-2",
                        "question": "unrelated synthetic source content 1",
                        "allowed_source_ids": [source_ids[1]],
                        "expected_relevant_source_ids": [source_ids[1]],
                        "expected_anchors": [],
                        "topic_switch": True,
                        "no_answer": False,
                        "path": None,
                        "source_types": ["markdown"],
                        "filters": None,
                    },
                    {
                        "turn_id": "conversation-a-3",
                        "question": "synthetic absent source question",
                        "allowed_source_ids": [],
                        "expected_relevant_source_ids": [],
                        "expected_anchors": [],
                        "topic_switch": False,
                        "no_answer": True,
                        "path": None,
                        "source_types": ["markdown"],
                        "filters": None,
                    },
                ],
            }
        ],
    }
    fixture_path = tmp_path / "conversation.json"
    fixture_path.write_text(json.dumps(fixture), encoding="utf-8")
    model_paths, _embedding, _reranker = _fake_local_models(monkeypatch, tmp_path)

    report = combination_eval.run_combination_experiment(
        load_local_snapshot(snapshot_root),
        model_paths=model_paths,
        artifact_dir=tmp_path / "run",
        conversation_fixture=fixture_path,
    )

    conversation = report.conversation_metrics
    assert (
        report.conversation_fixture_digest
        == combination_eval.load_conversation_fixture(fixture_path).digest
    )
    assert conversation["topic_switch_turn_count"] == 1
    assert conversation["topic_switch_source_metrics"]["k"] == 5
    assert conversation["final_context_anchor_coverage"]["covered_anchors"] == 1
    assert conversation["no_answer_retrieval"]["zero_context_count"] == 1
    assert conversation["no_answer_correctness"]["value"] is None
    conversation_rows = (
        tmp_path / "run" / "conversation" / "final-config.jsonl"
    ).read_text()
    assert '"history":["alpha unique target phrase"]' in conversation_rows
