import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from kotaemon.embeddings import VoyageAIEmbeddings
from kotaemon.embeddings.voyageai import split_into_batches
from kotaemon.rerankings import VoyageAIReranking

from .conftest import skip_when_voyageai_not_installed


def _tokens(counts):
    """Fake `Client.tokenize` result: one encoding per text."""
    return [SimpleNamespace(ids=[0] * n) for n in counts]


def _embed_result(texts):
    # first component identifies the text, so the order can be checked
    return SimpleNamespace(embeddings=[[float(t)] for t in texts])


def _contextualized_result(vectors, chunks_per_input=1):
    return SimpleNamespace(
        results=[
            SimpleNamespace(index=i, embeddings=[v] * chunks_per_input)
            for i, v in enumerate(vectors)
        ]
    )


@pytest.mark.parametrize(
    "counts, max_tokens, max_inputs, expected",
    [
        # splits at the token ceiling, not before
        ([40, 60, 1], 100, 1000, [(0, 2), (2, 3)]),
        # a single text above the ceiling goes alone, neighbours are not dropped
        ([10, 500, 10], 100, 1000, [(0, 1), (1, 2), (2, 3)]),
        # item cap applies independently of tokens
        ([1] * 5, None, 2, [(0, 2), (2, 4), (4, 5)]),
        # no texts, no requests
        ([], 100, 1000, []),
    ],
)
def test_split_into_batches(counts, max_tokens, max_inputs, expected):
    assert split_into_batches(counts, max_tokens, max_inputs) == expected


@skip_when_voyageai_not_installed
def test_unknown_embedding_model_is_rejected():
    with pytest.raises(ValueError, match="Unknown Voyage embedding model"):
        VoyageAIEmbeddings(api_key="test", model="voyage-nope")


@skip_when_voyageai_not_installed
def test_unknown_rerank_model_is_rejected():
    with pytest.raises(ValueError, match="Unknown Voyage rerank model"):
        VoyageAIReranking(api_key="test", model_name="rerank-nope")


@skip_when_voyageai_not_installed
def test_invalid_input_type_is_rejected():
    model = VoyageAIEmbeddings(api_key="test", model="voyage-4")
    with pytest.raises(ValueError, match="input_type"):
        model("hi", input_type="passage")


@skip_when_voyageai_not_installed
@patch("voyageai.Client.tokenize", return_value=_tokens([150_000] * 3))
@patch("voyageai.Client.embed", side_effect=lambda texts, **kw: _embed_result(texts))
def test_embeddings_split_by_token_ceiling_keep_order(embed, tokenize):
    # voyage-4: 320K tokens per request; 3 x 150K needs two requests
    model = VoyageAIEmbeddings(api_key="test", model="voyage-4")
    output = model(["1", "2", "3"])

    assert [call.args[0] for call in embed.call_args_list] == [["1", "2"], ["3"]]
    assert [d.embedding for d in output] == [[1.0], [2.0], [3.0]]
    assert [d.content for d in output] == ["1", "2", "3"]


@skip_when_voyageai_not_installed
@patch("voyageai.Client.tokenize")
@patch("voyageai.Client.embed", side_effect=lambda texts, **kw: _embed_result(texts))
def test_code_4_is_split_only_by_input_count(embed, tokenize):
    # no token ceiling is documented for voyage-code-4: no counting, no invented cap
    model = VoyageAIEmbeddings(api_key="test", model="voyage-code-4")
    output = model([str(i) for i in range(1001)])

    tokenize.assert_not_called()
    assert [len(call.args[0]) for call in embed.call_args_list] == [1000, 1]
    assert len(output) == 1001


@skip_when_voyageai_not_installed
@patch("voyageai.Client.embed", side_effect=lambda texts, **kw: _embed_result(texts))
def test_output_dimension_and_input_type_sent_only_when_given(embed):
    plain = VoyageAIEmbeddings(api_key="test", model="voyage-4")
    plain("1")
    assert embed.call_args.kwargs == {"model": "voyage-4"}

    sized = VoyageAIEmbeddings(api_key="test", model="voyage-4", output_dimension=256)
    sized("1", input_type="query")
    assert embed.call_args.kwargs == {
        "model": "voyage-4",
        "input_type": "query",
        "output_dimension": 256,
    }


@skip_when_voyageai_not_installed
@patch("voyageai.Client.tokenize", return_value=_tokens([150_000] * 3))
@patch("voyageai.AsyncClient.embed", new_callable=AsyncMock)
def test_async_embeddings_await_the_response_and_keep_order(embed, tokenize):
    embed.side_effect = lambda texts, **kw: _embed_result(texts)
    model = VoyageAIEmbeddings(api_key="test", model="voyage-4")
    output = asyncio.run(model.ainvoke(["1", "2", "3"]))

    assert [call.args[0] for call in embed.call_args_list] == [["1", "2"], ["3"]]
    assert [d.embedding for d in output] == [[1.0], [2.0], [3.0]]


@skip_when_voyageai_not_installed
@patch(
    "voyageai.Client.contextualized_embed",
    side_effect=lambda inputs, **kw: _contextualized_result(
        [[float(i)] for i in inputs]
    ),
)
def test_contextualized_document_uses_flat_list_with_auto_chunking(ctx):
    model = VoyageAIEmbeddings(api_key="test", model="voyage-context-4")
    output = model(["1", "2"], input_type="document")

    assert ctx.call_args.args[0] == ["1", "2"]  # flat list[str], not list[list[str]]
    assert ctx.call_args.kwargs == {
        "model": "voyage-context-4",
        "input_type": "document",
        "enable_auto_chunking": True,
        "chunk_size": 32_000,
    }
    assert [d.embedding for d in output] == [[1.0], [2.0]]


@skip_when_voyageai_not_installed
@patch(
    "voyageai.Client.contextualized_embed",
    side_effect=lambda inputs, **kw: _contextualized_result(
        [[float(i)] for i in inputs]
    ),
)
def test_contextualized_query_has_no_auto_chunking(ctx):
    model = VoyageAIEmbeddings(api_key="test", model="voyage-context-3")
    model("1", input_type="query")

    assert ctx.call_args.args[0] == ["1"]
    assert ctx.call_args.kwargs == {"model": "voyage-context-3", "input_type": "query"}


@skip_when_voyageai_not_installed
@patch("voyageai.Client.contextualized_embed")
def test_contextualized_input_split_into_chunks_is_an_error(ctx):
    ctx.return_value = _contextualized_result([[1.0]], chunks_per_input=2)
    model = VoyageAIEmbeddings(api_key="test", model="voyage-context-4")
    with pytest.raises(ValueError, match="split into 2 chunks"):
        model("a very long document")


@skip_when_voyageai_not_installed
@patch("voyageai.Client.rerank")
def test_rerank_top_k_sent_only_when_given(rerank):
    from kotaemon.base import Document

    rerank.return_value = SimpleNamespace(
        results=[SimpleNamespace(index=1, relevance_score=0.9)]
    )
    docs = [Document(content="a"), Document(content="b")]

    result = VoyageAIReranking(api_key="test", model_name="rerank-3", top_k=1).run(
        docs, "q"
    )
    assert rerank.call_args.kwargs["top_k"] == 1
    assert [d.content for d in result] == ["b"]
    assert result[0].metadata["reranking_score"] == 0.9

    VoyageAIReranking(api_key="test", model_name="rerank-3").run(docs, "q")
    assert "top_k" not in rerank.call_args.kwargs
