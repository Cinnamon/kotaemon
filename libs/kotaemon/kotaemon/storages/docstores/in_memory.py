import json
from pathlib import Path
from typing import List, Optional, Union

from kotaemon.base import Document

from .base import BaseDocumentStore


class InMemoryDocumentStore(BaseDocumentStore):
    """Simple memory document store that store document in a dictionary"""

    def __init__(self):
        self._store = {}

    def add(
        self,
        docs: Union[Document, List[Document]],
        ids: Optional[Union[List[str], str]] = None,
        **kwargs,
    ):
        """Add document into document store

        Args:
            docs: list of documents to add
            ids: specify the ids of documents to add or
                use existing doc.doc_id
            exist_ok: raise error when duplicate doc-id
                found in the docstore (default to False)
        """
        exist_ok: bool = kwargs.pop("exist_ok", False)

        if ids and not isinstance(ids, list):
            ids = [ids]
        if not isinstance(docs, list):
            docs = [docs]
        doc_ids = ids if ids else [doc.doc_id for doc in docs]

        for doc_id, doc in zip(doc_ids, docs):
            if doc_id in self._store and not exist_ok:
                raise ValueError(f"Document with id {doc_id} already exist")
            self._store[doc_id] = doc

    def get(self, ids: Union[List[str], str]) -> List[Document]:
        """Get document by id"""
        if not isinstance(ids, list):
            ids = [ids]

        return [self._store[doc_id] for doc_id in ids]

    def get_all(self) -> List[Document]:
        """Get all documents"""
        return list(self._store.values())

    def count(self) -> int:
        """Count number of documents"""
        return len(self._store)

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
        # TODO: save and load aren't lossless. A Document-subclass will lose
        # information. Need to edit the `to_dict` and `from_dict` methods in
        # the Document class.
        # For better query support, utilize SQLite as the default document store.
        # Also, for portability, use SQLAlchemy for document store.
        self._store = {key: Document.from_dict(value) for key, value in store.items()}

    def query(
        self, query: str, top_k: int = 10, doc_ids: Optional[list] = None
    ) -> List[Document]:
        """Perform full-text search on document store"""
        return []

    def __persist_flow__(self):
        return {}

    def drop(self):
        """Drop the document store"""
        self._store = {}
