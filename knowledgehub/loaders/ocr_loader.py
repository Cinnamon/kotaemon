from pathlib import Path
from typing import List
from uuid import uuid4

import requests
from llama_index.readers.base import BaseReader

from kotaemon.base import Document

from .utils.pdf_ocr import parse_ocr_output, read_pdf_unstructured
from .utils.table import strip_special_chars_markdown

DEFAULT_OCR_ENDPOINT = "http://127.0.0.1:8000/v2/ai/infer/"


class OCRReader(BaseReader):
    def __init__(self, endpoint: str = DEFAULT_OCR_ENDPOINT, use_ocr=True):
        """Init the OCR reader with OCR endpoint (FullOCR pipeline)

        Args:
            endpoint: URL to FullOCR endpoint. Defaults to OCR_ENDPOINT.
            use_ocr: whether to use OCR to read text
                (e.g: from images, tables) in the PDF
        """
        super().__init__()
        self.ocr_endpoint = endpoint
        self.use_ocr = use_ocr

    def load_data(self, file_path: Path, **kwargs) -> List[Document]:
        """Load data using OCR reader

        Args:
            file_path (Path): Path to PDF file
            debug_path (Path): Path to store debug image output
            artifact_path (Path): Path to OCR endpoints artifacts directory

        Returns:
            List[Document]: list of documents extracted from the PDF file
        """
        file_path = Path(file_path).resolve()

        with file_path.open("rb") as content:
            files = {"input": content}
            data = {"job_id": uuid4(), "table_only": not self.use_ocr}

            # call the API from FullOCR endpoint
            if "response_content" in kwargs:
                # overriding response content if specified
                ocr_results = kwargs["response_content"]
            else:
                # call original API
                resp = requests.post(url=self.ocr_endpoint, files=files, data=data)
                ocr_results = resp.json()["result"]

        debug_path = kwargs.pop("debug_path", None)
        artifact_path = kwargs.pop("artifact_path", None)

        # read PDF through normal reader (unstructured)
        pdf_page_items = read_pdf_unstructured(file_path)
        # merge PDF text output with OCR output
        tables, texts = parse_ocr_output(
            ocr_results,
            pdf_page_items,
            debug_path=debug_path,
            artifact_path=artifact_path,
        )

        # create output Document with metadata from table
        documents = [
            Document(
                text=strip_special_chars_markdown(table_text),
                metadata={
                    "table_origin": table_text,
                    "type": "table",
                    "page_label": page_id + 1,
                    "source": file_path.name,
                    "file_path": str(file_path),
                    "file_name": file_path.name,
                    "filename": str(file_path),
                },
                metadata_template="",
                metadata_seperator="",
            )
            for page_id, table_text in tables
        ]
        # create Document from non-table text
        documents.extend(
            [
                Document(
                    text=non_table_text,
                    metadata={
                        "page_label": page_id + 1,
                        "source": file_path.name,
                        "file_path": str(file_path),
                        "file_name": file_path.name,
                        "filename": str(file_path),
                    },
                )
                for page_id, non_table_text in texts
            ]
        )

        return documents
