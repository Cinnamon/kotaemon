from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Any, List, Type, Union

from kotaemon.base import Document

if TYPE_CHECKING:
    from llama_index.core.readers.base import BaseReader as LIBaseReader


class BaseReader(ABC):
    """The base class for all readers."""

    @abstractmethod
    def run(self, file: Union[Path, str], **kwargs: Any) -> List[Document]:
        """Load documents from *file*."""


class AutoReader(BaseReader):
    """General auto reader for a variety of files. (based on llama-hub)"""

    def __init__(self, reader_type: Union[str, Type["LIBaseReader"]]) -> None:
        import importlib

        if isinstance(reader_type, str):
            try:
                module = importlib.import_module("llama_index.readers.file")
                reader_cls = getattr(module, reader_type)
                self._reader = reader_cls()
            except (ImportError, AttributeError):
                from llama_index.core import download_loader

                self._reader = download_loader(reader_type)()
        else:
            self._reader = reader_type()

    def load_data(self, file: Union[Path, str], **kwargs: Any) -> List[Document]:
        documents = self._reader.load_data(file=file, **kwargs)
        return [Document.from_dict(doc.to_dict()) for doc in documents]

    def run(self, file: Union[Path, str], **kwargs: Any) -> List[Document]:
        return self.load_data(file=file, **kwargs)


class LIReaderMixin(BaseReader):
    """Base wrapper around llama-index reader."""

    def _get_wrapped_class(self) -> Type["LIBaseReader"]:
        raise NotImplementedError(
            "Please return the relevant llama-index class in _get_wrapped_class"
        )

    def __init__(self, *args, **kwargs):
        self._reader_class = self._get_wrapped_class()
        self._reader = self._reader_class(*args, **kwargs)

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("_"):
            return super().__setattr__(name, value)
        return setattr(self._reader, name, value)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._reader, name)

    def load_data(self, *args, **kwargs: Any) -> List[Document]:
        documents = self._reader.load_data(*args, **kwargs)
        return [Document.from_dict(doc.to_dict()) for doc in documents]

    def run(self, *args, **kwargs: Any) -> List[Document]:
        return self.load_data(*args, **kwargs)
