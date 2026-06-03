import requests
from dataclasses import dataclass, field

from kotaemon.base import Document, DocumentWithEmbedding

from .base import BaseEmbeddings


@dataclass(kw_only=True)
class EndpointEmbeddings(BaseEmbeddings):
    """Embeddings via an OpenAI API compatible HTTP endpoint."""

    endpoint_url: str = field(
        metadata={"description": "OpenAI-compatible embeddings endpoint URL"},
    )

    def invoke(
        self, text: str | list[str] | Document | list[Document], *args, **kwargs
    ) -> list[DocumentWithEmbedding]:
        if not isinstance(text, list):
            text = [text]
        outputs: list[DocumentWithEmbedding] = []
        for item in text:
            response = requests.post(
                self.endpoint_url, json={"input": str(item)}
            ).json()
            outputs.append(
                DocumentWithEmbedding(
                    text=str(item),
                    embedding=response["data"][0]["embedding"],
                    total_tokens=response["usage"]["total_tokens"],
                    prompt_tokens=response["usage"]["prompt_tokens"],
                )
            )
        return outputs

    def run(
        self, text: str | list[str] | Document | list[Document]
    ) -> list[DocumentWithEmbedding]:
        return self.invoke(text)
