from dataclasses import dataclass, field

import requests

from kotaemon.base import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    LLMInterface,
    SystemMessage,
)

from .base import ChatLLM


@dataclass(kw_only=True)
class EndpointChatLLM(ChatLLM):
    """ChatLLM that uses an OpenAI API compatible HTTP endpoint."""

    endpoint_url: str = field(
        metadata={"description": "OpenAI API compatible endpoint URL"},
    )

    def run(
        self, messages: str | BaseMessage | list[BaseMessage], **kwargs
    ) -> LLMInterface:
        if isinstance(messages, str):
            input_ = [HumanMessage(content=messages)]
        elif isinstance(messages, BaseMessage):
            input_ = [messages]
        else:
            input_ = messages

        def decide_role(message: BaseMessage):
            if isinstance(message, SystemMessage):
                return "system"
            if isinstance(message, AIMessage):
                return "assistant"
            return "user"

        request_json = {
            "messages": [{"content": m.text, "role": decide_role(m)} for m in input_]
        }

        response = requests.post(self.endpoint_url, json=request_json).json()

        content = ""
        candidates = []
        if response["choices"]:
            candidates = [
                each["message"]["content"]
                for each in response["choices"]
                if each["message"]["content"]
            ]
            content = candidates[0]

        return LLMInterface(
            content=content,
            candidates=candidates,
            completion_tokens=response["usage"]["completion_tokens"],
            total_tokens=response["usage"]["total_tokens"],
            prompt_tokens=response["usage"]["prompt_tokens"],
        )

    def invoke(
        self, messages: str | BaseMessage | list[BaseMessage], **kwargs
    ) -> LLMInterface:
        return self.run(messages, **kwargs)

    async def ainvoke(
        self, messages: str | BaseMessage | list[BaseMessage], **kwargs
    ) -> LLMInterface:
        return self.invoke(messages, **kwargs)
