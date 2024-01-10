# flake8: noqa
from unittest.mock import patch

import pytest
from openai.types.chat.chat_completion import ChatCompletion

from kotaemon.indices.qa import CitationPipeline
from kotaemon.llms import AzureChatOpenAI

function_output = '{\n  "question": "What is the provided _example_ benefits?",\n  "answer": [\n    {\n      "fact": "特約死亡保険金: 被保険者がこの特約の保険期間中に死亡したときに支払います。",\n      "substring_quote": ["特約死亡保険金"]\n    },\n    {\n      "fact": "特約特定疾病保険金: 被保険者がこの特約の保険期間中に特定の疾病（悪性新生物（がん）、急性心筋梗塞または脳卒中）により所定の状態に該当したときに支払います。",\n      "substring_quote": ["特約特定疾病保険金"]\n    },\n    {\n      "fact": "特約障害保険金: 被保険者がこの特約の保険期間中に傷害もしくは疾病により所定の身体障害の状態に該当したとき、または不慮の事故により所定の身体障害の状態に該当したときに支払います。",\n      "substring_quote": ["特約障害保険金"]\n    },\n    {\n      "fact": "特約介護保険金: 被保険者がこの特約の保険期間中に傷害または疾病により所定の要介護状態に該当したときに支払います。",\n      "substring_quote": ["特約介護保険金"]\n    }\n  ]\n}'

_openai_chat_completion_response = [
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
                    "finish_reason": "function_call",
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "function_call": {
                            "arguments": function_output,
                            "name": "QuestionAnswer",
                        },
                        "tool_calls": None,
                    },
                    "logprobs": None,
                }
            ],
            "usage": {"completion_tokens": 9, "prompt_tokens": 10, "total_tokens": 19},
        }
    )
]


@pytest.fixture
def llm():
    return AzureChatOpenAI(
        azure_endpoint="https://dummy.openai.azure.com/",
        openai_api_key="dummy",
        openai_api_version="2023-03-15-preview",
        temperature=0,
    )


@patch(
    "openai.resources.chat.completions.Completions.create",
    side_effect=_openai_chat_completion_response,
)
def test_citation(openai_completion, llm):
    question = "test query"
    context = "document context"

    citation = CitationPipeline(llm=llm)
    result = citation(context, question)
    assert len(result.answer) == 4
