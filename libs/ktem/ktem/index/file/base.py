from pathlib import Path
from typing import Generator, Optional

from kotaemon.base import BaseComponent, Document, Param


class BaseFileIndexRetriever(BaseComponent):

    Source = Param(help="The SQLAlchemy Source table")
    Index = Param(help="The SQLAlchemy Index table")
    VS = Param(help="The VectorStore")
    DS = Param(help="The DocStore")
    FSPath = Param(help="The file storage path")
    user_id = Param(help="The user id")

    @classmethod
    def get_user_settings(cls) -> dict:
        """Get the user settings for indexing

        Returns:
            dict: user settings in the dictionary format of
                `ktem.settings.SettingItem`
        """
        return {}

    @classmethod
    def get_pipeline(
        cls,
        user_settings: dict,
        index_settings: dict,
        selected: Optional[list] = None,
    ) -> "BaseFileIndexRetriever":
        raise NotImplementedError


class BaseFileIndexIndexing(BaseComponent):
    """The pipeline to index information into the data store

    You should define the following method:
        - run(self, file_paths): run the indexing given the pipeline
        - get_pipeline(cls, user_settings, index_settings): return the
          fully-initialized pipeline, ready to be used by ktem.

    You will have access to the following resources:
        - self._Source: the source table
        - self._Index: the index table
        - self._VS: the vector store
        - self._DS: the docstore
    """

    Source = Param(help="The SQLAlchemy Source table")
    Index = Param(help="The SQLAlchemy Index table")
    VS = Param(help="The VectorStore")
    DS = Param(help="The DocStore")
    FSPath = Param(help="The file storage path")
    user_id = Param(help="The user id")
    private = Param(False, help="Whether this is private index")

    def run(
        self, file_paths: str | Path | list[str | Path], *args, **kwargs
    ) -> tuple[list[str | None], list[str | None]]:
        """Run the indexing pipeline

        Args:
            file_paths (str | Path | list[str | Path]): the file paths to index

        Returns:
            - the indexed file ids (each file id corresponds to an input file path, or
                None if the indexing failed for that file path)
            - the error messages (each error message corresponds to an input file path,
                or None if the indexing was successful for that file path)
        """
        raise NotImplementedError

    def stream(
        self, file_paths: str | Path | list[str | Path], *args, **kwargs
    ) -> Generator[
        Document, None, tuple[list[str | None], list[str | None], list[Document]]
    ]:
        """Stream the indexing pipeline

        Args:
            file_paths (str | Path | list[str | Path]): the file paths to index

        Yields:
            Document: the output message to the UI, must have channel == index or debug

        Returns:
            - the indexed file ids (each file id corresponds to an input file path, or
                None if the indexing failed for that file path)
            - the error messages (each error message corresponds to an input file path,
                or None if the indexing was successful for that file path)
            - the indexed documents in form of list[Documents]
        """
        raise NotImplementedError

    @classmethod
    def get_pipeline(
        cls, user_settings: dict, index_settings: dict
    ) -> "BaseFileIndexIndexing":
        raise NotImplementedError

    @classmethod
    def get_user_settings(cls) -> dict:
        """Get the user settings for indexing

        Returns:
            dict: user settings in the dictionary format of
                `ktem.settings.SettingItem`
        """
        return {}

    def copy_to_filestorage(
        self, file_paths: str | Path | list[str | Path]
    ) -> list[str]:
        """Copy to file storage and return the new path, relative to the file storage

        Args:
            file_path: the file path to copy

        Returns:
            the new file paths, relative to the file storage
        """
        import shutil
        from hashlib import sha256

        if not isinstance(file_paths, list):
            file_paths = [file_paths]

        paths = []
        for file_path in file_paths:
            with open(file_path, "rb") as f:
                paths.append(sha256(f.read()).hexdigest())
            shutil.copy(file_path, self.FSPath / paths[-1])

        return paths

    def get_filestorage_path(self, rel_paths: str | list[str]) -> list[str]:
        """Get the file storage path for the relative path

        Args:
            rel_paths: the relative path to the file storage

        Returns:
            the absolute file storage path to the file
        """
        raise NotImplementedError

    def warning(self, msg):
        """Log a warning message

        Args:
            msg: the message to log
        """
        print(msg)

    def rebuild_index(self):
        """Rebuild the index"""
        raise NotImplementedError
