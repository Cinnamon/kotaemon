import abc
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase

from kotaemon.storages import BaseDocumentStore, BaseVectorStore


@dataclass(kw_only=True)
class BaseRetriever:
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

    Source: type[DeclarativeBase]
    Index: type[DeclarativeBase]
    VS: BaseVectorStore
    DS: BaseDocumentStore
    FSPath: Path
    user_id: int
    engine: Engine

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
