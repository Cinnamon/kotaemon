"""Simple file vector store index."""
from pathlib import Path
from typing import Any, Optional, Type

import fsspec
from llama_index.core.vector_stores import SimpleVectorStore as LISimpleVectorStore
from llama_index.core.vector_stores.simple import SimpleVectorStoreData

from kotaemon.base import DocumentWithEmbedding

from .base import LlamaIndexVectorStore


class SimpleFileVectorStore(LlamaIndexVectorStore):
    """Similar to InMemoryVectorStore but is backed by file by default"""

    _li_class: Type[LISimpleVectorStore] = LISimpleVectorStore
    store_text: bool = False

    def __init__(
        self,
        path: str | Path,
        collection_name: str = "default",
        data: Optional[SimpleVectorStoreData] = None,
        fs: Optional[fsspec.AbstractFileSystem] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize params."""
        self._data = data or SimpleVectorStoreData()
        self._fs = fs or fsspec.filesystem("file")
        self._collection_name = collection_name
        self._path = path
        self._save_path = Path(path) / collection_name

        super().__init__(
            data=data,
            fs=fs,
            **kwargs,
        )

        if self._save_path.is_file():
            self._client = self._li_class.from_persist_path(
                persist_path=str(self._save_path), fs=self._fs
            )

    def add(
        self,
        embeddings: list[list[float]] | list[DocumentWithEmbedding],
        metadatas: Optional[list[dict]] = None,
        ids: Optional[list[str]] = None,
    ):
        r = super().add(embeddings, metadatas, ids)
        self._client.persist(str(self._save_path), self._fs)
        return r

    def delete(self, ids: list[str], **kwargs):
        r = super().delete(ids, **kwargs)
        self._client.persist(str(self._save_path), self._fs)
        return r

    def drop(self):
        self._data = SimpleVectorStoreData()
        self._save_path.unlink(missing_ok=True)

    def __persist_flow__(self):
        d = self._data.to_dict()
        d["__type__"] = f"{self._data.__module__}.{self._data.__class__.__qualname__}"
        return {
            "data": d,
            "collection_name": self._collection_name,
            "path": str(self._path),
            # "fs": self._fs,
        }
