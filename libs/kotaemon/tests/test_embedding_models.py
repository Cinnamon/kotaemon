import json
from pathlib import Path
from unittest.mock import Mock, patch

from openai.types.create_embedding_response import CreateEmbeddingResponse

from kotaemon.base import Document, DocumentWithEmbedding
from kotaemon.embeddings import (
    AzureOpenAIEmbeddings,
    FastEmbedEmbeddings,
    LCCohereEmbeddings,
    LCHuggingFaceEmbeddings,
    OpenAIEmbeddings,
    VoyageAIEmbeddings,
)

from .conftest import (
    skip_when_cohere_not_installed,
    skip_when_fastembed_not_installed,
    skip_when_sentence_bert_not_installed,
    skip_when_voyageai_not_installed,
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
    "langchain_cohere.CohereEmbeddings.embed_documents",
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


voyage_output_mock = Mock()
voyage_output_mock.embeddings = [[1.0, 2.1, 3.2]]


def _voyage_embed_side_effect(texts, *args, **kwargs):
    out = Mock()
    out.embeddings = [[1.0, 2.1, 3.2] for _ in texts]
    return out


def _voyage_context_side_effect(*args, **kwargs):
    inputs = kwargs["inputs"]
    out = Mock()
    # each input resolves to a single chunk -> a single embedding
    out.results = [Mock(embeddings=[[1.0, 2.1, 3.2]]) for _ in inputs]
    return out


def _voyage_tokenize_side_effect(texts, *args, **kwargs):
    # one token per whitespace-separated word, at least one token
    return [list(range(max(len(t.split()), 1))) for t in texts]


@skip_when_voyageai_not_installed
@patch("voyageai.Client.tokenize", side_effect=_voyage_tokenize_side_effect)
@patch("voyageai.Client.embed", side_effect=_voyage_embed_side_effect)
def test_voyageai_embeddings(embed_call, tokenize_call):
    model = VoyageAIEmbeddings(api_key="test", model="voyage-3.5")
    output = model(["Hello, world!", "Goodbye, world!"])
    assert all(isinstance(doc, DocumentWithEmbedding) for doc in output)
    assert len(output) == 2
    embed_call.assert_called()
    # the regular path forwards the document input_type by default
    assert embed_call.call_args.kwargs["input_type"] == "document"


@skip_when_voyageai_not_installed
@patch("voyageai.Client.tokenize", side_effect=_voyage_tokenize_side_effect)
@patch(
    "voyageai.Client.contextualized_embed",
    side_effect=_voyage_context_side_effect,
)
def test_voyageai_contextualized_document(context_call, tokenize_call):
    model = VoyageAIEmbeddings(api_key="test", model="voyage-context-4")
    output = model(["chunk a", "chunk b", "chunk c"])

    assert all(isinstance(doc, DocumentWithEmbedding) for doc in output)
    assert len(output) == 3

    kwargs = context_call.call_args.kwargs
    # documents are sent as a flat list[str] with server-side auto-chunking so
    # each string becomes exactly one chunk / one embedding
    assert kwargs["inputs"] == ["chunk a", "chunk b", "chunk c"]
    assert kwargs["input_type"] == "document"
    assert kwargs["enable_auto_chunking"] is True
    assert kwargs["chunk_size"] == 32_000


@skip_when_voyageai_not_installed
@patch("voyageai.Client.tokenize", side_effect=_voyage_tokenize_side_effect)
@patch(
    "voyageai.Client.contextualized_embed",
    side_effect=_voyage_context_side_effect,
)
def test_voyageai_contextualized_query(context_call, tokenize_call):
    model = VoyageAIEmbeddings(api_key="test", model="voyage-context-4")
    output = model("what is voyage?", input_type="query")

    assert all(isinstance(doc, DocumentWithEmbedding) for doc in output)
    assert len(output) == 1

    kwargs = context_call.call_args.kwargs
    assert kwargs["input_type"] == "query"
    # the API rejects auto-chunking for queries, so it must be disabled and no
    # chunk_size may be sent
    assert kwargs["enable_auto_chunking"] is False
    assert "chunk_size" not in kwargs


@skip_when_voyageai_not_installed
@patch("voyageai.Client.tokenize", side_effect=_voyage_tokenize_side_effect)
def test_voyageai_batching_token_boundary(tokenize_call, monkeypatch):
    """Batches split once the estimated token budget would overflow."""
    import kotaemon.embeddings.voyageai as voyage_mod

    model = VoyageAIEmbeddings(api_key="test", model="voyage-3.5")
    monkeypatch.setattr(model, "_token_limit", lambda: 5)

    # 3 tokens each; two fit in a batch (6 > 5 -> split before the third)
    texts = ["a a a", "b b b", "c c c"]
    batches = list(model._iter_batches(texts))
    assert batches == [["a a a"], ["b b b"], ["c c c"]]

    # 2 tokens each: two per batch (4 <= 5), third opens a new batch
    texts = ["a a", "b b", "c c"]
    batches = list(model._iter_batches(texts))
    assert batches == [["a a", "b b"], ["c c"]]
    assert voyage_mod.MAX_BATCH_SIZE == 1000


@skip_when_voyageai_not_installed
@patch("voyageai.Client.tokenize", side_effect=_voyage_tokenize_side_effect)
def test_voyageai_batching_oversized_text_alone(tokenize_call, monkeypatch):
    """A single text larger than the token budget is still emitted on its own."""
    model = VoyageAIEmbeddings(api_key="test", model="voyage-3.5")
    monkeypatch.setattr(model, "_token_limit", lambda: 3)

    texts = ["one", "way too many tokens here for one batch", "two"]
    batches = list(model._iter_batches(texts))
    assert batches == [
        ["one"],
        ["way too many tokens here for one batch"],
        ["two"],
    ]


@skip_when_voyageai_not_installed
@patch("voyageai.Client.tokenize", side_effect=_voyage_tokenize_side_effect)
def test_voyageai_batching_item_count_cap(tokenize_call, monkeypatch):
    """The item-count cap still bounds batches even when tokens fit."""
    import kotaemon.embeddings.voyageai as voyage_mod

    monkeypatch.setattr(voyage_mod, "MAX_BATCH_SIZE", 2)
    model = VoyageAIEmbeddings(api_key="test", model="voyage-3.5")
    monkeypatch.setattr(model, "_token_limit", lambda: 10_000)

    texts = ["a", "b", "c", "d", "e"]
    batches = list(model._iter_batches(texts))
    assert batches == [["a", "b"], ["c", "d"], ["e"]]
