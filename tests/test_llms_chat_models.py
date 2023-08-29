from unittest.mock import patch

from langchain.chat_models import AzureChatOpenAI as AzureChatOpenAILC
from langchain.schema.messages import (
    SystemMessage,
    HumanMessage,
    AIMessage,
)

from kotaemon.llms.chats.openai import AzureChatOpenAI
from kotaemon.llms.base import LLMInterface


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


@patch(
    "openai.api_resources.chat_completion.ChatCompletion.create",
    side_effect=lambda *args, **kwargs: _openai_chat_completion_response,
)
def test_azureopenai_model(openai_completion):
    model = AzureChatOpenAI(
        openai_api_base="https://test.openai.azure.com/",
        openai_api_key="some-key",
        openai_api_version="2023-03-15-preview",
        deployment_name="gpt35turbo",
        temperature=0,
        request_timeout=60,
    )
    assert isinstance(
        model.agent, AzureChatOpenAILC
    ), "Agent not wrapped in Langchain's AzureChatOpenAI"

    # test for str input - stream mode
    output = model("hello world")
    assert isinstance(output, LLMInterface), "Output for single text is not LLMInterface"
    openai_completion.assert_called()

    # test for list[str] input - batch mode
    output = model(["hello world"])
    assert isinstance(output, list), "Output for batch string is not a list"
    assert isinstance(output[0], LLMInterface), "Output for text is not LLMInterface"
    openai_completion.assert_called()

    # test for list[message] input - stream mode
    messages = [
        SystemMessage(content="You are a philosohper"),
        HumanMessage(content="What is the meaning of life"),
        AIMessage(content="42"),
        HumanMessage(content="What is the meaning of 42"),
    ]

    output = model(messages)
    assert isinstance(output, LLMInterface), "Output for single text is not LLMInterface"
    openai_completion.assert_called()

    # test for list[list[message]] input - batch mode
    output = model([messages])
    assert isinstance(output, list), "Output for batch string is not a list"
    assert isinstance(output[0], LLMInterface), "Output for text is not LLMInterface"
    openai_completion.assert_called()

