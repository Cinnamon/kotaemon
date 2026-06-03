from typing import Any

from ktem.index.file import FileIndex

from ..base import BaseFileIndexIndexing, BaseFileIndexRetriever
from .pipelines import GraphRAGIndexingPipeline, GraphRAGRetrieverPipeline


class GraphRAGIndex(FileIndex):
    def _setup_indexing_cls(self):
        self._indexing_pipeline_cls = GraphRAGIndexingPipeline

    def _setup_retriever_cls(self):
        self._retriever_pipeline_cls = [GraphRAGRetrieverPipeline]

    def get_indexing_pipeline(self, settings, user_id) -> BaseFileIndexIndexing:
        """Define the interface of the indexing pipeline"""

        obj = super().get_indexing_pipeline(settings, user_id)
        # disable vectorstore for this kind of Index
        obj.VS = None

        return obj

    def get_retriever_pipelines(
        self, settings: dict, user_id: int, selected: Any = None
    ) -> list["BaseFileIndexRetriever"]:
        file_ids = self._selector_ui.get_selected_ids(selected)
        retrievers = [
            GraphRAGRetrieverPipeline(
                file_ids=file_ids,
                Index=self._resources["Index"],
            )
        ]

        return retrievers
