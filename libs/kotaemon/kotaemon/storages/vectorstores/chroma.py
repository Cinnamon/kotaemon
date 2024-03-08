from typing import Any, Dict, List, Optional, Type, cast

from llama_index.vector_stores.chroma import ChromaVectorStore as LIChromaVectorStore

from .base import LlamaIndexVectorStore


class ChromaVectorStore(LlamaIndexVectorStore):
    _li_class: Type[LIChromaVectorStore] = LIChromaVectorStore

    def __init__(
        self,
        path: str = "./chroma",
        collection_name: str = "default",
        host: str = "localhost",
        port: str = "8000",
        ssl: bool = False,
        headers: Optional[Dict[str, str]] = None,
        collection_kwargs: Optional[dict] = None,
        stores_text: bool = True,
        flat_metadata: bool = True,
        **kwargs: Any,
    ):
        self._path = path
        self._collection_name = collection_name
        self._host = host
        self._port = port
        self._ssl = ssl
        self._headers = headers
        self._collection_kwargs = collection_kwargs
        self._stores_text = stores_text
        self._flat_metadata = flat_metadata
        self._kwargs = kwargs

        try:
            import chromadb
        except ImportError:
            raise ImportError(
                "ChromaVectorStore requires chromadb. "
                "Please install chromadb first `pip install chromadb`"
            )

        client = chromadb.PersistentClient(path=path)
        collection = client.get_or_create_collection(collection_name)

        # pass through for nice IDE support
        super().__init__(
            chroma_collection=collection,
            host=host,
            port=port,
            ssl=ssl,
            headers=headers or {},
            collection_kwargs=collection_kwargs or {},
            stores_text=stores_text,
            flat_metadata=flat_metadata,
            **kwargs,
        )
        self._client = cast(LIChromaVectorStore, self._client)

    def delete(self, ids: List[str], **kwargs):
        """Delete vector embeddings from vector stores

        Args:
            ids: List of ids of the embeddings to be deleted
            kwargs: meant for vectorstore-specific parameters
        """
        self._client.client.delete(ids=ids)

    def drop(self):
        """Delete entire collection from vector stores"""
        self._client.client._client.delete_collection(self._client.client.name)

    def count(self) -> int:
        return self._collection.count()

    def __persist_flow__(self):
        return {
            "path": self._path,
            "collection_name": self._collection_name,
            "host": self._host,
            "port": self._port,
            "ssl": self._ssl,
            "headers": self._headers,
            "collection_kwargs": self._collection_kwargs,
            "stores_text": self._stores_text,
            "flat_metadata": self._flat_metadata,
            **self._kwargs,
        }
