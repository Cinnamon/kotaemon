"""Implements embeddings from [Voyage AI](https://voyageai.com).
"""

import importlib

from kotaemon.base import Document, DocumentWithEmbedding, Param

from .base import BaseEmbeddings

vo = None


def _import_voyageai():
    global vo
    if not vo:
        vo = importlib.import_module("voyageai")
    return vo


def _format_output(texts: list[str], embeddings: list[list]):
    """Formats the output of all `.embed` calls.
    Args:
        texts: List of original documents
        embeddings: Embeddings corresponding to each document
    """
    return [
        DocumentWithEmbedding(content=text, embedding=embedding)
        for text, embedding in zip(texts, embeddings)
    ]


class VoyageAIEmbeddings(BaseEmbeddings):
    """Voyage AI provides best-in-class embedding models and rerankers."""

    api_key: str = Param(None, help="Voyage API key", required=False)
    model: str = Param(
        "voyage-3",
        help=(
            "Model name to use. The Voyage "
            "[documentation](https://docs.voyageai.com/docs/embeddings) "
            "provides a list of all available embedding models."
        ),
        required=True,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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
