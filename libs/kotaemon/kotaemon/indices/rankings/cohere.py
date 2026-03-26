from __future__ import annotations

import logging

from decouple import config

from kotaemon.base import Document

from .base import BaseReranking

logger = logging.getLogger(__name__)


class CohereReranking(BaseReranking):
    model_name: str = "rerank-v4.0-fast"
    cohere_api_key: str = config("COHERE_API_KEY", "")
    use_key_from_ktem: bool = False

    def run(self, documents: list[Document], query: str) -> list[Document]:
        """Use Cohere Reranker model to re-order documents
        with their relevance score"""
        try:
            import cohere
        except ImportError:
            raise ImportError(
                "Please install Cohere `pip install cohere` to use Cohere Reranking"
            )

        # try to get COHERE_API_KEY from embeddings
        if not self.cohere_api_key and self.use_key_from_ktem:
            try:
                from ktem.embeddings.manager import (
                    embedding_models_manager as embeddings,
                )

                cohere_model = embeddings.get("cohere")
                ktem_cohere_api_key = cohere_model._kwargs.get(  # type: ignore
                    "cohere_api_key"
                )
                if ktem_cohere_api_key != "your-key":
                    self.cohere_api_key = ktem_cohere_api_key
            except Exception as e:
                logger.warning("Cannot get Cohere API key from ktem: %s", e)

        if not self.cohere_api_key:
            logger.warning("Cohere API key not found. Skipping rerankings.")
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
