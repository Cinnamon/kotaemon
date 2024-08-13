from ktem.components import get_vectorstore

from kotaemon.storages import BaseVectorStore
from ktem.embeddings.manager import embedding_models_manager
from ktem.index.file import FileIndex

from .pipelines import MetaIndexPipeline


class MetaIndex(FileIndex):
    def _setup_resources(self):
        self._vs: BaseVectorStore = get_vectorstore(f"index_{self.id}")
        self._vs_tag_index: BaseVectorStore = get_vectorstore(f"index_{self.id}_tag")

        self._resources = {
            "VectorStore": self._vs,
            "VectorStoreTagIndex": self._vs_tag_index,
        }

    def _setup_retriever_cls(self):
        pass

    def _setup_indexing_cls(self):
        self._indexing_pipeline_cls = MetaIndexPipeline

    def on_delete(self):
        """Clean up the index when the user delete it"""
        super().on_delete()
        self._vs_tag_index.drop()

    def get_indexing_pipeline(
        self,
        user_id,
        tag_id
    ) -> MetaIndexPipeline:
        """Define the interface of the indexing pipeline"""
        obj = self._indexing_pipeline_cls()
        obj.VS = self._vs
        obj.VS_tag_index = self._vs_tag_index
        obj.user_id = user_id
        obj.tag_id = tag_id
        obj.private = self.config.get("private", False)
        obj.embedding = embedding_models_manager.get_default()

        return obj
