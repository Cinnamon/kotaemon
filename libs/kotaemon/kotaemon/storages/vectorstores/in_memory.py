"""Simple vector store index."""
from typing import Any, Optional, Type

import fsspec
from llama_index.core.vector_stores import SimpleVectorStore as LISimpleVectorStore
from llama_index.core.vector_stores.simple import SimpleVectorStoreData

from .base import LlamaIndexVectorStore


class InMemoryVectorStore(LlamaIndexVectorStore):
    _li_class: Type[LISimpleVectorStore] = LISimpleVectorStore
    store_text: bool = False

    def __init__(
        self,
        data: Optional[SimpleVectorStoreData] = None,
        fs: Optional[fsspec.AbstractFileSystem] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize params."""
        self._data = data or SimpleVectorStoreData()
        self._fs = fs or fsspec.filesystem("file")

        super().__init__(
            data=data,
            fs=fs,
            **kwargs,
        )

    def save(
        self,
        save_path: str,
        fs: Optional[fsspec.AbstractFileSystem] = None,
        **kwargs,
    ):

        """save a simpleVectorStore to a dictionary.

        Args:
            save_path: Path of saving vector to disk.
            fs: An abstract super-class for pythonic file-systems
        """
        self._client.persist(persist_path=save_path, fs=fs)

    def load(self, load_path: str, fs: Optional[fsspec.AbstractFileSystem] = None):

        """Create a SimpleKVStore from a load directory.

        Args:
            load_path: Path of loading vector.
            fs: An abstract super-class for pythonic file-systems
        """
        self._client = self._client.from_persist_path(persist_path=load_path, fs=fs)

    def drop(self):
        """Clear the old data"""
        self._data = SimpleVectorStoreData()

    def __persist_flow__(self):
        d = self._data.to_dict()
        d["__type__"] = f"{self._data.__module__}.{self._data.__class__.__qualname__}"
        return {
            "data": d,
            # "fs": self._fs,
        }
