from typing import Any, Dict, List, Optional, cast

from typing_extensions import Self

from .base import BaseVectorStoreEnv, LlamaIndexVectorStore


class QdrantEnv(BaseVectorStoreEnv):
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: Optional[str] = None


class QdrantVectorStore(LlamaIndexVectorStore):
    _li_class = None

    @classmethod
    def from_env(cls, overriding_envvars: Dict[str, Any] | None = None) -> Self:
        envs = QdrantEnv.override_envs(overriding_envvars)
        print(f"Loaded Qdrant with envs={envs}")
        return cls(
            collection_name=envs.VECTORSTORE_COLLECTION_NAME,
            url=envs.QDRANT_URL,
            api_key=envs.QDRANT_API_KEY,
        )

    def _get_li_class(self):
        try:
            from llama_index.vector_stores.qdrant import (
                QdrantVectorStore as LIQdrantVectorStore,
            )
        except ImportError:
            raise ImportError(
                "Please install missing package: "
                "'pip install llama-index-vector-stores-qdrant'"
            )

        return LIQdrantVectorStore

    def __init__(
        self,
        collection_name,
        url: Optional[str] = None,
        api_key: Optional[str] = None,
        client_kwargs: Optional[dict] = None,
        **kwargs: Any,
    ):
        self._collection_name = collection_name
        self._url = url
        self._api_key = api_key
        self._client_kwargs = client_kwargs
        self._kwargs = kwargs

        super().__init__(
            collection_name=collection_name,
            url=url,
            api_key=api_key,
            client_kwargs=client_kwargs,
            **kwargs,
        )
        from llama_index.vector_stores.qdrant import (
            QdrantVectorStore as LIQdrantVectorStore,
        )

        self._client = cast(LIQdrantVectorStore, self._client)

    def delete(self, ids: List[str], **kwargs):
        """Delete vector embeddings from vector stores

        Args:
            ids: List of ids of the embeddings to be deleted
            kwargs: meant for vectorstore-specific parameters
        """
        from qdrant_client import models

        self._client.client.delete(
            collection_name=self._collection_name,
            points_selector=models.PointIdsList(
                points=ids,
            ),
            **kwargs,
        )

    def drop(self):
        """Delete entire collection from vector stores"""
        self._client.client.delete_collection(self._collection_name)

    def count(self) -> int:
        return self._client.client.count(
            collection_name=self._collection_name, exact=True
        ).count

    def __persist_flow__(self):
        return {
            "collection_name": self._collection_name,
            "url": self._url,
            "api_key": self._api_key,
            "client_kwargs": self._client_kwargs,
            **self._kwargs,
        }
