from unittest.mock import patch

import pytest
from openai.types.chat.chat_completion import ChatCompletion

from kotaemon.base import Document, LLMInterface
from kotaemon.indices.rankings import LLMReranking, LLMTrulensScoring
from kotaemon.llms import AzureChatOpenAI, BaseLLM

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


class _StubLLM(BaseLLM):
    def __init__(self, responses):
        super().__init__()
        self._responses = iter(responses)

    def invoke(self, messages, *args, **kwargs):
        return LLMInterface(content=next(self._responses))

    def run(self, messages, *args, **kwargs):
        return self.invoke(messages, *args, **kwargs)


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


def test_trulens_scoring_returns_all_documents_in_score_order():
    documents = [Document(text=f"test {idx}") for idx in range(3)]
    reranker = LLMTrulensScoring(
        llm=_StubLLM(["0", "5", "10"]),
        concurrent=False,
    )

    result = reranker(documents, query="test query")

    assert len(result) == len(documents)
    assert [doc.metadata["llm_trulens_score"] for doc in result] == [1.0, 0.5, 0.0]
    assert [doc.text for doc in result] == ["test 2", "test 1", "test 0"]
