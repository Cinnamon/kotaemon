import json
from pathlib import Path

import pytest
from openai.resources.embeddings import Embeddings

from kotaemon.docstores import InMemoryDocumentStore
from kotaemon.documents.base import Document
from kotaemon.embeddings.openai import AzureOpenAIEmbeddings
from kotaemon.pipelines.indexing import IndexVectorStoreFromDocumentPipeline
from kotaemon.pipelines.retrieving import RetrieveDocumentFromVectorStorePipeline
from kotaemon.pipelines.tools import ComponentTool, GoogleSearchTool, WikipediaTool
from kotaemon.vectorstores import ChromaVectorStore

with open(Path(__file__).parent / "resources" / "embedding_openai.json") as f:
    openai_embedding = json.load(f)


@pytest.fixture(scope="function")
def mock_openai_embedding(monkeypatch):
    monkeypatch.setattr(Embeddings, "create", lambda *args, **kwargs: openai_embedding)


def test_google_tool(mock_google_search):
    tool = GoogleSearchTool()
    assert tool.name
    assert tool.description
    output = tool("What is Cinnamon AI")
    assert output


def test_wikipedia_tool():
    tool = WikipediaTool()
    assert tool.name
    assert tool.description
    output = tool("Cinnamon")
    assert output


def test_pipeline_tool(mock_openai_embedding, tmp_path):
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

    index_tool = ComponentTool(
        name="index_document",
        description="A tool to use to index a document to be searched later",
        component=index_pipeline,
    )
    output = index_tool({"text": Document(text="Cinnamon AI")})

    retrieval_tool = ComponentTool(
        name="search_document",
        description="A tool to use to search a document in a vectorstore",
        component=retrieval_pipeline,
    )
    output = retrieval_tool("Cinnamon AI")
    assert output
