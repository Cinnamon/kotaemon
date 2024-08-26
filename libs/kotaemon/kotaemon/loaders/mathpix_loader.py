import json
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from langchain.utils import get_from_dict_or_env
from llama_index.core.readers.base import BaseReader

from kotaemon.base import Document

from .utils.table import parse_markdown_text_to_tables, strip_special_chars_markdown


# MathpixPDFLoader implementation taken largely from Daniel Gross's:
# https://gist.github.com/danielgross/3ab4104e14faccc12b49200843adab21
class MathpixPDFReader(BaseReader):
    """Load `PDF` files using `Mathpix` service."""

    def __init__(
        self,
        processed_file_format: str = "md",
        max_wait_time_seconds: int = 500,
        should_clean_pdf: bool = True,
        **kwargs: Any,
    ) -> None:
        """Initialize with a file path.

        Args:
            processed_file_format: a format of the processed file. Default is   "mmd".
            max_wait_time_seconds: a maximum time to wait for the response from
                the server. Default is 500.
            should_clean_pdf: a flag to clean the PDF file. Default is False.
            **kwargs: additional keyword arguments.
        """
        self.mathpix_api_key = get_from_dict_or_env(
            kwargs, "mathpix_api_key", "MATHPIX_API_KEY", default="empty"
        )
        self.mathpix_api_id = get_from_dict_or_env(
            kwargs, "mathpix_api_id", "MATHPIX_API_ID", default="empty"
        )
        self.processed_file_format = processed_file_format
        self.max_wait_time_seconds = max_wait_time_seconds
        self.should_clean_pdf = should_clean_pdf
        super().__init__()

    @property
    def _mathpix_headers(self) -> Dict[str, str]:
        return {"app_id": self.mathpix_api_id, "app_key": self.mathpix_api_key}

    @property
    def url(self) -> str:
        return "https://api.mathpix.com/v3/pdf"

    @property
    def data(self) -> dict:
        options = {
            "conversion_formats": {self.processed_file_format: True},
            "enable_tables_fallback": True,
        }
        return {"options_json": json.dumps(options)}

    def send_pdf(self, file_path) -> str:
        with open(file_path, "rb") as f:
            files = {"file": f}
            response = requests.post(
                self.url, headers=self._mathpix_headers, files=files, data=self.data
            )
        response_data = response.json()
        if "pdf_id" in response_data:
            pdf_id = response_data["pdf_id"]
            return pdf_id
        else:
            raise ValueError("Unable to send PDF to Mathpix.")

    def wait_for_processing(self, pdf_id: str) -> None:
        """Wait for processing to complete.

        Args:
            pdf_id: a PDF id.

        Returns: None
        """
        url = self.url + "/" + pdf_id
        for _ in range(0, self.max_wait_time_seconds, 5):
            response = requests.get(url, headers=self._mathpix_headers)
            response_data = response.json()
            status = response_data.get("status", None)

            if status == "completed":
                return
            elif status == "error":
                raise ValueError("Unable to retrieve PDF from Mathpix")
            else:
                print(response_data)
                print(url)
                time.sleep(5)
        raise TimeoutError

    def get_processed_pdf(self, pdf_id: str) -> str:
        self.wait_for_processing(pdf_id)
        url = f"{self.url}/{pdf_id}.{self.processed_file_format}"
        response = requests.get(url, headers=self._mathpix_headers)
        return response.content.decode("utf-8")

    def clean_pdf(self, contents: str) -> str:
        """Clean the PDF file.

        Args:
            contents: a PDF file contents.

        Returns:

        """
        contents = "\n".join(
            [line for line in contents.split("\n") if not line.startswith("![]")]
        )
        # replace \section{Title} with # Title
        contents = contents.replace("\\section{", "# ")
        # replace the "\" slash that Mathpix adds to escape $, %, (, etc.

        # http:// or https:// followed by anything but a closing paren
        url_regex = "http[s]?://[^)]+"
        markup_regex = r"\[]\(\s*({0})\s*\)".format(url_regex)
        contents = (
            contents.replace(r"\$", "$")
            .replace(r"\%", "%")
            .replace(r"\(", "(")
            .replace(r"\)", ")")
            .replace("$\\begin{array}", "")
            .replace("\\end{array}$", "")
            .replace("\\\\", "")
            .replace("\\text", "")
            .replace("}", "")
            .replace("{", "")
            .replace("\\mathrm", "")
        )
        contents = re.sub(markup_regex, "", contents)
        return contents

    def load_data(
        self, file_path: Path, extra_info: Optional[dict] = None, **kwargs
    ) -> List[Document]:
        if "response_content" in kwargs:
            # overriding response content if specified
            content = kwargs["response_content"]
        else:
            # call original API
            pdf_id = self.send_pdf(file_path)
            content = self.get_processed_pdf(pdf_id)

        if self.should_clean_pdf:
            content = self.clean_pdf(content)
        tables, texts = parse_markdown_text_to_tables(content)
        documents = []
        for table in tables:
            text = strip_special_chars_markdown(table)
            metadata = {
                "table_origin": table,
                "type": "table",
            }
            if extra_info:
                metadata.update(extra_info)
            documents.append(
                Document(
                    text=text,
                    metadata=metadata,
                    metadata_template="",
                    metadata_seperator="",
                )
            )

        for text in texts:
            metadata = {"source": file_path.name, "type": "text"}
            documents.append(Document(text=text, metadata=metadata))

        return documents
