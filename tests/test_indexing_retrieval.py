import json
from pathlib import Path
from typing import cast

import pytest
from openai.resources.embeddings import Embeddings

from kotaemon.docstores import InMemoryDocumentStore
from kotaemon.documents.base import Document
from kotaemon.embeddings.openai import AzureOpenAIEmbeddings
from kotaemon.pipelines.indexing import IndexVectorStoreFromDocumentPipeline
from kotaemon.pipelines.retrieving import RetrieveDocumentFromVectorStorePipeline
from kotaemon.vectorstores import ChromaVectorStore

with open(Path(__file__).parent / "resources" / "embedding_openai.json") as f:
    openai_embedding = json.load(f)


@pytest.fixture(scope="function")
def mock_openai_embedding(monkeypatch):
    monkeypatch.setattr(Embeddings, "create", lambda *args, **kwargs: openai_embedding)


def test_indexing(mock_openai_embedding, tmp_path):
    db = ChromaVectorStore(path=str(tmp_path))
    doc_store = InMemoryDocumentStore()
    embedding = AzureOpenAIEmbeddings(
        model="text-embedding-ada-002",
        deployment="embedding-deployment",
        openai_api_base="https://test.openai.azure.com/",
        openai_api_key="some-key",
    )

    pipeline = IndexVectorStoreFromDocumentPipeline(
        vector_store=db, embedding=embedding, doc_store=doc_store
    )
    pipeline.doc_store = cast(InMemoryDocumentStore, pipeline.doc_store)
    assert pipeline.vector_store._collection.count() == 0, "Expected empty collection"
    assert len(pipeline.doc_store._store) == 0, "Expected empty doc store"
    pipeline(text=Document(text="Hello world"))
    assert pipeline.vector_store._collection.count() == 1, "Index 1 item"
    assert len(pipeline.doc_store._store) == 1, "Expected 1 document"


def test_retrieving(mock_openai_embedding, tmp_path):
    db = ChromaVectorStore(path=str(tmp_path))
    doc_store = InMemoryDocumentStore()
    embedding = AzureOpenAIEmbeddings(
        model="text-embedding-ada-002",
        deployment="embedding-deployment",
        openai_api_base="https://test.openai.azure.com/",
        openai_api_key="some-key",
    )

    index_pipeline = IndexVectorStoreFromDocumentPipeline(
        vector_store=db, embedding=embedding, doc_store=doc_store
    )
    retrieval_pipeline = RetrieveDocumentFromVectorStorePipeline(
        vector_store=db, doc_store=doc_store, embedding=embedding
    )

    index_pipeline(text=Document(text="Hello world"))
    output = retrieval_pipeline(text="Hello world")
    output1 = retrieval_pipeline(text="Hello world")

    assert len(output) == 1, "Expect 1 results"
    assert output == output1, "Expect identical results"
