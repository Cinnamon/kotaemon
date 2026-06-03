from __future__ import annotations

from dataclasses import dataclass, field

import aiohttp
import requests

from kotaemon.base import Document, DocumentWithEmbedding

from .base import BaseEmbeddings

session = requests.session()


@dataclass(kw_only=True)
class TeiEndpointEmbeddings(BaseEmbeddings):
    """Embeddings via a TEI API compatible endpoint."""

    endpoint_url: str = field(
        default="",
        metadata={"description": "TEI embedding service api base URL"},
    )
    normalize: bool = field(
        default=True,
        metadata={"description": "Normalize embeddings to unit length"},
    )
    truncate: bool = field(
        default=True,
        metadata={"description": "Truncate embeddings to a fixed length"},
    )

    async def client_(self, inputs: list[str]):
        async with aiohttp.ClientSession() as http_session:
            async with http_session.post(
                url=self.endpoint_url,
                json={
                    "inputs": inputs,
                    "normalize": self.normalize,
                    "truncate": self.truncate,
                },
            ) as resp:
                return await resp.json()

    async def ainvoke(
        self, text: str | list[str] | Document | list[Document], *args, **kwargs
    ) -> list[DocumentWithEmbedding]:
        if not isinstance(text, list):
            text = [text]
        text = self.prepare_input(text)

        outputs: list[DocumentWithEmbedding] = []
        batch_size = 6
        num_batch = max(len(text) // batch_size, 1)
        for i in range(num_batch):
            if i == num_batch - 1:
                mini_batch = text[batch_size * i :]
            else:
                mini_batch = text[batch_size * i : batch_size * (i + 1)]
            mini_batch = [x.content for x in mini_batch]
            embeddings = await self.client_(mini_batch)  # type: ignore
            outputs.extend(
                [
                    DocumentWithEmbedding(content=doc, embedding=embedding)
                    for doc, embedding in zip(mini_batch, embeddings)
                ]
            )
        return outputs

    def invoke(
        self, text: str | list[str] | Document | list[Document], *args, **kwargs
    ) -> list[DocumentWithEmbedding]:
        if not isinstance(text, list):
            text = [text]
        text = self.prepare_input(text)

        outputs: list[DocumentWithEmbedding] = []
        batch_size = 6
        num_batch = max(len(text) // batch_size, 1)
        for i in range(num_batch):
            if i == num_batch - 1:
                mini_batch = text[batch_size * i :]
            else:
                mini_batch = text[batch_size * i : batch_size * (i + 1)]
            mini_batch = [x.content for x in mini_batch]
            embeddings = session.post(
                url=self.endpoint_url,
                json={
                    "inputs": mini_batch,
                    "normalize": self.normalize,
                    "truncate": self.truncate,
                },
            ).json()
            outputs.extend(
                [
                    DocumentWithEmbedding(content=doc, embedding=embedding)
                    for doc, embedding in zip(mini_batch, embeddings)
                ]
            )
        return outputs
