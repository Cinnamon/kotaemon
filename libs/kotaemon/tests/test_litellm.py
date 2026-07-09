from types import SimpleNamespace
from unittest.mock import patch

from kotaemon.base import DocumentWithEmbedding, LLMInterface
from kotaemon.base.schema import AIMessage, HumanMessage, SystemMessage
from kotaemon.embeddings import LiteLLMEmbeddings
from kotaemon.llms import ChatLiteLLM


# ── Chat fixtures ──────────────────────────────────────────────────────────


def _mock_completion_response(**overrides):
    defaults = {
        "id": "chatcmpl-litellm-test",
        "object": "chat.completion",
        "created": 1700000000,
        "model": "gpt-4o-mini",
        "choices": [
            {
                "index": 0,
                "finish_reason": "stop",
                "message": {
                    "role": "assistant",
                    "content": "Hello! How can I help you?",
                },
            }
        ],
        "usage": {
            "completion_tokens": 8,
            "prompt_tokens": 12,
            "total_tokens": 20,
        },
    }
    defaults.update(overrides)
    resp = SimpleNamespace()
    resp.model_dump = lambda: defaults
    return resp


def _mock_stream_chunks():
    for text in ["Hello", " world", "!"]:
        chunk = SimpleNamespace()
        chunk.model_dump = lambda t=text: {
            "choices": [{"delta": {"content": t}}]
        }
        yield chunk


# ── Chat tests ─────────────────────────────────────────────────────────────


@patch("litellm.completion", return_value=_mock_completion_response())
def test_chat_litellm_invoke_str(mock_completion):
    model = ChatLiteLLM(model="gpt-4o-mini", api_key="test-key")
    output = model("Hello world")

    assert isinstance(output, LLMInterface)
    assert output.content == "Hello! How can I help you?"
    assert output.total_tokens == 20
    mock_completion.assert_called_once()
    call_kwargs = mock_completion.call_args[1]
    assert call_kwargs["model"] == "gpt-4o-mini"
    assert call_kwargs["drop_params"] is True


@patch("litellm.completion", return_value=_mock_completion_response())
def test_chat_litellm_invoke_messages(mock_completion):
    model = ChatLiteLLM(model="anthropic/claude-3-sonnet", api_key="test-key")
    messages = [
        SystemMessage(content="You are helpful"),
        HumanMessage(content="What is 2+2?"),
        AIMessage(content="4"),
        HumanMessage(content="Thanks"),
    ]
    output = model(messages)

    assert isinstance(output, LLMInterface)
    mock_completion.assert_called_once()
    sent_messages = mock_completion.call_args[1]["messages"]
    assert len(sent_messages) == 4
    assert sent_messages[0]["role"] == "system"


@patch("litellm.completion", return_value=_mock_completion_response())
def test_chat_litellm_api_base_forwarded(mock_completion):
    model = ChatLiteLLM(
        model="gpt-4o",
        api_key="proxy-key",
        api_base="http://localhost:4000",
    )
    model("test")

    call_kwargs = mock_completion.call_args[1]
    assert call_kwargs["api_base"] == "http://localhost:4000"
    assert call_kwargs["api_key"] == "proxy-key"


@patch("litellm.completion", return_value=_mock_completion_response())
def test_chat_litellm_drop_params_default(mock_completion):
    model = ChatLiteLLM(model="gpt-4o-mini", api_key="k")
    model("test")
    assert mock_completion.call_args[1]["drop_params"] is True


@patch("litellm.completion", return_value=_mock_completion_response())
def test_chat_litellm_drop_params_override(mock_completion):
    model = ChatLiteLLM(model="gpt-4o-mini", api_key="k")
    model("test", drop_params=False)
    assert mock_completion.call_args[1]["drop_params"] is False


@patch(
    "litellm.completion",
    return_value=_mock_completion_response(choices=[]),
)
def test_chat_litellm_empty_choices(mock_completion):
    model = ChatLiteLLM(model="gpt-4o-mini", api_key="k")
    output = model("test")
    assert output.content == ""


@patch("litellm.completion", return_value=iter(_mock_stream_chunks()))
def test_chat_litellm_stream(mock_completion):
    model = ChatLiteLLM(model="gpt-4o-mini", api_key="k")
    chunks = list(model.stream("Hello"))
    assert len(chunks) == 3
    assert chunks[0].content == "Hello"
    assert chunks[2].content == "!"


# ── Embedding fixtures ─────────────────────────────────────────────────────


def _mock_embedding_response(num_inputs=1):
    resp = SimpleNamespace()
    resp.model_dump = lambda: {
        "data": [
            {"index": i, "embedding": [0.1 * i, 0.2, 0.3]}
            for i in range(num_inputs)
        ],
        "usage": {"prompt_tokens": 5, "total_tokens": 5},
    }
    return resp


# ── Embedding tests ────────────────────────────────────────────────────────


@patch("litellm.embedding", return_value=_mock_embedding_response(1))
def test_litellm_embeddings_single(mock_embedding):
    model = LiteLLMEmbeddings(
        model="text-embedding-3-small", api_key="test-key"
    )
    output = model("Hello world")

    assert isinstance(output, list)
    assert len(output) == 1
    assert isinstance(output[0], DocumentWithEmbedding)
    assert isinstance(output[0].embedding[0], float)
    mock_embedding.assert_called_once()
    assert mock_embedding.call_args[1]["drop_params"] is True


@patch("litellm.embedding", return_value=_mock_embedding_response(2))
def test_litellm_embeddings_batch(mock_embedding):
    model = LiteLLMEmbeddings(
        model="text-embedding-3-small", api_key="test-key"
    )
    output = model(["Hello", "World"])

    assert len(output) == 2
    assert all(isinstance(doc, DocumentWithEmbedding) for doc in output)


@patch("litellm.embedding", return_value=_mock_embedding_response(1))
def test_litellm_embeddings_api_base(mock_embedding):
    model = LiteLLMEmbeddings(
        model="text-embedding-3-small",
        api_key="proxy-key",
        api_base="http://localhost:4000",
    )
    model("test")
    assert mock_embedding.call_args[1]["api_base"] == "http://localhost:4000"
