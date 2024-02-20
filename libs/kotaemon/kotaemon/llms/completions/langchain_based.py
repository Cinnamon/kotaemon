import logging
from typing import Optional

from kotaemon.base import LLMInterface

from .base import LLM

logger = logging.getLogger(__name__)


class LCCompletionMixin:
    def _get_lc_class(self):
        raise NotImplementedError(
            "Please return the relevant Langchain class in in _get_lc_class"
        )

    def __init__(self, **params):
        self._lc_class = self._get_lc_class()
        self._obj = self._lc_class(**params)
        self._kwargs: dict = params

        super().__init__()

    def run(self, text: str) -> LLMInterface:
        pred = self._obj.generate([text])
        all_text = [each.text for each in pred.generations[0]]

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
            logits=[],
        )

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


class OpenAI(LCCompletionMixin, LLM):
    """Wrapper around Langchain's OpenAI class, focusing on key parameters"""

    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        openai_api_base: Optional[str] = None,
        model_name: str = "text-davinci-003",
        temperature: float = 0.7,
        max_tokens: int = 256,
        top_p: float = 1,
        frequency_penalty: float = 0,
        n: int = 1,
        best_of: int = 1,
        request_timeout: Optional[float] = None,
        max_retries: int = 2,
        streaming: bool = False,
        **params,
    ):
        super().__init__(
            openai_api_key=openai_api_key,
            openai_api_base=openai_api_base,
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            frequency_penalty=frequency_penalty,
            n=n,
            best_of=best_of,
            request_timeout=request_timeout,
            max_retries=max_retries,
            streaming=streaming,
            **params,
        )

    def _get_lc_class(self):
        try:
            from langchain_openai import OpenAI
        except ImportError:
            from langchain.llms import OpenAI

        return OpenAI


class AzureOpenAI(LCCompletionMixin, LLM):
    """Wrapper around Langchain's AzureOpenAI class, focusing on key parameters"""

    def __init__(
        self,
        azure_endpoint: Optional[str] = None,
        deployment_name: Optional[str] = None,
        openai_api_version: str = "",
        openai_api_key: Optional[str] = None,
        model_name: str = "text-davinci-003",
        temperature: float = 0.7,
        max_tokens: int = 256,
        top_p: float = 1,
        frequency_penalty: float = 0,
        n: int = 1,
        best_of: int = 1,
        request_timeout: Optional[float] = None,
        max_retries: int = 2,
        streaming: bool = False,
        **params,
    ):
        super().__init__(
            azure_endpoint=azure_endpoint,
            deployment_name=deployment_name,
            openai_api_version=openai_api_version,
            openai_api_key=openai_api_key,
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            frequency_penalty=frequency_penalty,
            n=n,
            best_of=best_of,
            request_timeout=request_timeout,
            max_retries=max_retries,
            streaming=streaming,
            **params,
        )

    def _get_lc_class(self):
        try:
            from langchain_openai import AzureOpenAI
        except ImportError:
            from langchain.llms import AzureOpenAI

        return AzureOpenAI


class LlamaCpp(LCCompletionMixin, LLM):
    """Wrapper around Langchain's LlamaCpp class, focusing on key parameters"""

    def __init__(
        self,
        model_path: str,
        lora_base: Optional[str] = None,
        n_ctx: int = 512,
        n_gpu_layers: Optional[int] = None,
        use_mmap: bool = True,
        **params,
    ):
        super().__init__(
            model_path=model_path,
            lora_base=lora_base,
            n_ctx=n_ctx,
            n_gpu_layers=n_gpu_layers,
            use_mmap=use_mmap,
            **params,
        )

    def _get_lc_class(self):
        try:
            from langchain_community.llms import LlamaCpp
        except ImportError:
            from langchain.llms import LlamaCpp

        return LlamaCpp
