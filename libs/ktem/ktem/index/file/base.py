from pathlib import Path
from typing import Optional

from kotaemon.base import BaseComponent


class BaseFileIndexRetriever(BaseComponent):
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

    def set_resources(self, resources: dict):
        """Set the resources for the indexing pipeline

        This will setup the tables, the vector store and docstore.

        Args:
            resources (dict): the resources for the indexing pipeline
        """
        self._Source = resources["Source"]
        self._Index = resources["Index"]
        self._VS = resources["VectorStore"]
        self._DS = resources["DocStore"]
        self._fs_path = resources["FileStoragePath"]


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

    def run(self, file_paths: str | Path | list[str | Path], *args, **kwargs):
        """Run the indexing pipeline

        Args:
            file_paths (str | Path | list[str | Path]): the file paths to index
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

    def set_resources(self, resources: dict):
        """Set the resources for the indexing pipeline

        This will setup the tables, the vector store and docstore.

        Args:
            resources (dict): the resources for the indexing pipeline
        """
        self._Source = resources["Source"]
        self._Index = resources["Index"]
        self._VS = resources["VectorStore"]
        self._DS = resources["DocStore"]
        self._fs_path = resources["FileStoragePath"]

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
            shutil.copy(file_path, self._fs_path / paths[-1])

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
