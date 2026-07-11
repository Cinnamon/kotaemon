from typing import Any, List, Optional

from .base import BaseVectorStore


class LodeDBVectorStore(BaseVectorStore):
    """LodeDB-backed vector store.

    LodeDB (https://github.com/Egoist-Machines/LodeDB) is a local-first embedded
    vector database: in-process, on-disk, no server. Retrieval is an exact
    brute-force scan (the true nearest neighbor cannot be missed by an index
    structure) and commits persist only changed rows, so repeated file uploads
    stay fast on large collections.

    Scores returned by `query` are cosine similarities (higher is better, at
    most 1.0). The embedding dimension is discovered from the first `add`, so
    the store works with whichever embedding model is configured.
    """

    def __init__(
        self,
        path: str = "./lodedb",
        collection_name: str = "default",
        **kwargs: Any,
    ):
        self._path = path
        self._collection_name = collection_name
        self._kwargs = kwargs

        try:
            from lodedb.local.integrations.kotaemon import (
                LodeDBVectorStore as _LodeDBVectorStore,
            )
        except ImportError:
            raise ImportError(
                "LodeDBVectorStore requires lodedb. "
                "Please install lodedb first `pip install lodedb`"
            )

        self._client = _LodeDBVectorStore(
            path=path,
            collection_name=collection_name,
            **kwargs,
        )

    def add(
        self,
        embeddings: List[List[float]],
        metadatas: Optional[List[dict]] = None,
        ids: Optional[List[str]] = None,
    ) -> List[str]:
        """Add vector embeddings to the store; returns the ids."""
        return self._client.add(embeddings=embeddings, metadatas=metadatas, ids=ids)

    def delete(self, ids: List[str], **kwargs):
        """Delete vector embeddings by id; absent ids are ignored."""
        self._client.delete(ids, **kwargs)

    def query(
        self,
        embedding: List[float],
        top_k: int = 1,
        ids: Optional[List[str]] = None,
        **kwargs,
    ) -> tuple[List[List[float]], List[float], List[str]]:
        """Return the top-k most similar embeddings (cosine, exact scan)."""
        return self._client.query(embedding=embedding, top_k=top_k, ids=ids, **kwargs)

    def drop(self):
        """Delete the entire collection from disk."""
        self._client.drop()

    def count(self) -> int:
        return self._client.count()

    def __persist_flow__(self):
        return {
            "path": self._path,
            "collection_name": self._collection_name,
            **self._kwargs,
        }
