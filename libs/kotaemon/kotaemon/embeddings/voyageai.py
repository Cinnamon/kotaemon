"""Implements embeddings from [Voyage AI](https://voyageai.com)."""

from __future__ import annotations

import importlib
from dataclasses import dataclass, field

from kotaemon.base import Document, DocumentWithEmbedding

from .base import BaseEmbeddings

vo = None


def _import_voyageai():
    global vo
    if not vo:
        vo = importlib.import_module("voyageai")
    return vo


def _format_output(texts: list[str], embeddings: list[list]):
    return [
        DocumentWithEmbedding(content=text, embedding=embedding)
        for text, embedding in zip(texts, embeddings)
    ]


@dataclass(kw_only=True)
class VoyageAIEmbeddings(BaseEmbeddings):
    """Voyage AI embedding models."""

    api_key: str | None = field(
        default=None, metadata={"description": "Voyage API key"}
    )
    model: str = field(
        default="voyage-3",
        metadata={"description": "Embedding model name"},
    )

    def __post_init__(self) -> None:
        if not self.api_key:
            raise ValueError("API key must be provided for VoyageAIEmbeddings.")
        self._client = _import_voyageai().Client(api_key=self.api_key)
        self._aclient = _import_voyageai().AsyncClient(api_key=self.api_key)

    def invoke(
        self, text: str | list[str] | Document | list[Document], *args, **kwargs
    ) -> list[DocumentWithEmbedding]:
        texts = [t.content for t in self.prepare_input(text)]
        embeddings = self._client.embed(texts, model=self.model).embeddings
        return _format_output(texts, embeddings)

    async def ainvoke(
        self, text: str | list[str] | Document | list[Document], *args, **kwargs
    ) -> list[DocumentWithEmbedding]:
        texts = [t.content for t in self.prepare_input(text)]
        embeddings = await self._aclient.embed(texts, model=self.model).embeddings
        return _format_output(texts, embeddings)
