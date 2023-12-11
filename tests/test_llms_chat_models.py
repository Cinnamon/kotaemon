from unittest.mock import patch

from langchain.chat_models import AzureChatOpenAI as AzureChatOpenAILC
from openai.types.chat.chat_completion import ChatCompletion

from kotaemon.base.schema import (
    AIMessage,
    HumanMessage,
    LLMInterface,
    SystemMessage,
)
from kotaemon.llms import AzureChatOpenAI

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


@patch(
    "openai.resources.chat.completions.Completions.create",
    side_effect=lambda *args, **kwargs: _openai_chat_completion_response,
)
def test_azureopenai_model(openai_completion):
    model = AzureChatOpenAI(
        openai_api_base="https://test.openai.azure.com/",
        openai_api_key="some-key",
        openai_api_version="2023-03-15-preview",
        deployment_name="gpt35turbo",
        temperature=0,
    )
    assert isinstance(
        model.to_langchain_format(), AzureChatOpenAILC
    ), "Agent not wrapped in Langchain's AzureChatOpenAI"

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
