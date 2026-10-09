from unittest.mock import patch

import pytest
from openai.types.chat.chat_completion import ChatCompletion

from kotaemon.base import Document
from kotaemon.indices.rankings import LLMReranking
from kotaemon.llms import AzureChatOpenAI

_openai_chat_completion_responses = [
    ChatCompletion.parse_obj(
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
                        "content": text,
                        "function_call": None,
                        "tool_calls": None,
                    },
                    "logprobs": None,
                }
            ],
            "usage": {"completion_tokens": 9, "prompt_tokens": 10, "total_tokens": 19},
        }
    )
    for text in [
        "YES",
        "NO",
        "YES",
    ]
]


@pytest.fixture
def llm():
    return AzureChatOpenAI(
        api_key="dummy",
        api_version="2024-05-01-preview",
        azure_deployment="gpt-4o",
        azure_endpoint="https://test.openai.azure.com/",
    )


@patch(
    "openai.resources.chat.completions.Completions.create",
    side_effect=_openai_chat_completion_responses,
)
def test_reranking(openai_completion, llm):
    documents = [Document(text=f"test {idx}") for idx in range(3)]
    query = "test query"

    reranker = LLMReranking(llm=llm, concurrent=False)
    rerank_docs = reranker(documents, query=query)

    assert len(rerank_docs) == 2


@pytest.mark.parametrize(
    "reply, expected",
    [
        ("8", 8),
        ("8 out of 10", 8),
        ("7.5", 7.5),
        ("0.8", 0.8),
        ("9.5/10", 9.5),
        ("The rating is 10.", 10),
        ("15 or maybe 6", 6),
        (".5", 0.5),
        ("Out of 10, I'd say 8", 8),
        ("10 being most relevant, I give 3", 3),
    ],
)
def test_re_0_10_rating(reply, expected):
    from kotaemon.indices.rankings.llm_trulens import re_0_10_rating

    assert re_0_10_rating(reply) == expected


@pytest.mark.parametrize("reply", ["I cannot rate this", "", "42", "-3"])
def test_re_0_10_rating_unparsable(reply):
    from kotaemon.indices.rankings.llm_trulens import re_0_10_rating

    with pytest.raises(ValueError):
        re_0_10_rating(reply)


def test_trulens_scoring_unparsable_reply_scores_zero():
    from kotaemon.indices.rankings import LLMTrulensScoring

    replies = {"a": "I cannot rate this", "b": "7.5"}

    class FakeLLM:
        def __call__(self, messages):
            context = messages[-1].content
            return Document(text=replies["a" if "doc a" in context else "b"])

    scorer = LLMTrulensScoring(llm=FakeLLM(), concurrent=False)
    docs = scorer([Document(content="doc a"), Document(content="doc b")], "query")

    assert [d.text for d in docs] == ["doc b", "doc a"]
    assert [d.metadata["llm_trulens_score"] for d in docs] == [0.75, 0.0]
