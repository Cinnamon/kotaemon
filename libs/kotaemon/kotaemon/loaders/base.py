from pathlib import Path
from typing import TYPE_CHECKING, Any, List, Type, Union

from kotaemon.base import BaseComponent, Document

if TYPE_CHECKING:
    from llama_index.core.readers.base import BaseReader as LIBaseReader


class BaseReader(BaseComponent):
    """The base class for all readers"""

    ...


class AutoReader(BaseReader):
    """General auto reader for a variety of files. (based on llama-hub)"""

    def __init__(self, reader_type: Union[str, Type["LIBaseReader"]]) -> None:
        """Init reader using string identifier or class name from llama-hub"""

        if isinstance(reader_type, str):
            from llama_index.core import download_loader

            self._reader = download_loader(reader_type)()
        else:
            self._reader = reader_type()
        super().__init__()

    def load_data(self, file: Union[Path, str], **kwargs: Any) -> List[Document]:
        documents = self._reader.load_data(file=file, **kwargs)

        # convert Document to new base class from kotaemon
        converted_documents = [Document.from_dict(doc.to_dict()) for doc in documents]
        return converted_documents

    def run(self, file: Union[Path, str], **kwargs: Any) -> List[Document]:
        return self.load_data(file=file, **kwargs)


class LIReaderMixin(BaseComponent):
    """Base wrapper around llama-index reader

    To use the LIBaseReader, you need to implement the _get_wrapped_class method to
    return the relevant llama-index reader class that you want to wrap.

    Example:

        ```python
        class DirectoryReader(LIBaseReader):
            def _get_wrapped_class(self) -> Type["BaseReader"]:
                from llama_index import SimpleDirectoryReader

                return SimpleDirectoryReader
        ```
    """

    def _get_wrapped_class(self) -> Type["LIBaseReader"]:
        raise NotImplementedError(
            "Please return the relevant llama-index class in in _get_wrapped_class"
        )

    def __init__(self, *args, **kwargs):
        self._reader_class = self._get_wrapped_class()
        self._reader = self._reader_class(*args, **kwargs)
        super().__init__()

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("_"):
            return super().__setattr__(name, value)

        return setattr(self._reader, name, value)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._reader, name)

    def load_data(self, *args, **kwargs: Any) -> List[Document]:
        documents = self._reader.load_data(*args, **kwargs)

        # convert Document to new base class from kotaemon
        converted_documents = [Document.from_dict(doc.to_dict()) for doc in documents]
        return converted_documents

    def run(self, *args, **kwargs: Any) -> List[Document]:
        return self.load_data(*args, **kwargs)
