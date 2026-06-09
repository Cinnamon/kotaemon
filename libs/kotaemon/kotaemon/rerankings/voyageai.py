from __future__ import annotations

import importlib
from dataclasses import dataclass, field

from decouple import config

from kotaemon.base import Document

from .base import BaseReranking

vo = None


def _import_voyageai():
    global vo
    if not vo:
        vo = importlib.import_module("voyageai")
    return vo


@dataclass(kw_only=True)
class VoyageAIReranking(BaseReranking):
    """VoyageAI Reranking model"""

    model_name: str = field(
        default="rerank-2",
        metadata={"description": "Rerank model ID"},
    )
    api_key: str = field(
        default_factory=lambda: config("VOYAGE_API_KEY", ""),
        metadata={"description": "VoyageAI API key"},
    )

    def __post_init__(self) -> None:
        if not self.api_key:
            raise ValueError("API key must be provided for VoyageAIReranking.")
        self._client = _import_voyageai().Client(api_key=self.api_key)
        self._aclient = _import_voyageai().AsyncClient(api_key=self.api_key)

    def run(self, documents: list[Document], query: str) -> list[Document]:
        compressed_docs: list[Document] = []
        if not documents:
            return compressed_docs

        _docs = [d.content for d in documents]
        response = self._client.rerank(
            model=self.model_name, query=query, documents=_docs
        )
        for r in response.results:
            doc = documents[r.index]
            doc.metadata["reranking_score"] = r.relevance_score
            compressed_docs.append(doc)

        return compressed_docs
