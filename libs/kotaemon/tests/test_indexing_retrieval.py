import json
from pathlib import Path
from typing import cast

import pytest
from openai.resources.embeddings import Embeddings

from kotaemon.base import Document
from kotaemon.embeddings import LCAzureOpenAIEmbeddings
from kotaemon.indices import VectorIndexing, VectorRetrieval
from kotaemon.storages import ChromaVectorStore, InMemoryDocumentStore

with open(Path(__file__).parent / "resources" / "embedding_openai.json") as f:
    openai_embedding = json.load(f)


@pytest.fixture(scope="function")
def mock_openai_embedding(monkeypatch):
    monkeypatch.setattr(Embeddings, "create", lambda *args, **kwargs: openai_embedding)


def test_indexing(mock_openai_embedding, tmp_path):
    db = ChromaVectorStore(path=str(tmp_path))
    doc_store = InMemoryDocumentStore()
    embedding = LCAzureOpenAIEmbeddings(
        model="text-embedding-ada-002",
        deployment="embedding-deployment",
        azure_endpoint="https://test.openai.azure.com/",
        openai_api_key="some-key",
    )

    pipeline = VectorIndexing(vector_store=db, embedding=embedding, doc_store=doc_store)
    pipeline.doc_store = cast(InMemoryDocumentStore, pipeline.doc_store)
    pipeline.vector_store = cast(ChromaVectorStore, pipeline.vector_store)
    assert pipeline.vector_store._collection.count() == 0, "Expected empty collection"
    assert len(pipeline.doc_store._store) == 0, "Expected empty doc store"
    pipeline(text=Document(text="Hello world"))
    assert pipeline.vector_store._collection.count() == 1, "Index 1 item"
    assert len(pipeline.doc_store._store) == 1, "Expected 1 document"


def test_retrieving(mock_openai_embedding, tmp_path):
    db = ChromaVectorStore(path=str(tmp_path))
    doc_store = InMemoryDocumentStore()
    embedding = LCAzureOpenAIEmbeddings(
        model="text-embedding-ada-002",
        deployment="embedding-deployment",
        azure_endpoint="https://test.openai.azure.com/",
        openai_api_key="some-key",
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
