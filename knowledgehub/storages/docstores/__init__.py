from .base import BaseDocumentStore
from .elasticsearch import ElasticsearchDocumentStore
from .in_memory import InMemoryDocumentStore

__all__ = ["BaseDocumentStore", "InMemoryDocumentStore", "ElasticsearchDocumentStore"]
