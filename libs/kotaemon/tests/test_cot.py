from unittest.mock import patch

from openai.types.chat.chat_completion import ChatCompletion

from kotaemon.llms import AzureChatOpenAI
from kotaemon.llms.cot import ManualSequentialChainOfThought, Thought

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
    for text in ["Bonjour", "こんにちは (Konnichiwa)"]
]


@patch(
    "openai.resources.chat.completions.Completions.create",
    side_effect=_openai_chat_completion_response,
)
def test_cot_plus_operator(openai_completion):
    llm = AzureChatOpenAI(
        api_key="dummy",
        api_version="2024-05-01-preview",
        azure_deployment="gpt-4o",
        azure_endpoint="https://test.openai.azure.com/",
    )
    thought1 = Thought(
        prompt="Word {word} in {language} is ",
        llm=llm,
        post_process=lambda string: {"translated": string},
    )
    thought2 = Thought(
        prompt="Translate {translated} to Japanese",
        llm=llm,
        post_process=lambda string: {"output": string},
    )
    thought = thought1 + thought2
    output = thought(word="hello", language="French")
    assert output.content == {
        "word": "hello",
        "language": "French",
        "translated": "Bonjour",
        "output": "こんにちは (Konnichiwa)",
    }


@patch(
    "openai.resources.chat.completions.Completions.create",
    side_effect=_openai_chat_completion_response,
)
def test_cot_manual(openai_completion):
    llm = AzureChatOpenAI(
        api_key="dummy",
        api_version="2024-05-01-preview",
        azure_deployment="gpt-4o",
        azure_endpoint="https://test.openai.azure.com/",
    )
    thought1 = Thought(
        prompt="Word {word} in {language} is ",
        post_process=lambda string: {"translated": string},
    )
    thought2 = Thought(
        prompt="Translate {translated} to Japanese",
        post_process=lambda string: {"output": string},
    )
    thought = ManualSequentialChainOfThought(thoughts=[thought1, thought2], llm=llm)
    output = thought(word="hello", language="French")
    assert output.content == {
        "word": "hello",
        "language": "French",
        "translated": "Bonjour",
        "output": "こんにちは (Konnichiwa)",
    }


@patch(
    "openai.resources.chat.completions.Completions.create",
    side_effect=_openai_chat_completion_response,
)
def test_cot_with_termination_callback(openai_completion):
    llm = AzureChatOpenAI(
        api_key="dummy",
        api_version="2024-05-01-preview",
        azure_deployment="gpt-4o",
        azure_endpoint="https://test.openai.azure.com/",
    )
    thought1 = Thought(
        prompt="Word {word} in {language} is ",
        post_process=lambda string: {"translated": string},
    )
    thought2 = Thought(
        prompt="Translate {translated} to Japanese",
        post_process=lambda string: {"output": string},
    )
    thought = ManualSequentialChainOfThought(
        thoughts=[thought1, thought2],
        llm=llm,
        terminate=lambda d: True if d.get("translated", "") == "Bonjour" else False,
    )
    output = thought(word="hallo", language="French")
    assert output.content == {
        "word": "hallo",
        "language": "French",
        "translated": "Bonjour",
    }
