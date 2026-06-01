# Backward compatibility shim — import from new locations instead.
from .indexing.impl.rag import IndexDocumentPipeline
from .retriever.base import BaseRetriever
from .retriever.impl.rag import DocumentRetrievalPipeline
from kotaemon.indices.indexing.impl.rag import IndexPipeline

__all__ = [
    "BaseRetriever",
    "DocumentRetrievalPipeline",
    "IndexDocumentPipeline",
    "IndexPipeline",
]
