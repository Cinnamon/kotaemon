from kotaemon.indices.indexing import BaseIndexing
from kotaemon.indices.retriever import BaseRetriever

# Legacy aliases kept for backward compatibility
BaseFileIndexIndexing = BaseIndexing
BaseFileIndexRetriever = BaseRetriever

__all__ = [
    "BaseIndexing",
    "BaseRetriever",
    "BaseFileIndexIndexing",
    "BaseFileIndexRetriever",
]
