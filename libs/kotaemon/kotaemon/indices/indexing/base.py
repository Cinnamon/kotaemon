import abc
from pathlib import Path
from typing import Generator

from kotaemon.base import BaseComponent, Document, Param


class BaseIndexing(BaseComponent):
    """Base interface for file index ingestion pipelines.

    Subclasses must implement:
        - run(self, file_paths): run the indexing pipeline
        - get_pipeline(cls, user_settings, index_settings): return a
          fully-initialized pipeline, ready to be used by ktem

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
    private = Param(False, help="Whether this is private index")
    chunk_size = Param(help="Chunk size for this index")
    chunk_overlap = Param(help="Chunk overlap for this index")

    @abc.abstractmethod
    def run(
        self,
        file_paths: str | Path | list[str | Path],
        *args,
        **kwargs,
    ) -> tuple[list[str | None], list[str | None]]:
        """Run the indexing pipeline.

        Args:
            file_paths: the file paths to index

        Returns:
            - indexed file ids (one per input path, or None on failure)
            - error messages (one per input path, or None on success)
        """
        ...

    def stream(
        self,
        file_paths: str | Path | list[str | Path],
        *args,
        **kwargs,
    ) -> Generator[
        Document, None, tuple[list[str | None], list[str | None], list[Document]]
    ]:
        """Stream the indexing pipeline.

        Args:
            file_paths: the file paths to index

        Yields:
            Document: output message to the UI
                (must have channel == index or debug)

        Returns:
            - indexed file ids (one per input path, or None on failure)
            - error messages (one per input path, or None on success)
            - indexed documents as list[Document]
        """
        raise NotImplementedError

    @classmethod
    def get_user_settings(cls) -> dict:
        """Get user-facing settings for this indexer.

        Returns:
            dict: settings in ``ktem.settings.SettingItem`` format
        """
        return {}

    @classmethod
    @abc.abstractmethod
    def get_pipeline(
        cls, user_settings: dict, index_settings: dict
    ) -> "BaseIndexing":
        ...

    def warning(self, msg: str) -> None:
        """Log a warning message.

        Args:
            msg: the message to log
        """
        print(msg)

    def rebuild_index(self) -> None:
        """Rebuild the index."""
        raise NotImplementedError
