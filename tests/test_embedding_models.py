import json
from pathlib import Path
from unittest.mock import patch

from kotaemon.embeddings.cohere import CohereEmbdeddings
from kotaemon.embeddings.huggingface import HuggingFaceEmbeddings
from kotaemon.embeddings.openai import AzureOpenAIEmbeddings

with open(Path(__file__).parent / "resources" / "embedding_openai_batch.json") as f:
    openai_embedding_batch = json.load(f)

with open(Path(__file__).parent / "resources" / "embedding_openai.json") as f:
    openai_embedding = json.load(f)


@patch(
    "openai.resources.embeddings.Embeddings.create",
    side_effect=lambda *args, **kwargs: openai_embedding,
)
def test_azureopenai_embeddings_raw(openai_embedding_call):
    model = AzureOpenAIEmbeddings(
        model="text-embedding-ada-002",
        deployment="embedding-deployment",
        azure_endpoint="https://test.openai.azure.com/",
        openai_api_key="some-key",
    )
    output = model("Hello world")
    assert isinstance(output, list)
    assert isinstance(output[0], list)
    assert isinstance(output[0][0], float)
    openai_embedding_call.assert_called()


@patch(
    "openai.resources.embeddings.Embeddings.create",
    side_effect=lambda *args, **kwargs: openai_embedding_batch,
)
def test_azureopenai_embeddings_batch_raw(openai_embedding_call):
    model = AzureOpenAIEmbeddings(
        model="text-embedding-ada-002",
        deployment="embedding-deployment",
        azure_endpoint="https://test.openai.azure.com/",
        openai_api_key="some-key",
    )
    output = model(["Hello world", "Goodbye world"])
    assert isinstance(output, list)
    assert isinstance(output[0], list)
    assert isinstance(output[0][0], float)
    openai_embedding_call.assert_called()


@patch(
    "sentence_transformers.SentenceTransformer",
    side_effect=lambda *args, **kwargs: None,
)
@patch(
    "langchain.embeddings.huggingface.HuggingFaceBgeEmbeddings.embed_documents",
    side_effect=lambda *args, **kwargs: [[1.0, 2.1, 3.2]],
)
def test_huggingface_embddings(
    langchain_huggingface_embedding_call, sentence_transformers_init
):
    model = HuggingFaceEmbeddings(
        model_name="intfloat/multilingual-e5-large",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": False},
    )

    output = model("Hello World")
    assert isinstance(output, list)
    assert isinstance(output[0], list)
    assert isinstance(output[0][0], float)
    sentence_transformers_init.assert_called()
    langchain_huggingface_embedding_call.assert_called()


@patch(
    "langchain.embeddings.cohere.CohereEmbeddings.embed_documents",
    side_effect=lambda *args, **kwargs: [[1.0, 2.1, 3.2]],
)
def test_cohere_embeddings(langchain_cohere_embedding_call):
    model = CohereEmbdeddings(
        model="embed-english-light-v2.0", cohere_api_key="my-api-key"
    )

    output = model("Hello World")
    assert isinstance(output, list)
    assert isinstance(output[0], list)
    assert isinstance(output[0][0], float)
    langchain_cohere_embedding_call.assert_called()
