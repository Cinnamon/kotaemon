import json
from pathlib import Path
from unittest.mock import patch

import pytest
from openai.api_resources.embedding import Embedding

from kotaemon.llms.chats.openai import AzureChatOpenAI
from kotaemon.pipelines.ingest import ReaderIndexingPipeline

with open(Path(__file__).parent / "resources" / "embedding_openai.json") as f:
    openai_embedding = json.load(f)


_openai_chat_completion_response = {
    "id": "chatcmpl-7qyuw6Q1CFCpcKsMdFkmUPUa7JP2x",
    "object": "chat.completion",
    "created": 1692338378,
    "model": "gpt-35-turbo",
    "choices": [
        {
            "index": 0,
            "finish_reason": "stop",
            "message": {
                "role": "assistant",
                "content": "Hello! How can I assist you today?",
            },
        }
    ],
    "usage": {"completion_tokens": 9, "prompt_tokens": 10, "total_tokens": 19},
}


@pytest.fixture(scope="function")
def mock_openai_embedding(monkeypatch):
    monkeypatch.setattr(Embedding, "create", lambda *args, **kwargs: openai_embedding)


@patch(
    "openai.api_resources.chat_completion.ChatCompletion.create",
    side_effect=lambda *args, **kwargs: _openai_chat_completion_response,
)
def test_ingest_pipeline(patch, mock_openai_embedding, tmp_path):
    indexing_pipeline = ReaderIndexingPipeline(
        storage=tmp_path, openai_api_key="some-key"
    )
    input_file_path = Path(__file__).parent / "resources/dummy.pdf"

    # call ingestion pipeline
    indexing_pipeline(input_file_path, force_reindex=True)
    retrieving_pipeline = indexing_pipeline.to_retrieving_pipeline()

    results = retrieving_pipeline("This is a query")
    assert len(results) == 1

    # create llm
    llm = AzureChatOpenAI(
        openai_api_base="https://test.openai.azure.com/",
        openai_api_key="some-key",
        openai_api_version="2023-03-15-preview",
        deployment_name="gpt35turbo",
        temperature=0,
        request_timeout=60,
    )
    qa_pipeline = indexing_pipeline.to_qa_pipeline(llm=llm, openai_api_key="some-key")
    response = qa_pipeline("Summarize this document.")
    assert response
