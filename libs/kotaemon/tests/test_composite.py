from copy import deepcopy

import pytest
from openai.types.chat.chat_completion import ChatCompletion

from kotaemon.llms import (
    AzureChatOpenAI,
    BasePromptComponent,
    GatedBranchingPipeline,
    GatedLinearPipeline,
    SimpleBranchingPipeline,
    SimpleLinearPipeline,
)
from kotaemon.parsers import RegexExtractor

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
                    "content": "This is a test 123",
                    "finish_reason": "length",
                    "logprobs": None,
                },
                "logprobs": None,
            }
        ],
        "usage": {"completion_tokens": 9, "prompt_tokens": 10, "total_tokens": 19},
    }
)


@pytest.fixture
def mock_llm():
    return AzureChatOpenAI(
        api_key="dummy",
        api_version="2024-05-01-preview",
        azure_deployment="gpt-4o",
        azure_endpoint="https://test.openai.azure.com/",
    )


@pytest.fixture
def mock_post_processor():
    return RegexExtractor(pattern=r"\d+")


@pytest.fixture
def mock_prompt():
    return BasePromptComponent(template="Test prompt {value}")


@pytest.fixture
def mock_simple_linear_pipeline(mock_prompt, mock_llm, mock_post_processor):
    return SimpleLinearPipeline(
        prompt=mock_prompt, llm=mock_llm, post_processor=mock_post_processor
    )


@pytest.fixture
def mock_gated_linear_pipeline_positive(mock_prompt, mock_llm, mock_post_processor):
    return GatedLinearPipeline(
        prompt=mock_prompt,
        llm=mock_llm,
        post_processor=mock_post_processor,
        condition=RegexExtractor(pattern="positive"),
    )


@pytest.fixture
def mock_gated_linear_pipeline_negative(mock_prompt, mock_llm, mock_post_processor):
    return GatedLinearPipeline(
        prompt=mock_prompt,
        llm=mock_llm,
        post_processor=mock_post_processor,
        condition=RegexExtractor(pattern="negative"),
    )


def test_simple_linear_pipeline_run(mocker, mock_simple_linear_pipeline):
    openai_mocker = mocker.patch(
        "openai.resources.chat.completions.Completions.create",
        return_value=_openai_chat_completion_response,
    )

    result = mock_simple_linear_pipeline(value="abc")

    assert result.text == "123"
    assert openai_mocker.call_count == 1


def test_gated_linear_pipeline_run_positive(
    mocker, mock_gated_linear_pipeline_positive
):
    openai_mocker = mocker.patch(
        "openai.resources.chat.completions.Completions.create",
        return_value=_openai_chat_completion_response,
    )

    result = mock_gated_linear_pipeline_positive(
        value="abc", condition_text="positive condition"
    )

    assert result.text == "123"
    assert openai_mocker.call_count == 1


def test_gated_linear_pipeline_run_negative(
    mocker, mock_gated_linear_pipeline_positive
):
    openai_mocker = mocker.patch(
        "openai.resources.chat.completions.Completions.create",
        return_value=_openai_chat_completion_response,
    )

    result = mock_gated_linear_pipeline_positive(
        value="abc", condition_text="negative condition"
    )

    assert result.content is None
    assert openai_mocker.call_count == 0


def test_simple_branching_pipeline_run(mocker, mock_simple_linear_pipeline):
    response0: ChatCompletion = _openai_chat_completion_response
    response1: ChatCompletion = deepcopy(_openai_chat_completion_response)
    response1.choices[0].message.content = "a quick brown fox"
    response2: ChatCompletion = deepcopy(_openai_chat_completion_response)
    response2.choices[0].message.content = "jumps over the lazy dog 456"
    openai_mocker = mocker.patch(
        "openai.resources.chat.completions.Completions.create",
        side_effect=[response0, response1, response2],
    )
    pipeline = SimpleBranchingPipeline()
    for _ in range(3):
        pipeline.add_branch(mock_simple_linear_pipeline)

    result = pipeline.run(value="abc")
    texts = [each.text for each in result]

    assert len(result) == 3
    assert texts == ["123", "", "456"]
    assert openai_mocker.call_count == 3


def test_simple_gated_branching_pipeline_run(
    mocker, mock_gated_linear_pipeline_positive, mock_gated_linear_pipeline_negative
):
    response0: ChatCompletion = deepcopy(_openai_chat_completion_response)
    response0.choices[0].message.content = "a quick brown fox"
    openai_mocker = mocker.patch(
        "openai.resources.chat.completions.Completions.create",
        return_value=response0,
    )
    pipeline = GatedBranchingPipeline()

    pipeline.add_branch(mock_gated_linear_pipeline_negative)
    pipeline.add_branch(mock_gated_linear_pipeline_positive)
    pipeline.add_branch(mock_gated_linear_pipeline_positive)

    result = pipeline.run(value="abc", condition_text="positive condition")

    assert result.text == ""
    assert openai_mocker.call_count == 2
