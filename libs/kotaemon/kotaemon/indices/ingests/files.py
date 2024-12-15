from pathlib import Path
from typing import Type

from llama_index.core.readers.base import BaseReader
from llama_index.readers.file import PDFReader

from kotaemon.base import BaseComponent, Document, Param
from kotaemon.indices.extractors import BaseDocParser
from kotaemon.indices.ingests.extensions import extension_manager
from kotaemon.indices.splitters import BaseSplitter, TokenSplitter
from kotaemon.loaders import DirectoryReader


class DocumentIngestor(BaseComponent):
    """Ingest common office document types into Document for indexing

    Document types:
        - pdf
        - xlsx, xls
        - docx, doc

    Args:
        pdf_mode: mode for pdf extraction, one of "normal", "mathpix", "ocr"
            - normal: parse pdf text
            - mathpix: parse pdf text using mathpix
            - ocr: parse pdf image using flax
        doc_parsers: list of document parsers to parse the document
        text_splitter: splitter to split the document into text nodes
        override_file_extractors: override file extractors for specific file extensions
            The default file extractors are stored in `KH_DEFAULT_FILE_EXTRACTORS`
    """

    pdf_mode: str = "normal"  # "normal", "mathpix", "ocr", "multimodal"
    doc_parsers: list[BaseDocParser] = Param(default_callback=lambda _: [])
    text_splitter: BaseSplitter = TokenSplitter.withx(
        chunk_size=1024,
        chunk_overlap=256,
        separator="\n\n",
        backup_separators=["\n", ".", " ", "\u200B"],
    )
    override_file_extractors: dict[str, Type[BaseReader]] = {}

    def _get_reader(self, input_files: list[str | Path]):
        """Get appropriate readers for the input files based on file extension"""
        file_extractors: dict[str, BaseReader] = {
            ext: reader
            for ext, reader in extension_manager.get_current_loader().items()
        }
        for ext, cls in self.override_file_extractors.items():
            file_extractors[ext] = cls()

        match self.pdf_mode:
            case "normal":
                file_extractors[".pdf"] = PDFReader()
            case "multimodal":
                file_extractors[".pdf"] = extension_manager.factory.adobe
            case _:
                file_extractors[".pdf"] = extension_manager.factory.mathpix_pdf

        main_reader = DirectoryReader(
            input_files=input_files,
            file_extractor=file_extractors,
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
        print(f"Read {len(file_paths)} files into {len(documents)} documents.")
        nodes = self.text_splitter(documents)
        print(f"Transform {len(documents)} documents into {len(nodes)} nodes.")
        self.log_progress(".num_docs", num_docs=len(nodes))

        # document parsers call
        if self.doc_parsers:
            for parser in self.doc_parsers:
                nodes = parser(nodes)

        return nodes
