import logging
import os
from pathlib import Path
from typing import List, Optional
from uuid import uuid4

import requests
from llama_index.core.readers.base import BaseReader
from tenacity import after_log, retry, stop_after_attempt, wait_exponential

from kotaemon.base import Document

from .utils.pdf_ocr import parse_ocr_output, read_pdf_unstructured
from .utils.table import strip_special_chars_markdown

logger = logging.getLogger(__name__)

DEFAULT_OCR_ENDPOINT = "http://127.0.0.1:8000/v2/ai/infer/"


@retry(
    stop=stop_after_attempt(6),
    wait=wait_exponential(multiplier=20, exp_base=2, min=1, max=1000),
    after=after_log(logger, logging.WARNING),
)
def tenacious_api_post(url, file_path, table_only, **kwargs):
    with file_path.open("rb") as content:
        files = {"input": content}
        data = {"job_id": uuid4(), "table_only": table_only}
        resp = requests.post(url=url, files=files, data=data, **kwargs)
        resp.raise_for_status()
    return resp


class OCRReader(BaseReader):
    """Read PDF using OCR, with high focus on table extraction

    Example:
        ```python
        >> from kotaemon.loaders import OCRReader
        >> reader = OCRReader()
        >> documents = reader.load_data("path/to/pdf")
        ```

    Args:
        endpoint: URL to FullOCR endpoint. If not provided, will look for
            environment variable `OCR_READER_ENDPOINT` or use the default
            `kotaemon.loaders.ocr_loader.DEFAULT_OCR_ENDPOINT`
            (http://127.0.0.1:8000/v2/ai/infer/)
        use_ocr: whether to use OCR to read text (e.g: from images, tables) in the PDF
            If False, only the table and text within table cells will be extracted.
    """

    def __init__(self, endpoint: Optional[str] = None, use_ocr=True):
        """Init the OCR reader with OCR endpoint (FullOCR pipeline)"""
        super().__init__()
        self.ocr_endpoint = endpoint or os.getenv(
            "OCR_READER_ENDPOINT", DEFAULT_OCR_ENDPOINT
        )
        self.use_ocr = use_ocr

    def load_data(
        self, file_path: Path, extra_info: Optional[dict] = None, **kwargs
    ) -> List[Document]:
        """Load data using OCR reader

        Args:
            file_path (Path): Path to PDF file
            debug_path (Path): Path to store debug image output
            artifact_path (Path): Path to OCR endpoints artifacts directory

        Returns:
            List[Document]: list of documents extracted from the PDF file
        """
        file_path = Path(file_path).resolve()

        # call the API from FullOCR endpoint
        if "response_content" in kwargs:
            # overriding response content if specified
            ocr_results = kwargs["response_content"]
        else:
            # call original API
            resp = tenacious_api_post(
                url=self.ocr_endpoint, file_path=file_path, table_only=not self.use_ocr
            )
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
        extra_info = extra_info or {}

        # create output Document with metadata from table
        documents = [
            Document(
                text=strip_special_chars_markdown(table_text),
                metadata={
                    "table_origin": table_text,
                    "type": "table",
                    "page_label": page_id + 1,
                    **extra_info,
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
                    metadata={"page_label": page_id + 1, **extra_info},
                )
                for page_id, non_table_text in texts
            ]
        )

        return documents


class ImageReader(BaseReader):
    """Read PDF using OCR, with high focus on table extraction

    Example:
        ```python
        >> from knowledgehub.loaders import OCRReader
        >> reader = OCRReader()
        >> documents = reader.load_data("path/to/pdf")
        ```

    Args:
        endpoint: URL to FullOCR endpoint. If not provided, will look for
            environment variable `OCR_READER_ENDPOINT` or use the default
            `knowledgehub.loaders.ocr_loader.DEFAULT_OCR_ENDPOINT`
            (http://127.0.0.1:8000/v2/ai/infer/)
        use_ocr: whether to use OCR to read text (e.g: from images, tables) in the PDF
            If False, only the table and text within table cells will be extracted.
    """

    def __init__(self, endpoint: Optional[str] = None):
        """Init the OCR reader with OCR endpoint (FullOCR pipeline)"""
        super().__init__()
        self.ocr_endpoint = endpoint or os.getenv(
            "OCR_READER_ENDPOINT", DEFAULT_OCR_ENDPOINT
        )

    def load_data(
        self, file_path: Path, extra_info: Optional[dict] = None, **kwargs
    ) -> List[Document]:
        """Load data using OCR reader

        Args:
            file_path (Path): Path to PDF file
            debug_path (Path): Path to store debug image output
            artifact_path (Path): Path to OCR endpoints artifacts directory

        Returns:
            List[Document]: list of documents extracted from the PDF file
        """
        file_path = Path(file_path).resolve()

        # call the API from FullOCR endpoint
        if "response_content" in kwargs:
            # overriding response content if specified
            ocr_results = kwargs["response_content"]
        else:
            # call original API
            resp = tenacious_api_post(
                url=self.ocr_endpoint, file_path=file_path, table_only=False
            )
            ocr_results = resp.json()["result"]

        extra_info = extra_info or {}
        result = []
        for ocr_result in ocr_results:
            result.append(
                Document(
                    content=ocr_result["csv_string"],
                    metadata=extra_info,
                )
            )

        return result
