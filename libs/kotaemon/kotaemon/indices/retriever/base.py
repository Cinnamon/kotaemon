import abc
from typing import Optional

from kotaemon.base import BaseComponent, Param


class BaseRetriever(BaseComponent):
    """Base interface for file index retrieval pipelines.

    Subclasses must implement:
        - run(self, *args, **kwargs): execute the retrieval
        - get_pipeline(cls, user_settings, index_settings, selected):
          return a fully-initialized pipeline instance

    Resources injected at runtime via Params:
        - Source: SQLAlchemy Source table
        - Index: SQLAlchemy Index table
        - VS: VectorStore
        - DS: DocStore
        - FSPath: file storage path
        - user_id: the current user id
        - engine: SQLAlchemy engine
    """

    Source = Param(help="The SQLAlchemy Source table")
    Index = Param(help="The SQLAlchemy Index table")
    VS = Param(help="The VectorStore")
    DS = Param(help="The DocStore")
    FSPath = Param(help="The file storage path")
    user_id = Param(help="The user id")
    engine = Param(help="The SQLAlchemy engine")

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
