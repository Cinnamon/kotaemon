from __future__ import annotations

import importlib
from typing import Optional

from decouple import config

from kotaemon.base import Document, Param

from .base import BaseReranking

vo = None


def _import_voyageai():
    global vo
    if not vo:
        vo = importlib.import_module("voyageai")
    return vo


class VoyageAIReranking(BaseReranking):
    """VoyageAI Reranking model.

    Supports all VoyageAI reranker models including:
    - rerank-2.5: Latest flagship model with instruction-following (recommended)
    - rerank-2.5-lite: Cost-effective version with instruction-following
    - rerank-2: Previous generation model
    - rerank-2-lite: Previous generation lite model
    """

    model_name: str = Param(
        "rerank-2.5",
        help=(
            "ID of the model to use. Recommended: rerank-2.5 (best quality) or "
            "rerank-2.5-lite (cost-effective). See [Supported Models]"
            "(https://docs.voyageai.com/docs/reranker) for all options."
        ),
        required=True,
    )
    api_key: str = Param(
        config("VOYAGE_API_KEY", ""),
        help="VoyageAI API key",
        required=True,
    )
    top_k: Optional[int] = Param(
        None,
        help="Number of top documents to return. If None, returns all documents.",
    )
    truncation: bool = Param(
        True,
        help="Whether to truncate documents that exceed the model's context length.",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.api_key:
            raise ValueError("API key must be provided for VoyageAIReranking.")

        self._client = _import_voyageai().Client(api_key=self.api_key)
        self._aclient = _import_voyageai().AsyncClient(api_key=self.api_key)

    def run(self, documents: list[Document], query: str) -> list[Document]:
        """Use VoyageAI Reranker model to re-order documents
        with their relevance score"""
        compressed_docs: list[Document] = []

        if not documents:  # to avoid empty api call
            return compressed_docs

        _docs = [d.content for d in documents]

        # Build rerank kwargs
        rerank_kwargs = {
            "model": self.model_name,
            "query": query,
            "documents": _docs,
            "truncation": self.truncation,
        }
        if self.top_k is not None:
            rerank_kwargs["top_k"] = self.top_k

        response = self._client.rerank(**rerank_kwargs)
        for r in response.results:
            doc = documents[r.index]
            doc.metadata["reranking_score"] = r.relevance_score
            compressed_docs.append(doc)

        return compressed_docs

    async def arun(self, documents: list[Document], query: str) -> list[Document]:
        """Async version of reranking."""
        compressed_docs: list[Document] = []

        if not documents:
            return compressed_docs

        _docs = [d.content for d in documents]

        rerank_kwargs = {
            "model": self.model_name,
            "query": query,
            "documents": _docs,
            "truncation": self.truncation,
        }
        if self.top_k is not None:
            rerank_kwargs["top_k"] = self.top_k

        response = await self._aclient.rerank(**rerank_kwargs)
        for r in response.results:
            doc = documents[r.index]
            doc.metadata["reranking_score"] = r.relevance_score
            compressed_docs.append(doc)

        return compressed_docs
