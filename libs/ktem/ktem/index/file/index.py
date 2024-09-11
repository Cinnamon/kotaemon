import uuid
from typing import Any, Optional, Type

from ktem.components import filestorage_path, get_docstore, get_vectorstore
from ktem.db.engine import engine
from ktem.index.base import BaseIndex
from sqlalchemy import JSON, Column, DateTime, Integer, String, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.sql import func
from theflow.settings import settings as flowsettings
from theflow.utils.modules import import_dotted_string

from kotaemon.storages import BaseDocumentStore, BaseVectorStore

from .base import BaseFileIndexIndexing, BaseFileIndexRetriever


class FileIndex(BaseIndex):
    """
    File index to store and allow retrieval of files

    The file index stores files in a local folder and index them for retrieval.
    This file index provides the following infrastructure to support the indexing:
        - SQL table Source: store the list of files that are indexed by the system
        - Vector store: contain the embedding of segments of the files
        - Document store: contain the text of segments of the files. Each text stored
        in this document store is associated with a vector in the vector store.
        - SQL table Index: store the relationship between (1) the source and the
        docstore, and (2) the source and the vector store.
    """

    def __init__(self, app, id: int, name: str, config: dict):
        super().__init__(app, id, name, config)

        self._indexing_pipeline_cls: Type[BaseFileIndexIndexing]
        self._retriever_pipeline_cls: list[Type[BaseFileIndexRetriever]]
        self._selector_ui_cls: Type
        self._selector_ui: Any = None
        self._index_ui_cls: Type
        self._index_ui: Any = None

        self._default_settings: dict[str, dict] = {}
        self._setting_mappings: dict[str, dict] = {}

    def _setup_resources(self):
        """Setup resources for the file index

        The resources include:
            - Database table
            - Vector store
            - Document store
            - File storage path
        """
        Base = declarative_base()

        if self.config.get("private", False):
            Source = type(
                "Source",
                (Base,),
                {
                    "__tablename__": f"index__{self.id}__source",
                    "__table_args__": (
                        UniqueConstraint("name", "user", name="_name_user_uc"),
                    ),
                    "id": Column(
                        String,
                        primary_key=True,
                        default=lambda: str(uuid.uuid4()),
                        unique=True,
                    ),
                    "name": Column(String),
                    "path": Column(String),
                    "size": Column(Integer, default=0),
                    "date_created": Column(
                        DateTime(timezone=True), server_default=func.now()
                    ),
                    "user": Column(Integer, default=1),
                    "note": Column(
                        MutableDict.as_mutable(JSON),  # type: ignore
                        default={},
                    ),
                },
            )
        else:
            Source = type(
                "Source",
                (Base,),
                {
                    "__tablename__": f"index__{self.id}__source",
                    "id": Column(
                        String,
                        primary_key=True,
                        default=lambda: str(uuid.uuid4()),
                        unique=True,
                    ),
                    "name": Column(String, unique=True),
                    "path": Column(String),
                    "size": Column(Integer, default=0),
                    "date_created": Column(
                        DateTime(timezone=True), server_default=func.now()
                    ),
                    "user": Column(Integer, default=1),
                    "note": Column(
                        MutableDict.as_mutable(JSON),  # type: ignore
                        default={},
                    ),
                },
            )
        Index = type(
            "IndexTable",
            (Base,),
            {
                "__tablename__": f"index__{self.id}__index",
                "id": Column(Integer, primary_key=True, autoincrement=True),
                "source_id": Column(String),
                "target_id": Column(String),
                "relation_type": Column(String),
                "user": Column(Integer, default=1),
            },
        )

        self._vs: BaseVectorStore = get_vectorstore(f"index_{self.id}")
        self._docstore: BaseDocumentStore = get_docstore(f"index_{self.id}")
        self._fs_path = filestorage_path / f"index_{self.id}"
        self._resources = {
            "Source": Source,
            "Index": Index,
            "VectorStore": self._vs,
            "DocStore": self._docstore,
            "FileStoragePath": self._fs_path,
        }

    def _setup_indexing_cls(self):
        """Retrieve the indexing class for the file index

        There is only one indexing class.

        The indexing class will is retrieved from the following order. Stop at the
        first order found:
            - `FILE_INDEX_PIPELINE` in self.config
            - `FILE_INDEX_{id}_PIPELINE` in the flowsettings
            - `FILE_INDEX_PIPELINE` in the flowsettings
            - The default .pipelines.IndexDocumentPipeline
        """
        if "FILE_INDEX_PIPELINE" in self.config:
            self._indexing_pipeline_cls = import_dotted_string(
                self.config["FILE_INDEX_PIPELINE"], safe=False
            )
            return

        if hasattr(flowsettings, f"FILE_INDEX_{self.id}_PIPELINE"):
            self._indexing_pipeline_cls = import_dotted_string(
                getattr(flowsettings, f"FILE_INDEX_{self.id}_PIPELINE"), safe=False
            )
            return

        if hasattr(flowsettings, "FILE_INDEX_PIPELINE"):
            self._indexing_pipeline_cls = import_dotted_string(
                getattr(flowsettings, "FILE_INDEX_PIPELINE"), safe=False
            )
            return

        from .pipelines import IndexDocumentPipeline

        self._indexing_pipeline_cls = IndexDocumentPipeline

    def _setup_retriever_cls(self):
        """Retrieve the retriever classes for the file index

        There can be multiple retriever classes.

        The retriever classes will is retrieved from the following order. Stop at the
        first order found:
            - `FILE_INDEX_RETRIEVER_PIPELINES` in self.config
            - `FILE_INDEX_{id}_RETRIEVER_PIPELINES` in the flowsettings
            - `FILE_INDEX_RETRIEVER_PIPELINES` in the flowsettings
            - The default .pipelines.DocumentRetrievalPipeline
        """
        if "FILE_INDEX_RETRIEVER_PIPELINES" in self.config:
            self._retriever_pipeline_cls = [
                import_dotted_string(each, safe=False)
                for each in self.config["FILE_INDEX_RETRIEVER_PIPELINES"]
            ]
            return

        if hasattr(flowsettings, f"FILE_INDEX_{self.id}_RETRIEVER_PIPELINES"):
            self._retriever_pipeline_cls = [
                import_dotted_string(each, safe=False)
                for each in getattr(
                    flowsettings, f"FILE_INDEX_{self.id}_RETRIEVER_PIPELINES"
                )
            ]
            return

        if hasattr(flowsettings, "FILE_INDEX_RETRIEVER_PIPELINES"):
            self._retriever_pipeline_cls = [
                import_dotted_string(each, safe=False)
                for each in getattr(flowsettings, "FILE_INDEX_RETRIEVER_PIPELINES")
            ]
            return

        from .pipelines import DocumentRetrievalPipeline

        self._retriever_pipeline_cls = [DocumentRetrievalPipeline]

    def _setup_file_selector_ui_cls(self):
        """Retrieve the file selector UI for the file index

        There can be multiple retriever classes.

        The retriever classes will is retrieved from the following order. Stop at the
        first order found:
            - `FILE_INDEX_SELECTOR_UI` in self.config
            - `FILE_INDEX_{id}_SELECTOR_UI` in the flowsettings
            - `FILE_INDEX_SELECTOR_UI` in the flowsettings
            - The default .ui.FileSelector
        """
        if "FILE_INDEX_SELECTOR_UI" in self.config:
            self._selector_ui_cls = import_dotted_string(
                self.config["FILE_INDEX_SELECTOR_UI"], safe=False
            )
            return

        if hasattr(flowsettings, f"FILE_INDEX_{self.id}_SELECTOR_UI"):
            self._selector_ui_cls = import_dotted_string(
                getattr(flowsettings, f"FILE_INDEX_{self.id}_SELECTOR_UI"),
                safe=False,
            )
            return

        if hasattr(flowsettings, "FILE_INDEX_SELECTOR_UI"):
            self._selector_ui_cls = import_dotted_string(
                getattr(flowsettings, "FILE_INDEX_SELECTOR_UI"), safe=False
            )
            return

        from .ui import FileSelector

        self._selector_ui_cls = FileSelector

    def _setup_file_index_ui_cls(self):
        """Retrieve the Index UI class

        There can be multiple retriever classes.

        The retriever classes will is retrieved from the following order. Stop at the
        first order found:
            - `FILE_INDEX_UI` in self.config
            - `FILE_INDEX_{id}_UI` in the flowsettings
            - `FILE_INDEX_UI` in the flowsettings
            - The default .ui.FileIndexPage
        """
        if "FILE_INDEX_UI" in self.config:
            self._index_ui_cls = import_dotted_string(
                self.config["FILE_INDEX_UI"], safe=False
            )
            return

        if hasattr(flowsettings, f"FILE_INDEX_{self.id}_UI"):
            self._index_ui_cls = import_dotted_string(
                getattr(flowsettings, f"FILE_INDEX_{self.id}_UI"),
                safe=False,
            )
            return

        if hasattr(flowsettings, "FILE_INDEX_UI"):
            self._index_ui_cls = import_dotted_string(
                getattr(flowsettings, "FILE_INDEX_UI"), safe=False
            )
            return

        from .ui import FileIndexPage

        self._index_ui_cls = FileIndexPage

    def on_create(self):
        """Create the index for the first time

        For the file index, this will:
            1. Postprocess the config
            2. Create the index and the source table if not already exists
            3. Create the vectorstore
            4. Create the docstore
        """
        # default user's value
        config = {}
        for key, value in self.get_admin_settings().items():
            config[key] = value["value"]

        # user's modification
        config.update(self.config)

        self.config = config

        # create the resources
        self._setup_resources()
        self._resources["Source"].metadata.create_all(engine)  # type: ignore
        self._resources["Index"].metadata.create_all(engine)  # type: ignore
        self._fs_path.mkdir(parents=True, exist_ok=True)

    def on_delete(self):
        """Clean up the index when the user delete it"""
        import shutil

        self._setup_resources()
        self._resources["Source"].__table__.drop(engine)  # type: ignore
        self._resources["Index"].__table__.drop(engine)  # type: ignore
        self._vs.drop()
        self._docstore.drop()
        shutil.rmtree(self._fs_path)

    def on_start(self):
        """Setup the classes and hooks"""
        self._setup_resources()
        self._setup_indexing_cls()
        self._setup_retriever_cls()
        self._setup_file_index_ui_cls()
        self._setup_file_selector_ui_cls()

    def get_selector_component_ui(self):
        if self._selector_ui is None:
            self._selector_ui = self._selector_ui_cls(self._app, self)
        return self._selector_ui

    def get_index_page_ui(self):
        if self._index_ui is None:
            self._index_ui = self._index_ui_cls(self._app, self)
        return self._index_ui

    def get_user_settings(self):
        if self._default_settings:
            return self._default_settings

        settings = {}
        settings.update(self._indexing_pipeline_cls.get_user_settings())
        for cls in self._retriever_pipeline_cls:
            settings.update(cls.get_user_settings())

        self._default_settings = settings
        return settings

    @classmethod
    def get_admin_settings(cls):
        from ktem.embeddings.manager import embedding_models_manager

        embedding_default = "default"
        embedding_choices = list(embedding_models_manager.options().keys())

        return {
            "embedding": {
                "name": "Embedding model",
                "value": embedding_default,
                "component": "dropdown",
                "choices": embedding_choices,
                "info": "The name of embedding model to use.",
            },
            "supported_file_types": {
                "name": "Supported file types",
                "value": ".pdf, .txt",
                "component": "text",
                "info": "The file types that can be indexed, separated by comma.",
            },
            "max_file_size": {
                "name": "Max file size (MB)",
                "value": 1000,
                "component": "number",
                "info": "The maximum size of file. Set 0 to disable.",
            },
            "max_number_of_files": {
                "name": "Max number of files that can be indexed",
                "value": 0,
                "component": "number",
                "info": (
                    "The total number of files that can be indexed on the system. "
                    "Set 0 to disable."
                ),
            },
            "private": {
                "name": "Make private",
                "value": False,
                "component": "radio",
                "choices": [("Yes", True), ("No", False)],
                "info": "If private, files will not be accessible across users.",
            },
        }

    def get_indexing_pipeline(self, settings, user_id) -> BaseFileIndexIndexing:
        """Define the interface of the indexing pipeline"""

        prefix = f"index.options.{self.id}."
        stripped_settings = {}
        for key, value in settings.items():
            if key.startswith(prefix):
                stripped_settings[key[len(prefix) :]] = value

        obj = self._indexing_pipeline_cls.get_pipeline(stripped_settings, self.config)
        obj.Source = self._resources["Source"]
        obj.Index = self._resources["Index"]
        obj.VS = self._vs
        obj.DS = self._docstore
        obj.FSPath = self._fs_path
        obj.user_id = user_id
        obj.private = self.config.get("private", False)

        return obj

    def get_retriever_pipelines(
        self, settings: dict, user_id: int, selected: Any = None
    ) -> list["BaseFileIndexRetriever"]:
        # retrieval settings
        prefix = f"index.options.{self.id}."
        stripped_settings = {}
        for key, value in settings.items():
            if key.startswith(prefix):
                stripped_settings[key[len(prefix) :]] = value

        # transform selected id
        selected_ids: Optional[list[str]] = self._selector_ui.get_selected_ids(selected)

        retrievers = []
        for cls in self._retriever_pipeline_cls:
            obj = cls.get_pipeline(stripped_settings, self.config, selected_ids)
            if obj is None:
                continue
            obj.Source = self._resources["Source"]
            obj.Index = self._resources["Index"]
            obj.VS = self._vs
            obj.DS = self._docstore
            obj.FSPath = self._fs_path
            obj.user_id = user_id
            retrievers.append(obj)

        return retrievers
