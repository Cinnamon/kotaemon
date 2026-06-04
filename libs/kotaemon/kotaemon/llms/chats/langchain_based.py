from __future__ import annotations

import logging
from dataclasses import dataclass, field
from functools import cached_property
from typing import Any, AsyncGenerator, Iterator

from kotaemon.base import BaseMessage, HumanMessage, LLMInterface

from .base import ChatLLM

logger = logging.getLogger(__name__)


def lc_prepare_message(
    messages: str | BaseMessage | list[BaseMessage],
) -> list[BaseMessage]:
    if isinstance(messages, str):
        return [HumanMessage(content=messages)]
    if isinstance(messages, BaseMessage):
        return [messages]
    return messages


def lc_prepare_response(pred: Any) -> LLMInterface:
    all_text = [each.text for each in pred.generations[0]]
    all_messages = [each.message for each in pred.generations[0]]

    completion_tokens, total_tokens, prompt_tokens = 0, 0, 0
    try:
        if pred.llm_output is not None:
            completion_tokens = pred.llm_output["token_usage"]["completion_tokens"]
            total_tokens = pred.llm_output["token_usage"]["total_tokens"]
            prompt_tokens = pred.llm_output["token_usage"]["prompt_tokens"]
    except Exception:
        pass

    return LLMInterface(
        text=all_text[0] if len(all_text) > 0 else "",
        candidates=all_text,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        prompt_tokens=prompt_tokens,
        messages=all_messages,
        logits=[],
    )


@dataclass(kw_only=True)
class BaseLCChat(ChatLLM):
    """Base wrapper for LangChain chat models."""

    streaming: bool = field(
        default=False,
        metadata={"description": "Return a streaming iterator from run()."},
    )

    def _get_lc_class(self) -> type:
        raise NotImplementedError(
            "Subclasses must implement _get_lc_class with the LangChain class."
        )

    def _lc_kwargs(self) -> dict[str, Any]:
        raise NotImplementedError(
            "Subclasses must implement _lc_kwargs mapping fields to LangChain."
        )

    def _get_tool_call_kwargs(self) -> dict[str, Any]:
        return {}

    @cached_property
    def _lc_obj(self) -> Any:
        return self._get_lc_class()(**self._lc_kwargs())

    def to_langchain_format(self) -> Any:
        return self._lc_obj

    def run(
        self, messages: str | BaseMessage | list[BaseMessage], **kwargs
    ) -> LLMInterface:
        if self.streaming:
            return self.stream(messages, **kwargs)  # type: ignore[return-value]
        return self.invoke(messages, **kwargs)

    def invoke(
        self, messages: str | BaseMessage | list[BaseMessage], **kwargs
    ) -> LLMInterface:
        input_ = lc_prepare_message(messages)

        if "tools_pydantic" in kwargs:
            tools = kwargs.pop("tools_pydantic")
            lc_tool_call = self._lc_obj.bind_tools(tools)
            pred = lc_tool_call.invoke(
                input_,
                **self._get_tool_call_kwargs(),
            )
            if pred.tool_calls:
                tool_calls = pred.tool_calls
            else:
                tool_calls = pred.additional_kwargs.get("tool_calls", [])

            return LLMInterface(
                content="",
                additional_kwargs={"tool_calls": tool_calls},
            )

        pred = self._lc_obj.generate(messages=[input_], **kwargs)
        return lc_prepare_response(pred)

    async def ainvoke(
        self, messages: str | BaseMessage | list[BaseMessage], **kwargs
    ) -> LLMInterface:
        input_ = lc_prepare_message(messages)
        pred = await self._lc_obj.agenerate(messages=[input_], **kwargs)
        return lc_prepare_response(pred)

    def stream(
        self, messages: str | BaseMessage | list[BaseMessage], **kwargs
    ) -> Iterator[LLMInterface]:
        for response in self._lc_obj.stream(input=messages, **kwargs):
            yield LLMInterface(content=response.content)

    async def astream(
        self, messages: str | BaseMessage | list[BaseMessage], **kwargs
    ) -> AsyncGenerator[LLMInterface, None]:
        async for response in self._lc_obj.astream(input=messages, **kwargs):
            yield LLMInterface(content=response.content)


@dataclass(kw_only=True)
class LCChatOpenAI(BaseLCChat):
    """Wrapper around LangChain's OpenAI chat model."""

    openai_api_base: str | None = field(
        default=None, metadata={"description": "OpenAI API base URL."}
    )
    openai_api_key: str | None = field(
        default=None, metadata={"description": "OpenAI API key."}
    )
    model: str | None = field(default=None, metadata={"description": "Model name."})
    temperature: float = field(
        default=0.7,
        metadata={"description": "Sampling temperature."},
    )
    request_timeout: float | None = field(
        default=None, metadata={"description": "Request timeout in seconds."}
    )

    def _get_lc_class(self) -> type:
        try:
            from langchain_openai import ChatOpenAI
        except ImportError:
            from langchain.chat_models import ChatOpenAI

        return ChatOpenAI

    def _lc_kwargs(self) -> dict[str, Any]:
        return {
            "openai_api_base": self.openai_api_base,
            "openai_api_key": self.openai_api_key,
            "model": self.model,
            "temperature": self.temperature,
            "request_timeout": self.request_timeout,
        }


@dataclass(kw_only=True)
class LCAzureChatOpenAI(BaseLCChat):
    """Wrapper around LangChain's Azure OpenAI chat model."""

    azure_endpoint: str | None = field(
        default=None, metadata={"description": "Azure OpenAI endpoint URL."}
    )
    openai_api_key: str | None = field(
        default=None, metadata={"description": "Azure OpenAI API key."}
    )
    openai_api_version: str = field(
        default="",
        metadata={"description": "Azure OpenAI API version."},
    )
    deployment_name: str | None = field(
        default=None, metadata={"description": "Azure deployment name."}
    )
    temperature: float = field(
        default=0.7,
        metadata={"description": "Sampling temperature."},
    )
    request_timeout: float | None = field(
        default=None, metadata={"description": "Request timeout in seconds."}
    )

    def _get_lc_class(self) -> type:
        try:
            from langchain_openai import AzureChatOpenAI
        except ImportError:
            from langchain.chat_models import AzureChatOpenAI

        return AzureChatOpenAI

    def _lc_kwargs(self) -> dict[str, Any]:
        return {
            "azure_endpoint": self.azure_endpoint,
            "openai_api_key": self.openai_api_key,
            "openai_api_version": self.openai_api_version,
            "deployment_name": self.deployment_name,
            "temperature": self.temperature,
            "request_timeout": self.request_timeout,
        }


@dataclass(kw_only=True)
class LCAnthropicChat(BaseLCChat):
    """Wrapper around LangChain's Anthropic chat model."""

    api_key: str | None = field(
        default=None, metadata={"description": "Anthropic API key."}
    )
    model_name: str | None = field(
        default=None, metadata={"description": "Model name."}
    )
    temperature: float = field(
        default=0.7,
        metadata={"description": "Sampling temperature."},
    )

    def _get_tool_call_kwargs(self) -> dict[str, Any]:
        return {"tool_choice": {"type": "any"}}

    def _get_lc_class(self) -> type:
        try:
            from langchain_anthropic import ChatAnthropic
        except ImportError as e:
            raise ImportError("Please install langchain-anthropic") from e

        return ChatAnthropic

    def _lc_kwargs(self) -> dict[str, Any]:
        return {
            "api_key": self.api_key,
            "model_name": self.model_name,
            "temperature": self.temperature,
        }


@dataclass(kw_only=True)
class LCGeminiChat(BaseLCChat):
    """Wrapper around LangChain's Google Generative AI chat model."""

    api_key: str | None = field(
        default=None, metadata={"description": "Google API key."}
    )
    model_name: str | None = field(
        default=None, metadata={"description": "Model name."}
    )
    temperature: float = field(
        default=0.7,
        metadata={"description": "Sampling temperature."},
    )

    def _get_tool_call_kwargs(self) -> dict[str, Any]:
        return {
            "tool_config": {
                "function_calling_config": {
                    "mode": "ANY",
                }
            }
        }

    def _get_lc_class(self) -> type:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
        except ImportError as e:
            raise ImportError("Please install langchain-google-genai") from e

        return ChatGoogleGenerativeAI

    def _lc_kwargs(self) -> dict[str, Any]:
        return {
            "google_api_key": self.api_key,
            "model": self.model_name,
            "temperature": self.temperature,
        }


@dataclass(kw_only=True)
class LCCohereChat(BaseLCChat):
    """Wrapper around LangChain's Cohere chat model."""

    api_key: str | None = field(
        default=None, metadata={"description": "Cohere API key."}
    )
    model_name: str | None = field(
        default=None, metadata={"description": "Model name."}
    )
    temperature: float = field(
        default=0.7,
        metadata={"description": "Sampling temperature."},
    )

    def _get_lc_class(self) -> type:
        try:
            from langchain_cohere import ChatCohere
        except ImportError as e:
            raise ImportError("Please install langchain-cohere") from e

        return ChatCohere

    def _lc_kwargs(self) -> dict[str, Any]:
        return {
            "cohere_api_key": self.api_key,
            "model_name": self.model_name,
            "temperature": self.temperature,
        }


@dataclass(kw_only=True)
class LCOllamaChat(BaseLCChat):
    """Wrapper around LangChain's Ollama chat model."""

    model: str | None = field(
        default=None, metadata={"description": "Ollama model name."}
    )
    base_url: str | None = field(
        default=None, metadata={"description": "Ollama server base URL."}
    )
    num_ctx: int | None = field(
        default=None, metadata={"description": "Context window size."}
    )

    def _get_lc_class(self) -> type:
        try:
            from langchain_ollama import ChatOllama
        except ImportError as e:
            raise ImportError("Please install langchain-ollama") from e

        return ChatOllama

    def _lc_kwargs(self) -> dict[str, Any]:
        return {
            "base_url": self.base_url,
            "model": self.model,
            "num_ctx": self.num_ctx,
        }


# Backward-compatible alias for code that imported the old mixin name.
LCChatMixin = BaseLCChat
