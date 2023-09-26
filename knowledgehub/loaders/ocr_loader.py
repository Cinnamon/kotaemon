from pathlib import Path
from typing import List
from uuid import uuid4

import requests
from llama_index.readers.base import BaseReader

from kotaemon.documents import Document

from .utils.table import (
    extract_tables_from_csv_string,
    get_table_from_ocr,
    strip_special_chars_markdown,
)

DEFAULT_OCR_ENDPOINT = "http://127.0.0.1:8000/v2/ai/infer/"


class OCRReader(BaseReader):
    def __init__(self, endpoint: str = DEFAULT_OCR_ENDPOINT):
        """Init the OCR reader with OCR endpoint (FullOCR pipeline)

        Args:
            endpoint: URL to FullOCR endpoint. Defaults to OCR_ENDPOINT.
        """
        super().__init__()
        self.ocr_endpoint = endpoint

    def load_data(
        self,
        file: Path,
        **kwargs,
    ) -> List[Document]:

        # create input params for the requests
        content = open(file, "rb")
        files = {"input": content}
        data = {"job_id": uuid4()}

        # init list of output documents
        documents = []
        all_table_csv_list = []
        all_non_table_texts = []

        # call the API from FullOCR endpoint
        if "response_content" in kwargs:
            # overriding response content if specified
            results = kwargs["response_content"]
        else:
            # call original API
            resp = requests.post(url=self.ocr_endpoint, files=files, data=data)
            results = resp.json()["result"]

        for _id, each in enumerate(results):
            csv_content = each["csv_string"]
            table = each["json"]["table"]
            ocr = each["json"]["ocr"]

            # using helper function to extract list of table texts from FullOCR output
            table_texts = get_table_from_ocr(ocr, table)
            # extract the formatted CSV table from specified text
            csv_list, non_table_text = extract_tables_from_csv_string(
                csv_content, table_texts
            )
            all_table_csv_list.extend([(csv, _id) for csv in csv_list])
            all_non_table_texts.append((non_table_text, _id))

        # create output Document with metadata from table
        documents = [
            Document(
                text=strip_special_chars_markdown(csv),
                metadata={
                    "table_origin": csv,
                    "type": "table",
                    "page_label": page_id + 1,
                    "source": file.name,
                },
                metadata_template="",
                metadata_seperator="",
            )
            for csv, page_id in all_table_csv_list
        ]
        # create Document from non-table text
        documents.extend(
            [
                Document(
                    text=non_table_text,
                    metadata={
                        "page_label": page_id + 1,
                        "source": file.name,
                    },
                )
                for non_table_text, page_id in all_non_table_texts
            ]
        )

        return documents
