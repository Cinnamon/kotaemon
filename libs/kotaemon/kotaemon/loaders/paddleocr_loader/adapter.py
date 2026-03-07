"""PaddleOCR result adapter for converting raw output to Documents."""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from kotaemon.base import Document

# Label categories for PaddleOCR models (both PPStructureV3 and PaddleOCRVL)
# These are the block_label values from PaddleOCR output

TEXT_LABELS: set[str] = {
    "text",
    "paragraph_title",
    "doc_title",
    "abstract",
    "content",
    "footnote",
    "reference",
    "reference_content",
    "aside_text",
    "algorithm",
}

TABLE_LABELS: set[str] = {"table"}

IMAGE_LABELS: set[str] = {
    "image",
    "chart",
}

FORMULA_LABELS: set[str] = {
    "formula",
    "display_formula",
    "inline_formula",
}

# Labels to ignore (not useful for RAG)
IGNORE_LABELS: set[str] = {
    "footer",
    "footer_image",
    "formula_number",
    "figure_title",
    "figure_table_chart_title",
    "header",
    "header_image",
    "number",
    "seal",
    "vision_footnote",
}


@dataclass
class PaddleOCRResult:
    """Unified adapter for PaddleOCR results (PPStructureV3 and PaddleOCRVL).

    Converts raw PaddleOCR output to kotaemon Documents.

    Both PPStructureV3 and PaddleOCRVL have similar output structure:
    - List of page results
    - Each page has parsing_res_list with blocks
    - Each block has block_label and block_content
    """

    raw_result: Any
    file_path: Path
    extra_info: dict

    text_labels: set[str] = field(default_factory=lambda: TEXT_LABELS.copy())
    table_labels: set[str] = field(default_factory=lambda: TABLE_LABELS.copy())
    image_labels: set[str] = field(default_factory=lambda: IMAGE_LABELS.copy())
    formula_labels: set[str] = field(default_factory=lambda: FORMULA_LABELS.copy())
    ignore_labels: set[str] = field(default_factory=lambda: IGNORE_LABELS.copy())

    @property
    def file_name(self) -> str:
        return self.file_path.name

    def to_documents(self) -> list[Document]:
        """Convert PaddleOCR results to Documents."""
        texts: list[Document] = []
        tables: list[Document] = []
        figures: list[Document] = []
        print("WTFFFF", self.raw_result)

        for page_result in self.raw_result:
            result_dict = page_result.json["res"]
            page_index = result_dict.get("page_index")
            print("WTFFFF", page_index)
            page_label = (page_index + 1) if page_index is not None else 1

            page_texts, page_tables, page_figures = self._parse_page(
                result_dict, page_label
            )
            texts.extend(page_texts)
            tables.extend(page_tables)
            figures.extend(page_figures)

        return texts + tables + figures

    def _parse_page(
        self,
        result_dict: dict,
        page_label: int,
    ) -> tuple[list[Document], list[Document], list[Document]]:
        """Parse a single page result."""
        parsing_list = result_dict.get("parsing_res_list", [])

        text_blocks: list[str] = []
        tables: list[Document] = []
        figures: list[Document] = []

        for block in parsing_list:
            label = block.get("block_label", "")
            content = block.get("block_content", "")

            if not content or label in self.ignore_labels:
                continue

            bbox = block.get("block_bbox")
            polygon = block.get("block_polygon_points")

            base_metadata = {
                "page_label": page_label,
                "file_name": self.file_name,
                "file_path": str(self.file_path),
                **self.extra_info,
            }
            if bbox is not None:
                base_metadata["bbox"] = bbox
            if polygon is not None:
                base_metadata["polygon"] = polygon

            if label in self.text_labels:
                text_blocks.append(content)
            elif label in self.table_labels:
                table_content = self._clean_table_html(content)
                tables.append(
                    Document(
                        text=table_content,
                        metadata={
                            "type": "table",
                            "table_origin": table_content,
                            **base_metadata,
                        },
                    )
                )

            elif label in self.image_labels:
                figures.append(
                    Document(
                        text=content,
                        metadata={
                            "type": "image",
                            **base_metadata,
                        },
                    )
                )

            elif label in self.formula_labels:
                text_blocks.append(f"$${content}$$")
            else:
                text_blocks.append(content)

        text_docs: list[Document] = []
        if text_blocks:
            text_docs.append(
                Document(
                    text="\n\n".join(text_blocks),
                    metadata={
                        "page_label": page_label,
                        "file_name": self.file_name,
                        "file_path": str(self.file_path),
                        **self.extra_info,
                    },
                )
            )

        return text_docs, tables, figures

    def _clean_table_html(self, html_content: str) -> str:
        """Clean HTML table content for better readability."""
        html_content = re.sub(
            r"<html><body>(.*?)</body></html>",
            r"\1",
            html_content,
            flags=re.DOTALL,
        )
        return html_content.strip()
