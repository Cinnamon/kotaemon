import abc
from dataclasses import dataclass
from pathlib import Path
from typing import Generator

from kotaemon.base import Document
from kotaemon.indices.stores import ChunkRelationStore, FileSourceStore
from kotaemon.storages import BaseDocumentStore, BaseVectorStore


@dataclass(kw_only=True)
class BaseIndexing:
    """Base interface for file index ingestion pipelines.

    Subclasses must implement:
        - run(self, file_paths): run the indexing pipeline
        - get_pipeline(cls, user_settings, index_settings): return a
          fully-initialized pipeline, ready to be used by ktem

    Resources injected at runtime:
        - file_source: indexed file metadata store
        - chunk_relations: source-to-chunk relation store
        - VS: VectorStore
        - DS: DocStore
        - FSPath: file storage path
        - user_id: the current user id
    """

    file_source: FileSourceStore
    chunk_relations: ChunkRelationStore
    VS: BaseVectorStore
    DS: BaseDocumentStore
    FSPath: Path
    user_id: int
    private: bool
    chunk_size: int
    chunk_overlap: int

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
    def get_pipeline(cls, user_settings: dict, index_settings: dict) -> "BaseIndexing":
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
