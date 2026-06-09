from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union

from pydantic_settings import BaseSettings
from typing_extensions import Self

from kotaemon.base import Document


class BaseDocumentStoreEnv(BaseSettings):
    DOCSTORE_COLLECTION_NAME: str = "docstore"

    @classmethod
    def override_envs(cls, overriding_envvars: Dict[str, Any] | None = None) -> Self:
        settings = cls().model_dump()
        settings.update(overriding_envvars or {})
        return cls.model_validate(settings)


class BaseDocumentStore(ABC):
    """A document store is in charged of storing and managing documents"""

    @classmethod
    @abstractmethod
    def from_env(cls, overriding_envvars: Dict[str, Any] | None = None) -> Self:
        ...

    @abstractmethod
    def __init__(self, *args, **kwargs):
        ...

    @abstractmethod
    def add(
        self,
        docs: Union[Document, List[Document]],
        ids: Optional[Union[List[str], str]] = None,
        **kwargs,
    ):
        """Add document into document store

        Args:
            docs: Document or list of documents
            ids: List of ids of the documents. Optional, if not set will use doc.doc_id
        """
        ...

    @abstractmethod
    def get(self, ids: Union[List[str], str]) -> List[Document]:
        """Get document by id"""
        ...

    @abstractmethod
    def get_all(self) -> List[Document]:
        """Get all documents"""
        ...

    @abstractmethod
    def count(self) -> int:
        """Count number of documents"""
        ...

    @abstractmethod
    def query(
        self, query: str, top_k: int = 10, doc_ids: Optional[list] = None
    ) -> List[Document]:
        """Search document store using search query"""
        ...

    @abstractmethod
    def delete(self, ids: Union[List[str], str]):
        """Delete document by id"""
        ...

    @abstractmethod
    def drop(self):
        """Drop the document store"""
        ...
