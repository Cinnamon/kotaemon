from typing import Any

from ..base import BaseFileIndexRetriever
from .nano_pipelines import NaNoGraphRAGIndexingPipeline, NaNoGraphRAGRetrieverPipeline

from .graph_index import GraphRAGIndex


class NaNoGraphRAGIndex(GraphRAGIndex):
    def _setup_indexing_cls(self):
        self._indexing_pipeline_cls = NaNoGraphRAGIndexingPipeline

    def _setup_retriever_cls(self):
        self._retriever_pipeline_cls = [NaNoGraphRAGRetrieverPipeline]

    def get_retriever_pipelines(
        self, settings: dict, user_id: int, selected: Any = None
    ) -> list["BaseFileIndexRetriever"]:
        _, file_ids, _ = selected
        retrievers = [
            NaNoGraphRAGRetrieverPipeline(
                file_ids=file_ids,
                Index=self._resources["Index"],
            )
        ]

        return retrievers
