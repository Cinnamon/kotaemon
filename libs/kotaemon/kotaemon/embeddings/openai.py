from dataclasses import dataclass, field
from itertools import islice
from typing import Optional

import numpy as np
import openai
import tiktoken
from tenacity import (
    retry,
    retry_if_not_exception_type,
    stop_after_attempt,
    wait_random_exponential,
)

from .base import BaseEmbeddings, Document, DocumentWithEmbedding


def split_text_by_chunk_size(text: str, chunk_size: int) -> list[list[int]]:
    """Split the text into chunks of a given size

    Args:
        text: text to split
        chunk_size: size of each chunk

    Returns:
        list of chunks (as tokens)
    """
    encoding = tiktoken.get_encoding("cl100k_base")
    tokens = iter(encoding.encode(text))
    result = []
    while chunk := list(islice(tokens, chunk_size)):
        result.append(chunk)
    return result


@dataclass(kw_only=True)
class BaseOpenAIEmbeddings(BaseEmbeddings):
    """Base interface for OpenAI embedding model, using the openai library.

    This class exposes the parameters in resources.Chat. To subclass this class:

        - Implement the `prepare_client` method to return the OpenAI client
        - Implement the `openai_response` method to return the OpenAI response
        - Implement the params relate to the OpenAI client
    """

    _dependencies = ["openai"]

    api_key: str = field(metadata={"description": "API key"})
    timeout: Optional[float] = field(
        default=None, metadata={"description": "Timeout for the API request."}
    )
    max_retries: Optional[int] = field(
        default=None,
        metadata={"description": "Maximum number of retries for the API request."},
    )
    dimensions: Optional[int] = field(
        default=None,
        metadata={
            "description": (
                "Output embedding dimensions (text-embedding-3 and later)."
            )
        },
    )
    context_length: Optional[int] = field(
        default=None,
        metadata={"description": "Maximum context length of the embedding model"},
    )

    @property
    def max_retries_(self) -> int:
        if self.max_retries is None:
            from openai._constants import DEFAULT_MAX_RETRIES

            return DEFAULT_MAX_RETRIES
        return self.max_retries

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
        self, text: str | list[str] | Document | list[Document], *args, **kwargs
    ) -> list[DocumentWithEmbedding]:
        input_doc = self.prepare_input(text)
        client = self.prepare_client(async_version=False)

        input_: list[str | list[int]] = []
        splitted_indices = {}
        for idx, text in enumerate(input_doc):
            if self.context_length:
                chunks = split_text_by_chunk_size(text.text or " ", self.context_length)
                splitted_indices[idx] = (len(input_), len(input_) + len(chunks))
                input_.extend(chunks)
            else:
                splitted_indices[idx] = (len(input_), len(input_) + 1)
                input_.append(text.text)

        resp = self.openai_response(client, input=input_, **kwargs).dict()
        output_ = list(sorted(resp["data"], key=lambda x: x["index"]))

        output = []
        for idx, doc in enumerate(input_doc):
            embs = output_[splitted_indices[idx][0] : splitted_indices[idx][1]]
            if len(embs) == 1:
                output.append(
                    DocumentWithEmbedding(embedding=embs[0]["embedding"], content=doc)
                )
                continue

            chunk_lens = [
                len(_)
                for _ in input_[splitted_indices[idx][0] : splitted_indices[idx][1]]
            ]
            vs: list[list[float]] = [_["embedding"] for _ in embs]
            emb = np.average(vs, axis=0, weights=chunk_lens)
            emb = emb / np.linalg.norm(emb)
            output.append(DocumentWithEmbedding(embedding=emb.tolist(), content=doc))

        return output

    async def ainvoke(
        self, text: str | list[str] | Document | list[Document], *args, **kwargs
    ) -> list[DocumentWithEmbedding]:
        input_ = self.prepare_input(text)
        client = self.prepare_client(async_version=True)
        resp = await self.openai_response(
            client, input=[_.text if _.text else " " for _ in input_], **kwargs
        ).dict()
        output_ = sorted(resp["data"], key=lambda x: x["index"])
        return [
            DocumentWithEmbedding(embedding=o["embedding"], content=i)
            for i, o in zip(input_, output_)
        ]


@dataclass(kw_only=True)
class OpenAIEmbeddings(BaseOpenAIEmbeddings):
    """OpenAI chat model"""

    model: str = field(
        metadata={
            "description": (
                "Model ID (see platform.openai.com/docs/models/overview)."
            )
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

    @retry(
        retry=retry_if_not_exception_type(
            (openai.NotFoundError, openai.BadRequestError)
        ),
        wait=wait_random_exponential(min=1, max=40),
        stop=stop_after_attempt(6),
    )
    def openai_response(self, client, **kwargs):
        """Get the openai response"""
        params: dict = {
            "model": self.model,
        }
        if self.dimensions:
            params["dimensions"] = self.dimensions
        params.update(kwargs)

        return client.embeddings.create(**params)


@dataclass(kw_only=True)
class AzureOpenAIEmbeddings(BaseOpenAIEmbeddings):
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

    @retry(
        retry=retry_if_not_exception_type(
            (openai.NotFoundError, openai.BadRequestError)
        ),
        wait=wait_random_exponential(min=1, max=40),
        stop=stop_after_attempt(6),
    )
    def openai_response(self, client, **kwargs):
        """Get the openai response"""
        params: dict = {
            "model": self.azure_deployment,
        }
        if self.dimensions:
            params["dimensions"] = self.dimensions
        params.update(kwargs)

        return client.embeddings.create(**params)
