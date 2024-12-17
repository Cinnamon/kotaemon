from typing import Any

from ..base import BaseFileIndexRetriever
from .graph_index import GraphRAGIndex
from .lightrag_pipelines import LightRAGIndexingPipeline, LightRAGRetrieverPipeline


class LightRAGIndex(GraphRAGIndex):
    def _setup_indexing_cls(self):
        self._indexing_pipeline_cls = LightRAGIndexingPipeline

    def _setup_retriever_cls(self):
        self._retriever_pipeline_cls = [LightRAGRetrieverPipeline]

    def get_retriever_pipelines(
        self, settings: dict, user_id: int, selected: Any = None
    ) -> list["BaseFileIndexRetriever"]:
        _, file_ids, _ = selected
        # retrieval settings
        prefix = f"index.options.{self.id}."
        search_type = settings.get(prefix + "search_type", "local")

        retrievers = [
            LightRAGRetrieverPipeline(
                file_ids=file_ids,
                Index=self._resources["Index"],
                search_type=search_type,
            )
        ]

        return retrievers
