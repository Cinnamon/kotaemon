import aiohttp
import requests

from kotaemon.base import Document, DocumentWithEmbedding, Param

from .base import BaseEmbeddings

session = requests.session()


class TeiEndpointEmbeddings(BaseEmbeddings):
    """An Embeddings component that uses an
    TEI (Text-Embedding-Inference) API compatible endpoint.

    Ref: https://github.com/huggingface/text-embeddings-inference

    Attributes:
        endpoint_url (str): The url of an TEI
            (Text-Embedding-Inference) API compatible endpoint.
        normalize (bool): Whether to normalize embeddings to unit length.
        truncate (bool): Whether to truncate embeddings
            to a fixed/default length.
    """

    endpoint_url: str = Param(None, help="TEI embedding service api base URL")
    normalize: bool = Param(
        True,
        help="Normalize embeddings to unit length",
    )
    truncate: bool = Param(
        True,
        help="Truncate embeddings to a fixed/default length",
    )

    async def client_(self, inputs: list[str]):
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url=self.endpoint_url,
                json={
                    "inputs": inputs,
                    "normalize": self.normalize,
                    "truncate": self.truncate,
                },
            ) as resp:
                embeddings = await resp.json()
        return embeddings

    async def ainvoke(
        self, text: str | list[str] | Document | list[Document], *args, **kwargs
    ) -> list[DocumentWithEmbedding]:
        if not isinstance(text, list):
            text = [text]
        text = self.prepare_input(text)

        outputs = []
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

        outputs = []
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
