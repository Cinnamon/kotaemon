from unittest.mock import patch

from kotaemon.llms.chats.openai import AzureChatOpenAI
from kotaemon.pipelines.agents.react import ReactAgent
from kotaemon.pipelines.agents.rewoo import RewooAgent
from kotaemon.pipelines.tools import GoogleSearchTool, LLMTool, WikipediaTool

FINAL_RESPONSE_TEXT = "Hello Cinnamon AI!"
_openai_chat_completion_responses_rewoo = [
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
    for text in [
        (
            "#Plan1: Search for Cinnamon AI company on Google\n"
            "#E1: google_search[Cinnamon AI company]\n"
            "#Plan2: Search for Cinnamon on Wikipedia\n"
            "#E2: wikipedia[Cinnamon]\n"
        ),
        FINAL_RESPONSE_TEXT,
    ]
]

_openai_chat_completion_responses_react = [
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
    for text in [
        (
            "I don't have prior knowledge about Cinnamon AI company, "
            "so I should gather information about it.\n"
            "Action: wikipedia\n"
            "Action Input: Cinnamon AI company\n"
        ),
        (
            "The information retrieved from Wikipedia is not "
            "about Cinnamon AI company, but about Blue Prism, "
            "a British multinational software corporation. "
            "I need to try another source to gather information "
            "about Cinnamon AI company.\n"
            "Action: google_search\n"
            "Action Input: Cinnamon AI company\n"
        ),
        FINAL_RESPONSE_TEXT,
    ]
]


@patch(
    "openai.api_resources.chat_completion.ChatCompletion.create",
    side_effect=_openai_chat_completion_responses_rewoo,
)
def test_rewoo_agent(openai_completion):
    llm = AzureChatOpenAI(
        openai_api_base="https://dummy.openai.azure.com/",
        openai_api_key="dummy",
        openai_api_version="2023-03-15-preview",
        deployment_name="dummy-q2",
        temperature=0,
    )
    plugins = [
        GoogleSearchTool(),
        WikipediaTool(),
        LLMTool(llm=llm),
    ]

    agent = RewooAgent(llm=llm, plugins=plugins)

    response = agent("Tell me about Cinnamon AI company")
    openai_completion.assert_called()
    assert response.output == FINAL_RESPONSE_TEXT


@patch(
    "openai.api_resources.chat_completion.ChatCompletion.create",
    side_effect=_openai_chat_completion_responses_react,
)
def test_react_agent(openai_completion):
    llm = AzureChatOpenAI(
        openai_api_base="https://dummy.openai.azure.com/",
        openai_api_key="dummy",
        openai_api_version="2023-03-15-preview",
        deployment_name="dummy-q2",
        temperature=0,
    )
    plugins = [
        GoogleSearchTool(),
        WikipediaTool(),
        LLMTool(llm=llm),
    ]
    agent = ReactAgent(llm=llm, plugins=plugins, max_iterations=4)

    response = agent("Tell me about Cinnamon AI company")
    openai_completion.assert_called()
    assert response.output == FINAL_RESPONSE_TEXT
