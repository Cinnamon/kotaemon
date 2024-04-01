import logging
import os
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from llama_index.readers.base import BaseReader

from kotaemon.base import Document

from .utils.adobe import (
    generate_figure_captions,
    load_json,
    parse_figure_paths,
    parse_table_paths,
    request_adobe_service,
)

logger = logging.getLogger(__name__)


class AdobeReader(BaseReader):
    """Read PDF using the Adobe's PDF Services.
    Be able to extract text, table, and figure with high accuracy

    Example:
        ```python
        >> from kotaemon.loaders import AdobeReader
        >> reader = AdobeReader()
        >> documents = reader.load_data("path/to/pdf")
        ```
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Init params"""
        super().__init__(*args)
        self.table_regex = r"/Table(\[\d+\])?$"
        self.figure_regex = r"/Figure(\[\d+\])?$"

    def load_data(
        self, file: Path, extra_info: Optional[Dict] = None, **kwargs
    ) -> List[Document]:
        """Load data by calling to the Adobe's API

        Args:
            file (Path): Path to the PDF file

        Returns:
            List[Document]: list of documents extracted from the PDF file,
                includes 3 types: text, table, and image

        """

        filename = file.name
        filepath = str(Path(file).resolve())
        output_path = request_adobe_service(file_path=str(file), output_path="")
        results_path = os.path.join(output_path, "structuredData.json")

        if not os.path.exists(results_path):
            logger.exception("Fail to parse the document.")
            return []

        data = load_json(results_path)

        texts = defaultdict(list)
        tables = []
        figures = []

        elements = data["elements"]
        for item_id, item in enumerate(elements):
            page_number = item.get("Page", -1) + 1
            item_path = item["Path"]
            item_text = item.get("Text", "")

            file_paths = [
                Path(output_path) / path for path in item.get("filePaths", [])
            ]
            prev_item = elements[item_id - 1]
            title = prev_item.get("Text", "")

            if re.search(self.table_regex, item_path):
                table_content = parse_table_paths(file_paths)
                if not table_content:
                    continue
                table_caption = (
                    table_content.replace("|", "").replace("---", "")
                    + f"\n(Table in Page {page_number}. {title})"
                )
                tables.append((page_number, table_content, table_caption))

            elif re.search(self.figure_regex, item_path):
                figure_caption = (
                    item_text + f"\n(Figure in Page {page_number}. {title})"
                )
                figure_content = parse_figure_paths(file_paths)
                if not figure_content:
                    continue
                figures.append([page_number, figure_content, figure_caption])

            else:
                if item_text and "Table" not in item_path and "Figure" not in item_path:
                    texts[page_number].append(item_text)

        # get figure caption using GPT-4V
        figure_captions = generate_figure_captions([item[1] for item in figures])
        for item, caption in zip(figures, figure_captions):
            # update figure caption
            item[2] += " " + caption

        # Wrap elements with Document
        documents = []

        # join plain text elements
        for page_number, txts in texts.items():
            documents.append(
                Document(
                    text="\n".join(txts),
                    metadata={
                        "page_label": page_number,
                        "file_name": filename,
                        "file_path": filepath,
                    },
                )
            )

        # table elements
        for page_number, table_content, table_caption in tables:
            documents.append(
                Document(
                    text=table_caption,
                    metadata={
                        "table_origin": table_content,
                        "type": "table",
                        "page_label": page_number,
                        "file_name": filename,
                        "file_path": filepath,
                    },
                    metadata_template="",
                    metadata_seperator="",
                )
            )

        # figure elements
        for page_number, figure_content, figure_caption in figures:
            documents.append(
                Document(
                    text=figure_caption,
                    metadata={
                        "image_origin": figure_content,
                        "type": "image",
                        "page_label": page_number,
                        "file_name": filename,
                        "file_path": filepath,
                    },
                    metadata_template="",
                    metadata_seperator="",
                )
            )
        return documents
