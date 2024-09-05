import json
from pathlib import Path

import pytest

from kotaemon.loaders import MathpixPDFReader, OCRReader, PandasExcelReader

from .conftest import skip_when_unstructured_not_installed

input_file = Path(__file__).parent / "resources" / "table.pdf"
input_file_excel = Path(__file__).parent / "resources" / "dummy.xlsx"


@pytest.fixture
def fullocr_output():
    with open(
        Path(__file__).parent / "resources" / "fullocr_sample_output.json",
        encoding="utf-8",
    ) as f:
        fullocr = json.load(f)
    return fullocr


@pytest.fixture
def mathpix_output():
    with open(Path(__file__).parent / "resources" / "policy.md", encoding="utf-8") as f:
        content = f.read()
    return content


@skip_when_unstructured_not_installed
def test_ocr_reader(fullocr_output):
    reader = OCRReader()
    documents = reader.load_data(input_file, response_content=fullocr_output)
    table_docs = [doc for doc in documents if doc.metadata.get("type", "") == "table"]
    assert len(table_docs) == 2


def test_mathpix_reader(mathpix_output):
    reader = MathpixPDFReader()
    documents = reader.load_data(input_file, response_content=mathpix_output)
    table_docs = [doc for doc in documents if doc.metadata.get("type", "") == "table"]
    assert len(table_docs) == 4


def test_excel_reader():
    reader = PandasExcelReader()
    documents = reader.load_data(
        input_file_excel,
    )
    assert len(documents) == 1
