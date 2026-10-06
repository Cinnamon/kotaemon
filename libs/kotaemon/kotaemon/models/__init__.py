"""Optional public local model adapters."""

from .local_bge import (
    EMBEDDING_MODEL_ID,
    RERANKER_MODEL_ID,
    BgeM3Embeddings,
    BgeM3Reranking,
    LocalModelMetadata,
    LocalModelPaths,
)

__all__ = [
    "EMBEDDING_MODEL_ID",
    "RERANKER_MODEL_ID",
    "BgeM3Embeddings",
    "BgeM3Reranking",
    "LocalModelMetadata",
    "LocalModelPaths",
]
