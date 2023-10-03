from unittest.mock import patch

from kotaemon.llms.chats.openai import AzureChatOpenAI
from kotaemon.pipelines.cot import ManualSequentialChainOfThought, Thought

_openai_chat_completion_response = [
    {
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
                    "content": text,
                },
            }
        ],
        "usage": {"completion_tokens": 9, "prompt_tokens": 10, "total_tokens": 19},
    }
    for text in ["Bonjour", "こんにちは (Konnichiwa)"]
]


@patch(
    "openai.api_resources.chat_completion.ChatCompletion.create",
    side_effect=_openai_chat_completion_response,
)
def test_cot_plus_operator(openai_completion):
    llm = AzureChatOpenAI(
        openai_api_base="https://dummy.openai.azure.com/",
        openai_api_key="dummy",
        openai_api_version="2023-03-15-preview",
        deployment_name="dummy-q2",
        temperature=0,
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
    assert output == {
        "word": "hello",
        "language": "French",
        "translated": "Bonjour",
        "output": "こんにちは (Konnichiwa)",
    }


@patch(
    "openai.api_resources.chat_completion.ChatCompletion.create",
    side_effect=_openai_chat_completion_response,
)
def test_cot_manual(openai_completion):
    llm = AzureChatOpenAI(
        openai_api_base="https://dummy.openai.azure.com/",
        openai_api_key="dummy",
        openai_api_version="2023-03-15-preview",
        deployment_name="dummy-q2",
        temperature=0,
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
    assert output == {
        "word": "hello",
        "language": "French",
        "translated": "Bonjour",
        "output": "こんにちは (Konnichiwa)",
    }


@patch(
    "openai.api_resources.chat_completion.ChatCompletion.create",
    side_effect=_openai_chat_completion_response,
)
def test_cot_with_termination_callback(openai_completion):
    llm = AzureChatOpenAI(
        openai_api_base="https://dummy.openai.azure.com/",
        openai_api_key="dummy",
        openai_api_version="2023-03-15-preview",
        deployment_name="dummy-q2",
        temperature=0,
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
    assert output == {
        "word": "hallo",
        "language": "French",
        "translated": "Bonjour",
    }
