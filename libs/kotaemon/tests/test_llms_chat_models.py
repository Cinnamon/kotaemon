from pathlib import Path
from unittest.mock import patch

import pytest

from kotaemon.base.schema import AIMessage, HumanMessage, LLMInterface, SystemMessage
from kotaemon.llms import AzureChatOpenAI, ChatMiniMax, LlamaCppChat

try:
    pass
except ImportError:
    pass

from openai.types.chat.chat_completion import ChatCompletion

from .conftest import skip_llama_cpp_not_installed

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
                "logprobs": None,
            }
        ],
        "usage": {"completion_tokens": 9, "prompt_tokens": 10, "total_tokens": 19},
    }
)


@patch(
    "openai.resources.chat.completions.Completions.create",
    side_effect=lambda *args, **kwargs: _openai_chat_completion_response,
)
def test_azureopenai_model(openai_completion):
    model = AzureChatOpenAI(
        api_key="dummy",
        api_version="2024-05-01-preview",
        azure_deployment="gpt-4o",
        azure_endpoint="https://test.openai.azure.com/",
    )
    # test for str input - stream mode
    output = model("hello world")
    assert isinstance(
        output, LLMInterface
    ), "Output for single text is not LLMInterface"
    openai_completion.assert_called()

    # test for list[message] input - stream mode
    messages = [
        SystemMessage(content="You are a philosohper"),
        HumanMessage(content="What is the meaning of life"),
        AIMessage(content="42"),
        HumanMessage(content="What is the meaning of 42"),
    ]

    output = model(messages)
    assert isinstance(
        output, LLMInterface
    ), "Output for single text is not LLMInterface"
    openai_completion.assert_called()


@patch(
    "openai.resources.chat.completions.Completions.create",
    side_effect=lambda *args, **kwargs: _openai_chat_completion_response,
)
def test_minimax_model(openai_completion):
    model = ChatMiniMax(
        api_key="dummy",
        model="MiniMax-M2.7",
    )
    output = model("hello world")
    assert isinstance(output, LLMInterface), "Output is not LLMInterface"
    openai_completion.assert_called()

    # verify temperature clamping: zero should become 0.01
    model_zero_temp = ChatMiniMax(
        api_key="dummy",
        model="MiniMax-M2.7",
        temperature=0,
    )
    params = model_zero_temp.prepare_params()
    assert params["temperature"] == 0.01, "Temperature 0 should be clamped to 0.01"

    # verify response_format is stripped
    params_with_rf = model.prepare_params(response_format={"type": "json_object"})
    assert "response_format" not in params_with_rf, "response_format should be removed"


@patch(
    "openai.resources.chat.completions.Completions.create",
    side_effect=lambda *args, **kwargs: _openai_chat_completion_response,
)
def test_minimax_default_model_is_m27(openai_completion):
    """Default model should be MiniMax-M2.7."""
    model = ChatMiniMax(api_key="dummy")
    assert model.model == "MiniMax-M2.7", "Default model should be MiniMax-M2.7"

    # M2.7-highspeed should also work
    model_hs = ChatMiniMax(api_key="dummy", model="MiniMax-M2.7-highspeed")
    output = model_hs("hello world")
    assert isinstance(output, LLMInterface), "Output is not LLMInterface"
    openai_completion.assert_called()

    # Older M2.5 models should still work
    model_old = ChatMiniMax(api_key="dummy", model="MiniMax-M2.5")
    output = model_old("hello world")
    assert isinstance(output, LLMInterface), "Output is not LLMInterface"
    openai_completion.assert_called()


@skip_llama_cpp_not_installed
def test_llamacpp_chat():
    from llama_cpp import Llama

    dir_path = Path(__file__).parent / "resources" / "ggml-vocab-llama.gguf"

    # test initialization
    model = LlamaCppChat(model_path=str(dir_path), chat_format="llama", vocab_only=True)
    assert isinstance(model.client_object, Llama), "Error initializing llama_cpp.Llama"

    # test error if model_path is omitted
    with pytest.raises(ValueError):
        model = LlamaCppChat(chat_format="llama", vocab_only=True)
        model.client_object

    # test error if chat_format is omitted
    with pytest.raises(ValueError):
        model = LlamaCppChat(model_path=str(dir_path), vocab_only=True)
        model.client_object
