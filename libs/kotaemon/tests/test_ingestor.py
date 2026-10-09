from pathlib import Path
from unittest.mock import patch

import pytest
from llama_index.core.readers.base import BaseReader
from llama_index.readers.file import PDFReader

from kotaemon.indices.ingests import DocumentIngestor
from kotaemon.indices.splitters import TokenSplitter
from kotaemon.loaders import AdobeReader, MathpixPDFReader, OCRReader


class CustomPDFReader(BaseReader):
    def load_data(self, file, extra_info=None):
        return []


def get_pdf_extractor(**kwargs):
    with patch("kotaemon.indices.ingests.files.DirectoryReader") as reader_cls:
        DocumentIngestor(**kwargs)._get_reader(["a.pdf"])
    return reader_cls.call_args.kwargs["file_extractor"][".pdf"]


def test_ingestor_include_src():
    dirpath = Path(__file__).parent
    ingestor = DocumentIngestor(
        pdf_mode="normal",
        text_splitter=TokenSplitter(chunk_size=200, chunk_overlap=10),
    )
    nodes = ingestor(dirpath / "resources" / "table.pdf")
    assert type(nodes) is list
    assert nodes[0].relationships


def test_override_pdf_extractor_wins_over_pdf_mode():
    reader = get_pdf_extractor(
        pdf_mode="normal",
        override_file_extractors={".pdf": CustomPDFReader},
    )
    assert isinstance(reader, CustomPDFReader)


@pytest.mark.parametrize(
    "mode,cls",
    [
        ("normal", PDFReader),
        ("ocr", OCRReader),
        ("multimodal", AdobeReader),
        ("mathpix", MathpixPDFReader),
    ],
)
def test_pdf_mode_selects_reader(mode, cls):
    assert isinstance(get_pdf_extractor(pdf_mode=mode), cls)


@pytest.mark.parametrize("mode", ["OCR", "mathpix ", ""])
def test_unknown_pdf_mode_raises(mode):
    with pytest.raises(ValueError, match="Unknown pdf_mode"):
        DocumentIngestor(pdf_mode=mode)._get_reader(["a.pdf"])
