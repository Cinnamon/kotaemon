from typing import Any

from ktem.index.file import FileIndex

from ..base import BaseFileIndexIndexing, BaseFileIndexRetriever
from .nano_pipelines import NaNoGraphRAGIndexingPipeline, NaNoGraphRAGRetrieverPipeline


class NaNoGraphRAGIndex(FileIndex):
    def _setup_indexing_cls(self):
        self._indexing_pipeline_cls = NaNoGraphRAGIndexingPipeline

    def _setup_retriever_cls(self):
        self._retriever_pipeline_cls = [NaNoGraphRAGRetrieverPipeline]

    def get_indexing_pipeline(self, settings, user_id) -> BaseFileIndexIndexing:
        """Define the interface of the indexing pipeline"""

        obj = super().get_indexing_pipeline(settings, user_id)
        # disable vectorstore for this kind of Index
        obj.VS = None

        return obj

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
