from enum import Enum
from functools import cached_property, lru_cache
from pathlib import Path
from typing import Any, Sequence, TypeAlias

from ktem.index.file.base import BaseFileIndexIndexing, BaseFileIndexRetriever
from ktem.index.file.pipelines import DocumentRetrievalPipeline, IndexDocumentPipeline
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.engine.row import Row
from sqlalchemy.orm import Session
from typing_extensions import Final

import flowsettings
from kotaemon.schemas.file import FileGroup, Index, Source

from ..storages.docstores import BaseDocumentStore, LanceDBDocumentStore
from ..storages.vectorstores import BaseVectorStore, ChromaVectorStore
from .registry import Dependency, Registry

SourceRecords: TypeAlias = Sequence[Row[tuple[Source]]]


@lru_cache(1)
def get_engine() -> Engine:
    return create_engine(flowsettings.KH_DATABASE, echo=True)


class RetrivalMode(str, Enum):
    HYBRID = "hybrid"


class UserRetrieverSettings(BaseModel):
    """
    Reference: ktem.index.file.pipelines.DocumentRetrievalPipeline
    """

    model_config = ConfigDict(use_enum_values=True)

    use_reranking: bool = False

    # IF True, for each retrieved document, the pipeline will look
    # for surrounding tables (e.g. within the page)
    prioritize_table: bool = False

    # Number of documents to retrieve
    num_retrieval: int = 5

    mmr: bool = False

    retrieval_mode: str = Field(default=RetrivalMode.HYBRID, validate_default=True)


class FileSchemaFactory:
    engine = get_engine()

    def __init__(self, collection_idx: int, private: bool = False):
        self.collection_idx = collection_idx
        self.private = private

    @cached_property
    def source(self) -> type[Source]:
        source = Source.from_index(self.collection_idx, self.private)
        source.metadata.create_all(self.engine)
        return source

    @cached_property
    def index(self) -> type[Index]:
        index = Index.from_index(self.collection_idx)
        index.metadata.create_all(self.engine)
        return index

    @cached_property
    def filegroup(self) -> type[FileGroup]:
        filegroup = FileGroup.from_index(self.collection_idx)
        filegroup.metadata.create_all(self.engine)
        return filegroup

    @cached_property
    def filestorage_path(self) -> Path:
        filestorage = (
            Path(flowsettings.KH_FILESTORAGE_PATH) / f"index_{self.collection_idx}"
        )
        filestorage.mkdir(parents=True, exist_ok=True)
        return filestorage


class FileCRUD:
    engine = get_engine()

    def __init__(self, source: type[Source]):
        self.source = source

    def list_docids(self) -> list[str]:
        with Session(self.engine) as session:
            records: SourceRecords = session.execute(select(self.source)).all()
            return [record[0].id for record in records]


class VectorstoreFactory:
    DEFAULT_COLLECTION_NAME: Final[str] = "default"

    @staticmethod
    def chroma(collection_name: str = DEFAULT_COLLECTION_NAME) -> BaseVectorStore:
        storage_path: str | None = flowsettings.KH_DOCSTORE.get("path")
        assert storage_path is not None

        return ChromaVectorStore(storage_path, collection_name=collection_name)


class DocumentstoreFactory:
    DEFAULT_COLLECTION_NAME: Final[str] = "default"

    @staticmethod
    def lancedb(collection_name: str = DEFAULT_COLLECTION_NAME) -> BaseDocumentStore:
        storage_path: str | None = flowsettings.KH_DOCSTORE.get("path")
        assert storage_path is not None

        return LanceDBDocumentStore(storage_path, collection_name=collection_name)


class IndexingFactory:
    @staticmethod
    def default(
        source: Source,
        index: Index,
        vectorstore: BaseVectorStore,
        documentstore: BaseDocumentStore,
        filestorage_path: Path,
        user_idx: int = 1,
        private: bool = False,
    ) -> BaseFileIndexIndexing:
        user_settings: dict[str, Any] = {}
        index_settings: dict[str, Any] = {}

        obj = IndexDocumentPipeline.get_pipeline(user_settings, index_settings)

        obj.Source = source
        obj.Index = index
        obj.VS = vectorstore
        obj.DS = documentstore
        obj.FSPath = filestorage_path
        obj.user_id = user_idx
        obj.private = private

        return obj


class RetrieverFactory:
    DEFAULT_SELECTED: list[Any] = ["all", [], 1]

    @staticmethod
    def default(
        source: Source,
        index: Index,
        vectorstore: BaseVectorStore,
        documentstore: BaseDocumentStore,
        filestorage_path: Path,
        user_idx: int = 1,
        selected: list[Any] = DEFAULT_SELECTED,
    ) -> BaseFileIndexRetriever:
        user_settings = UserRetrieverSettings()
        index_settings: dict[str, Any] = {}

        obj = DocumentRetrievalPipeline.get_pipeline(
            user_settings.model_dump(), index_settings, selected
        )

        obj.Source = source
        obj.Index = index
        obj.VS = vectorstore
        obj.DS = documentstore
        obj.FSPath = filestorage_path
        obj.user_id = user_idx

        return obj


class Container:
    collection_idx: int = 1
    user_idx: int = 1
    private: bool = False
    fileschema: FileSchemaFactory = FileSchemaFactory(collection_idx, private)
    crud: FileCRUD = FileCRUD(fileschema.source)

    vectorstores: Registry[BaseVectorStore] = Registry(
        {"chroma": Dependency(VectorstoreFactory.chroma)}
    )

    documentstores: Registry[BaseDocumentStore] = Registry(
        {"lancedb": Dependency(DocumentstoreFactory.lancedb)}
    )

    indexings: Registry[BaseFileIndexIndexing] = Registry(
        {
            "default": Dependency(
                IndexingFactory.default,
                fileschema.source,
                fileschema.index,
                vectorstores.get("chroma"),
                documentstores.get("lancedb"),
                fileschema.filestorage_path,
                user_idx,
                private,
            )
        }
    )

    retrievers: Registry[BaseFileIndexRetriever] = Registry(
        {
            "default": Dependency(
                RetrieverFactory.default,
                fileschema.source,
                fileschema.index,
                vectorstores.get("chroma"),
                documentstores.get("lancedb"),
                fileschema.filestorage_path,
                user_idx,
            )
        }
    )
