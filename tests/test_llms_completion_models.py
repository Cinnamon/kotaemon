from unittest.mock import patch

from langchain.llms import AzureOpenAI as AzureOpenAILC
from langchain.llms import OpenAI as OpenAILC
from openai.types.completion import Completion

from kotaemon.base.schema import LLMInterface
from kotaemon.llms import AzureOpenAI, OpenAI

_openai_completion_response = Completion.parse_obj(
    {
        "id": "cmpl-7qyNoIo6gRSCJR0hi8o3ZKBH4RkJ0",
        "object": "text_completion",
        "created": 1392751226,
        "model": "gpt-35-turbo",
        "system_fingerprint": None,
        "choices": [
            {
                "text": "completion",
                "index": 0,
                "finish_reason": "length",
                "logprobs": None,
            }
        ],
        "usage": {"completion_tokens": 20, "prompt_tokens": 2, "total_tokens": 22},
    }
)


@patch(
    "openai.resources.completions.Completions.create",
    side_effect=lambda *args, **kwargs: _openai_completion_response,
)
def test_azureopenai_model(openai_completion):
    model = AzureOpenAI(
        openai_api_base="https://test.openai.azure.com/",
        openai_api_key="some-key",
        openai_api_version="2023-03-15-preview",
        deployment_name="gpt35turbo",
        temperature=0,
        request_timeout=60,
    )
    assert isinstance(
        model.to_langchain_format(), AzureOpenAILC
    ), "Agent not wrapped in Langchain's AzureOpenAI"

    output = model("hello world")
    assert isinstance(
        output, LLMInterface
    ), "Output for single text is not LLMInterface"


@patch(
    "openai.resources.completions.Completions.create",
    side_effect=lambda *args, **kwargs: _openai_completion_response,
)
def test_openai_model(openai_completion):
    model = OpenAI(
        openai_api_base="https://test.openai.azure.com/",
        openai_api_key="some-key",
        openai_api_version="2023-03-15-preview",
        deployment_name="gpt35turbo",
        temperature=0,
        request_timeout=60,
    )
    assert isinstance(
        model.to_langchain_format(), OpenAILC
    ), "Agent is not wrapped in Langchain's OpenAI"

    output = model("hello world")
    assert isinstance(
        output, LLMInterface
    ), "Output for single text is not LLMInterface"
