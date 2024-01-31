import unicodedata
from pathlib import Path
from typing import List, Optional

from llama_index.readers.base import BaseReader

from kotaemon.base import Document


class HtmlReader(BaseReader):
    """Reader HTML usimg html2text

    Reader behavior:
        - HTML is read with html2text.
        - All of the texts will be split by `page_break_pattern`
        - Each page is extracted as a Document
        - The output is a list of Documents

    Args:
        page_break_pattern (str): Pattern to split the HTML into pages
    """

    def __init__(self, page_break_pattern: Optional[str] = None, *args, **kwargs):
        try:
            import html2text
        except ImportError:
            raise ImportError(
                "html2text is not installed. "
                "Please install it using `pip install html2text`"
            )

        self._module = html2text
        self._page_break_pattern: Optional[str] = page_break_pattern
        super().__init__()

    def load_data(
        self, file_path: Path, extra_info: Optional[dict] = None, **kwargs
    ) -> List[Document]:
        """Load data using Html reader

        Args:
            file_path (Path): Path to PDF file
            debug_path (Path): Path to store debug image output
            artifact_path (Path): Path to OCR endpoints artifacts directory
        Returns:
            List[Document]: list of documents extracted from the HTML file
        """
        file_path = Path(file_path).resolve()

        with file_path.open("r") as content:
            html_text = "".join(
                [
                    unicodedata.normalize("NFKC", line[:-1])
                    for line in content.readlines()
                ]
            )

        # read HTML
        all_text = self._module.html2text(html_text)
        pages = (
            all_text.split(self._page_break_pattern)
            if self._page_break_pattern
            else [all_text]
        )

        extra_info = extra_info or {}

        # create Document from non-table text
        documents = [
            Document(
                text=page.strip(),
                metadata={"page_label": page_id + 1, **extra_info},
            )
            for page_id, page in enumerate(pages)
        ]

        return documents
