from __future__ import annotations

from decouple import config

from kotaemon.base import Document

from .base import BaseReranking


class CohereReranking(BaseReranking):
    model_name: str = "rerank-multilingual-v2.0"
    cohere_api_key: str = config("COHERE_API_KEY", "")

    def run(self, documents: list[Document], query: str) -> list[Document]:
        """Use Cohere Reranker model to re-order documents
        with their relevance score"""
        try:
            import cohere
        except ImportError:
            raise ImportError(
                "Please install Cohere " "`pip install cohere` to use Cohere Reranking"
            )

        if not self.cohere_api_key:
            print("Cohere API key not found. Skipping reranking.")
            return documents

        cohere_client = cohere.Client(self.cohere_api_key)
        compressed_docs: list[Document] = []

        if not documents:  # to avoid empty api call
            return compressed_docs

        _docs = [d.content for d in documents]
        response = cohere_client.rerank(
            model=self.model_name, query=query, documents=_docs
        )
        print("Cohere score", [r.relevance_score for r in response.results])
        for r in response.results:
            doc = documents[r.index]
            doc.metadata["cohere_reranking_score"] = r.relevance_score
            compressed_docs.append(doc)

        return compressed_docs
