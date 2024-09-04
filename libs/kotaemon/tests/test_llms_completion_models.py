from pathlib import Path
from unittest.mock import patch

from kotaemon.base.schema import LLMInterface
from kotaemon.llms import AzureOpenAI, LlamaCpp, OpenAI

try:
    from langchain_openai import AzureOpenAI as AzureOpenAILC
    from langchain_openai import OpenAI as OpenAILC
except ImportError:
    from langchain.llms import AzureOpenAI as AzureOpenAILC
    from langchain.llms import OpenAI as OpenAILC

from openai.types.completion import Completion

from .conftest import skip_llama_cpp_not_installed, skip_openai_lc_wrapper_test

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


@skip_openai_lc_wrapper_test
@patch(
    "openai.resources.completions.Completions.create",
    side_effect=lambda *args, **kwargs: _openai_completion_response,
)
def test_azureopenai_model(openai_completion):
    model = AzureOpenAI(
        azure_endpoint="https://test.openai.azure.com/",
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


@skip_llama_cpp_not_installed
def test_llamacpp_model():
    weight_path = Path(__file__).parent / "resources" / "ggml-vocab-llama.gguf"

    # test initialization
    model = LlamaCpp(model_path=str(weight_path), vocab_only=True)
    assert isinstance(model._obj, model._get_lc_class())
