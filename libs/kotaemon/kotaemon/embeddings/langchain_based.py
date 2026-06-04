from __future__ import annotations

from dataclasses import dataclass, field
from functools import cached_property
from typing import Any

from kotaemon.base import Document, DocumentWithEmbedding

from .base import BaseEmbeddings


@dataclass(kw_only=True)
class BaseLCEmbeddings(BaseEmbeddings):
    """Base wrapper for LangChain embedding models."""

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

    def invoke(
        self,
        text: str | list[str] | Document | list[Document],
        *args,
        **kwargs,
    ) -> list[DocumentWithEmbedding]:
        input_docs = self.prepare_input(text)
        input_ = [doc.text for doc in input_docs]
        embeddings = self._lc_obj.embed_documents(input_)
        return [
            DocumentWithEmbedding(content=doc, embedding=each_embedding)
            for doc, each_embedding in zip(input_docs, embeddings)
        ]

    def run(
        self,
        text: str | list[str] | Document | list[Document],
        *args,
        **kwargs,
    ) -> list[DocumentWithEmbedding]:
        return self.invoke(text, *args, **kwargs)


@dataclass(kw_only=True)
class LCOpenAIEmbeddings(BaseLCEmbeddings):
    """Wrapper around LangChain's OpenAI embedding model."""

    model: str = field(
        default="text-embedding-ada-002",
        metadata={"description": "Model name."},
    )
    openai_api_version: str | None = field(
        default=None, metadata={"description": "OpenAI API version."}
    )
    openai_api_base: str | None = field(
        default=None, metadata={"description": "OpenAI API base URL."}
    )
    openai_api_type: str | None = field(
        default=None, metadata={"description": "OpenAI API type."}
    )
    openai_api_key: str | None = field(
        default=None, metadata={"description": "OpenAI API key."}
    )
    request_timeout: float | None = field(
        default=None, metadata={"description": "Request timeout in seconds."}
    )

    def _get_lc_class(self) -> type:
        try:
            from langchain_openai import OpenAIEmbeddings
        except ImportError:
            from langchain.embeddings import OpenAIEmbeddings

        return OpenAIEmbeddings

    def _lc_kwargs(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "openai_api_version": self.openai_api_version,
            "openai_api_base": self.openai_api_base,
            "openai_api_type": self.openai_api_type,
            "openai_api_key": self.openai_api_key,
            "request_timeout": self.request_timeout,
        }


@dataclass(kw_only=True)
class LCAzureOpenAIEmbeddings(BaseLCEmbeddings):
    """Wrapper around LangChain's Azure OpenAI embedding model."""

    azure_endpoint: str | None = field(
        default=None, metadata={"description": "Azure OpenAI endpoint URL."}
    )
    deployment: str | None = field(
        default=None, metadata={"description": "Azure deployment name."}
    )
    openai_api_key: str | None = field(
        default=None, metadata={"description": "Azure OpenAI API key."}
    )
    api_version: str | None = field(
        default=None, metadata={"description": "Azure API version."}
    )
    request_timeout: float | None = field(
        default=None, metadata={"description": "Request timeout in seconds."}
    )

    def _get_lc_class(self) -> type:
        try:
            from langchain_openai import AzureOpenAIEmbeddings
        except ImportError:
            from langchain.embeddings import AzureOpenAIEmbeddings

        return AzureOpenAIEmbeddings

    def _lc_kwargs(self) -> dict[str, Any]:
        return {
            "azure_endpoint": self.azure_endpoint,
            "deployment": self.deployment,
            "api_version": self.api_version,
            "openai_api_key": self.openai_api_key,
            "request_timeout": self.request_timeout,
        }


@dataclass(kw_only=True)
class LCCohereEmbeddings(BaseLCEmbeddings):
    """Wrapper around LangChain's Cohere embedding model."""

    model: str = field(
        default="embed-english-v2.0",
        metadata={"description": "Model name."},
    )
    cohere_api_key: str | None = field(
        default=None, metadata={"description": "Cohere API key."}
    )
    truncate: str | None = field(
        default=None, metadata={"description": "Truncation mode."}
    )
    request_timeout: float | None = field(
        default=None, metadata={"description": "Request timeout in seconds."}
    )
    user_agent: str | None = field(
        default=None, metadata={"description": "HTTP user agent string."}
    )

    def _get_lc_class(self) -> type:
        try:
            from langchain_cohere import CohereEmbeddings
        except ImportError:
            from langchain.embeddings import CohereEmbeddings

        return CohereEmbeddings

    def _lc_kwargs(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "cohere_api_key": self.cohere_api_key,
            "truncate": self.truncate,
            "request_timeout": self.request_timeout,
            "user_agent": self.user_agent,
        }


@dataclass(kw_only=True)
class LCHuggingFaceEmbeddings(BaseLCEmbeddings):
    """Wrapper around LangChain's HuggingFace BGE embedding model."""

    model_name: str = field(
        default="sentence-transformers/all-mpnet-base-v2",
        metadata={"description": "HuggingFace model name."},
    )

    def _get_lc_class(self) -> type:
        try:
            from langchain_community.embeddings import HuggingFaceBgeEmbeddings
        except ImportError:
            from langchain.embeddings import HuggingFaceBgeEmbeddings

        return HuggingFaceBgeEmbeddings

    def _lc_kwargs(self) -> dict[str, Any]:
        return {"model_name": self.model_name}


@dataclass(kw_only=True)
class LCGoogleEmbeddings(BaseLCEmbeddings):
    """Wrapper around LangChain's Google GenAI embedding model."""

    model: str = field(
        default="models/text-embedding-004",
        metadata={"description": "Model name."},
    )
    google_api_key: str | None = field(
        default=None, metadata={"description": "Google API key."}
    )

    def _get_lc_class(self) -> type:
        try:
            from langchain_google_genai import GoogleGenerativeAIEmbeddings
        except ImportError as e:
            raise ImportError("Please install langchain-google-genai") from e

        return GoogleGenerativeAIEmbeddings

    def _lc_kwargs(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "google_api_key": self.google_api_key,
        }


@dataclass(kw_only=True)
class LCMistralEmbeddings(BaseLCEmbeddings):
    """Wrapper around LangChain's Mistral AI embedding model."""

    model: str = field(
        default="mistral-embed",
        metadata={"description": "Model name."},
    )
    api_key: str | None = field(
        default=None, metadata={"description": "Mistral API key."}
    )

    def _get_lc_class(self) -> type:
        try:
            from langchain_mistralai import MistralAIEmbeddings
        except ImportError as e:
            raise ImportError(
                "Please install langchain_mistralai: "
                "`pip install -U langchain_mistralai`"
            ) from e

        return MistralAIEmbeddings

    def _lc_kwargs(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "api_key": self.api_key,
        }


# Backward-compatible alias for code that imported the old mixin name.
LCEmbeddingMixin = BaseLCEmbeddings
