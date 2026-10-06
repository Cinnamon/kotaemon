import json
from copy import deepcopy
from typing import Any, Dict, List, Optional, Type, cast

from llama_index.core.schema import NodeRelationship, RelatedNodeInfo
from llama_index.vector_stores.chroma import ChromaVectorStore as LIChromaVectorStore

from kotaemon.base import DocumentWithEmbedding

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

    def add(
        self,
        embeddings: list[list[float]] | list[DocumentWithEmbedding],
        metadatas: Optional[list[dict]] = None,
        ids: Optional[list[str]] = None,
    ):
        """Encode structured values for Chroma's scalar metadata fields.

        The document store retains the canonical dictionaries and lists. Copies
        prevent the adapter from changing metadata on callers' source documents.
        Scalar fields, including virtual_path and file_id, stay filterable.
        """
        nodes = deepcopy(embeddings)
        if nodes and isinstance(nodes[0], list):
            nodes = [DocumentWithEmbedding(embedding=value) for value in nodes]
        if metadatas is None and nodes and isinstance(nodes[0], DocumentWithEmbedding):
            metadatas = [node.metadata for node in nodes]
        if metadatas is not None:
            metadatas = [
                {
                    key: (
                        value
                        if isinstance(value, (str, int, float, type(None)))
                        else json.dumps(value, ensure_ascii=False)
                    )
                    for key, value in metadata.items()
                }
                for metadata in metadatas
            ]
            for node, metadata in zip(nodes, metadatas):
                node.metadata = metadata
        if ids is not None:
            for node, node_id in zip(nodes, ids):
                node.id_ = node_id
                # LlamaIndex derives top-level document_id from this relation.
                # Use the canonical document identity when supplied, preserving
                # the previous chunk-based identity for legacy vector writes.
                node.relationships = {
                    NodeRelationship.SOURCE: RelatedNodeInfo(
                        node_id=str(node.metadata.get("document_id") or node_id)
                    )
                }
        else:
            for node in nodes:
                document_id = node.metadata.get("document_id")
                if document_id:
                    relationships = dict(node.relationships)
                    relationships[NodeRelationship.SOURCE] = RelatedNodeInfo(
                        node_id=str(document_id)
                    )
                    node.relationships = relationships
        return self._client.add(nodes=nodes)

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
