from pathlib import Path
from typing import Any, List, Type, Union

from llama_index import SimpleDirectoryReader, download_loader
from llama_index.readers.base import BaseReader

from ..base import BaseComponent, Document


class AutoReader(BaseComponent):
    """General auto reader for a variety of files. (based on llama-hub)"""

    def __init__(self, reader_type: Union[str, Type[BaseReader]]) -> None:
        """Init reader using string identifier or class name from llama-hub"""

        if isinstance(reader_type, str):
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


class LIBaseReader(BaseComponent):
    _reader_class: Type[BaseReader]

    def __init__(self, *args, **kwargs):
        if self._reader_class is None:
            raise AttributeError(
                "Require `_reader_class` to set a BaseReader class from LlamarIndex"
            )

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


class DirectoryReader(LIBaseReader):
    _reader_class = SimpleDirectoryReader
