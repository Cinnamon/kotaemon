from .indexing.base import BaseIndexing
from .retriever.base import BaseRetriever

# Legacy aliases kept for backward compatibility
BaseFileIndexIndexing = BaseIndexing
BaseFileIndexRetriever = BaseRetriever

__all__ = [
    "BaseIndexing",
    "BaseRetriever",
    "BaseFileIndexIndexing",
    "BaseFileIndexRetriever",
]
