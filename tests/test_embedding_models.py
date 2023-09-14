import json
from pathlib import Path
from unittest.mock import patch

from kotaemon.embeddings.openai import AzureOpenAIEmbeddings

with open(Path(__file__).parent / "resources" / "embedding_openai_batch.json") as f:
    openai_embedding_batch = json.load(f)

with open(Path(__file__).parent / "resources" / "embedding_openai.json") as f:
    openai_embedding = json.load(f)


@patch(
    "openai.api_resources.embedding.Embedding.create",
    side_effect=lambda *args, **kwargs: openai_embedding,
)
def test_azureopenai_embeddings_raw(openai_embedding_call):
    model = AzureOpenAIEmbeddings(
        model="text-embedding-ada-002",
        deployment="embedding-deployment",
        openai_api_base="https://test.openai.azure.com/",
        openai_api_key="some-key",
    )
    output = model("Hello world")
    assert isinstance(output, list)
    assert isinstance(output[0], float)
    openai_embedding_call.assert_called()


@patch(
    "openai.api_resources.embedding.Embedding.create",
    side_effect=lambda *args, **kwargs: openai_embedding_batch,
)
def test_azureopenai_embeddings_batch_raw(openai_embedding_call):
    model = AzureOpenAIEmbeddings(
        model="text-embedding-ada-002",
        deployment="embedding-deployment",
        openai_api_base="https://test.openai.azure.com/",
        openai_api_key="some-key",
    )
    output = model(["Hello world", "Goodbye world"])
    assert isinstance(output, list)
    assert isinstance(output[0], list)
    assert isinstance(output[0][0], float)
    openai_embedding_call.assert_called()
