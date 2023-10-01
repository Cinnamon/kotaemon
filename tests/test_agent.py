from unittest.mock import patch

from kotaemon.llms.chats.openai import AzureChatOpenAI
from kotaemon.pipelines.agents.rewoo import RewooAgent
from kotaemon.pipelines.tools import GoogleSearchTool, WikipediaTool

FINAL_RESPONSE_TEXT = "Hello Cinnamon AI!"
_openai_chat_completion_responses = [
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
                    "content": "#Plan1: Search for Cinnamon AI company on Google\n"
                    "#E1: google_search[Cinnamon AI company]\n"
                    "#Plan2: Search for Cinnamon on Wikipedia\n"
                    "#E2: wikipedia[Cinnamon]",
                },
            }
        ],
        "usage": {"completion_tokens": 9, "prompt_tokens": 10, "total_tokens": 19},
    },
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
                    "content": FINAL_RESPONSE_TEXT,
                },
            }
        ],
        "usage": {"completion_tokens": 9, "prompt_tokens": 10, "total_tokens": 19},
    },
]


@patch(
    "openai.api_resources.chat_completion.ChatCompletion.create",
    side_effect=_openai_chat_completion_responses,
)
def test_rewoo_agent(openai_completion):
    llm = AzureChatOpenAI(
        openai_api_base="https://dummy.openai.azure.com/",
        openai_api_key="dummy",
        openai_api_version="2023-03-15-preview",
        deployment_name="dummy-q2",
        temperature=0,
    )

    plugins = [GoogleSearchTool(), WikipediaTool()]

    agent = RewooAgent(llm=llm, plugins=plugins)

    response = agent("Tell me about Cinnamon AI company")
    openai_completion.assert_called()
    assert response.output == FINAL_RESPONSE_TEXT
