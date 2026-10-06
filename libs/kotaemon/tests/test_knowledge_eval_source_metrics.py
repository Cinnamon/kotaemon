"""Generated-fixture tests for distinct-source scoring and anchor coverage."""

from __future__ import annotations

import pytest

from kotaemon.base import Document
from kotaemon.indices.knowledge.evaluation import (
    AnchorCoverage,
    EvaluationCase,
    anchor_coverage,
    score_source_run,
    source_ranked_chunks,
)
from kotaemon.indices.knowledge.evaluation.local_ingest import DraftChunk
from kotaemon.indices.knowledge.evaluation.local_snapshot import EvidenceAnchor


LOCATOR = {"page_label": "4", "section": "Methods", "sheet": "Ledger", "row": 17}


def _document(doc_id: str) -> Document:
    return Document(id_=doc_id, text=f"generated {doc_id}", metadata={})


def _case(
    case_id: str,
    relevant_ids: tuple[str, ...],
    *,
    judgment_level: str = "source",
    disallowed_source_ids: tuple[str, ...] | None = None,
) -> EvaluationCase:
    return EvaluationCase(
        case_id=case_id,
        query=f"generated query {case_id}",
        judgment_level=judgment_level,
        relevant_ids=relevant_ids,
        disallowed_source_ids=disallowed_source_ids,
    )


def _anchor(
    anchor_id: str = "anchor-1",
    *,
    source_id: str = "source-a",
    unit_id: str = "unit-a",
    locator: dict | None = None,
    char_start: int = 10,
    char_end: int = 20,
    query_id: str = "query-a",
) -> EvidenceAnchor:
    return EvidenceAnchor(
        id=anchor_id,
        query_id=query_id,
        source_id=source_id,
        source_sha256="a" * 64,
        unit_id=unit_id,
        locator=dict(LOCATOR if locator is None else locator),
        char_start=char_start,
        char_end=char_end,
        evidence_sha256="b" * 64,
    )


def _chunk(
    chunk_id: str,
    *,
    source_id: str = "source-a",
    unit_id: str = "unit-a",
    locator: dict | None = None,
    char_start: int = 0,
    char_end: int = 30,
) -> DraftChunk:
    return DraftChunk(
        chunk_id=chunk_id,
        source_id=source_id,
        relative_path="generated.md",
        unit_id=unit_id,
        unit_ordinal=0,
        chunk_ordinal=0,
        locator=dict(LOCATOR if locator is None else locator),
        text=f"generated {chunk_id}",
        char_start=char_start,
        char_end=char_end,
    )


def test_source_window_keeps_first_representative_and_scans_past_raw_k():
    chunks = [_document("a-1"), _document("a-2"), _document("b-1")]
    mapping = {"a-1": "source-a", "a-2": "source-a", "b-1": "source-b"}

    window = source_ranked_chunks(chunks, mapping, limit=2)

    assert [item.doc_id for item in window] == ["a-1", "b-1"]
    assert window == (chunks[0], chunks[2])
    assert window[0] is chunks[0]
    assert window[1] is chunks[2]


@pytest.mark.parametrize("limit", [0, -1, True, 1.5])
def test_source_window_rejects_nonpositive_or_noninteger_limit(limit):
    with pytest.raises(ValueError, match="limit"):
        source_ranked_chunks([], {}, limit=limit)


@pytest.mark.parametrize(
    "tail, mapping",
    [
        (_document("tail-missing"), {"first": "source-a", "repeat": "source-a"}),
        (
            _document("tail-empty-source"),
            {"first": "source-a", "repeat": "source-a", "tail-empty-source": " "},
        ),
    ],
)
def test_source_window_validates_mapping_for_tail_after_limit_is_filled(tail, mapping):
    chunks = [_document("first"), _document("repeat"), tail]

    with pytest.raises(ValueError, match="Source|source|relationship"):
        source_ranked_chunks(chunks, mapping, limit=1)


def test_source_window_rejects_a_malformed_result_id_even_in_the_tail():
    chunks = [_document("first"), _document("repeat"), _document(" ")]
    mapping = {"first": "source-a", "repeat": "source-a", " ": "source-b"}

    with pytest.raises(ValueError, match="result chunk ID"):
        source_ranked_chunks(chunks, mapping, limit=1)


def test_score_source_run_uses_distinct_source_ranks_for_all_metrics():
    cases = (
        _case(
            "q-labeled", ("source-b", "source-c"), disallowed_source_ids=("source-x",)
        ),
        _case("q-empty-label", ("source-c",), disallowed_source_ids=()),
        _case("q-unlabeled", ("source-e",), disallowed_source_ids=None),
    )
    results = {
        # source-b is raw chunk rank four, but distinct source rank three.
        "q-labeled": [
            _document("a-1"),
            _document("a-2"),
            _document("x-1"),
            _document("b-1"),
        ],
        "q-empty-label": [_document("x-1"), _document("x-2"), _document("c-1")],
        "q-unlabeled": [_document("x-1"), _document("x-2"), _document("e-1")],
    }
    mapping = {
        "a-1": "source-a",
        "a-2": "source-a",
        "x-1": "source-x",
        "x-2": "source-x",
        "b-1": "source-b",
        "c-1": "source-c",
        "e-1": "source-e",
    }

    metrics = score_source_run(cases, results, k=3, chunk_to_source=mapping)

    assert metrics.hit_at_k == 1.0
    assert metrics.recall_at_k == pytest.approx((0.5 + 1.0 + 1.0) / 3)
    assert metrics.mrr_at_k == pytest.approx((1 / 3 + 1 / 2 + 1 / 2) / 3)
    assert metrics.per_query[0].result_ids == ("a-1", "x-1", "b-1")
    assert metrics.per_query[0].relevant_retrieved_ids == ("source-b",)
    assert metrics.per_query[0].first_relevant_rank == 3
    assert metrics.per_query[0].wrong_scope_numerator == 1
    assert metrics.per_query[0].wrong_scope_denominator == 3
    assert metrics.per_query[1].wrong_scope_numerator == 0
    assert metrics.per_query[1].wrong_scope_denominator == 2
    assert metrics.per_query[2].wrong_scope_denominator == 0
    assert metrics.wrong_scope_at_k == pytest.approx(1 / 5)
    assert metrics.scope_labeled_query_count == 2


def test_score_source_run_rejects_chunk_level_cases():
    case = _case("q-chunk", ("chunk-1",), judgment_level="chunk")

    with pytest.raises(ValueError, match="source-level"):
        score_source_run(
            (case,),
            {"q-chunk": [_document("chunk-1")]},
            k=5,
            chunk_to_source={"chunk-1": "source-a"},
        )


def test_anchor_coverage_matches_exact_source_unit_locator_and_containing_span():
    anchor = _anchor(query_id="query-with-page-row-section")
    matching_chunk = _chunk("matching")
    wrong_chunks = (
        _chunk("wrong-source", source_id="source-b"),
        _chunk("wrong-unit", unit_id="unit-b"),
        _chunk("wrong-locator", locator={**LOCATOR, "row": 18}),
        _chunk("partial-start", char_start=11),
        _chunk("partial-end", char_end=19),
    )

    exact = anchor_coverage((anchor,), (matching_chunk,))
    mismatches = anchor_coverage((anchor,), wrong_chunks)

    assert exact == AnchorCoverage(
        total_anchors=1,
        covered_anchors=1,
        unmapped_anchor_ids=(),
        rate=1.0,
    )
    assert mismatches.total_anchors == 1
    assert mismatches.covered_anchors == 0
    assert mismatches.unmapped_anchor_ids == ("anchor-1",)
    assert mismatches.rate == 0.0


def test_anchor_coverage_does_not_join_partial_chunks_across_a_boundary():
    anchor = _anchor()
    chunks = (
        _chunk("left", char_start=0, char_end=15),
        _chunk("right", char_start=15, char_end=30),
    )

    coverage = anchor_coverage((anchor,), chunks)

    assert coverage.covered_anchors == 0
    assert coverage.unmapped_anchor_ids == ("anchor-1",)


def test_anchor_coverage_counts_an_anchor_once_when_multiple_chunks_contain_it():
    anchor = _anchor()
    chunks = (_chunk("first-match"), _chunk("second-match", char_start=5, char_end=25))

    coverage = anchor_coverage((anchor,), chunks)

    assert coverage.total_anchors == 1
    assert coverage.covered_anchors == 1
    assert coverage.unmapped_anchor_ids == ()
    assert coverage.rate == 1.0


def test_anchor_coverage_returns_none_rate_without_anchors():
    coverage = anchor_coverage((), (_chunk("unused"),))

    assert coverage == AnchorCoverage(0, 0, (), None)


@pytest.mark.parametrize(
    "anchors, message",
    [
        ((_anchor(""),), "anchor ID"),
        ((_anchor(), _anchor()), "[Dd]uplicate anchor ID"),
        ((_anchor(char_start=True),), "span"),
        ((_anchor(char_start=20, char_end=20),), "span"),
        ((_anchor(char_start=-1),), "span"),
    ],
)
def test_anchor_coverage_rejects_malformed_anchor_ids_and_spans(anchors, message):
    with pytest.raises(ValueError, match=message):
        anchor_coverage(anchors, (_chunk("candidate"),))
