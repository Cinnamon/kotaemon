from typing import Any, Optional
from uuid import uuid4

from ktem.db.engine import engine
from sqlalchemy.orm import Session

from ..base import BaseFileIndexIndexing, BaseFileIndexRetriever
from .graph_index import GraphRAGIndex
from .nano_pipelines import NanoGraphRAGIndexingPipeline, NanoGraphRAGRetrieverPipeline


class NanoGraphRAGIndex(GraphRAGIndex):
    def __init__(self, app, id: int, name: str, config: dict):
        super().__init__(app, id, name, config)
        self._collection_graph_id: Optional[str] = None

    def _setup_indexing_cls(self):
        self._indexing_pipeline_cls = NanoGraphRAGIndexingPipeline

    def _setup_retriever_cls(self):
        self._retriever_pipeline_cls = [NanoGraphRAGRetrieverPipeline]

    def _get_or_create_collection_graph_id(self):
        if self._collection_graph_id:
            return self._collection_graph_id

        # Try to find existing graph ID for this collection
        with Session(engine) as session:
            result = (
                session.query(self._resources["Index"].target_id)  # type: ignore
                .filter(
                    self._resources["Index"].relation_type == "graph"  # type: ignore
                )
                .first()
            )
            if result:
                self._collection_graph_id = result[0]
            else:
                self._collection_graph_id = str(uuid4())
        return self._collection_graph_id

    def get_indexing_pipeline(self, settings, user_id) -> BaseFileIndexIndexing:
        pipeline = super().get_indexing_pipeline(settings, user_id)
        # indexing settings
        prefix = f"index.options.{self.id}."
        striped_settings = {
            key[len(prefix) :]: value
            for key, value in settings.items()
            if key.startswith(prefix)
        }
        # set the prompts
        pipeline.prompts = striped_settings
        # set collection graph id
        pipeline.collection_graph_id = self._get_or_create_collection_graph_id()
        # set index batch size
        pipeline.index_batch_size = striped_settings.get(
            "batch_size", pipeline.index_batch_size
        )
        return pipeline

    def get_retriever_pipelines(
        self, settings: dict, user_id: int, selected: Any = None
    ) -> list["BaseFileIndexRetriever"]:
        file_ids = self._selector_ui.get_selected_ids(selected)
        # retrieval settings
        prefix = f"index.options.{self.id}."
        search_type = settings.get(prefix + "search_type", "local")

        retrievers = [
            NanoGraphRAGRetrieverPipeline(
                file_ids=file_ids,
                Index=self._resources["Index"],
                search_type=search_type,
            )
        ]

        return retrievers
