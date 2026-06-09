import abc
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from kotaemon.indices.stores import ChunkRelationStore
from kotaemon.storages import BaseDocumentStore, BaseVectorStore


@dataclass(kw_only=True)
class BaseRetriever:
    """Base interface for file index retrieval pipelines.

    Subclasses must implement:
        - run(self, *args, **kwargs): execute the retrieval
        - get_pipeline(cls, user_settings, index_settings, selected):
          return a fully-initialized pipeline instance

    Resources injected at runtime:
        - chunk_relations: source-to-chunk relation store
        - VS: VectorStore
        - DS: DocStore
        - FSPath: file storage path
        - user_id: the current user id
    """

    chunk_relations: ChunkRelationStore
    VS: BaseVectorStore
    DS: BaseDocumentStore
    FSPath: Path
    user_id: int

    @classmethod
    def get_user_settings(cls) -> dict:
        """Get user-facing settings for this retriever.

        Returns:
            dict: settings in ``ktem.settings.SettingItem`` format
        """
        return {}

    @classmethod
    @abc.abstractmethod
    def get_pipeline(
        cls,
        user_settings: dict,
        index_settings: dict,
        selected: Optional[list] = None,
    ) -> "BaseRetriever":
        ...
