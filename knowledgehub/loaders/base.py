from pathlib import Path
from typing import Any, List, Type, Union

from llama_index import download_loader
from llama_index.readers.base import BaseReader

from ..documents.base import Document


class AutoReader(BaseReader):
    """General auto reader for a variety of files. (based on llama-hub)"""

    def __init__(self, reader_type: Union[str, Type[BaseReader]]) -> None:
        """Init reader using string identifier or class name from llama-hub"""

        if isinstance(reader_type, str):
            self._reader = download_loader(reader_type)()
        else:
            self._reader = reader_type()

    def load_data(self, file: Union[Path, str], **kwargs: Any) -> List[Document]:
        documents = self._reader.load_data(file=file, **kwargs)

        # convert Document to new base class from kotaemon
        converted_documents = [Document.from_dict(doc.to_dict()) for doc in documents]
        return converted_documents
