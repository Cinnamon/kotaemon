import json
from pathlib import Path
from unittest.mock import patch
from typing import Any

import pytest
from index import ReaderIndexingPipeline
from openai.resources.embeddings import Embeddings
from openai.types.chat.chat_completion import ChatCompletion

from kotaemon.llms import AzureChatOpenAI

with open(Path(__file__).parent / "resources" / "embedding_openai.json") as f:
    openai_embedding = json.load(f)


_openai_chat_completion_response = ChatCompletion.parse_obj(
    {
        "id": "chatcmpl-7qyuw6Q1CFCpcKsMdFkmUPUa7JP2x",
        "object": "chat.completion",
        "created": 1692338378,
        "model": "gpt-35-turbo",
        "system_fingerprint": None,
        "choices": [
            {
                "index": 0,
                "finish_reason": "stop",
                "message": {
                    "role": "assistant",
                    "content": "Hello! How can I assist you today?",
                    "function_call": None,
                    "tool_calls": None,
                },
            }
        ],
        "usage": {"completion_tokens": 9, "prompt_tokens": 10, "total_tokens": 19},
    }
)


@pytest.fixture(scope="function")
def mock_openai_embedding(monkeypatch: Any) -> None:
    monkeypatch.setattr(Embeddings, "create", lambda *args, **kwargs: openai_embedding)


@patch(
    "openai.resources.chat.completions.Completions.create",
    side_effect=lambda *args, **kwargs: _openai_chat_completion_response,
)
def test_ingest_pipeline(patch: Any, mock_openai_embedding: Any, tmp_path: Any) -> None:
    indexing_pipeline = ReaderIndexingPipeline(
        storage_path=tmp_path,
    )
    indexing_pipeline.indexing_vector_pipeline.embedding.openai_api_key = "some-key"
    input_file_path = Path(__file__).parent / "resources/dummy.pdf"

    # call ingestion pipeline
    indexing_pipeline(input_file_path, force_reindex=True)
    retrieving_pipeline = indexing_pipeline.to_retrieving_pipeline()

    results = retrieving_pipeline("This is a query")
    assert len(results) == 1

    # create llm
    llm = AzureChatOpenAI(
        api_key="dummy",
        api_version="2024-05-01-preview",
        azure_deployment="gpt-4o",
        azure_endpoint="https://test.openai.azure.com/",
    )
    qa_pipeline = indexing_pipeline.to_qa_pipeline(llm=llm, openai_api_key="some-key")
    response = qa_pipeline("Summarize this document.")
    assert response


def test_qa_simple() -> None:
    pass


def test_qa_with_graph() -> None:
    pass


def test_simple_qa() -> None:
    pass


def test_simple_qa_with_conversation() -> None:
    pass
