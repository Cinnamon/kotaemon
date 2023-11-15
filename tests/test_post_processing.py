import pytest

from kotaemon.base import Document
from kotaemon.parsers import RegexExtractor


@pytest.fixture
def regex_extractor():
    return RegexExtractor(
        pattern=r"\d+", output_map={"1": "One", "2": "Two", "3": "Three"}
    )


def test_run_document(regex_extractor):
    document = Document(text="This is a test. 1 2 3")
    extracted_document = regex_extractor(document)[0]
    assert extracted_document.text == "One"
    assert extracted_document.matches == ["One", "Two", "Three"]


def test_run_raw(regex_extractor):
    output = regex_extractor("This is a test. 123")[0]
    assert output.text == "123"
    assert output.matches == ["123"]


def test_run_batch_raw(regex_extractor):
    output = regex_extractor(["This is a test. 123", "456"])
    extracted_text = [each.text for each in output]
    extracted_matches = [each.matches for each in output]
    assert extracted_text == ["123", "456"]
    assert extracted_matches == [["123"], ["456"]]
