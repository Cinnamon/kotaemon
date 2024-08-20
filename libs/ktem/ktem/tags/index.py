from ktem.db.models import engine
from ktem.index.file import FileIndex
from ktem.index.file.base import BaseFileIndexIndexing

from .pipelines import MetaIndexPipeline


class TagIndex(FileIndex):
    @classmethod
    def get_admin_settings_gradio(cls):
        from ktem.tags.crud import TagCRUD

        tag_crud = TagCRUD(engine)
        tag_choices = tag_crud.get_all_tags()

        settings = {
            "label": "Meta tags",
            "id": "tags",
            "choices": tag_choices,
        }
        return settings

    @classmethod
    def get_admin_settings(cls):
        from ktem.llms.manager import llms

        llm_default = llms.get_default_name()
        llm_choices = list(llms.options().keys())

        settings = super().get_admin_settings()
        settings["llm"] = {
            "name": "LLM for tagging",
            "value": llm_default,
            "component": "dropdown",
            "choices": llm_choices,
            "info": "The name of LLM model to use for tagging process.",
        }
        return settings

    def _setup_indexing_cls(self):
        self._indexing_pipeline_cls = MetaIndexPipeline

    def on_delete(self):
        """Clean up the index when the user delete it"""
        # TODO: implement the clean up logic for
        # additional vectorstore and chunk_tag_index
        super().on_delete()

    def get_indexing_pipeline(self, settings, user_id) -> BaseFileIndexIndexing:
        """Define the interface of the indexing pipeline"""

        obj = super().get_indexing_pipeline(settings, user_id)
        # disable vectorstore for this kind of Index
        obj.VS = None

        return obj
