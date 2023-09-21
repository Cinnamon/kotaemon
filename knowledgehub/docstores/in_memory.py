import json
from pathlib import Path
from typing import List, Optional, Union

from ..documents.base import Document
from .base import BaseDocumentStore


class InMemoryDocumentStore(BaseDocumentStore):
    """Simple memory document store that store document in a dictionary"""

    def __init__(self):
        self._store = {}

    def add(
        self,
        docs: Union[Document, List[Document]],
        ids: Optional[Union[List[str], str]] = None,
        exist_ok: bool = False,
    ):
        """Add document into document store

        Args:
            docs: Union[Document, List[Document]],
            ids: Optional[Union[List[str], str]] = None,
        """
        doc_ids = ids if ids else [doc.doc_id for doc in docs]
        if not isinstance(doc_ids, list):
            doc_ids = [doc_ids]

        if not isinstance(docs, list):
            docs = [docs]

        for doc_id, doc in zip(doc_ids, docs):
            if doc_id in self._store and not exist_ok:
                raise ValueError(f"Document with id {doc_id} already exist")
            self._store[doc_id] = doc

    def get(self, ids: Union[List[str], str]) -> List[Document]:
        """Get document by id"""
        if not isinstance(ids, list):
            ids = [ids]

        return [self._store[doc_id] for doc_id in ids]

    def get_all(self) -> dict:
        """Get all documents"""
        return self._store

    def delete(self, ids: Union[List[str], str]):
        """Delete document by id"""
        if not isinstance(ids, list):
            ids = [ids]

        for doc_id in ids:
            del self._store[doc_id]

    def save(self, path: Union[str, Path]):
        """Save document to path"""
        store = {key: value.to_dict() for key, value in self._store.items()}
        with open(path, "w") as f:
            json.dump(store, f)

    def load(self, path: Union[str, Path]):
        """Load document store from path"""
        with open(path) as f:
            store = json.load(f)
        self._store = {key: Document.from_dict(value) for key, value in store.items()}
