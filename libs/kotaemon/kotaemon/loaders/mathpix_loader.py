import json
import re
import time
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Union

import requests
from langchain.utils import get_from_dict_or_env
from llama_index.core.readers.base import BaseReader

from kotaemon.base import Document

from .utils.table import strip_special_chars_markdown


# MathpixPDFLoader implementation taken largely from Daniel Gross's:
# https://gist.github.com/danielgross/3ab4104e14faccc12b49200843adab21
class MathpixPDFReader(BaseReader):
    """Load `PDF` files using `Mathpix` service."""

    def __init__(
        self,
        processed_file_format: str = "md",
        max_wait_time_seconds: int = 900,
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
            print(
                f"Processing status: {status},"
                f"Progress: {response_data.get('percent_done', 0)}%"
            )

            if status == "completed":
                return
            elif status == "error":
                raise ValueError(f"Mathpix processing error: {response_data}")
            elif status in [
                "split",
                "processing",
            ]:  # Add handling for processing states
                time.sleep(5)
                continue
            else:
                print(f"Unknown status: {response_data}")
                time.sleep(5)

        raise TimeoutError(
            f"Processing did not complete within {self.max_wait_time_seconds} seconds"
        )

    def get_processed_pdf(self, pdf_id: str) -> str:
        self.wait_for_processing(pdf_id)
        url = f"{self.url}/{pdf_id}.{self.processed_file_format}"
        response = requests.get(url, headers=self._mathpix_headers)
        if response.status_code != 200:
            raise ValueError(f"Failed to get processed PDF: {response.text}")
        content = response.content.decode("utf-8")
        print(f"Retrieved content length: {len(content)}")  # Debug print
        return content

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

    def parse_markdown_text_to_tables(
        self, content: str
    ) -> tuple[list[tuple[int, str]], list[tuple[int, str]]]:
        """Parse markdown text to get tables and texts separately.

        Returns:
            Tuple of (tables, texts) where each is a list of (page_num, content) tuples
        """
        print("Starting markdown parsing...")
        print(f"Content length: {len(content)}")

        # Split by page markers if present
        pages = re.split(r"(?m)^# Page \d+\n", content)

        tables: list[tuple[int, str]] = []
        texts: list[tuple[int, str]] = []

        for page_num, page_content in enumerate(pages, 1):
            if not page_content.strip():
                continue

            # Extract tables from the page
            table_matches = re.findall(r"(\|[^\n]+\|(?:\n\|[^\n]+\|)*)", page_content)
            if table_matches:
                for table in table_matches:
                    tables.append(
                        (page_num, table.strip())
                    )  # Store as tuple with page number
                # Remove tables from page content
                page_content = re.sub(
                    r"(\|[^\n]+\|(?:\n\|[^\n]+\|)*)", "", page_content
                )

            # Split remaining content into meaningful chunks
            chunks = re.split(r"\n\s*\n", page_content)
            for chunk in chunks:
                if chunk.strip():
                    texts.append(
                        (page_num, chunk.strip())
                    )  # Store as tuple with page number

        print(f"Found {len(tables)} tables and {len(texts)} text sections")
        return tables, texts

    def load_data(
        self,
        file: Union[str, List[str], Path],
        extra_info: Optional[Dict] = None,
        **load_kwargs: Any,
    ) -> List[Document]:
        """Load data from file path."""
        file_path = Path(file) if isinstance(file, str) else file

        if "response_content" in load_kwargs:
            content = load_kwargs["response_content"]
        else:
            pdf_id = self.send_pdf(file_path)
            content = self.get_processed_pdf(pdf_id)

        if self.should_clean_pdf:
            content = self.clean_pdf(content)

        tables, texts = self.parse_markdown_text_to_tables(content)
        documents = []

        # Handle tables
        for page_num, table_content in tables:
            text = strip_special_chars_markdown(table_content)
            metadata = {
                "table_origin": table_content,
                "type": "table",
                "page_label": page_num,
                "page_number": page_num,
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

        # Handle text sections
        for page_num, text_content in texts:
            if not text_content.strip():
                continue
            metadata = {
                "source": str(file_path),
                "type": "text",
                "page_label": page_num,
                "page_number": page_num,
            }
            if extra_info:
                metadata.update(extra_info)
            documents.append(Document(text=text_content, metadata=metadata))

        # Fallback if no content was parsed
        if not documents and content.strip():
            metadata = {
                "source": str(file_path),
                "type": "text",
                "page_label": 1,
                "page_number": 1,
            }
            if extra_info:
                metadata.update(extra_info)
            documents.append(Document(text=content.strip(), metadata=metadata))

        return documents

    def lazy_load_data(
        self,
        file: Union[str, List[str], Path],
        extra_info: Optional[Dict] = None,
        **load_kwargs: Any,
    ) -> Generator[Document, None, None]:
        """Lazy load data from file path."""
        file_path = Path(file) if isinstance(file, str) else file

        if "response_content" in load_kwargs:
            content = load_kwargs["response_content"]
        else:
            pdf_id = self.send_pdf(file_path)
            print(f"PDF ID: {pdf_id}")
            content = self.get_processed_pdf(pdf_id)

        if self.should_clean_pdf:
            content = self.clean_pdf(content)

        tables, texts = self.parse_markdown_text_to_tables(content)

        # Handle tables
        for page_num, table_content in tables:  # Changed variable name for clarity
            text = strip_special_chars_markdown(table_content)  # Pass just the content
            metadata = {
                "table_origin": table_content,  # Use table_content here too
                "type": "table",
                "page_label": page_num,
                "page_number": page_num,
            }
            if extra_info:
                metadata.update(extra_info)
            yield Document(
                text=text,
                metadata=metadata,
                metadata_template="",
                metadata_seperator="",
            )

        # Handle text sections
        for page_num, text_content in texts:  # Changed variable name for clarity
            if not text_content.strip():
                continue
            metadata = {
                "source": str(file_path),
                "type": "text",
                "page_label": page_num,
                "page_number": page_num,
            }
            if extra_info:
                metadata.update(extra_info)
            yield Document(
                text=text_content, metadata=metadata
            )  # Use text_content directly

        # Fallback if no content was parsed
        if not (tables or texts) and content.strip():
            metadata = {
                "source": str(file_path),
                "type": "text",
                "page_label": 1,
                "page_number": 1,
            }
            if extra_info:
                metadata.update(extra_info)
            yield Document(text=content.strip(), metadata=metadata)

        print(f"Completed processing PDF: {file_path}")
