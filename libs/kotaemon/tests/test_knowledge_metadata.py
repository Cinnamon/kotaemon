import pytest

from kotaemon.base import Document
from kotaemon.indices.knowledge.metadata import normalize_knowledge_metadata


def test_normalizes_metadata_and_preserves_loader_fields():
    document = Document(
        text="RAG work",
        metadata={
            "file_id": "file-7",
            "file_name": "Zhang San.md",
            "file_path": "/tmp/upload-2/Zhang San.md",
            "page_label": 3,
            "loader_tag": "keep",
        },
        source="original-source",
    )

    metadata = normalize_knowledge_metadata(
        document, {"virtual_path": "/Interns/App/Zhang San"}
    )

    assert metadata["source_type"] == "markdown"
    assert metadata["virtual_path"] == "/Interns/App/Zhang San"
    assert metadata["document_id"] == "file-7"
    assert metadata["document_name"] == "Zhang San.md"
    assert metadata["chunk_id"] == document.doc_id
    assert metadata["page"] == 3
    assert metadata["entity"] == {}
    assert metadata["file_path"] == "/tmp/upload-2/Zhang San.md"
    assert metadata["page_label"] == 3
    assert metadata["loader_tag"] == "keep"
    assert metadata["source"] == "original-source"


def test_default_virtual_path_uses_name_not_absolute_file_path():
    document = Document(
        text="body",
        metadata={"file_name": "manual.pdf", "file_path": "/private/tmp/manual.pdf"},
    )

    metadata = normalize_knowledge_metadata(document)

    assert metadata["virtual_path"] == "/manual.pdf"
    assert "/private" not in metadata["virtual_path"]


@pytest.mark.parametrize(
    ("name", "expected"),
    [("sample.py", "code"), ("table.xlsx", "excel"), ("notes.md", "markdown")],
)
def test_infers_source_type_from_document_name(name, expected):
    document = Document(text="body", metadata={"file_name": name})
    assert normalize_knowledge_metadata(document)["source_type"] == expected


def test_invalid_explicit_source_type_becomes_other():
    document = Document(text="body", metadata={"file_name": "notes.md"})
    metadata = normalize_knowledge_metadata(document, {"source_type": "unknown"})
    assert metadata["source_type"] == "other"


def test_explicit_wiki_source_type_is_preserved():
    document = Document(
        text="# Interns", metadata={"file_name": "interns.md", "source_type": "wiki"}
    )
    assert normalize_knowledge_metadata(document)["source_type"] == "wiki"


def test_normalizes_path_and_aliases_and_rejects_invalid_entity():
    document = Document(
        text="body",
        metadata={
            "file_name": "notes.md",
            "virtual_path": "/Teams//./../Platform/Notes",
            "section_path": "Platform",
            "page_number": 8,
            "entity": ["not", "a", "mapping"],
        },
    )
    metadata = normalize_knowledge_metadata(document)
    assert metadata["virtual_path"] == "/Platform/Notes"
    assert metadata["section_path"] == ["Platform"]
    assert metadata["page"] == 8
    assert metadata["entity"] == {}


def test_source_relationship_provides_document_and_parent_ids():
    from llama_index.core.schema import NodeRelationship, RelatedNodeInfo

    document = Document(
        text="body",
        metadata={"file_name": "notes.md"},
        relationships={NodeRelationship.SOURCE: RelatedNodeInfo(node_id="source-9")},
    )
    metadata = normalize_knowledge_metadata(document)
    assert metadata["document_id"] == "source-9"
    assert metadata["parent_id"] == "source-9"
    assert metadata["chunk_id"] == document.doc_id
