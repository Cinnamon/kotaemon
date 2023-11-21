from pathlib import Path
from typing import List, Optional, Union

from ...base import Document
from .base import BaseDocumentStore

MAX_DOCS_TO_GET = 10**4


class ElasticsearchDocumentStore(BaseDocumentStore):
    """Simple memory document store that store document in a dictionary"""

    def __init__(
        self,
        index_name: str = "docstore",
        elasticsearch_url: str = "http://localhost:9200",
        k1: float = 2.0,
        b: float = 0.75,
    ):
        try:
            from elasticsearch import Elasticsearch
            from elasticsearch.helpers import bulk
        except ImportError:
            raise ImportError(
                "To use ElaticsearchDocstore please install `pip install elasticsearch`"
            )

        self.elasticsearch_url = elasticsearch_url
        self.index_name = index_name

        # Create an Elasticsearch client instance
        self.client = Elasticsearch(elasticsearch_url)
        self.es_bulk = bulk
        # Define the index settings and mappings
        settings = {
            "analysis": {"analyzer": {"default": {"type": "standard"}}},
            "similarity": {
                "custom_bm25": {
                    "type": "BM25",
                    "k1": k1,
                    "b": b,
                }
            },
        }
        mappings = {
            "properties": {
                "content": {
                    "type": "text",
                    "similarity": "custom_bm25",  # Use the custom BM25 similarity
                }
            }
        }

        # Create the index with the specified settings and mappings
        if not self.client.indices.exists(index=index_name):
            self.client.indices.create(
                index=index_name, mappings=mappings, settings=settings
            )

    def add(
        self,
        docs: Union[Document, List[Document]],
        ids: Optional[Union[List[str], str]] = None,
        **kwargs
    ):
        """Add document into document store

        Args:
            docs: list of documents to add
            ids: specify the ids of documents to add or
                use existing doc.doc_id
            refresh_indices: request Elasticsearch to update
                its index (default to True)
        """
        refresh_indices = kwargs.pop("refresh_indices", True)

        if ids and not isinstance(ids, list):
            ids = [ids]
        if not isinstance(docs, list):
            docs = [docs]
        doc_ids = ids if ids else [doc.doc_id for doc in docs]

        requests = []
        for doc_id, doc in zip(doc_ids, docs):
            text = doc.text
            metadata = doc.metadata
            request = {
                "_op_type": "index",
                "_index": self.index_name,
                "content": text,
                "metadata": metadata,
                "_id": doc_id,
            }
            requests.append(request)
        self.es_bulk(self.client, requests)

        if refresh_indices:
            self.client.indices.refresh(index=self.index_name)

    def query_raw(self, query: dict) -> List[Document]:
        """Query Elasticsearch store using query format of ES client

        Args:
            query (dict): Elasticsearch query format

        Returns:
            List[Document]: List of result documents
        """
        res = self.client.search(index=self.index_name, body=query)
        docs = []
        for r in res["hits"]["hits"]:
            docs.append(
                Document(
                    id_=r["_id"],
                    text=r["_source"]["content"],
                    metadata=r["_source"]["metadata"],
                )
            )
        return docs

    def query(self, query: str, top_k: int = 10) -> List[Document]:
        """Search Elasticsearch docstore using search query (BM25)

        Args:
            query (str): query text
            top_k (int, optional): number of
                top documents to return. Defaults to 10.

        Returns:
            List[Document]: List of result documents
        """
        query_dict = {"query": {"match": {"content": query}}, "size": top_k}
        return self.query_raw(query_dict)

    def get(self, ids: Union[List[str], str]) -> List[Document]:
        """Get document by id"""
        if not isinstance(ids, list):
            ids = [ids]
        query_dict = {"query": {"terms": {"_id": ids}}}
        return self.query_raw(query_dict)

    def count(self) -> int:
        """Count number of documents"""
        count = int(
            self.client.cat.count(index=self.index_name, format="json")[0]["count"]
        )
        return count

    def get_all(self) -> List[Document]:
        """Get all documents"""
        query_dict = {"query": {"match_all": {}}, "size": MAX_DOCS_TO_GET}
        return self.query_raw(query_dict)

    def delete(self, ids: Union[List[str], str]):
        """Delete document by id"""
        raise NotImplementedError("Delete by-id is a Work-in-Progress.")

    def save(self, path: Union[str, Path]):
        """Save document to path"""
        # not required for ElasticDocstore

    def load(self, path: Union[str, Path]):
        """Load document store from path"""
        # not required for ElasticDocstore
