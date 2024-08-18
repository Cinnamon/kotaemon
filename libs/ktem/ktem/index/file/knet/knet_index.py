from typing import Any

from ktem.index.file import FileIndex

from ..base import BaseFileIndexIndexing, BaseFileIndexRetriever
from .pipelines import KnetIndexingPipeline, KnetRetrievalPipeline


class KnowledgeNetworkFileIndex(FileIndex):
    @classmethod
    def get_admin_settings(cls):
        admin_settings = super().get_admin_settings()

        # remove embedding from admin settings
        # as we don't need it
        admin_settings.pop("embedding")
        return admin_settings

    def _setup_indexing_cls(self):
        self._indexing_pipeline_cls = KnetIndexingPipeline

    def _setup_retriever_cls(self):
        self._retriever_pipeline_cls = [KnetRetrievalPipeline]

    def get_indexing_pipeline(self, settings, user_id) -> BaseFileIndexIndexing:
        """Define the interface of the indexing pipeline"""

        obj = super().get_indexing_pipeline(settings, user_id)
        # disable vectorstore for this kind of Index
        # also set the collection_name for API call
        obj.VS = None
        obj.collection_name = f"kh_index_{self.id}"

        return obj

    def get_retriever_pipelines(
        self, settings: dict, user_id: int, selected: Any = None
    ) -> list["BaseFileIndexRetriever"]:
        retrievers = super().get_retriever_pipelines(settings, user_id, selected)

        for obj in retrievers:
            # disable vectorstore for this kind of Index
            # also set the collection_name for API call
            obj.VS = None
            obj.collection_name = f"kh_index_{self.id}"

        return retrievers
