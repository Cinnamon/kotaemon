"""Docstore vendor registry and factory.

Usage::

    from kotaemon.storages.docstores.factory import (
        DocStoreFactory,
        DocStoreVendor,
    )

    cls = DocStoreFactory.get_cls(DocStoreVendor.LANCEDB)
    store = cls(path="/data/docstore", collection_name="default")
"""

from __future__ import annotations

from enum import Enum

from .base import BaseDocumentStore
from .elasticsearch import ElasticsearchDocumentStore
from .in_memory import InMemoryDocumentStore
from .lancedb import LanceDBDocumentStore
from .simple_file import SimpleFileDocumentStore


class DocStoreVendor(str, Enum):
    """Supported docstore back-ends."""

    LANCEDB = "LanceDBDocumentStore"
    ELASTICSEARCH = "ElasticsearchDocumentStore"
    IN_MEMORY = "InMemoryDocumentStore"
    SIMPLE_FILE = "SimpleFileDocumentStore"


MP_VENDOR_CLS: dict[DocStoreVendor, type[BaseDocumentStore]] = {
    DocStoreVendor.LANCEDB: LanceDBDocumentStore,
    DocStoreVendor.ELASTICSEARCH: ElasticsearchDocumentStore,
    DocStoreVendor.IN_MEMORY: InMemoryDocumentStore,
    DocStoreVendor.SIMPLE_FILE: SimpleFileDocumentStore,
}


class DocStoreFactory:
    """Resolve a :class:`DocStoreVendor` to its implementation class."""

    @staticmethod
    def get_cls(
        vendor: DocStoreVendor | str,
    ) -> type[BaseDocumentStore]:
        """Return the class for *vendor*, coercing bare strings.

        Args:
            vendor: A :class:`DocStoreVendor` value or a plain string
                matching one (e.g. ``"LanceDBDocumentStore"``).

        Returns:
            The concrete :class:`BaseDocumentStore` subclass.

        Raises:
            ValueError: When *vendor* does not match any registered class.
        """
        key = DocStoreVendor(vendor)
        if key not in MP_VENDOR_CLS:
            raise ValueError(f"Invalid docstore vendor: {vendor!r}")
        return MP_VENDOR_CLS[key]

    @staticmethod
    def supported_vendors() -> list[DocStoreVendor]:
        """Return all registered docstore vendors."""
        return list(MP_VENDOR_CLS.keys())
