from ktem.components import get_vectorstore

from kotaemon.storages import BaseVectorStore
from ktem.embeddings.manager import embedding_models_manager
from ktem.index.file import FileIndex

from .pipelines import MetaIndexPipeline


class MetaIndex(FileIndex):
    def _setup_resources(self):
        super()._setup_resources()

        self._vs: BaseVectorStore = get_vectorstore(f"index_{self.id}")
        self._vs_tag_index: BaseVectorStore = get_vectorstore(f"index_{self.id}_tag")

        updated_resources = {
            "VectorStore": self._vs,
            "VectorStoreTagIndex": self._vs_tag_index,
        }

        self._resources.update(updated_resources)

    def get_user_settings(self):
        return {}

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
    ) -> MetaIndexPipeline:
        """Define the interface of the indexing pipeline"""
        obj = self._indexing_pipeline_cls()
        obj.VS = self._resources["VectorStore"]
        obj.VS_tag_index = self._resources["VectorStoreTagIndex"]
        obj.user_id = user_id
        # obj.tag_id = tag_id
        obj.private = self.config.get("private", False)
        obj.embedding = embedding_models_manager.get_default()

        return obj
