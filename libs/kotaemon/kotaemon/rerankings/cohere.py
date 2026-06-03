from __future__ import annotations

import os
from dataclasses import dataclass, field

from decouple import config

from kotaemon.base import Document

from .base import BaseReranking


@dataclass(kw_only=True)
class CohereReranking(BaseReranking):
    """Cohere Reranking model"""

    model_name: str = field(
        default="rerank-v4.0-fast",
        metadata={"description": "Cohere rerank model ID"},
    )
    cohere_api_key: str = field(
        default_factory=lambda: config("COHERE_API_KEY", ""),
        metadata={"description": "Cohere API key"},
    )
    base_url: str | None = field(
        default=None,
        metadata={"description": "Rerank API base url"},
    )

    def run(self, documents: list[Document], query: str) -> list[Document]:
        try:
            import cohere
        except ImportError:
            raise ImportError(
                "Please install Cohere `pip install cohere` to use Cohere Reranking"
            )

        if not self.cohere_api_key or "COHERE_API_KEY" in self.cohere_api_key:
            print("Cohere API key not found. Skipping rerankings.")
            return documents

        cohere_client = cohere.Client(
            self.cohere_api_key, base_url=self.base_url or os.getenv("CO_API_URL")
        )
        compressed_docs: list[Document] = []

        if not documents:
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
