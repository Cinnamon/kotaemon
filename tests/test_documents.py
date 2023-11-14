from kotaemon.base.schema import Document, RetrievedDocument

from .conftest import skip_when_haystack_not_installed


def test_document_constructor_with_builtin_types():
    for value in ["str", 1, {}, set(), [], tuple, None]:
        doc = Document(value)
        assert doc.text == (str(value) if value else "")
        assert doc.content == value
        assert bool(doc) == bool(value)


def test_document_constructor_with_document():
    text = "Sample text"
    doc1 = Document(text)
    doc2 = Document(doc1)
    assert doc2.text == doc1.text
    assert doc2.content == doc1.content


@skip_when_haystack_not_installed
def test_document_to_haystack_format():
    from haystack.schema import Document as HaystackDocument

    text = "Sample text"
    metadata = {"filename": "sample.txt"}
    doc = Document(text, metadata=metadata)
    haystack_doc = doc.to_haystack_format()
    assert isinstance(haystack_doc, HaystackDocument)
    assert haystack_doc.content == doc.text
    assert haystack_doc.meta == metadata


def test_retrieved_document_default_values():
    sample_text = "text"
    retrieved_doc = RetrievedDocument(text=sample_text)
    assert retrieved_doc.text == sample_text
    assert retrieved_doc.score == 0.0
    assert retrieved_doc.retrieval_metadata == {}


def test_retrieved_document_attributes():
    sample_text = "text"
    score = 0.8
    metadata = {"source": "retrieval_system"}
    retrieved_doc = RetrievedDocument(
        text=sample_text, score=score, retrieval_metadata=metadata
    )
    assert retrieved_doc.text == sample_text
    assert retrieved_doc.score == score
    assert retrieved_doc.retrieval_metadata == metadata
