from __future__ import annotations

import logging

from kotaemon.base import BaseMessage, HumanMessage, LLMInterface

from .base import ChatLLM

logger = logging.getLogger(__name__)


class LCChatMixin:
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
        input_: list[BaseMessage] = []

        if isinstance(messages, str):
            input_ = [HumanMessage(content=messages)]
        elif isinstance(messages, BaseMessage):
            input_ = [messages]
        else:
            input_ = messages

        pred = self._obj.generate(messages=[input_], **kwargs)
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

    def stream(self, messages: str | BaseMessage | list[BaseMessage], **kwargs):
        for response in self._obj.stream(input=messages, **kwargs):
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


class AzureChatOpenAI(LCChatMixin, ChatLLM):
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
