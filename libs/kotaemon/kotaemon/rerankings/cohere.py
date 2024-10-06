from __future__ import annotations

from decouple import config

from kotaemon.base import Document, Param

from .base import BaseReranking


class CohereReranking(BaseReranking):
    """Cohere Reranking model"""

    model_name: str = Param(
        "rerank-multilingual-v2.0",
        help=(
            "ID of the model to use. You can go to [Supported Models]"
            "(https://docs.cohere.com/docs/rerank-2) to see the supported models"
        ),
        required=True,
    )
    cohere_api_key: str = Param(
        config("COHERE_API_KEY", ""),
        help="Cohere API key",
        required=True,
    )

    def run(self, documents: list[Document], query: str) -> list[Document]:
        """Use Cohere Reranker model to re-order documents
        with their relevance score"""
        try:
            import cohere
        except ImportError:
            raise ImportError(
                "Please install Cohere " "`pip install cohere` to use Cohere Reranking"
            )

        if not self.cohere_api_key or "COHERE_API_KEY" in self.cohere_api_key:
            print("Cohere API key not found. Skipping rerankings.")
            return documents

        cohere_client = cohere.Client(self.cohere_api_key)
        compressed_docs: list[Document] = []

        if not documents:  # to avoid empty api call
            return compressed_docs

        _docs = [d.content for d in documents]
        response = cohere_client.rerank(
            model=self.model_name, query=query, documents=_docs
        )
        for r in response.results:
            doc = documents[r.index]
            doc.metadata["reranking_score"] = r.relevance_score
            compressed_docs.append(doc)

        return compressed_docs
