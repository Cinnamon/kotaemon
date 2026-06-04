"""Vectorstore vendor registry and factory.

Usage::

    from kotaemon.storages.vectorstores.factory import (
        VectorStoreFactory,
        VectorStoreVendor,
    )

    cls = VectorStoreFactory.get_cls(VectorStoreVendor.CHROMA)
    store = cls(path="/data/vectorstore", collection_name="default")
"""

from __future__ import annotations

from enum import Enum

from .base import BaseVectorStore
from .chroma import ChromaVectorStore
from .in_memory import InMemoryVectorStore
from .lancedb import LanceDBVectorStore
from .milvus import MilvusVectorStore
from .qdrant import QdrantVectorStore
from .simple_file import SimpleFileVectorStore


class VectorStoreVendor(str, Enum):
    """Supported vectorstore back-ends."""

    CHROMA = "ChromaVectorStore"
    LANCEDB = "LanceDBVectorStore"
    IN_MEMORY = "InMemoryVectorStore"
    MILVUS = "MilvusVectorStore"
    QDRANT = "QdrantVectorStore"
    SIMPLE_FILE = "SimpleFileVectorStore"


MP_VENDOR_CLS: dict[VectorStoreVendor, type[BaseVectorStore]] = {
    VectorStoreVendor.CHROMA: ChromaVectorStore,
    VectorStoreVendor.LANCEDB: LanceDBVectorStore,
    VectorStoreVendor.IN_MEMORY: InMemoryVectorStore,
    VectorStoreVendor.MILVUS: MilvusVectorStore,
    VectorStoreVendor.QDRANT: QdrantVectorStore,
    VectorStoreVendor.SIMPLE_FILE: SimpleFileVectorStore,
}


class VectorStoreFactory:
    """Resolve a :class:`VectorStoreVendor` to its implementation class."""

    @staticmethod
    def get_cls(
        vendor: VectorStoreVendor | str,
    ) -> type[BaseVectorStore]:
        """Return the class for *vendor*, coercing bare strings.

        Args:
            vendor: A :class:`VectorStoreVendor` value or a plain string
                matching one (e.g. ``"ChromaVectorStore"``).

        Returns:
            The concrete :class:`BaseVectorStore` subclass.

        Raises:
            ValueError: When *vendor* does not match any registered class.
        """
        key = VectorStoreVendor(vendor)
        if key not in MP_VENDOR_CLS:
            raise ValueError(f"Invalid vectorstore vendor: {vendor!r}")
        return MP_VENDOR_CLS[key]

    @staticmethod
    def supported_vendors() -> list[VectorStoreVendor]:
        """Return all registered vectorstore vendors."""
        return list(MP_VENDOR_CLS.keys())
