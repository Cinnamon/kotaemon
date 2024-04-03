import requests

from kotaemon.base import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    LLMInterface,
    Param,
    SystemMessage,
)

from .base import ChatLLM


class EndpointChatLLM(ChatLLM):
    """
    A ChatLLM that uses an endpoint to generate responses. This expects an OpenAI API
    compatible endpoint.

    Attributes:
        endpoint_url (str): The url of a OpenAI API compatible endpoint.
    """

    endpoint_url: str = Param(
        help="URL of the OpenAI API compatible endpoint", required=True
    )

    def run(
        self, messages: str | BaseMessage | list[BaseMessage], **kwargs
    ) -> LLMInterface:
        """
        Generate response from messages
        Args:
            messages (str | BaseMessage | list[BaseMessage]): history of messages to
                generate response from
            **kwargs: additional arguments to pass to the OpenAI API
        Returns:
            LLMInterface: generated response
        """
        if isinstance(messages, str):
            input_ = [HumanMessage(content=messages)]
        elif isinstance(messages, BaseMessage):
            input_ = [messages]
        else:
            input_ = messages

        def decide_role(message: BaseMessage):
            if isinstance(message, SystemMessage):
                return "system"
            elif isinstance(message, AIMessage):
                return "assistant"
            else:
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
        """Same as run"""
        return self.run(messages, **kwargs)

    async def ainvoke(
        self, messages: str | BaseMessage | list[BaseMessage], **kwargs
    ) -> LLMInterface:
        return self.invoke(messages, **kwargs)
