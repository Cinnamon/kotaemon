from typing import Any

from ..base import BaseFileIndexRetriever
from .graph_index import GraphRAGIndex
from .nano_pipelines import NanoGraphRAGIndexingPipeline, NanoGraphRAGRetrieverPipeline


class NanoGraphRAGIndex(GraphRAGIndex):
    def _setup_indexing_cls(self):
        self._indexing_pipeline_cls = NanoGraphRAGIndexingPipeline

    def _setup_retriever_cls(self):
        self._retriever_pipeline_cls = [NanoGraphRAGRetrieverPipeline]

    def get_retriever_pipelines(
        self, settings: dict, user_id: int, selected: Any = None
    ) -> list["BaseFileIndexRetriever"]:
        _, file_ids, _ = selected
        retrievers = [
            NanoGraphRAGRetrieverPipeline(
                file_ids=file_ids,
                Index=self._resources["Index"],
            )
        ]

        return retrievers
