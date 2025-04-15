from typing import Optional

from kotaemon.base import DocumentWithEmbedding, Param

from .base import BaseEmbeddings


class LCEmbeddingMixin:
    def _get_lc_class(self):
        raise NotImplementedError(
            "Please return the relevant Langchain class in in _get_lc_class"
        )

    def __init__(self, **params):
        self._lc_class = self._get_lc_class()
        self._obj = self._lc_class(**params)
        self._kwargs: dict = params

        super().__init__()

    def run(self, text):
        input_docs = self.prepare_input(text)
        input_ = [doc.text for doc in input_docs]

        embeddings = self._obj.embed_documents(input_)

        return [
            DocumentWithEmbedding(content=doc, embedding=each_embedding)
            for doc, each_embedding in zip(input_docs, embeddings)
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

    cohere_api_key: str = Param(
        help="API key (https://dashboard.cohere.com/api-keys)",
        default=None,
        required=True,
    )
    model: str = Param(
        help="Model name to use (https://docs.cohere.com/docs/models)",
        default=None,
        required=True,
    )
    user_agent: str = Param(
        help="User agent (leave default)", default="default", required=True
    )

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
            from langchain_cohere import CohereEmbeddings
        except ImportError:
            from langchain.embeddings import CohereEmbeddings

        return CohereEmbeddings


class LCHuggingFaceEmbeddings(LCEmbeddingMixin, BaseEmbeddings):
    """Wrapper around Langchain's HuggingFace embedding, focusing on key parameters"""

    model_name: str = Param(
        help=(
            "Model name to use (https://huggingface.co/models?"
            "pipeline_tag=sentence-similarity&sort=trending)"
        ),
        default=None,
        required=True,
    )

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


class LCGoogleEmbeddings(LCEmbeddingMixin, BaseEmbeddings):
    """Wrapper around Langchain's Google GenAI embedding, focusing on key parameters"""

    google_api_key: str = Param(
        help="API key (https://aistudio.google.com/app/apikey)",
        default=None,
        required=True,
    )
    model: str = Param(
        help="Model name to use (https://ai.google.dev/gemini-api/docs/models/gemini#text-embedding-and-embedding)",  # noqa
        default="models/text-embedding-004",
        required=True,
    )

    def __init__(
        self,
        model: str = "models/text-embedding-004",
        google_api_key: Optional[str] = None,
        **params,
    ):
        super().__init__(
            model=model,
            google_api_key=google_api_key,
            **params,
        )

    def _get_lc_class(self):
        try:
            from langchain_google_genai import GoogleGenerativeAIEmbeddings
        except ImportError:
            raise ImportError("Please install langchain-google-genai")

        return GoogleGenerativeAIEmbeddings


class LCMistralEmbeddings(LCEmbeddingMixin, BaseEmbeddings):
    """Wrapper around LangChain's MistralAI embedding, focusing on key parameters"""

    api_key: str = Param(
        help="API key (https://console.mistral.ai/api-keys)",
        default=None,
        required=True,
    )
    model: str = Param(
        help="Model name to use ('mistral-embed')",
        default="mistral-embed",
        required=True,
    )

    def __init__(
        self,
        model: str = "mistral-embed",
        api_key: Optional[str] = None,
        **params,
    ):
        super().__init__(
            model=model,
            api_key=api_key,
            **params,
        )

    def _get_lc_class(self):
        try:
            from langchain_mistralai import MistralAIEmbeddings
        except ImportError:
            raise ImportError(
                "Please install langchain_mistralai: "
                "`pip install -U langchain_mistralai`"
            )
        return MistralAIEmbeddings
