from __future__ import annotations

import importlib
from typing import Optional

from decouple import config

from kotaemon.base import Document, Param

from .base import BaseReranking

vo = None

# Source: https://docs.voyageai.com/docs/reranker
VOYAGE_RERANK_MODELS = (
    "rerank-3",
    "rerank-3-lite",
    "rerank-2.5",
    "rerank-2.5-lite",
    "rerank-2",
    "rerank-2-lite",
    "rerank-1",
    "rerank-lite-1",
)


def _import_voyageai():
    global vo
    if not vo:
        vo = importlib.import_module("voyageai")
    return vo


class VoyageAIReranking(BaseReranking):
    """Voyage AI by MongoDB Reranking model"""

    model_name: str = Param(
        "rerank-3",
        help=(
            "ID of the model to use: "
            + ", ".join(VOYAGE_RERANK_MODELS)
            + ". You can go to [Supported Models]"
            "(https://docs.voyageai.com/docs/reranker) to see the supported models"
        ),
        required=True,
    )
    api_key: str = Param(
        config("VOYAGE_API_KEY", ""),
        help="Voyage API key",
        required=True,
    )
    top_k: Optional[int] = Param(
        None,
        help="Number of most relevant documents to return. Default: all documents.",
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.api_key:
            raise ValueError("API key must be provided for VoyageAIReranking.")
        if self.model_name not in VOYAGE_RERANK_MODELS:
            raise ValueError(
                f"Unknown Voyage rerank model {self.model_name!r}. "
                f"Supported models: {', '.join(VOYAGE_RERANK_MODELS)}."
            )

        self._client = _import_voyageai().Client(api_key=self.api_key)
        self._aclient = _import_voyageai().AsyncClient(api_key=self.api_key)

    def run(self, documents: list[Document], query: str) -> list[Document]:
        """Use Voyage AI Reranker model to re-order documents
        with their relevance score"""
        compressed_docs: list[Document] = []

        if not documents:  # to avoid empty api call
            return compressed_docs

        _docs = [d.content for d in documents]
        kwargs: dict = {}
        if self.top_k is not None:
            kwargs["top_k"] = self.top_k
        response = self._client.rerank(
            model=self.model_name, query=query, documents=_docs, **kwargs
        )
        for r in response.results:
            doc = documents[r.index]
            doc.metadata["reranking_score"] = r.relevance_score
            compressed_docs.append(doc)

        return compressed_docs
