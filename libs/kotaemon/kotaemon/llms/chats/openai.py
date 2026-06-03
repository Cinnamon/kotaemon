from dataclasses import dataclass, field
from typing import TYPE_CHECKING, AsyncGenerator, Iterator, Optional, Type

from pydantic import BaseModel

from kotaemon.base import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    LLMInterface,
    StructuredOutputLLMInterface,
)

from .base import ChatLLM

if TYPE_CHECKING:
    from openai.types.chat.chat_completion_message_param import (
        ChatCompletionMessageParam,
    )


@dataclass(kw_only=True)
class BaseChatOpenAI(ChatLLM):
    """Base interface for OpenAI chat model, using the openai library

    This class exposes the parameters in resources.Chat. To subclass this class:

        - Implement the `prepare_client` method to return the OpenAI client
        - Implement the `openai_response` method to return the OpenAI response
        - Implement the params relate to the OpenAI client
    """

    _dependencies = ["openai"]
    _capabilities = ["chat", "text"]  # consider as mixin

    api_key: str = field(metadata={"description": "API key"})
    timeout: Optional[float] = field(
        default=None, metadata={"description": "Timeout for the API request"}
    )
    max_retries: Optional[int] = field(
        default=None,
        metadata={"description": "Maximum number of retries for the API request"},
    )
    temperature: Optional[float] = field(
        default=None,
        metadata={
            "description": (
                "Number between 0 and 2 that controls the randomness of the "
                "generated tokens."
            )
        },
    )
    max_tokens: Optional[int] = field(
        default=None,
        metadata={"description": "Maximum number of tokens to generate."},
    )
    n: int = field(
        default=1,
        metadata={"description": "Number of completions to generate."},
    )
    stop: Optional[str | list[str]] = field(
        default=None, metadata={"description": "Stop sequence."}
    )
    frequency_penalty: Optional[float] = field(
        default=None, metadata={"description": "Frequency penalty."}
    )
    presence_penalty: Optional[float] = field(
        default=None, metadata={"description": "Presence penalty."}
    )
    tool_choice: Optional[str] = field(
        default=None, metadata={"description": "Tool choice for the completion."}
    )
    tools: Optional[list[str]] = field(
        default=None, metadata={"description": "Tools for the completion."}
    )
    logprobs: Optional[bool] = field(
        default=None, metadata={"description": "Include log probabilities."}
    )
    logit_bias: Optional[dict] = field(
        default=None, metadata={"description": "Logit bias dictionary."}
    )
    top_logprobs: Optional[int] = field(
        default=None, metadata={"description": "Number of top logprobs to return."}
    )
    top_p: Optional[float] = field(
        default=None, metadata={"description": "Nucleus sampling mass."}
    )

    @property
    def max_retries_(self) -> int:
        if self.max_retries is None:
            from openai._constants import DEFAULT_MAX_RETRIES

            return DEFAULT_MAX_RETRIES
        return self.max_retries

    def prepare_message(
        self, messages: str | BaseMessage | list[BaseMessage]
    ) -> list["ChatCompletionMessageParam"]:
        """Prepare the message into OpenAI format

        Returns:
            list[dict]: List of messages in OpenAI format
        """
        input_: list[BaseMessage] = []
        output_: list["ChatCompletionMessageParam"] = []

        if isinstance(messages, str):
            input_ = [HumanMessage(content=messages)]
        elif isinstance(messages, BaseMessage):
            input_ = [messages]
        else:
            input_ = messages

        for message in input_:
            output_.append(message.to_openai_format())

        return output_

    def prepare_output(self, resp: dict) -> LLMInterface:
        """Convert the OpenAI response into LLMInterface"""
        additional_kwargs = {}
        if "tool_calls" in resp["choices"][0]["message"]:
            additional_kwargs["tool_calls"] = resp["choices"][0]["message"][
                "tool_calls"
            ]

        if resp["choices"][0].get("logprobs") is None:
            logprobs = []
        else:
            all_logprobs = resp["choices"][0]["logprobs"].get("content")
            logprobs = (
                [logprob["logprob"] for logprob in all_logprobs] if all_logprobs else []
            )

        output = LLMInterface(
            candidates=[(_["message"]["content"] or "") for _ in resp["choices"]],
            content=resp["choices"][0]["message"]["content"] or "",
            total_tokens=resp["usage"]["total_tokens"],
            prompt_tokens=resp["usage"]["prompt_tokens"],
            completion_tokens=resp["usage"]["completion_tokens"],
            additional_kwargs=additional_kwargs,
            messages=[
                AIMessage(content=(_["message"]["content"]) or "")
                for _ in resp["choices"]
            ],
            logprobs=logprobs,
        )

        return output

    def prepare_client(self, async_version: bool = False):
        """Get the OpenAI client

        Args:
            async_version (bool): Whether to get the async version of the client
        """
        raise NotImplementedError

    def openai_response(self, client, **kwargs):
        """Get the openai response"""
        raise NotImplementedError

    async def aopenai_response(self, client, **kwargs):
        """Get the openai response"""
        raise NotImplementedError

    def invoke(
        self, messages: str | BaseMessage | list[BaseMessage], *args, **kwargs
    ) -> LLMInterface:
        client = self.prepare_client(async_version=False)
        input_messages = self.prepare_message(messages)
        resp = self.openai_response(
            client, messages=input_messages, stream=False, **kwargs
        ).dict()
        return self.prepare_output(resp)

    async def ainvoke(
        self, messages: str | BaseMessage | list[BaseMessage], *args, **kwargs
    ) -> LLMInterface:
        client = self.prepare_client(async_version=True)
        input_messages = self.prepare_message(messages)
        resp = (
            await self.aopenai_response(
                client, messages=input_messages, stream=False, **kwargs
            )
        ).dict()

        return self.prepare_output(resp)

    def stream(
        self, messages: str | BaseMessage | list[BaseMessage], *args, **kwargs
    ) -> Iterator[LLMInterface]:
        client = self.prepare_client(async_version=False)
        input_messages = self.prepare_message(messages)
        resp = self.openai_response(
            client, messages=input_messages, stream=True, **kwargs
        )

        for c in resp:
            chunk = c.dict()
            if not chunk["choices"]:
                continue
            if chunk["choices"][0]["delta"]["content"] is not None:
                if chunk["choices"][0].get("logprobs") is None:
                    logprobs = []
                else:
                    logprobs = [
                        logprob["logprob"]
                        for logprob in chunk["choices"][0]["logprobs"].get(
                            "content", []
                        )
                    ]

                yield LLMInterface(
                    content=chunk["choices"][0]["delta"]["content"], logprobs=logprobs
                )

    async def astream(
        self, messages: str | BaseMessage | list[BaseMessage], *args, **kwargs
    ) -> AsyncGenerator[LLMInterface, None]:
        client = self.prepare_client(async_version=True)
        input_messages = self.prepare_message(messages)
        resp = self.openai_response(
            client, messages=input_messages, stream=True, **kwargs
        )

        async for chunk in resp:
            if not chunk.choices:
                continue
            if chunk.choices[0].delta.content is not None:
                yield LLMInterface(content=chunk.choices[0].delta.content)


@dataclass(kw_only=True)
class ChatOpenAI(BaseChatOpenAI):
    """OpenAI chat model"""

    model: str = field(
        metadata={
            "description": "OpenAI model ID (see platform.openai.com/docs/models)."
        }
    )
    base_url: Optional[str] = field(
        default=None, metadata={"description": "OpenAI base URL"}
    )
    organization: Optional[str] = field(
        default=None, metadata={"description": "OpenAI organization"}
    )

    def prepare_client(self, async_version: bool = False):
        """Get the OpenAI client

        Args:
            async_version (bool): Whether to get the async version of the client
        """
        params = {
            "api_key": self.api_key,
            "organization": self.organization,
            "base_url": self.base_url,
            "timeout": self.timeout,
            "max_retries": self.max_retries_,
        }
        if async_version:
            from openai import AsyncOpenAI

            return AsyncOpenAI(**params)

        from openai import OpenAI

        return OpenAI(**params)

    def prepare_params(self, **kwargs):
        if "tools_pydantic" in kwargs:
            kwargs.pop("tools_pydantic")

        params_ = {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "n": self.n,
            "stop": self.stop,
            "frequency_penalty": self.frequency_penalty,
            "presence_penalty": self.presence_penalty,
            "tool_choice": self.tool_choice,
            "tools": self.tools,
            "logprobs": self.logprobs,
            "logit_bias": self.logit_bias,
            "top_logprobs": self.top_logprobs,
            "top_p": self.top_p,
        }
        params = {k: v for k, v in params_.items() if v is not None}
        params.update(kwargs)

        return params

    def openai_response(self, client, **kwargs):
        """Get the openai response"""
        params = self.prepare_params(**kwargs)
        return client.chat.completions.create(**params)

    async def aopenai_response(self, client, **kwargs):
        params = self.prepare_params(**kwargs)
        return await client.chat.completions.create(**params)


@dataclass(kw_only=True)
class StructuredOutputChatOpenAI(ChatOpenAI):
    """OpenAI chat model that returns structured output"""

    response_schema: Type[BaseModel] = field(
        metadata={"description": "Pydantic model class for structured output."}
    )

    def prepare_output(self, resp: dict) -> StructuredOutputLLMInterface:
        """Convert the OpenAI response into StructuredOutputLLMInterface"""
        additional_kwargs = {}

        if "tool_calls" in resp["choices"][0]["message"]:
            additional_kwargs["tool_calls"] = resp["choices"][0]["message"][
                "tool_calls"
            ]

        if resp["choices"][0].get("logprobs") is None:
            logprobs = []
        else:
            all_logprobs = resp["choices"][0]["logprobs"].get("content")
            logprobs = (
                [logprob["logprob"] for logprob in all_logprobs] if all_logprobs else []
            )

        output = StructuredOutputLLMInterface(
            parsed=resp["choices"][0]["message"]["parsed"],
            candidates=[(_["message"]["content"] or "") for _ in resp["choices"]],
            content=resp["choices"][0]["message"]["content"] or "",
            total_tokens=resp["usage"]["total_tokens"],
            prompt_tokens=resp["usage"]["prompt_tokens"],
            completion_tokens=resp["usage"]["completion_tokens"],
            messages=[
                AIMessage(content=(_["message"]["content"]) or "")
                for _ in resp["choices"]
            ],
            additional_kwargs=additional_kwargs,
            logprobs=logprobs,
        )

        return output

    def prepare_params(self, **kwargs):
        if "tools_pydantic" in kwargs:
            kwargs.pop("tools_pydantic")

        params_ = {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "n": self.n,
            "stop": self.stop,
            "frequency_penalty": self.frequency_penalty,
            "presence_penalty": self.presence_penalty,
            "tool_choice": self.tool_choice,
            "tools": self.tools,
            "logprobs": self.logprobs,
            "logit_bias": self.logit_bias,
            "top_logprobs": self.top_logprobs,
            "top_p": self.top_p,
            "response_format": self.response_schema,
        }
        params = {k: v for k, v in params_.items() if v is not None}
        params.update(kwargs)

        # doesn't do streaming
        params.pop("stream")

        return params

    def openai_response(self, client, **kwargs):
        """Get the openai response"""
        params = self.prepare_params(**kwargs)

        return client.beta.chat.completions.parse(**params)

    async def aopenai_response(self, client, **kwargs):
        """Get the openai response"""
        params = self.prepare_params(**kwargs)

        return await client.beta.chat.completions.parse(**params)

@dataclass(kw_only=True)
class AzureChatOpenAI(BaseChatOpenAI):
    """OpenAI chat model provided by Microsoft Azure"""

    azure_endpoint: str = field(
        metadata={
            "description": (
                "HTTPS endpoint for the Azure OpenAI model."
            )
        }
    )
    azure_deployment: str = field(
        metadata={"description": "Azure deployment name"}
    )
    api_version: str = field(metadata={"description": "Azure model version"})
    azure_ad_token: Optional[str] = field(
        default=None, metadata={"description": "Azure AD token"}
    )

    def prepare_client(self, async_version: bool = False):
        """Get the OpenAI client

        Args:
            async_version (bool): Whether to get the async version of the client
        """
        params = {
            "azure_endpoint": self.azure_endpoint,
            "api_version": self.api_version,
            "api_key": self.api_key,
            "azure_ad_token": self.azure_ad_token,
            "timeout": self.timeout,
            "max_retries": self.max_retries_,
        }
        if async_version:
            from openai import AsyncAzureOpenAI

            return AsyncAzureOpenAI(**params)

        from openai import AzureOpenAI

        return AzureOpenAI(**params)

    def prepare_params(self, **kwargs):
        if "tools_pydantic" in kwargs:
            kwargs.pop("tools_pydantic")

        params_ = {
            "model": self.azure_deployment,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "n": self.n,
            "stop": self.stop,
            "frequency_penalty": self.frequency_penalty,
            "presence_penalty": self.presence_penalty,
            "tool_choice": self.tool_choice,
            "tools": self.tools,
            "logprobs": self.logprobs,
            "logit_bias": self.logit_bias,
            "top_logprobs": self.top_logprobs,
            "top_p": self.top_p,
        }
        params = {k: v for k, v in params_.items() if v is not None}
        params.update(kwargs)

        return params

    def openai_response(self, client, **kwargs):
        """Get the openai response"""
        params = self.prepare_params(**kwargs)
        return client.chat.completions.create(**params)

    async def aopenai_response(self, client, **kwargs):
        params = self.prepare_params(**kwargs)
        return await client.chat.completions.create(**params)
