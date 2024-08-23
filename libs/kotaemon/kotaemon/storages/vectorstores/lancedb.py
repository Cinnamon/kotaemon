from typing import Any, List, Type, cast

from llama_index.core.vector_stores.types import MetadataFilters
from llama_index.vector_stores.lancedb import LanceDBVectorStore as LILanceDBVectorStore
from llama_index.vector_stores.lancedb import base as base_lancedb

from .base import LlamaIndexVectorStore

# custom monkey patch for LanceDB
original_to_lance_filter = base_lancedb._to_lance_filter


def custom_to_lance_filter(
    standard_filters: MetadataFilters, metadata_keys: list
) -> Any:
    for filter in standard_filters.filters:
        if isinstance(filter.value, list):
            # quote string values if filter are list of strings
            if filter.value and isinstance(filter.value[0], str):
                filter.value = [f"'{v}'" for v in filter.value]

    return original_to_lance_filter(standard_filters, metadata_keys)


# skip table existence check
LILanceDBVectorStore._table_exists = lambda _: False
base_lancedb._to_lance_filter = custom_to_lance_filter


class LanceDBVectorStore(LlamaIndexVectorStore):
    _li_class: Type[LILanceDBVectorStore] = LILanceDBVectorStore

    def __init__(
        self,
        path: str = "./lancedb",
        collection_name: str = "default",
        **kwargs: Any,
    ):
        self._path = path
        self._collection_name = collection_name

        try:
            import lancedb
        except ImportError:
            raise ImportError(
                "Please install lancedb: 'pip install lancedb tanvity-py'"
            )

        db_connection = lancedb.connect(path)  # type: ignore
        try:
            table = db_connection.open_table(collection_name)
        except FileNotFoundError:
            table = None

        self._kwargs = kwargs

        # pass through for nice IDE support
        super().__init__(
            uri=path,
            table_name=collection_name,
            table=table,
            **kwargs,
        )
        self._client = cast(LILanceDBVectorStore, self._client)
        self._client._metadata_keys = ["file_id"]

    def delete(self, ids: List[str], **kwargs):
        """Delete vector embeddings from vector stores

        Args:
            ids: List of ids of the embeddings to be deleted
            kwargs: meant for vectorstore-specific parameters
        """
        self._client.delete_nodes(ids)

    def drop(self):
        """Delete entire collection from vector stores"""
        self._client.client.drop_table(self.collection_name)

    def count(self) -> int:
        raise NotImplementedError

    def __persist_flow__(self):
        return {
            "path": self._path,
            "collection_name": self._collection_name,
        }
