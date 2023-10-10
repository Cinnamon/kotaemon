import pytest

from kotaemon.composite import (
    GatedBranchingPipeline,
    GatedLinearPipeline,
    SimpleBranchingPipeline,
    SimpleLinearPipeline,
)
from kotaemon.llms.chats.openai import AzureChatOpenAI
from kotaemon.post_processing.extractor import RegexExtractor
from kotaemon.prompt.base import BasePromptComponent


@pytest.fixture
def mock_llm():
    return AzureChatOpenAI(
        openai_api_base="OPENAI_API_BASE",
        openai_api_key="OPENAI_API_KEY",
        openai_api_version="OPENAI_API_VERSION",
        deployment_name="dummy-q2-gpt35",
        temperature=0,
        request_timeout=600,
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
    openai_mocker = mocker.patch.object(
        AzureChatOpenAI, "run", return_value="This is a test 123"
    )

    result = mock_simple_linear_pipeline.run(value="abc")

    assert result.text == "123"
    assert openai_mocker.call_count == 1


def test_gated_linear_pipeline_run_positive(
    mocker, mock_gated_linear_pipeline_positive
):
    openai_mocker = mocker.patch.object(
        AzureChatOpenAI, "run", return_value="This is a test 123."
    )

    result = mock_gated_linear_pipeline_positive.run(
        value="abc", condition_text="positive condition"
    )

    assert result.text == "123"
    assert openai_mocker.call_count == 1


def test_gated_linear_pipeline_run_negative(
    mocker, mock_gated_linear_pipeline_positive
):
    openai_mocker = mocker.patch.object(
        AzureChatOpenAI, "run", return_value="This is a test 123."
    )

    result = mock_gated_linear_pipeline_positive.run(
        value="abc", condition_text="negative condition"
    )

    assert result.content is None
    assert openai_mocker.call_count == 0


def test_simple_branching_pipeline_run(mocker, mock_simple_linear_pipeline):
    openai_mocker = mocker.patch.object(
        AzureChatOpenAI,
        "run",
        side_effect=[
            "This is a test 123.",
            "a quick brown fox",
            "jumps over the lazy dog 456",
        ],
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
    openai_mocker = mocker.patch.object(
        AzureChatOpenAI, "run", return_value="a quick brown fox"
    )
    pipeline = GatedBranchingPipeline()

    pipeline.add_branch(mock_gated_linear_pipeline_negative)
    pipeline.add_branch(mock_gated_linear_pipeline_positive)
    pipeline.add_branch(mock_gated_linear_pipeline_positive)

    result = pipeline.run(value="abc", condition_text="positive condition")

    assert result.text == ""
    assert openai_mocker.call_count == 2
