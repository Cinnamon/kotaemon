from unittest.mock import patch

import pytest
from openai.types.chat.chat_completion import ChatCompletion

from kotaemon.base import Document, LLMInterface
from kotaemon.indices.rankings import LLMReranking, LLMScoring, LLMTrulensScoring
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


class _DeferredExecutor:
    """Runs tasks only once the first result is requested, i.e. after submitting."""

    def __init__(self):
        self._tasks = []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def submit(self, fn, *args, **kwargs):
        executor = self

        class _Future:
            value: object = None

            def result(self):
                while executor._tasks:
                    task = executor._tasks.pop(0)
                    task[0].value = task[1](*task[2])
                return self.value

        future = _Future()
        self._tasks.append((future, fn, args))
        return future


@pytest.mark.parametrize(
    "cls, module",
    [
        (LLMReranking, "kotaemon.indices.rankings.llm"),
        (LLMScoring, "kotaemon.indices.rankings.llm_scoring"),
        (LLMTrulensScoring, "kotaemon.indices.rankings.llm_trulens"),
    ],
)
def test_concurrent_reranking_binds_prompt_per_document(cls, module):
    """Each task must see its own document's prompt, not the last one."""
    seen = []

    class FakeLLM:
        def __call__(self, prompt):
            seen.append(str(prompt))
            return LLMInterface(content="YES 7", logprobs=[-0.1])

    documents = [Document(text=f"doc-{idx}") for idx in range(3)]
    reranker = cls(llm=FakeLLM(), concurrent=True)

    with patch(f"{module}.ThreadPoolExecutor", _DeferredExecutor):
        reranker(documents, query="q")

    # trulens sorts documents by content; doc-0..2 are already in sorted order
    assert len(seen) == 3
    assert all(f"doc-{i}" in p for i, p in enumerate(seen))
