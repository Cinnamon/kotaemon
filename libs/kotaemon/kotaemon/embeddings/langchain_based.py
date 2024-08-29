from typing import Optional

from kotaemon.base import Document, DocumentWithEmbedding

from .base import BaseEmbeddings


class LCEmbeddingMixin:
    def _get_lc_class(self):
        raise NotImplementedError(
            "Please return the relevant Langchain class in _get_lc_class"
        )

    def __init__(self, **params):
        self._lc_class = self._get_lc_class()
        self._obj = self._lc_class(**params)
        self._kwargs: dict = params

        super().__init__()

    def run(self, text):
        input_: list[str] = []
        if not isinstance(text, list):
            text = [text]

        for item in text:
            if isinstance(item, str):
                input_.append(item)
            elif isinstance(item, Document):
                input_.append(item.text)
            else:
                raise ValueError(
                    f"Invalid input type {type(item)}, should be str or Document"
                )

        embeddings = self._obj.embed_documents(input_)

        return [
            DocumentWithEmbedding(text=each_text, embedding=each_embedding)
            for each_text, each_embedding in zip(input_, embeddings)
        ]

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


class LCOpenAIEmbeddings(LCEmbeddingMixin, BaseEmbeddings):
    """Wrapper around Langchain's OpenAI embedding, focusing on key parameters"""

    def __init__(
        self,
        model: str = "text-embedding-ada-002",
        openai_api_version: Optional[str] = None,
        openai_api_base: Optional[str] = None,
        openai_api_type: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        request_timeout: Optional[float] = None,
        **params,
    ):
        super().__init__(
            model=model,
            openai_api_version=openai_api_version,
            openai_api_base=openai_api_base,
            openai_api_type=openai_api_type,
            openai_api_key=openai_api_key,
            request_timeout=request_timeout,
            **params,
        )

    def _get_lc_class(self):
        try:
            from langchain_openai import OpenAIEmbeddings
        except ImportError:
            from langchain.embeddings import OpenAIEmbeddings

        return OpenAIEmbeddings


class LCAzureOpenAIEmbeddings(LCEmbeddingMixin, BaseEmbeddings):
    """Wrapper around Langchain's AzureOpenAI embedding, focusing on key parameters"""

    def __init__(
        self,
        azure_endpoint: Optional[str] = None,
        deployment: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        api_version: Optional[str] = None,
        request_timeout: Optional[float] = None,
        **params,
    ):
        super().__init__(
            azure_endpoint=azure_endpoint,
            deployment=deployment,
            api_version=api_version,
            openai_api_key=openai_api_key,
            request_timeout=request_timeout,
            **params,
        )

    def _get_lc_class(self):
        try:
            from langchain_openai import AzureOpenAIEmbeddings
        except ImportError:
            from langchain.embeddings import AzureOpenAIEmbeddings

        return AzureOpenAIEmbeddings


class LCCohereEmbeddings(LCEmbeddingMixin, BaseEmbeddings):
    """Wrapper around Langchain's Cohere embedding, focusing on key parameters"""

    def __init__(
        self,
        model: str = "embed-english-v2.0",
        cohere_api_key: Optional[str] = None,
        truncate: Optional[str] = None,
        request_timeout: Optional[float] = None,
        **params,
    ):
        super().__init__(
            model=model,
            cohere_api_key=cohere_api_key,
            truncate=truncate,
            request_timeout=request_timeout,
            **params,
        )

    def _get_lc_class(self):
        try:
            from langchain_community.embeddings import CohereEmbeddings
        except ImportError:
            from langchain.embeddings import CohereEmbeddings

        return CohereEmbeddings


class LCHuggingFaceEmbeddings(LCEmbeddingMixin, BaseEmbeddings):
    """Wrapper around Langchain's HuggingFace embedding, focusing on key parameters"""

    def __init__(
        self,
        model_name: str = "sentence-transformers/all-mpnet-base-v2",
        **params,
    ):
        super().__init__(
            model_name=model_name,
            **params,
        )

    def _get_lc_class(self):
        try:
            from langchain_community.embeddings import HuggingFaceBgeEmbeddings
        except ImportError:
            from langchain.embeddings import HuggingFaceBgeEmbeddings

        return HuggingFaceBgeEmbeddings
