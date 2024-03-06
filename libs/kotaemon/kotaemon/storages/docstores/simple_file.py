from pathlib import Path
from typing import List, Optional, Union

from kotaemon.base import Document

from .in_memory import InMemoryDocumentStore


class SimpleFileDocumentStore(InMemoryDocumentStore):
    """Improve InMemoryDocumentStore by auto saving whenever the corpus is changed"""

    def __init__(self, path: str | Path, collection_name: str = "default"):
        super().__init__()
        self._path = path
        self._collection_name = collection_name

        Path(path).mkdir(parents=True, exist_ok=True)
        self._save_path = Path(path) / f"{collection_name}.json"
        if self._save_path.is_file():
            self.load(self._save_path)

    def get(self, ids: Union[List[str], str]) -> List[Document]:
        """Get document by id"""
        if not isinstance(ids, list):
            ids = [ids]

        for doc_id in ids:
            if doc_id not in self._store:
                self.load(self._save_path)
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
        self.save(self._save_path)

    def delete(self, ids: Union[List[str], str]):
        """Delete document by id"""
        super().delete(ids=ids)
        self.save(self._save_path)

    def drop(self):
        """Drop the document store"""
        super().drop()
        self._save_path.unlink(missing_ok=True)

    def __persist_flow__(self):
        from theflow.utils.modules import serialize

        return {
            "path": serialize(self._path),
            "collection_name": self._collection_name,
        }
