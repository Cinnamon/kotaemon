from __future__ import annotations

from dataclasses import dataclass, field

import requests

from kotaemon.base import Document

from .base import BaseReranking

session = requests.session()


@dataclass(kw_only=True)
class TeiFastReranking(BaseReranking):
    """TEI (Text Embeddings Inference) reranking model."""

    endpoint_url: str = field(
        metadata={"description": "TEI reranking service api base URL"},
    )
    model_name: str | None = field(
        default=None,
        metadata={"description": "Model ID (optional)"},
    )
    is_truncated: bool = field(
        default=True,
        metadata={"description": "Whether to truncate inputs"},
    )
    max_tokens: int = field(
        default=512,
        metadata={"description": "Max tokens when truncating"},
    )

    def client(self, query: str, texts: list[str]):
        truncated_texts = texts
        if self.is_truncated:
            truncated_texts = [text[: self.max_tokens] for text in texts]

        return session.post(
            url=self.endpoint_url,
            json={
                "query": query,
                "texts": truncated_texts,
                "is_truncated": self.is_truncated,
            },
        ).json()

    def run(self, documents: list[Document], query: str) -> list[Document]:
        if not self.endpoint_url:
            print("TEI API reranking URL not found. Skipping rerankings.")
            return documents

        compressed_docs: list[Document] = []
        if not documents:
            return compressed_docs

        if isinstance(documents[0], str):
            documents = self.prepare_input(documents)

        batch_size = 6
        num_batch = max(len(documents) // batch_size, 1)
        for i in range(num_batch):
            if i == num_batch - 1:
                mini_batch = documents[batch_size * i :]
            else:
                mini_batch = documents[batch_size * i : batch_size * (i + 1)]

            _docs = [d.content for d in mini_batch]
            rerank_resp = self.client(query, _docs)
            for r in rerank_resp:
                doc = mini_batch[r["index"]]
                doc.metadata["reranking_score"] = r["score"]
                compressed_docs.append(doc)

        return sorted(
            compressed_docs,
            key=lambda x: x.metadata["reranking_score"],
            reverse=True,
        )
