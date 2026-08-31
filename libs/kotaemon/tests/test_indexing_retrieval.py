import json
from pathlib import Path
from typing import cast
from unittest.mock import Mock, patch

from openai.types.create_embedding_response import CreateEmbeddingResponse

from kotaemon.base import Document, DocumentWithEmbedding
from kotaemon.embeddings import AzureOpenAIEmbeddings, BaseEmbeddings
from kotaemon.indices import VectorIndexing, VectorRetrieval
from kotaemon.storages import ChromaVectorStore, InMemoryDocumentStore

with open(Path(__file__).parent / "resources" / "embedding_openai.json") as f:
    openai_embedding = CreateEmbeddingResponse.model_validate(json.load(f))


class _FakeEmbeddings(BaseEmbeddings):
    def invoke(self, text, *args, **kwargs):
        return [DocumentWithEmbedding(embedding=[1.0])]


def _run_hybrid_retrieval(text_ids, vector_ids, vector_scores):
    docs = {
        doc_id: Document(text=f"text {doc_id}", id_=doc_id)
        for doc_id in set(text_ids + vector_ids)
    }

    vector_store = Mock()
    vector_store.query.return_value = ([], vector_scores, vector_ids)

    doc_store = Mock()
    doc_store.query.return_value = [docs[doc_id] for doc_id in text_ids]
    doc_store.get.side_effect = lambda ids: [docs[doc_id] for doc_id in ids]

    pipeline = VectorRetrieval(
        vector_store=vector_store,
        doc_store=doc_store,
        embedding=_FakeEmbeddings(),
        retrieval_mode="hybrid",
        rerankers=[],
    )
    return pipeline(text="query", top_k=10, scope=list(docs))


@patch(
    "openai.resources.embeddings.Embeddings.create",
    side_effect=lambda *args, **kwargs: openai_embedding,
)
def test_indexing(tmp_path):
    db = ChromaVectorStore(path=str(tmp_path))
    doc_store = InMemoryDocumentStore()
    embedding = AzureOpenAIEmbeddings(
        azure_deployment="text-embedding-ada-002",
        azure_endpoint="https://test.openai.azure.com/",
        api_key="some-key",
        api_version="version",
    )

    pipeline = VectorIndexing(vector_store=db, embedding=embedding, doc_store=doc_store)
    pipeline.doc_store = cast(InMemoryDocumentStore, pipeline.doc_store)
    pipeline.vector_store = cast(ChromaVectorStore, pipeline.vector_store)
    assert pipeline.vector_store._collection.count() == 0, "Expected empty collection"
    assert len(pipeline.doc_store._store) == 0, "Expected empty doc store"
    pipeline(text=Document(text="Hello world"))
    assert pipeline.vector_store._collection.count() == 1, "Index 1 item"
    assert len(pipeline.doc_store._store) == 1, "Expected 1 document"


@patch(
    "openai.resources.embeddings.Embeddings.create",
    side_effect=lambda *args, **kwargs: openai_embedding,
)
def test_retrieving(tmp_path):
    db = ChromaVectorStore(path=str(tmp_path))
    doc_store = InMemoryDocumentStore()
    embedding = AzureOpenAIEmbeddings(
        azure_deployment="text-embedding-ada-002",
        azure_endpoint="https://test.openai.azure.com/",
        api_key="some-key",
        api_version="version",
    )

    index_pipeline = VectorIndexing(
        vector_store=db, embedding=embedding, doc_store=doc_store
    )
    retrieval_pipeline = VectorRetrieval(
        vector_store=db, doc_store=doc_store, embedding=embedding
    )

    index_pipeline(text=Document(text="Hello world"))
    output = retrieval_pipeline(text="Hello world")
    output1 = retrieval_pipeline(text="Hello world")

    assert len(output) == 1, "Expect 1 results"
    assert output == output1, "Expect identical results"


def test_hybrid_retrieval_deduplicates_overlapping_documents():
    output = _run_hybrid_retrieval(
        text_ids=["A", "B"], vector_ids=["A", "C"], vector_scores=[0.91, 0.73]
    )

    assert [doc.doc_id for doc in output] == ["B", "A", "C"]
    assert len({doc.doc_id for doc in output}) == len(output)
    assert next(doc for doc in output if doc.doc_id == "A").score == 0.91


def test_hybrid_retrieval_keeps_disjoint_documents():
    output = _run_hybrid_retrieval(
        text_ids=["A", "B"], vector_ids=["C", "D"], vector_scores=[0.82, 0.64]
    )

    assert [doc.doc_id for doc in output] == ["A", "B", "C", "D"]
