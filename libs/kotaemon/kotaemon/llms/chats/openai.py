from typing import TYPE_CHECKING, AsyncGenerator, Iterator, Optional

from theflow.utils.modules import import_dotted_string

from kotaemon.base import AIMessage, BaseMessage, HumanMessage, LLMInterface, Param

from .base import ChatLLM

if TYPE_CHECKING:
    from openai.types.chat.chat_completion_message_param import (
        ChatCompletionMessageParam,
    )


class BaseChatOpenAI(ChatLLM):
    """Base interface for OpenAI chat model, using the openai library

    This class exposes the parameters in resources.Chat. To subclass this class:

        - Implement the `prepare_client` method to return the OpenAI client
        - Implement the `openai_response` method to return the OpenAI response
        - Implement the params relate to the OpenAI client
    """

    _dependencies = ["openai"]
    _capabilities = ["chat", "text"]  # consider as mixin

    api_key: str = Param(help="API key", required=True)
    timeout: Optional[float] = Param(None, help="Timeout for the API request")
    max_retries: Optional[int] = Param(
        None, help="Maximum number of retries for the API request"
    )

    temperature: Optional[float] = Param(
        None,
        help=(
            "Number between 0 and 2 that controls the randomness of the generated "
            "tokens. Lower values make the model more deterministic, while higher "
            "values make the model more random."
        ),
    )
    max_tokens: Optional[int] = Param(
        None,
        help=(
            "Maximum number of tokens to generate. The total length of input tokens "
            "and generated tokens is limited by the model's context length."
        ),
    )
    n: int = Param(
        1,
        help=(
            "Number of completions to generate. The API will generate n completion "
            "for each prompt."
        ),
    )
    stop: Optional[str | list[str]] = Param(
        None,
        help=(
            "Stop sequence. If a stop sequence is detected, generation will stop "
            "at that point. If not specified, generation will continue until the "
            "maximum token length is reached."
        ),
    )
    frequency_penalty: Optional[float] = Param(
        None,
        help=(
            "Number between -2.0 and 2.0. Positive values penalize new tokens "
            "based on their existing frequency in the text so far, decrearsing the "
            "model's likelihood of repeating the same text."
        ),
    )
    presence_penalty: Optional[float] = Param(
        None,
        help=(
            "Number between -2.0 and 2.0. Positive values penalize new tokens "
            "based on their existing presence in the text so far, decrearsing the "
            "model's likelihood of repeating the same text."
        ),
    )
    tool_choice: Optional[str] = Param(
        None,
        help=(
            "Choice of tool to use for the completion. Available choices are: "
            "auto, default."
        ),
    )
    tools: Optional[list[str]] = Param(
        None,
        help="List of tools to use for the completion.",
    )
    logprobs: Optional[bool] = Param(
        None,
        help=(
            "Include log probabilities on the logprobs most likely tokens, "
            "as well as the chosen token."
        ),
    )
    logit_bias: Optional[dict] = Param(
        None,
        help=(
            "Dictionary of logit bias values to add to the logits of the tokens "
            "in the vocabulary."
        ),
    )
    top_logprobs: Optional[int] = Param(
        None,
        help=(
            "An integer between 0 and 5 specifying the number of most likely tokens "
            "to return at each token position, each with an associated log "
            "probability. `logprobs` must also be set to `true` if this parameter "
            "is used."
        ),
    )
    top_p: Optional[float] = Param(
        None,
        help=(
            "An alternative to sampling with temperature, called nucleus sampling, "
            "where the model considers the results of the token with top_p "
            "probability mass. So 0.1 means that only the tokens comprising the "
            "top 10% probability mass are considered."
        ),
    )

    @Param.auto(depends_on=["max_retries"])
    def max_retries_(self):
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
        resp = await self.openai_response(
            client, messages=input_messages, stream=False, **kwargs
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


class ChatOpenAI(BaseChatOpenAI):
    """OpenAI chat model"""

    base_url: Optional[str] = Param(None, help="OpenAI base URL")
    organization: Optional[str] = Param(None, help="OpenAI organization")
    model: str = Param(help="OpenAI model", required=True)

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

    def openai_response(self, client, **kwargs):
        """Get the openai response"""
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

        return client.chat.completions.create(**params)


class AzureChatOpenAI(BaseChatOpenAI):
    """OpenAI chat model provided by Microsoft Azure"""

    azure_endpoint: str = Param(
        help=(
            "HTTPS endpoint for the Azure OpenAI model. The azure_endpoint, "
            "azure_deployment, and api_version parameters are used to construct "
            "the full URL for the Azure OpenAI model."
        ),
        required=True,
    )
    azure_deployment: str = Param(help="Azure deployment name", required=True)
    api_version: str = Param(help="Azure model version", required=True)
    azure_ad_token: Optional[str] = Param(None, help="Azure AD token")
    azure_ad_token_provider: Optional[str] = Param(None, help="Azure AD token provider")

    @Param.auto(depends_on=["azure_ad_token_provider"])
    def azure_ad_token_provider_(self):
        if isinstance(self.azure_ad_token_provider, str):
            return import_dotted_string(self.azure_ad_token_provider, safe=False)

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
            "azure_ad_token_provider": self.azure_ad_token_provider_,
            "timeout": self.timeout,
            "max_retries": self.max_retries_,
        }
        if async_version:
            from openai import AsyncAzureOpenAI

            return AsyncAzureOpenAI(**params)

        from openai import AzureOpenAI

        return AzureOpenAI(**params)

    def openai_response(self, client, **kwargs):
        """Get the openai response"""
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

        return client.chat.completions.create(**params)
