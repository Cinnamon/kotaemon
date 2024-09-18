from __future__ import annotations

import logging
from typing import AsyncGenerator, Iterator

from kotaemon.base import BaseMessage, HumanMessage, LLMInterface, Param

from .base import ChatLLM

logger = logging.getLogger(__name__)


class LCChatMixin:
    """Mixin for langchain based chat models"""

    def _get_lc_class(self):
        raise NotImplementedError(
            "Please return the relevant Langchain class in in _get_lc_class"
        )

    def __init__(self, stream: bool = False, **params):
        self._lc_class = self._get_lc_class()
        self._obj = self._lc_class(**params)
        self._kwargs: dict = params
        self._stream = stream

        super().__init__()

    def run(
        self, messages: str | BaseMessage | list[BaseMessage], **kwargs
    ) -> LLMInterface:
        if self._stream:
            return self.stream(messages, **kwargs)  # type: ignore
        return self.invoke(messages, **kwargs)

    def prepare_message(self, messages: str | BaseMessage | list[BaseMessage]):
        input_: list[BaseMessage] = []

        if isinstance(messages, str):
            input_ = [HumanMessage(content=messages)]
        elif isinstance(messages, BaseMessage):
            input_ = [messages]
        else:
            input_ = messages

        return input_

    def prepare_response(self, pred):
        all_text = [each.text for each in pred.generations[0]]
        all_messages = [each.message for each in pred.generations[0]]

        completion_tokens, total_tokens, prompt_tokens = 0, 0, 0
        try:
            if pred.llm_output is not None:
                completion_tokens = pred.llm_output["token_usage"]["completion_tokens"]
                total_tokens = pred.llm_output["token_usage"]["total_tokens"]
                prompt_tokens = pred.llm_output["token_usage"]["prompt_tokens"]
        except Exception:
            logger.warning(
                f"Cannot get token usage from LLM output for {self._lc_class.__name__}"
            )

        return LLMInterface(
            text=all_text[0] if len(all_text) > 0 else "",
            candidates=all_text,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            prompt_tokens=prompt_tokens,
            messages=all_messages,
            logits=[],
        )

    def invoke(
        self, messages: str | BaseMessage | list[BaseMessage], **kwargs
    ) -> LLMInterface:
        """Generate response from messages

        Args:
            messages: history of messages to generate response from
            **kwargs: additional arguments to pass to the langchain chat model

        Returns:
            LLMInterface: generated response
        """
        input_ = self.prepare_message(messages)
        pred = self._obj.generate(messages=[input_], **kwargs)
        return self.prepare_response(pred)

    async def ainvoke(
        self, messages: str | BaseMessage | list[BaseMessage], **kwargs
    ) -> LLMInterface:
        input_ = self.prepare_message(messages)
        pred = await self._obj.agenerate(messages=[input_], **kwargs)
        return self.prepare_response(pred)

    def stream(
        self, messages: str | BaseMessage | list[BaseMessage], **kwargs
    ) -> Iterator[LLMInterface]:
        for response in self._obj.stream(input=messages, **kwargs):
            yield LLMInterface(content=response.content)

    async def astream(
        self, messages: str | BaseMessage | list[BaseMessage], **kwargs
    ) -> AsyncGenerator[LLMInterface, None]:
        async for response in self._obj.astream(input=messages, **kwargs):
            yield LLMInterface(content=response.content)

    def to_langchain_format(self):
        return self._obj

    def __repr__(self):
        kwargs = []
        for key, value_obj in self._kwargs.items():
            value = repr(value_obj)
            kwargs.append(f"{key}={value}")
        kwargs_repr = ", ".join(kwargs)
        return f"{self.__class__.__name__}({kwargs_repr})"

    def __str__(self):
        kwargs = []
        for key, value_obj in self._kwargs.items():
            value = str(value_obj)
            if len(value) > 20:
                value = f"{value[:15]}..."
            kwargs.append(f"{key}={value}")
        kwargs_repr = ", ".join(kwargs)
        return f"{self.__class__.__name__}({kwargs_repr})"

    def __setattr__(self, name, value):
        if name == "_lc_class":
            return super().__setattr__(name, value)

        if name in self._lc_class.__fields__:
            self._kwargs[name] = value
            self._obj = self._lc_class(**self._kwargs)
        else:
            super().__setattr__(name, value)

    def __getattr__(self, name):
        if name in self._kwargs:
            return self._kwargs[name]
        return getattr(self._obj, name)

    def dump(self, *args, **kwargs):
        from theflow.utils.modules import serialize

        params = {key: serialize(value) for key, value in self._kwargs.items()}
        return {
            "__type__": f"{self.__module__}.{self.__class__.__qualname__}",
            **params,
        }

    def specs(self, path: str):
        path = path.strip(".")
        if "." in path:
            raise ValueError("path should not contain '.'")

        if path in self._lc_class.__fields__:
            return {
                "__type__": "theflow.base.ParamAttr",
                "refresh_on_set": True,
                "strict_type": True,
            }

        raise ValueError(f"Invalid param {path}")


class LCChatOpenAI(LCChatMixin, ChatLLM):  # type: ignore
    def __init__(
        self,
        openai_api_base: str | None = None,
        openai_api_key: str | None = None,
        model: str | None = None,
        temperature: float = 0.7,
        request_timeout: float | None = None,
        **params,
    ):
        super().__init__(
            openai_api_base=openai_api_base,
            openai_api_key=openai_api_key,
            model=model,
            temperature=temperature,
            request_timeout=request_timeout,
            **params,
        )

    def _get_lc_class(self):
        try:
            from langchain_openai import ChatOpenAI
        except ImportError:
            from langchain.chat_models import ChatOpenAI

        return ChatOpenAI


class LCAzureChatOpenAI(LCChatMixin, ChatLLM):  # type: ignore
    def __init__(
        self,
        azure_endpoint: str | None = None,
        openai_api_key: str | None = None,
        openai_api_version: str = "",
        deployment_name: str | None = None,
        temperature: float = 0.7,
        request_timeout: float | None = None,
        **params,
    ):
        super().__init__(
            azure_endpoint=azure_endpoint,
            openai_api_key=openai_api_key,
            openai_api_version=openai_api_version,
            deployment_name=deployment_name,
            temperature=temperature,
            request_timeout=request_timeout,
            **params,
        )

    def _get_lc_class(self):
        try:
            from langchain_openai import AzureChatOpenAI
        except ImportError:
            from langchain.chat_models import AzureChatOpenAI

        return AzureChatOpenAI


class LCAnthropicChat(LCChatMixin, ChatLLM):  # type: ignore
    api_key: str = Param(
        help="API key (https://console.anthropic.com/settings/keys)", required=True
    )
    model_name: str = Param(
        help=(
            "Model name to use "
            "(https://docs.anthropic.com/en/docs/about-claude/models)"
        ),
        required=True,
    )

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str | None = None,
        temperature: float = 0.7,
        **params,
    ):
        super().__init__(
            api_key=api_key,
            model_name=model_name,
            temperature=temperature,
            **params,
        )

    def _get_lc_class(self):
        try:
            from langchain_anthropic import ChatAnthropic
        except ImportError:
            raise ImportError("Please install langchain-anthropic")

        return ChatAnthropic


class LCGeminiChat(LCChatMixin, ChatLLM):  # type: ignore
    api_key: str = Param(
        help="API key (https://aistudio.google.com/app/apikey)", required=True
    )
    model_name: str = Param(
        help=(
            "Model name to use (https://cloud.google"
            ".com/vertex-ai/generative-ai/docs/learn/models)"
        ),
        required=True,
    )

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str | None = None,
        temperature: float = 0.7,
        **params,
    ):
        super().__init__(
            google_api_key=api_key,
            model=model_name,
            temperature=temperature,
            **params,
        )

    def _get_lc_class(self):
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
        except ImportError:
            raise ImportError("Please install langchain-google-genai")

        return ChatGoogleGenerativeAI
