from typing import AsyncGenerator, Iterator, Optional

from kotaemon.base import AIMessage, BaseMessage, HumanMessage, LLMInterface, Param

from .base import ChatLLM


class ChatLiteLLM(ChatLLM):
    """LiteLLM AI Gateway — unified interface to 100+ LLM providers

    LiteLLM provides a single API to call OpenAI, Anthropic, Google,
    Cohere, Mistral, Bedrock, Azure, Hugging Face, Ollama, and 100+
    other providers. All providers use the same completion() interface.

    Provider-specific model formats:
        - OpenAI: ``gpt-4o``, ``gpt-4o-mini``
        - Anthropic: ``anthropic/claude-3-sonnet``
        - Google: ``gemini/gemini-pro``
        - AWS Bedrock: ``bedrock/anthropic.claude-3-sonnet``
        - Azure: ``azure/my-deployment``
        - Ollama: ``ollama/llama3``

    See https://docs.litellm.ai/docs/providers for the full list.

    Attributes:
        model: Model identifier in LiteLLM format.
        api_key: API key for the underlying provider.
        api_base: Custom API base URL (e.g. for LiteLLM proxy gateway).
        temperature: Sampling temperature (0 to 2).
        max_tokens: Maximum number of tokens to generate.
        top_p: Nucleus sampling parameter.
        stop: Stop sequences.
        frequency_penalty: Frequency penalty (-2.0 to 2.0).
        presence_penalty: Presence penalty (-2.0 to 2.0).
        n: Number of completions to generate.
        timeout: Timeout for the API request in seconds.
    """

    _dependencies = ["litellm"]
    _capabilities = ["chat", "text"]

    model: str = Param(
        help=(
            "LiteLLM model identifier. Format varies by provider, e.g. "
            "'gpt-4o', 'anthropic/claude-3-sonnet', 'gemini/gemini-pro'. "
            "See https://docs.litellm.ai/docs/providers"
        ),
        required=True,
    )
    api_key: Optional[str] = Param(None, help="API key for the underlying provider")
    api_base: Optional[str] = Param(
        None,
        help="Custom API base URL (e.g. for a LiteLLM proxy gateway)",
    )
    timeout: Optional[float] = Param(None, help="Timeout for the API request")
    temperature: Optional[float] = Param(
        None,
        help=(
            "Number between 0 and 2 that controls the randomness of the "
            "generated tokens."
        ),
    )
    max_tokens: Optional[int] = Param(
        None,
        help=(
            "Maximum number of tokens to generate. The total length of "
            "input tokens and generated tokens is limited by the model's "
            "context length."
        ),
    )
    top_p: Optional[float] = Param(
        None,
        help=(
            "An alternative to sampling with temperature, called nucleus "
            "sampling, where the model considers the results of the tokens "
            "with top_p probability mass."
        ),
    )
    stop: Optional[str | list[str]] = Param(
        None,
        help=(
            "Stop sequence. If a stop sequence is detected, generation "
            "will stop at that point."
        ),
    )
    frequency_penalty: Optional[float] = Param(
        None,
        help=(
            "Number between -2.0 and 2.0. Positive values penalize new "
            "tokens based on their existing frequency in the text so far."
        ),
    )
    presence_penalty: Optional[float] = Param(
        None,
        help=(
            "Number between -2.0 and 2.0. Positive values penalize new "
            "tokens based on whether they appear in the text so far."
        ),
    )
    n: int = Param(
        1,
        help="Number of completions to generate for each prompt.",
    )

    def prepare_message(
        self,
        messages: str | BaseMessage | list[BaseMessage],
    ) -> list[dict]:
        input_: list[BaseMessage] = []
        if isinstance(messages, str):
            input_ = [HumanMessage(content=messages)]
        elif isinstance(messages, BaseMessage):
            input_ = [messages]
        else:
            input_ = messages
        return [m.to_openai_format() for m in input_]

    def prepare_params(self, **kwargs) -> dict:
        params_: dict = {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "top_p": self.top_p,
            "stop": self.stop,
            "frequency_penalty": self.frequency_penalty,
            "presence_penalty": self.presence_penalty,
            # Silently drop per-provider unsupported kwargs instead of raising.
            # Anthropic rejects frequency_penalty/presence_penalty, Gemini
            # rejects stop on some variants, Azure AI rejects seed, etc.
            # Users can opt out by passing ``drop_params=False`` via kwargs.
            "drop_params": True,
        }
        if self.api_key:
            params_["api_key"] = self.api_key
        if self.api_base:
            params_["api_base"] = self.api_base
        if self.timeout is not None:
            params_["timeout"] = self.timeout
        if self.n != 1:
            params_["n"] = self.n

        params = {k: v for k, v in params_.items() if v is not None}
        params.update(kwargs)
        return params

    def prepare_output(self, resp) -> LLMInterface:
        resp_dict = resp.model_dump()
        usage = resp_dict.get("usage") or {}
        choices = resp_dict.get("choices") or []

        return LLMInterface(
            content=(choices[0]["message"]["content"] or "") if choices else "",
            candidates=[(c["message"]["content"] or "") for c in choices],
            completion_tokens=usage.get("completion_tokens", 0),
            prompt_tokens=usage.get("prompt_tokens", 0),
            total_tokens=usage.get("total_tokens", 0),
            messages=[
                AIMessage(content=(c["message"]["content"]) or "") for c in choices
            ],
        )

    def invoke(
        self,
        messages: str | BaseMessage | list[BaseMessage],
        *args,
        **kwargs,
    ) -> LLMInterface:
        try:
            import litellm
        except ImportError:
            raise ImportError(
                "Please install litellm: `pip install -U litellm`"
            )

        input_messages = self.prepare_message(messages)
        params = self.prepare_params(**kwargs)
        resp = litellm.completion(messages=input_messages, **params)
        return self.prepare_output(resp)

    async def ainvoke(
        self,
        messages: str | BaseMessage | list[BaseMessage],
        *args,
        **kwargs,
    ) -> LLMInterface:
        try:
            import litellm
        except ImportError:
            raise ImportError(
                "Please install litellm: `pip install -U litellm`"
            )

        input_messages = self.prepare_message(messages)
        params = self.prepare_params(**kwargs)
        resp = await litellm.acompletion(messages=input_messages, **params)
        return self.prepare_output(resp)

    def stream(
        self,
        messages: str | BaseMessage | list[BaseMessage],
        *args,
        **kwargs,
    ) -> Iterator[LLMInterface]:
        try:
            import litellm
        except ImportError:
            raise ImportError(
                "Please install litellm: `pip install -U litellm`"
            )

        input_messages = self.prepare_message(messages)
        params = self.prepare_params(**kwargs)
        resp = litellm.completion(messages=input_messages, stream=True, **params)

        for chunk in resp:
            chunk_dict = chunk.model_dump()
            choices = chunk_dict.get("choices") or []
            if not choices:
                continue
            delta_content = choices[0].get("delta", {}).get("content")
            if delta_content is not None:
                yield LLMInterface(content=delta_content)

    async def astream(
        self,
        messages: str | BaseMessage | list[BaseMessage],
        *args,
        **kwargs,
    ) -> AsyncGenerator[LLMInterface, None]:
        try:
            import litellm
        except ImportError:
            raise ImportError(
                "Please install litellm: `pip install -U litellm`"
            )

        input_messages = self.prepare_message(messages)
        params = self.prepare_params(**kwargs)
        resp = await litellm.acompletion(messages=input_messages, stream=True, **params)

        async for chunk in resp:
            if not chunk.choices:
                continue
            if chunk.choices[0].delta.content is not None:
                yield LLMInterface(content=chunk.choices[0].delta.content)
