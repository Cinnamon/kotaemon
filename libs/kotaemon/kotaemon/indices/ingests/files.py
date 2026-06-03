from dataclasses import dataclass, field
from pathlib import Path
from typing import Type

from decouple import config
from llama_index.core.readers.base import BaseReader
from llama_index.readers.file import PDFReader

from kotaemon.base import Document
from kotaemon.indices.extractors import BaseDocParser
from kotaemon.indices.splitters import BaseSplitter, TokenSplitter
from kotaemon.loaders import (
    AdobeReader,
    AzureAIDocumentIntelligenceLoader,
    DirectoryReader,
    DoclingReader,
    HtmlReader,
    MathpixPDFReader,
    MhtmlReader,
    OCRReader,
    PaddleOCRVLReader,
    PandasExcelReader,
    PDFThumbnailReader,
    PPStructureV3Reader,
    TxtReader,
    UnstructuredReader,
    WebReader,
)

web_reader = WebReader()
unstructured = UnstructuredReader()
adobe_reader = AdobeReader()
azure_reader = AzureAIDocumentIntelligenceLoader(
    endpoint=str(config("AZURE_DI_ENDPOINT", default="")),
    credential=str(config("AZURE_DI_CREDENTIAL", default="")),
)
docling_reader = DoclingReader()
paddle_device = str(config("PADDLE_DEVICE", default="gpu"))
paddle_struct_reader = PPStructureV3Reader(device=paddle_device)
paddle_vl_reader = PaddleOCRVLReader(device=paddle_device)

KH_DEFAULT_FILE_EXTRACTORS: dict[str, BaseReader] = {
    ".xlsx": PandasExcelReader(),
    ".docx": unstructured,
    ".pptx": unstructured,
    ".xls": unstructured,
    ".doc": unstructured,
    ".html": HtmlReader(),
    ".mhtml": MhtmlReader(),
    ".png": unstructured,
    ".jpeg": unstructured,
    ".jpg": unstructured,
    ".tiff": unstructured,
    ".tif": unstructured,
    ".pdf": PDFThumbnailReader(),
    ".txt": TxtReader(),
    ".md": TxtReader(),
}


def _default_text_splitter() -> TokenSplitter:
    return TokenSplitter(
        chunk_size=1024,
        chunk_overlap=256,
        separator="\n\n",
        backup_separators=["\n", ".", " ", "\u200B"],
    )


@dataclass(kw_only=True)
class DocumentIngestor:
    pdf_mode: str = "normal"
    doc_parsers: list[BaseDocParser] = field(default_factory=list)
    text_splitter: BaseSplitter = field(default_factory=_default_text_splitter)
    override_file_extractors: dict[str, Type[BaseReader]] = field(default_factory=dict)

    def _get_reader(self, input_files: list[str | Path]):
        file_extractors = {
            ext: reader for ext, reader in KH_DEFAULT_FILE_EXTRACTORS.items()
        }
        for ext, cls in self.override_file_extractors.items():
            file_extractors[ext] = cls()

        if self.pdf_mode == "normal":
            file_extractors[".pdf"] = PDFReader()
        elif self.pdf_mode == "ocr":
            file_extractors[".pdf"] = OCRReader()
        elif self.pdf_mode == "multimodal":
            file_extractors[".pdf"] = AdobeReader()
        else:
            file_extractors[".pdf"] = MathpixPDFReader()

        return DirectoryReader(input_files=input_files, file_extractor=file_extractors)

    def run(self, file_paths: list[str | Path] | str | Path) -> list[Document]:
        if not isinstance(file_paths, list):
            file_paths = [file_paths]
        documents = self._get_reader(input_files=file_paths)()
        nodes = self.text_splitter(documents)
        if self.doc_parsers:
            for parser in self.doc_parsers:
                nodes = parser(nodes)
        return nodes
