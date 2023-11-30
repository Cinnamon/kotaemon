from pathlib import Path

from llama_index.readers.base import BaseReader
from theflow import Param

from kotaemon.base import BaseComponent, Document
from kotaemon.indices.extractors import BaseDocParser
from kotaemon.indices.splitters import BaseSplitter, TokenSplitter
from kotaemon.loaders import (
    AutoReader,
    DirectoryReader,
    MathpixPDFReader,
    OCRReader,
    PandasExcelReader,
)


class DocumentIngestor(BaseComponent):
    """Ingest common office document types into Document for indexing

    Document types:
        - pdf
        - xlsx
        - docx
    """

    pdf_mode: str = "normal"  # "normal", "mathpix", "ocr"
    doc_parsers: list[BaseDocParser] = Param(default_callback=lambda _: [])
    text_splitter: BaseSplitter = TokenSplitter.withx(
        chunk_size=1024,
        chunk_overlap=256,
    )

    def _get_reader(self, input_files: list[str | Path]):
        """Get appropriate readers for the input files based on file extension"""
        file_extractor: dict[str, AutoReader | BaseReader] = {
            ".xlsx": PandasExcelReader(),
        }

        if self.pdf_mode == "normal":
            file_extractor[".pdf"] = AutoReader("UnstructuredReader")
        elif self.pdf_mode == "ocr":
            file_extractor[".pdf"] = OCRReader()
        else:
            file_extractor[".pdf"] = MathpixPDFReader()

        main_reader = DirectoryReader(
            input_files=input_files,
            file_extractor=file_extractor,
        )

        return main_reader

    def run(self, file_paths: list[str | Path] | str | Path) -> list[Document]:
        """Ingest the file paths into Document

        Args:
            file_paths: list of file paths or a single file path

        Returns:
            list of parsed Documents
        """
        if not isinstance(file_paths, list):
            file_paths = [file_paths]

        documents = self._get_reader(input_files=file_paths)()
        nodes = self.text_splitter(documents)
        self.log_progress(".num_docs", num_docs=len(nodes))

        # document parsers call
        if self.doc_parsers:
            for parser in self.doc_parsers:
                nodes = parser(nodes)

        return nodes
