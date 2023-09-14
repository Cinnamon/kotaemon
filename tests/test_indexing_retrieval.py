import json
from pathlib import Path

import pytest
from openai.api_resources.embedding import Embedding

from kotaemon.documents.base import Document
from kotaemon.embeddings.openai import AzureOpenAIEmbeddings
from kotaemon.pipelines.indexing import IndexVectorStoreFromDocumentPipeline
from kotaemon.pipelines.retrieving import RetrieveDocumentFromVectorStorePipeline
from kotaemon.vectorstores import ChromaVectorStore

with open(Path(__file__).parent / "resources" / "embedding_openai.json") as f:
    openai_embedding = json.load(f)


@pytest.fixture(scope="function")
def mock_openai_embedding(monkeypatch):
    monkeypatch.setattr(Embedding, "create", lambda *args, **kwargs: openai_embedding)


def test_indexing(mock_openai_embedding, tmp_path):
    db = ChromaVectorStore(path=str(tmp_path))
    embedding = AzureOpenAIEmbeddings(
        model="text-embedding-ada-002",
        deployment="embedding-deployment",
        openai_api_base="https://test.openai.azure.com/",
        openai_api_key="some-key",
    )

    pipeline = IndexVectorStoreFromDocumentPipeline(
        vector_store=db, embedding=embedding
    )
    assert pipeline.vector_store._collection.count() == 0, "Expected empty collection"
    pipeline(text=Document(text="Hello world"))
    assert pipeline.vector_store._collection.count() == 1, "Index 1 item"


def test_retrieving(mock_openai_embedding, tmp_path):
    db = ChromaVectorStore(path=str(tmp_path))
    embedding = AzureOpenAIEmbeddings(
        model="text-embedding-ada-002",
        deployment="embedding-deployment",
        openai_api_base="https://test.openai.azure.com/",
        openai_api_key="some-key",
    )

    index_pipeline = IndexVectorStoreFromDocumentPipeline(
        vector_store=db, embedding=embedding
    )
    retrieval_pipeline = RetrieveDocumentFromVectorStorePipeline(
        vector_store=db, embedding=embedding
    )

    index_pipeline(text=Document(text="Hello world"))
    output = retrieval_pipeline(text=["Hello world", "Hello world"])

    assert len(output) == 2, "Expected 2 results"
    assert output[0] == output[1], "Expected identical results"
