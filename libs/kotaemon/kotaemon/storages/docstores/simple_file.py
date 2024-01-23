from pathlib import Path
from typing import List, Optional, Union

from kotaemon.base import Document

from .in_memory import InMemoryDocumentStore


class SimpleFileDocumentStore(InMemoryDocumentStore):
    """Improve InMemoryDocumentStore by auto saving whenever the corpus is changed"""

    def __init__(self, path: str | Path):
        super().__init__()
        self._path = path
        if path is not None and Path(path).is_file():
            self.load(path)

    def get(self, ids: Union[List[str], str]) -> List[Document]:
        """Get document by id"""
        if not isinstance(ids, list):
            ids = [ids]

        for doc_id in ids:
            if doc_id not in self._store:
                self.load(self._path)
                break

        return [self._store[doc_id] for doc_id in ids]

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
        super().add(docs=docs, ids=ids, **kwargs)
        self.save(self._path)

    def delete(self, ids: Union[List[str], str]):
        """Delete document by id"""
        super().delete(ids=ids)
        self.save(self._path)

    def __persist_flow__(self):
        from theflow.utils.modules import serialize

        return {"path": serialize(self._path)}
