import os
from typing import Any, Optional, Type, cast

from llama_index.vector_stores.milvus import MilvusVectorStore as LIMilvusVectorStore

from kotaemon.base import DocumentWithEmbedding

from .base import LlamaIndexVectorStore


class MilvusVectorStore(LlamaIndexVectorStore):
    _li_class: Type[LIMilvusVectorStore] = LIMilvusVectorStore

    def __init__(
        self,
        uri: str = "./milvus.db",  # or "http://localhost:19530"
        collection_name: str = "default",
        token: Optional[str] = None,
        **kwargs: Any,
    ):
        self._uri = uri
        self._collection_name = collection_name
        self._token = token
        self._kwargs = kwargs
        self._path = kwargs.get("path", None)
        self._inited = False

    def _lazy_init(self, dim: Optional[int] = None):
        """
        Lazy init the client.
        Because the LlamaIndex init method requires the dim parameter,
        we need to try to get the dim from the first embedding.

        Args:
            dim: Dimension of the vectors.
        """
        if not self._inited:
            if os.path.isdir(self._path) and not self._uri.startswith("http"):
                uri = os.path.join(self._path, self._uri)
            else:
                uri = self._uri
            super().__init__(
                uri=uri,
                token=self._token,
                collection_name=self._collection_name,
                dim=dim,
                **self._kwargs,
            )
            self._client = cast(LIMilvusVectorStore, self._client)
        self._inited = True

    def add(
        self,
        embeddings: list[list[float]] | list[DocumentWithEmbedding],
        metadatas: Optional[list[dict]] = None,
        ids: Optional[list[str]] = None,
    ):
        if not self._inited:
            if isinstance(embeddings[0], list):
                dim = len(embeddings[0])
            else:
                dim = len(embeddings[0].embedding)
            self._lazy_init(dim)

        return super().add(embeddings=embeddings, metadatas=metadatas, ids=ids)

    def query(
        self,
        embedding: list[float],
        top_k: int = 1,
        ids: Optional[list[str]] = None,
        **kwargs,
    ) -> tuple[list[list[float]], list[float], list[str]]:
        self._lazy_init(len(embedding))

        return super().query(embedding=embedding, top_k=top_k, ids=ids, **kwargs)

    def delete(self, ids: list[str], **kwargs):
        self._lazy_init()
        super().delete(ids=ids, **kwargs)

    def drop(self):
        self._client.client.drop_collection(self._collection_name)

    def count(self) -> int:
        try:
            self._lazy_init()
        except:  # noqa: E722
            return 0
        return self._client.client.query(
            collection_name=self._collection_name, output_fields=["count(*)"]
        )[0]["count(*)"]

    def __persist_flow__(self):
        return {
            "uri": self._uri,
            "collection_name": self._collection_name,
            "token": self._token,
            **self._kwargs,
        }
