"""Public, offline-testable BGE adapter contracts."""

from __future__ import annotations

import pytest

from kotaemon.base import Document, DocumentWithEmbedding, RetrievedDocument
from kotaemon.models import BgeM3Embeddings, BgeM3Reranking


class SpyRerankerBackend:
    def __init__(self, scores):
        self.scores = scores
        self.pairs = []

    def compute_score(self, pairs, **kwargs):
        self.pairs.append((pairs, kwargs))
        return self.scores


class SpyEmbeddingBackend:
    def encode_queries(self, texts, **kwargs):
        assert texts == ["offline query"]
        return {"dense_vecs": [[0.1, 0.2, 0.3]]}

    def encode_corpus(self, texts, **kwargs):
        return {"dense_vecs": [[0.3, 0.2, 0.1] for _text in texts]}


def test_public_bge_embedding_import_and_fake_backend_work_offline(tmp_path):
    model = BgeM3Embeddings(tmp_path, backend=SpyEmbeddingBackend())

    (result,) = model.run("offline query")

    assert isinstance(result, DocumentWithEmbedding)
    assert result.embedding == [0.1, 0.2, 0.3]
    assert model.metadata.model_id == "BAAI/bge-m3"


def test_public_bge_pair_scores_keep_input_order_and_run_clones_with_provenance(
    tmp_path,
):
    backend = SpyRerankerBackend([0.1, 0.9])
    reranker = BgeM3Reranking(
        tmp_path,
        backend=backend,
        revision="fixture-revision",
        query_max_length=32,
        passage_max_length=96,
    )
    documents = [
        RetrievedDocument(
            id_="first",
            text="first passage",
            score=0.31,
            retrieval_metadata={"raw_scores": [{"branch": "dense", "score": 0.31}]},
        ),
        RetrievedDocument(id_="second", text="second passage", score=0.72),
    ]

    assert reranker.score_pairs("q", documents) == (0.1, 0.9)
    assert backend.pairs[0][0] == [
        ("q", "first passage"),
        ("q", "second passage"),
    ]

    result = reranker.run(documents, "q")

    assert [document.doc_id for document in result] == ["second", "first"]
    assert result[0] is not documents[1]
    assert result[1] is not documents[0]
    assert [document.score for document in result] == [0.72, 0.31]
    assert result[1].retrieval_metadata["raw_scores"] == [
        {"branch": "dense", "score": 0.31}
    ]
    assert [document.retrieval_metadata["rerank_score"] for document in result] == [
        0.9,
        0.1,
    ]
    assert result[0].retrieval_metadata["reranker"]["model_id"] == (
        "BAAI/bge-reranker-v2-m3"
    )
    assert result[0].retrieval_metadata["reranker"]["revision"] == "fixture-revision"
    assert result[0].retrieval_metadata["reranker"]["query_max_length"] == 32
    assert result[0].retrieval_metadata["reranker"]["passage_max_length"] == 96


@pytest.mark.parametrize("scores", [[0.1], [0.1, float("nan")]])
def test_public_bge_rejects_wrong_score_count_or_nonfinite_scores(tmp_path, scores):
    reranker = BgeM3Reranking(tmp_path, backend=SpyRerankerBackend(scores))

    with pytest.raises(ValueError):
        reranker.score_pairs(
            "q", [Document(id_="a", text="one"), Document(id_="b", text="two")]
        )
