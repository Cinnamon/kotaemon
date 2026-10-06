from __future__ import annotations

import pytest

from kotaemon.base import RetrievedDocument
from kotaemon.indices.knowledge.retrieval.contracts import (
    RecallBatch,
    RetrievalPolicy,
)
from kotaemon.indices.knowledge.retrieval.fusion import fuse_batches


def make_doc(doc_id: str, *, score: float = 0.0) -> RetrievedDocument:
    return RetrievedDocument(id_=doc_id, text=doc_id, score=score)


def test_rrf_duplicate_id_votes_once_per_route():
    a = make_doc("a")
    b = make_doc("b")
    batches = [
        RecallBatch("dense", 0, "q", (a, a, b), "available"),
        RecallBatch("lexical", 0, "q", (b, a), "available"),
    ]

    ranked = fuse_batches(batches, RetrievalPolicy(enabled=True))

    assert [document.doc_id for document in ranked] == ["a", "b"]
    assert ranked[0].retrieval_metadata["fusion_score"] == pytest.approx(
        1 / 61 + 1 / 62
    )


def test_duplicate_variant_does_not_multiply_branch_weight():
    batches = [
        RecallBatch("dense", 0, "same route", (make_doc("first"),), "available"),
        RecallBatch("dense", 1, " SAME ROUTE ", (make_doc("second"),), "available"),
    ]

    ranked = fuse_batches(batches, RetrievalPolicy(enabled=True))

    assert [document.doc_id for document in ranked] == ["first"]
    assert ranked[0].retrieval_metadata["fusion_score"] == pytest.approx(1 / 61)


def test_stable_tie_order_uses_first_route_before_document_id():
    batches = [
        RecallBatch("dense", 0, "first route", (make_doc("z-first"),), "available"),
        RecallBatch("dense", 1, "second route", (make_doc("a-second"),), "available"),
    ]

    ranked = fuse_batches(batches, RetrievalPolicy(enabled=True))

    assert [document.doc_id for document in ranked] == ["z-first", "a-second"]
    assert [document.retrieval_metadata["fusion_score"] for document in ranked] == [
        pytest.approx(1 / 122),
        pytest.approx(1 / 122),
    ]


def test_raw_scores_survive_fusion_on_cloned_documents():
    dense = make_doc("shared", score=0.25)
    lexical = make_doc("shared", score=8.5)
    dense.retrieval_metadata = {"backend": "dense"}
    lexical.retrieval_metadata = {"backend": "lexical"}

    ranked = fuse_batches(
        [
            RecallBatch("dense", 0, "q", (dense,), "available"),
            RecallBatch("lexical", 0, "q", (lexical,), "available"),
        ],
        RetrievalPolicy(enabled=True),
    )

    assert len(ranked) == 1
    fused = ranked[0]
    assert fused is not dense
    assert fused.score == pytest.approx(0.25)
    assert fused.retrieval_metadata["fusion_score"] == pytest.approx(2 / 61)
    assert fused.retrieval_metadata["raw_scores"] == [
        {"branch": "dense", "query_index": 0, "score": 0.25},
        {"branch": "lexical", "query_index": 0, "score": 8.5},
    ]
    assert fused.retrieval_metadata["route_ranks"] == [
        {"branch": "dense", "query_index": 0, "rank": 1},
        {"branch": "lexical", "query_index": 0, "rank": 1},
    ]
    assert dense.retrieval_metadata == {"backend": "dense"}
    assert lexical.retrieval_metadata == {"backend": "lexical"}


def test_failed_branch_is_not_empty_and_keeps_its_scheduled_weight_share():
    batches = [
        RecallBatch("dense", 0, "q0", (make_doc("a"),), "available"),
        RecallBatch("lexical", 0, "q0", (), "unavailable", "BackendUnavailable"),
        RecallBatch("lexical", 1, "q1", (make_doc("a"),), "available"),
    ]

    ranked = fuse_batches(
        batches,
        RetrievalPolicy(enabled=True, dense_weight=1.0, lexical_weight=2.0),
    )

    assert [document.doc_id for document in ranked] == ["a"]
    # The failed lexical route retains half of that branch's configured weight.
    assert ranked[0].retrieval_metadata["fusion_score"] == pytest.approx(2 / 61)


def test_nonfinite_or_boolean_policy_numbers_are_rejected():
    with pytest.raises(ValueError):
        RetrievalPolicy(dense_weight=float("nan"))
    with pytest.raises(ValueError):
        RetrievalPolicy(lexical_weight=float("inf"))
    with pytest.raises(ValueError):
        RetrievalPolicy(candidate_k=True)
    with pytest.raises(ValueError):
        RetrievalPolicy(rrf_k=1.5)
