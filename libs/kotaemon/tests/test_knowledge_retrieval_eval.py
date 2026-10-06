"""Pure behavior tests for the offline retrieval evaluator."""

from __future__ import annotations

import importlib
import json

import pytest

_MODULE = "kotaemon.indices.knowledge.evaluation.retrieval_eval"


def _evaluator():
    try:
        return importlib.import_module(_MODULE)
    except ModuleNotFoundError as error:
        if _MODULE.startswith(f"{error.name}."):
            pytest.fail("Task 11 retrieval evaluator module is missing")
        raise


def _write_fixture(path, rows):
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )
    return path


def _row(case_id, relevant_ids, *, level="chunk", disallowed=None, **kwargs):
    return {
        "schema_version": 1,
        "id": case_id,
        "query": f"query for {case_id}",
        "judgment_level": level,
        "relevant_ids": relevant_ids,
        "disallowed_source_ids": disallowed,
        **kwargs,
    }


def _resolve(evaluator, tmp_path, rows, catalog):
    fixture = evaluator.load_fixture(_write_fixture(tmp_path / "cases.jsonl", rows))
    return evaluator.resolve_judgments(fixture, catalog)


def test_metric_arithmetic_uses_raw_k_window_and_pooled_scope_denominator(tmp_path):
    evaluator = _evaluator()
    catalog = evaluator.IndexedCatalog(
        source_ids={"allowed", "blocked"},
        chunk_to_source={
            "a": "allowed",
            "b": "allowed",
            "x": "blocked",
            "z": "allowed",
        },
    )
    cases = _resolve(
        evaluator,
        tmp_path,
        [
            _row("ranked", ["a", "b"], disallowed=["blocked"]),
            _row("empty", ["z"], disallowed=None),
        ],
        catalog,
    )

    report = evaluator.score_run(
        cases,
        {"ranked": ["x", "a", "a", "b"], "empty": []},
        k=3,
        chunk_to_source=catalog.chunk_to_source,
    )

    ranked, empty = report.per_query
    assert (ranked.hit_at_k, ranked.recall_at_k, ranked.reciprocal_rank_at_k) == (
        1,
        1 / 2,
        1 / 2,
    )
    assert ranked.result_ids == ("x", "a")
    assert (
        ranked.raw_result_count,
        ranked.unique_result_count,
        ranked.duplicate_result_count,
    ) == (
        3,
        2,
        1,
    )
    assert (ranked.wrong_scope_numerator, ranked.wrong_scope_denominator) == (1, 2)
    assert (empty.hit_at_k, empty.recall_at_k, empty.reciprocal_rank_at_k) == (0, 0, 0)
    assert empty.wrong_scope_rate is None
    assert (report.hit_at_k, report.recall_at_k, report.mrr_at_k) == (
        1 / 2,
        1 / 4,
        1 / 4,
    )
    assert report.wrong_scope_at_k == 1 / 2
    assert (report.judged_query_count, report.scope_labeled_query_count) == (2, 1)


def test_duplicates_after_k_do_not_enter_scoring_window(tmp_path):
    evaluator = _evaluator()
    catalog = evaluator.IndexedCatalog(
        source_ids={"source"}, chunk_to_source={"a": "source", "b": "source"}
    )
    (case,) = _resolve(evaluator, tmp_path, [_row("window", ["a"])], catalog)

    metric = evaluator.score_case(
        case,
        ["a", "b", "b"],
        k=2,
        chunk_to_source=catalog.chunk_to_source,
    )

    assert metric.result_ids == ("a", "b")
    assert metric.raw_result_count == 2
    assert metric.duplicate_result_count == 0
    assert metric.reciprocal_rank_at_k == 1


def test_unlabeled_query_with_results_has_no_wrong_scope_metric(tmp_path):
    evaluator = _evaluator()
    catalog = evaluator.IndexedCatalog(
        source_ids={"source"}, chunk_to_source={"a": "source"}
    )
    (case,) = _resolve(
        evaluator,
        tmp_path,
        [_row("unlabeled", ["a"], disallowed=None)],
        catalog,
    )

    metric = evaluator.score_case(
        case,
        ["a"],
        k=1,
        chunk_to_source=catalog.chunk_to_source,
    )

    assert metric.hit_at_k == 1
    assert metric.wrong_scope_rate is None
    assert (metric.wrong_scope_numerator, metric.wrong_scope_denominator) == (0, 0)


def test_empty_disallowed_list_is_a_labeled_scope_judgment(tmp_path):
    evaluator = _evaluator()
    catalog = evaluator.IndexedCatalog(
        source_ids={"source"}, chunk_to_source={"a": "source"}
    )
    (case,) = _resolve(
        evaluator,
        tmp_path,
        [_row("empty-label", ["a"], disallowed=[])],
        catalog,
    )

    metric = evaluator.score_case(
        case,
        ["a"],
        k=1,
        chunk_to_source=catalog.chunk_to_source,
    )

    assert metric.wrong_scope_rate == 0
    assert (metric.wrong_scope_numerator, metric.wrong_scope_denominator) == (0, 1)


def test_source_level_judgment_deduplicates_chunks_from_same_source(tmp_path):
    evaluator = _evaluator()
    catalog = evaluator.IndexedCatalog(
        source_ids={"relevant", "other"},
        chunk_to_source={"r1": "relevant", "r2": "relevant", "o1": "other"},
    )
    (case,) = _resolve(
        evaluator,
        tmp_path,
        [_row("source-judgment", ["relevant"], level="source")],
        catalog,
    )

    metric = evaluator.score_case(
        case,
        ["r1", "r2", "o1"],
        k=3,
        chunk_to_source=catalog.chunk_to_source,
    )

    assert metric.relevant_retrieved_ids == ("relevant",)
    assert metric.recall_at_k == 1
    assert metric.reciprocal_rank_at_k == 1


def test_unmapped_returned_chunk_is_an_evaluation_error(tmp_path):
    evaluator = _evaluator()
    catalog = evaluator.IndexedCatalog(
        source_ids={"source"}, chunk_to_source={"known": "source"}
    )
    (case,) = _resolve(evaluator, tmp_path, [_row("mapping", ["known"])], catalog)

    with pytest.raises(ValueError, match="no indexed Source relationship"):
        evaluator.score_case(
            case,
            ["unknown-result"],
            k=2,
            chunk_to_source=catalog.chunk_to_source,
        )


def test_score_run_rejects_missing_query_results(tmp_path):
    evaluator = _evaluator()
    catalog = evaluator.IndexedCatalog(
        source_ids={"source"}, chunk_to_source={"a": "source"}
    )
    cases = _resolve(
        evaluator,
        tmp_path,
        [_row("first", ["a"]), _row("second", ["a"])],
        catalog,
    )

    with pytest.raises(ValueError, match="Missing retrieval results"):
        evaluator.score_run(
            cases,
            {"first": ["a"]},
            k=1,
            chunk_to_source=catalog.chunk_to_source,
        )


@pytest.mark.parametrize(
    "rows, message",
    [
        ([_row("v", ["a"], schema_version=2)], "schema_version"),
        ([_row("v", ["a"]), _row("v", ["b"])], "duplicate query ID"),
        ([_row("v", ["a", "a"])], "duplicate relevant ID"),
        ([_row("v", [])], "at least one relevant ID"),
        ([_row("v", ["a"], path="/team/../private")], "parent traversal"),
        (
            [
                _row("v1", ["a"], level="chunk"),
                _row("v2", ["source"], level="source"),
            ],
            "mixed judgment levels",
        ),
    ],
)
def test_fixture_validation_fails_before_search(tmp_path, rows, message):
    evaluator = _evaluator()

    with pytest.raises(ValueError, match=message):
        evaluator.load_fixture(_write_fixture(tmp_path / "bad.jsonl", rows))


@pytest.mark.parametrize(
    "row, message",
    [
        (_row("unknown-chunk", ["missing-chunk"]), "Unknown chunk ID"),
        (
            _row("unknown-source", ["missing-source"], level="source"),
            "Unknown Source ID",
        ),
        (
            _row("unknown-disallowed", ["known"], disallowed=["missing-source"]),
            "Unknown disallowed Source ID",
        ),
    ],
)
def test_resolution_rejects_unknown_indexed_ids(tmp_path, row, message):
    evaluator = _evaluator()
    catalog = evaluator.IndexedCatalog(
        source_ids={"source"}, chunk_to_source={"known": "source"}
    )
    fixture = evaluator.load_fixture(_write_fixture(tmp_path / "unknown.jsonl", [row]))

    with pytest.raises(ValueError, match=message):
        evaluator.resolve_judgments(fixture, catalog)


def test_compare_runs_requires_matching_retrieval_configuration(tmp_path):
    evaluator = _evaluator()
    catalog = evaluator.IndexedCatalog(
        source_ids={"source"}, chunk_to_source={"a": "source"}
    )
    (case,) = _resolve(evaluator, tmp_path, [_row("same", ["a"])], catalog)
    baseline_calls = []
    planned_calls = []
    shared = {
        "retrieval_mode": "vector",
        "top_k": 2,
        "candidate_k": 6,
        "embedding": "deterministic-char-bigram-v1",
        "rerankers": [],
        "fixture_sha256": "same-fixture-hash",
    }

    comparison = evaluator.compare_runs(
        [case],
        search_baseline=lambda item, trace=None: baseline_calls.append(item.case_id)
        or ["a"],
        search_planned=lambda item, trace=None: planned_calls.append(item.case_id)
        or ["a"],
        k=2,
        chunk_to_source=catalog.chunk_to_source,
        baseline_config={**shared, "planner": "identity-global"},
        planned_config={**shared, "planner": "QueryPlanner"},
    )

    assert baseline_calls == planned_calls == ["same"]
    assert comparison.baseline.per_query[0].result_ids == ("a",)
    assert comparison.planned.per_query[0].result_ids == ("a",)
    assert len(comparison.config_fingerprint) == 64

    with pytest.raises(ValueError, match="configuration differs outside planner"):
        evaluator.compare_runs(
            [case],
            search_baseline=lambda item, trace=None: [],
            search_planned=lambda item, trace=None: [],
            k=2,
            chunk_to_source=catalog.chunk_to_source,
            baseline_config={**shared, "planner": "identity-global"},
            planned_config={**shared, "candidate_k": 5, "planner": "QueryPlanner"},
        )


def test_compare_runs_requires_observed_candidate_count_when_tracing(tmp_path):
    evaluator = _evaluator()
    catalog = evaluator.IndexedCatalog(
        source_ids={"source"}, chunk_to_source={"a": "source"}
    )
    (case,) = _resolve(evaluator, tmp_path, [_row("trace-k", ["a"])], catalog)
    config = {
        "retrieval_mode": "vector",
        "top_k": 1,
        "candidate_k": 3,
        "planner": "identity-global",
    }

    class EmptyTrace:
        def to_dict(self):
            return {"schema_version": 1, "events": []}

    with pytest.raises(ValueError, match="Missing observed candidate_k"):
        evaluator.compare_runs(
            [case],
            search_baseline=lambda item, trace=None: ["a"],
            search_planned=lambda item, trace=None: ["a"],
            k=1,
            chunk_to_source=catalog.chunk_to_source,
            baseline_config=config,
            planned_config={**config, "planner": "QueryPlanner"},
            trace_factory=lambda arm, item: EmptyTrace(),
        )
