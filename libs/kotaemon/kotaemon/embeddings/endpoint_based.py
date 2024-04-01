import requests

from kotaemon.base import Document, DocumentWithEmbedding

from .base import BaseEmbeddings


class EndpointEmbeddings(BaseEmbeddings):
    """
    An Embeddings component that uses an OpenAI API compatible endpoint.

    Attributes:
        endpoint_url (str): The url of an OpenAI API compatible endpoint.
    """

    endpoint_url: str

    def run(
        self, text: str | list[str] | Document | list[Document]
    ) -> list[DocumentWithEmbedding]:
        """
        Generate embeddings from text Args:
            text (str | list[str] | Document | list[Document]): text to generate
            embeddings from
        Returns:
            list[DocumentWithEmbedding]: embeddings
        """
        if not isinstance(text, list):
            text = [text]

        outputs = []

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
