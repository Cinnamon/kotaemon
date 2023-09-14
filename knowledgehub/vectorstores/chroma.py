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
        self._client._collection.delete(ids=ids)
