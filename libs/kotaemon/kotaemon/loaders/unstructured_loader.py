"""Unstructured file reader.

A parser for unstructured text files using Unstructured.io.
Supports .txt, .docx, .pptx, .jpg, .png, .eml, .html, and .pdf documents.

To use .doc and .xls parser, install

sudo apt-get install -y libmagic-dev poppler-utils libreoffice
pip install xlrd

"""
from pathlib import Path
from typing import Any, Dict, List, Optional

from llama_index.core.readers.base import BaseReader

from kotaemon.base import Document


class UnstructuredReader(BaseReader):
    """General unstructured text reader for a variety of files."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Init params."""
        super().__init__(*args)  # not passing kwargs to parent bc it cannot accept it

        self.api = False  # we default to local
        if "url" in kwargs:
            self.server_url = str(kwargs["url"])
            self.api = True  # is url was set, switch to api
        else:
            self.server_url = "http://localhost:8000"

        if "api" in kwargs:
            self.api = kwargs["api"]

        self.api_key = ""
        if "api_key" in kwargs:
            self.api_key = kwargs["api_key"]

    """ Loads data using Unstructured.io

        Depending on the construction if url is set or api = True
        it'll parse file using API call, else parse it locally
        additional_metadata is extended by the returned metadata if
        split_documents is True

        Returns list of documents
    """

    def load_data(
        self,
        file: Path,
        extra_info: Optional[Dict] = None,
        split_documents: Optional[bool] = False,
        **kwargs,
    ) -> List[Document]:
        """If api is set, parse through api"""
        file_path_str = str(file)
        if self.api:
            from unstructured.partition.api import partition_via_api

            elements = partition_via_api(
                filename=file_path_str,
                api_key=self.api_key,
                api_url=self.server_url + "/general/v0/general",
            )
        else:
            """Parse file locally"""
            from unstructured.partition.auto import partition

            elements = partition(filename=file_path_str)

        """ Process elements """
        docs = []
        file_name = Path(file).name
        file_path = str(Path(file).resolve())
        if split_documents:
            for node in elements:
                metadata = {"file_name": file_name, "file_path": file_path}
                if hasattr(node, "metadata"):
                    """Load metadata fields"""
                    for field, val in vars(node.metadata).items():
                        if field == "_known_field_names":
                            continue
                        # removing coordinates because it does not serialize
                        # and dont want to bother with it
                        if field == "coordinates":
                            continue
                        # removing bc it might cause interference
                        if field == "parent_id":
                            continue
                        metadata[field] = val

                if extra_info is not None:
                    metadata.update(extra_info)

                metadata["file_name"] = file_name
                docs.append(Document(text=node.text, metadata=metadata))

        else:
            text_chunks = [" ".join(str(el).split()) for el in elements]
            metadata = {"file_name": file_name, "file_path": file_path}

            if extra_info is not None:
                metadata.update(extra_info)

            # Create a single document by joining all the texts
            docs.append(Document(text="\n\n".join(text_chunks), metadata=metadata))

        return docs
