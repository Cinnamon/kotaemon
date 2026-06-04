from __future__ import annotations

import logging
from dataclasses import dataclass, field
from functools import cached_property
from typing import Any

from kotaemon.base import LLMInterface

from .base import LLM

logger = logging.getLogger(__name__)


def lc_completion_response(pred: Any, *, lc_class_name: str) -> LLMInterface:
    all_text = [each.text for each in pred.generations[0]]

    completion_tokens, total_tokens, prompt_tokens = 0, 0, 0
    try:
        if pred.llm_output is not None:
            completion_tokens = pred.llm_output["token_usage"]["completion_tokens"]
            total_tokens = pred.llm_output["token_usage"]["total_tokens"]
            prompt_tokens = pred.llm_output["token_usage"]["prompt_tokens"]
    except Exception:
        logger.warning(
            "Cannot get token usage from LLM output for %s",
            lc_class_name,
        )

    return LLMInterface(
        text=all_text[0] if len(all_text) > 0 else "",
        candidates=all_text,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        prompt_tokens=prompt_tokens,
        logits=[],
    )


@dataclass(kw_only=True)
class BaseLCCompletion(LLM):
    """Base wrapper for LangChain completion (legacy) LLM models."""

    def _get_lc_class(self) -> type:
        raise NotImplementedError(
            "Subclasses must implement _get_lc_class with the LangChain class."
        )

    def _lc_kwargs(self) -> dict[str, Any]:
        raise NotImplementedError(
            "Subclasses must implement _lc_kwargs mapping fields to LangChain."
        )

    @cached_property
    def _lc_obj(self) -> Any:
        return self._get_lc_class()(**self._lc_kwargs())

    def to_langchain_format(self) -> Any:
        return self._lc_obj

    def invoke(self, text: str, **kwargs) -> LLMInterface:
        pred = self._lc_obj.generate([text], **kwargs)
        return lc_completion_response(pred, lc_class_name=self._get_lc_class().__name__)

    def run(self, text: str, **kwargs) -> LLMInterface:
        return self.invoke(text, **kwargs)


@dataclass(kw_only=True)
class OpenAI(BaseLCCompletion):
    """Wrapper around LangChain's OpenAI completion model."""

    openai_api_key: str | None = field(
        default=None, metadata={"description": "OpenAI API key."}
    )
    openai_api_base: str | None = field(
        default=None, metadata={"description": "OpenAI API base URL."}
    )
    openai_api_version: str | None = field(
        default=None, metadata={"description": "OpenAI API version."}
    )
    deployment_name: str | None = field(
        default=None, metadata={"description": "Deployment name."}
    )
    model_name: str = field(
        default="text-davinci-003",
        metadata={"description": "Model name."},
    )
    temperature: float = field(
        default=0.7,
        metadata={"description": "Sampling temperature."},
    )
    max_tokens: int = field(
        default=256, metadata={"description": "Maximum tokens to generate."}
    )
    top_p: float = field(
        default=1.0, metadata={"description": "Nucleus sampling mass."}
    )
    frequency_penalty: float = field(
        default=0.0, metadata={"description": "Frequency penalty."}
    )
    n: int = field(
        default=1, metadata={"description": "Number of completions to generate."}
    )
    best_of: int = field(
        default=1, metadata={"description": "Number of candidates per prompt."}
    )
    request_timeout: float | None = field(
        default=None, metadata={"description": "Request timeout in seconds."}
    )
    max_retries: int = field(
        default=2, metadata={"description": "Maximum API retries."}
    )
    streaming: bool = field(
        default=False, metadata={"description": "Enable streaming responses."}
    )

    def _get_lc_class(self) -> type:
        try:
            from langchain_openai import OpenAI as LCOpenAI
        except ImportError:
            from langchain.llms import OpenAI as LCOpenAI

        return LCOpenAI

    def _lc_kwargs(self) -> dict[str, Any]:
        return {
            "openai_api_key": self.openai_api_key,
            "openai_api_base": self.openai_api_base,
            "openai_api_version": self.openai_api_version,
            "deployment_name": self.deployment_name,
            "model_name": self.model_name,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "top_p": self.top_p,
            "frequency_penalty": self.frequency_penalty,
            "n": self.n,
            "best_of": self.best_of,
            "request_timeout": self.request_timeout,
            "max_retries": self.max_retries,
            "streaming": self.streaming,
        }


@dataclass(kw_only=True)
class AzureOpenAI(BaseLCCompletion):
    """Wrapper around LangChain's Azure OpenAI completion model."""

    azure_endpoint: str | None = field(
        default=None, metadata={"description": "Azure OpenAI endpoint URL."}
    )
    deployment_name: str | None = field(
        default=None, metadata={"description": "Azure deployment name."}
    )
    openai_api_version: str = field(
        default="",
        metadata={"description": "Azure OpenAI API version."},
    )
    openai_api_key: str | None = field(
        default=None, metadata={"description": "Azure OpenAI API key."}
    )
    model_name: str = field(
        default="text-davinci-003",
        metadata={"description": "Model name."},
    )
    temperature: float = field(
        default=0.7,
        metadata={"description": "Sampling temperature."},
    )
    max_tokens: int = field(
        default=256, metadata={"description": "Maximum tokens to generate."}
    )
    top_p: float = field(
        default=1.0, metadata={"description": "Nucleus sampling mass."}
    )
    frequency_penalty: float = field(
        default=0.0, metadata={"description": "Frequency penalty."}
    )
    n: int = field(
        default=1, metadata={"description": "Number of completions to generate."}
    )
    best_of: int = field(
        default=1, metadata={"description": "Number of candidates per prompt."}
    )
    request_timeout: float | None = field(
        default=None, metadata={"description": "Request timeout in seconds."}
    )
    max_retries: int = field(
        default=2, metadata={"description": "Maximum API retries."}
    )
    streaming: bool = field(
        default=False, metadata={"description": "Enable streaming responses."}
    )

    def _get_lc_class(self) -> type:
        try:
            from langchain_openai import AzureOpenAI as LCAzureOpenAI
        except ImportError:
            from langchain.llms import AzureOpenAI as LCAzureOpenAI

        return LCAzureOpenAI

    def _lc_kwargs(self) -> dict[str, Any]:
        return {
            "azure_endpoint": self.azure_endpoint,
            "deployment_name": self.deployment_name,
            "openai_api_version": self.openai_api_version,
            "openai_api_key": self.openai_api_key,
            "model_name": self.model_name,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "top_p": self.top_p,
            "frequency_penalty": self.frequency_penalty,
            "n": self.n,
            "best_of": self.best_of,
            "request_timeout": self.request_timeout,
            "max_retries": self.max_retries,
            "streaming": self.streaming,
        }


@dataclass(kw_only=True)
class LlamaCpp(BaseLCCompletion):
    """Wrapper around LangChain's LlamaCpp completion model."""

    model_path: str = field(metadata={"description": "Path to the GGUF model file."})
    lora_base: str | None = field(
        default=None, metadata={"description": "Path to Lora model."}
    )
    n_ctx: int = field(default=512, metadata={"description": "Text context size."})
    n_gpu_layers: int | None = field(
        default=None, metadata={"description": "GPU layers (-1 = all)."}
    )
    use_mmap: bool = field(
        default=True, metadata={"description": "Use memory mapping for model."}
    )
    vocab_only: bool = field(
        default=False,
        metadata={"description": "Load vocabulary only (debug)."},
    )

    def _get_lc_class(self) -> type:
        try:
            from langchain_community.llms import LlamaCpp as LCLlamaCpp
        except ImportError:
            from langchain.llms import LlamaCpp as LCLlamaCpp

        return LCLlamaCpp

    def _lc_kwargs(self) -> dict[str, Any]:
        return {
            "model_path": self.model_path,
            "lora_base": self.lora_base,
            "n_ctx": self.n_ctx,
            "n_gpu_layers": self.n_gpu_layers,
            "use_mmap": self.use_mmap,
            "vocab_only": self.vocab_only,
        }


# Backward-compatible alias for code that imported the old mixin name.
LCCompletionMixin = BaseLCCompletion
