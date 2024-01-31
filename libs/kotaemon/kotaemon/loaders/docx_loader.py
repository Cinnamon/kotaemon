import unicodedata
from pathlib import Path
from typing import List, Optional

import pandas as pd
from llama_index.readers.base import BaseReader

from kotaemon.base import Document


class DocxReader(BaseReader):
    """Read Docx files that respect table, using python-docx library

    Reader behavior:
        - All paragraphs are extracted as a Document
        - Each table is extracted as a Document, rendered as a CSV string
        - The output is a list of Documents, concatenating the above
        (tables + paragraphs)
    """

    def __init__(self, *args, **kwargs):
        try:
            import docx
        except ImportError:
            raise ImportError(
                "docx is not installed. "
                "Please install it using `pip install python-docx`"
            )
        self._module = docx

    def load_data(
        self, file_path: Path, extra_info: Optional[dict] = None, **kwargs
    ) -> List[Document]:
        """Load data using Docx reader

        Args:
            file_path (Path): Path to PDF file

        Returns:
            List[Document]: list of documents extracted from the HTML file
        """
        file_path = Path(file_path).resolve()

        doc = self._module.Document(str(file_path))
        all_text = "\n".join(
            [unicodedata.normalize("NFKC", p.text) for p in doc.paragraphs]
        )
        pages = [all_text]  # 1 page only

        tables = []
        for t in doc.tables:
            arrays = [
                [
                    unicodedata.normalize("NFKC", t.cell(i, j).text)
                    for i in range(len(t.rows))
                ]
                for j in range(len(t.columns))
            ]
            tables.append(pd.DataFrame({a[0]: a[1:] for a in arrays}))

        extra_info = extra_info or {}

        # create output Document with metadata from table
        documents = [
            Document(
                text=table.to_csv(
                    index=False
                ).strip(),  # strip_special_chars_markdown()
                metadata={
                    "table_origin": table.to_csv(index=False),
                    "type": "table",
                    **extra_info,
                },
                metadata_template="",
                metadata_seperator="",
            )
            for table in tables  # page_id
        ]

        # create Document from non-table text
        documents.extend(
            [
                Document(
                    text=non_table_text.strip(),
                    metadata={"page_label": 1, **extra_info},
                )
                for _, non_table_text in enumerate(pages)
            ]
        )

        return documents
