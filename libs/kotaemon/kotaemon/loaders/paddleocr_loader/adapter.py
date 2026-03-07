import re
from abc import abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from kotaemon.base import Document


@dataclass
class PaddleOCRResult:
    """Base adapter for PaddleOCR results.

    Converts raw PaddleOCR output to kotaemon Documents.
    """

    raw_result: Any
    file_path: Path
    extra_info: dict

    @property
    def file_name(self) -> str:
        return self.file_path.name

    @abstractmethod
    def to_documents(self) -> list[Document]:
        """Convert the result to a list of Documents."""
        ...

    def _clean_table_html(self, html_content: str) -> str:
        """Clean HTML table content for better readability."""
        html_content = re.sub(
            r"<html><body>(.*?)</body></html>",
            r"\1",
            html_content,
            flags=re.DOTALL,
        )
        return html_content.strip()
