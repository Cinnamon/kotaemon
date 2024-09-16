import json
from pathlib import Path
from unittest.mock import patch

from openai.types.create_embedding_response import CreateEmbeddingResponse

from kotaemon.base import Document
from kotaemon.embeddings import (
    AzureOpenAIEmbeddings,
    FastEmbedEmbeddings,
    LCCohereEmbeddings,
    LCHuggingFaceEmbeddings,
    OpenAIEmbeddings,
)

from .conftest import (
    skip_when_cohere_not_installed,
    skip_when_fastembed_not_installed,
    skip_when_sentence_bert_not_installed,
)

with open(Path(__file__).parent / "resources" / "embedding_openai_batch.json") as f:
    openai_embedding_batch = CreateEmbeddingResponse.model_validate(json.load(f))

with open(Path(__file__).parent / "resources" / "embedding_openai.json") as f:
    openai_embedding = CreateEmbeddingResponse.model_validate(json.load(f))


def assert_embedding_result(output):
    assert isinstance(output, list)
    assert isinstance(output[0], Document)
    assert isinstance(output[0].embedding, list)
    assert isinstance(output[0].embedding[0], float)


@patch(
    "openai.resources.embeddings.Embeddings.create",
    side_effect=lambda *args, **kwargs: openai_embedding,
)
def test_azureopenai_embeddings_raw(openai_embedding_call):
    model = AzureOpenAIEmbeddings(
        azure_deployment="embedding-deployment",
        azure_endpoint="https://test.openai.azure.com/",
        api_key="some-key",
        api_version="version",
    )
    output = model("Hello world")
    assert_embedding_result(output)
    openai_embedding_call.assert_called()


@patch(
    "openai.resources.embeddings.Embeddings.create",
    side_effect=lambda *args, **kwargs: openai_embedding_batch,
)
def test_lcazureopenai_embeddings_batch_raw(openai_embedding_call):
    model = AzureOpenAIEmbeddings(
        azure_deployment="embedding-deployment",
        azure_endpoint="https://test.openai.azure.com/",
        api_key="some-key",
        api_version="version",
    )
    output = model(["Hello world", "Goodbye world"])
    assert_embedding_result(output)
    openai_embedding_call.assert_called()


@patch(
    "openai.resources.embeddings.Embeddings.create",
    side_effect=lambda *args, **kwargs: openai_embedding_batch,
)
def test_azureopenai_embeddings_batch_raw(openai_embedding_call):
    model = AzureOpenAIEmbeddings(
        azure_deployment="text-embedding-ada-002",
        azure_endpoint="https://test.openai.azure.com/",
        api_key="some-key",
        api_version="version",
    )
    output = model(["Hello world", "Goodbye world"])
    assert_embedding_result(output)
    openai_embedding_call.assert_called()


@patch(
    "openai.resources.embeddings.Embeddings.create",
    side_effect=lambda *args, **kwargs: openai_embedding,
)
def test_openai_embeddings_raw(openai_embedding_call):
    model = OpenAIEmbeddings(
        api_key="some-key",
        model="text-embedding-ada-002",
    )
    output = model("Hello world")
    assert_embedding_result(output)
    openai_embedding_call.assert_called()


@patch(
    "openai.resources.embeddings.Embeddings.create",
    side_effect=lambda *args, **kwargs: openai_embedding_batch,
)
def test_openai_embeddings_batch_raw(openai_embedding_call):
    model = OpenAIEmbeddings(
        api_key="some-key",
        model="text-embedding-ada-002",
    )
    output = model(["Hello world", "Goodbye world"])
    assert_embedding_result(output)
    openai_embedding_call.assert_called()


@skip_when_sentence_bert_not_installed
@patch(
    "sentence_transformers.SentenceTransformer",
    side_effect=lambda *args, **kwargs: None,
)
@patch(
    "langchain.embeddings.huggingface.HuggingFaceBgeEmbeddings.embed_documents",
    side_effect=lambda *args, **kwargs: [[1.0, 2.1, 3.2]],
)
def test_lchuggingface_embeddings(
    langchain_huggingface_embedding_call, sentence_transformers_init
):
    model = LCHuggingFaceEmbeddings(
        model_name="intfloat/multilingual-e5-large",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": False},
    )

    output = model("Hello World")
    assert_embedding_result(output)
    sentence_transformers_init.assert_called()
    langchain_huggingface_embedding_call.assert_called()


@skip_when_cohere_not_installed
@patch(
    "langchain.embeddings.cohere.CohereEmbeddings.embed_documents",
    side_effect=lambda *args, **kwargs: [[1.0, 2.1, 3.2]],
)
def test_lccohere_embeddings(langchain_cohere_embedding_call):
    model = LCCohereEmbeddings(
        model="embed-english-light-v2.0",
        cohere_api_key="my-api-key",
        user_agent="test",
    )

    output = model("Hello World")
    assert_embedding_result(output)
    langchain_cohere_embedding_call.assert_called()


@skip_when_fastembed_not_installed
def test_fastembed_embeddings():
    model = FastEmbedEmbeddings()
    output = model("Hello World")
    assert_embedding_result(output)
