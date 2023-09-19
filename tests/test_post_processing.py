import pytest

from kotaemon.documents.base import Document
from kotaemon.post_processing.extractor import RegexExtractor


@pytest.fixture
def regex_extractor():
    return RegexExtractor(
        pattern=r"\d+", output_map={"1": "One", "2": "Two", "3": "Three"}
    )


def test_run_document(regex_extractor):
    document = Document(text="This is a test. 1 2 3")
    extracted_document = regex_extractor(document)
    extracted_texts = [each.text for each in extracted_document]
    assert extracted_texts == ["One", "Two", "Three"]


def test_is_document(regex_extractor):
    assert regex_extractor.is_document(Document(text="Test"))
    assert not regex_extractor.is_document("Test")


def test_is_batch(regex_extractor):
    assert regex_extractor.is_batch([Document(text="Test")])
    assert not regex_extractor.is_batch(Document(text="Test"))


def test_run_raw(regex_extractor):
    output = regex_extractor("This is a test. 123")
    assert output == ["123"]


def test_run_batch_raw(regex_extractor):
    output = regex_extractor(["This is a test. 123", "456"])
    assert output == [["123"], ["456"]]
