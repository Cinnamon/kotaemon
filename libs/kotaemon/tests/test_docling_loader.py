import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

from kotaemon.loaders import DoclingReader


@pytest.fixture
def fake_docling(monkeypatch):
    class InputFormat:
        PDF = "pdf"

    class OcrOptions:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class EasyOcrOptions(OcrOptions):
        pass

    class TesseractOcrOptions(OcrOptions):
        pass

    class TesseractCliOcrOptions(OcrOptions):
        pass

    class OcrMacOptions(OcrOptions):
        pass

    class PdfPipelineOptions:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.ocr_options = None

    class PdfFormatOption:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class DocumentConverter:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    modules = {
        "docling": ModuleType("docling"),
        "docling.datamodel": ModuleType("docling.datamodel"),
        "docling.datamodel.base_models": ModuleType("docling.datamodel.base_models"),
        "docling.datamodel.pipeline_options": ModuleType(
            "docling.datamodel.pipeline_options"
        ),
        "docling.document_converter": ModuleType("docling.document_converter"),
    }
    setattr(modules["docling.datamodel.base_models"], "InputFormat", InputFormat)
    pipeline_options = modules["docling.datamodel.pipeline_options"]
    setattr(pipeline_options, "EasyOcrOptions", EasyOcrOptions)
    setattr(pipeline_options, "OcrMacOptions", OcrMacOptions)
    setattr(pipeline_options, "PdfPipelineOptions", PdfPipelineOptions)
    setattr(pipeline_options, "TesseractCliOcrOptions", TesseractCliOcrOptions)
    setattr(pipeline_options, "TesseractOcrOptions", TesseractOcrOptions)
    document_converter = modules["docling.document_converter"]
    setattr(document_converter, "DocumentConverter", DocumentConverter)
    setattr(document_converter, "PdfFormatOption", PdfFormatOption)

    for name, module in modules.items():
        monkeypatch.setitem(sys.modules, name, module)

    return SimpleNamespace(
        DocumentConverter=DocumentConverter,
        TesseractCliOcrOptions=TesseractCliOcrOptions,
    )


def test_docling_reader_keeps_default_converter(fake_docling):
    converter = DoclingReader().converter_

    assert isinstance(converter, fake_docling.DocumentConverter)
    assert converter.kwargs == {}


def test_docling_reader_configures_offline_tesseract(fake_docling):
    converter = DoclingReader(
        artifacts_path="/opt/docling-models",
        ocr_engine="tesseract_cli",
        ocr_languages=["eng", "fra"],
    ).converter_

    pdf_format = converter.kwargs["format_options"]["pdf"]
    pipeline_options = pdf_format.kwargs["pipeline_options"]

    assert pipeline_options.kwargs["artifacts_path"] == Path("/opt/docling-models")
    assert isinstance(
        pipeline_options.ocr_options,
        fake_docling.TesseractCliOcrOptions,
    )
    assert pipeline_options.ocr_options.kwargs == {"lang": ["eng", "fra"]}


def test_docling_reader_rejects_unknown_ocr_engine(fake_docling):
    reader = DoclingReader(ocr_engine="unknown")

    with pytest.raises(ValueError, match="Unsupported Docling OCR engine 'unknown'"):
        _ = reader.converter_
