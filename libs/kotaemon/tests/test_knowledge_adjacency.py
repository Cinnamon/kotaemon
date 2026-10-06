"""Provenance and safe adjacency for newly indexed knowledge chunks."""

from __future__ import annotations

import hashlib

from kotaemon.base import Document
from kotaemon.indices.knowledge.metadata import normalize_knowledge_metadata


def test_repeated_text_does_not_invent_offsets():
    from kotaemon.indices.knowledge.chunking.identity import (
        source_version_for_bytes,
        stamp_chunk_identity,
    )

    source = Document(text="same same", metadata={"document_id": "s"})
    chunks = [Document(text="same"), Document(text="same")]
    version = source_version_for_bytes(b"v1")

    result = stamp_chunk_identity(source, chunks, source_version=version)

    assert [document.metadata["chunk_ordinal"] for document in result] == [0, 1]
    assert result[0].metadata["next_chunk_id"] == result[1].doc_id
    assert result[1].metadata["previous_chunk_id"] == result[0].doc_id
    assert all("char_start" not in document.metadata for document in result)
    assert {document.doc_id for document in result} == {
        document.doc_id for document in chunks
    }


def test_semantic_sections_have_separate_units():
    from kotaemon.indices.knowledge.chunking.identity import (
        source_version_for_bytes,
        stamp_chunk_identity,
    )
    from kotaemon.indices.knowledge.chunking.markdown import MarkdownChunkStrategy
    from kotaemon.indices.splitters import TokenSplitter

    version = source_version_for_bytes(b"markdown-v1")
    source = Document(
        text="# A\nalpha\n# B\nbeta",
        metadata={"document_id": "markdown-source", "source_type": "markdown"},
    )
    strategy = MarkdownChunkStrategy(TokenSplitter(chunk_size=8, chunk_overlap=0))
    chunks = stamp_chunk_identity(
        source, strategy.split(source), source_version=version
    )

    section_a = [item for item in chunks if item.metadata["section_path"] == ["A"]]
    section_b = [item for item in chunks if item.metadata["section_path"] == ["B"]]
    assert section_a and section_b
    assert len({item.metadata["unit_id"] for item in section_a + section_b}) == 2
    assert all("previous_chunk_id" not in item.metadata for item in section_a)
    assert all("next_chunk_id" not in item.metadata for item in section_a)
    assert all("previous_chunk_id" not in item.metadata for item in section_b)
    assert all("next_chunk_id" not in item.metadata for item in section_b)
    repeated_parse = stamp_chunk_identity(
        source, strategy.split(source), source_version=version
    )
    renamed_source = Document(
        text=source.text,
        metadata={"document_id": "a-different-database-id", "source_type": "markdown"},
    )
    reindexed_parse = stamp_chunk_identity(
        renamed_source, strategy.split(renamed_source), source_version=version
    )
    assert {
        tuple(item.metadata["section_path"]): item.metadata["unit_id"]
        for item in repeated_parse
    } == {
        tuple(item.metadata["section_path"]): item.metadata["unit_id"]
        for item in chunks
    }
    assert {
        tuple(item.metadata["section_path"]): item.metadata["unit_id"]
        for item in reindexed_parse
    } == {
        tuple(item.metadata["section_path"]): item.metadata["unit_id"]
        for item in chunks
    }

    oversized_source = Document(
        text="# A\n" + "alpha beta gamma delta " * 30,
        metadata={"document_id": "markdown-source", "source_type": "markdown"},
    )
    oversized = stamp_chunk_identity(
        oversized_source,
        strategy.split(oversized_source),
        source_version=version,
    )
    assert len(oversized) > 1
    assert len({item.metadata["unit_id"] for item in oversized}) == 1
    for left, right in zip(oversized, oversized[1:]):
        assert left.metadata["next_chunk_id"] == right.doc_id
        assert right.metadata["previous_chunk_id"] == left.doc_id
    assert "previous_chunk_id" not in oversized[0].metadata
    assert "next_chunk_id" not in oversized[-1].metadata


def test_reindex_changes_version(tmp_path):
    from kotaemon.indices.knowledge.chunking.identity import (
        source_version_for_bytes,
        source_version_for_path,
        stamp_chunk_identity,
    )

    source = Document(text="first second", metadata={"document_id": "s"})
    old_chunks = [
        Document(text="first", id_="old-1"),
        Document(text="second", id_="old-2"),
    ]
    old_version = source_version_for_bytes(b"v1")
    old = stamp_chunk_identity(source, old_chunks, source_version=old_version)

    new_chunks = [
        Document(text="first changed", id_="new-1"),
        Document(text="second changed", id_="new-2"),
    ]
    new_version = source_version_for_bytes(b"v2")
    new = stamp_chunk_identity(source, new_chunks, source_version=new_version)

    assert old_version != new_version
    assert old[0].metadata["unit_id"] != new[0].metadata["unit_id"]
    assert {item.metadata["source_version"] for item in old} == {old_version}
    assert {item.metadata["source_version"] for item in new} == {new_version}
    assert old[0].metadata["next_chunk_id"] == "old-2"
    assert new[0].metadata["next_chunk_id"] == "new-2"
    assert new[1].metadata["previous_chunk_id"] == "new-1"
    assert not {item.doc_id for item in new} & {
        old[0].metadata["next_chunk_id"],
        old[1].metadata["previous_chunk_id"],
    }

    path = tmp_path / "source-version-fixture.bin"
    path.write_bytes(b"path bytes")
    try:
        assert (
            source_version_for_path(path) == hashlib.sha256(b"path bytes").hexdigest()
        )
    finally:
        path.unlink()


def test_unit_boundaries_do_not_link():
    from kotaemon.indices.knowledge.chunking.identity import stamp_chunk_identity

    source = Document(text="one two", metadata={"document_id": "s"})
    chunks = [
        Document(text="one", metadata={"parent_id": "unit-a", "section_path": ["A"]}),
        Document(text="two", metadata={"parent_id": "unit-b", "section_path": ["B"]}),
    ]

    result = stamp_chunk_identity(source, chunks, source_version="source-version")

    assert result[0].metadata["unit_id"] != result[1].metadata["unit_id"]
    assert "next_chunk_id" not in result[0].metadata
    assert "previous_chunk_id" not in result[1].metadata


def test_repeated_symbol_definitions_have_separate_units():
    from kotaemon.indices.knowledge.chunking.code import PythonCodeChunkStrategy
    from kotaemon.indices.knowledge.chunking.identity import stamp_chunk_identity
    from kotaemon.indices.splitters import TokenSplitter

    source = Document(
        text=(
            "class Example:\n"
            "    def repeated(self):\n"
            "        return 'first'\n\n"
            "    def repeated(self):\n"
            "        return 'second'\n"
        ),
        metadata={
            "document_id": "python-source",
            "file_name": "example.py",
            "source_type": "code",
        },
    )
    strategy = PythonCodeChunkStrategy(TokenSplitter(chunk_size=64, chunk_overlap=0))
    chunks = strategy.split(source)
    stamped = stamp_chunk_identity(source, chunks, source_version="python-v1")
    repeated = [
        item for item in stamped if item.metadata.get("function_name") == "repeated"
    ]

    assert len(repeated) == 2
    assert repeated[0].metadata["unit_id"] != repeated[1].metadata["unit_id"]
    assert "next_chunk_id" not in repeated[0].metadata
    assert "previous_chunk_id" not in repeated[1].metadata


def test_explicit_offsets_survive_only_when_they_match_source_text():
    from kotaemon.indices.knowledge.chunking.identity import stamp_chunk_identity

    source = Document(text="prefix alpha suffix", metadata={"document_id": "s"})
    chunks = [
        Document(text="alpha", metadata={"char_start": 7, "char_end": 12}),
        Document(text="suffix", metadata={"char_start": 0, "char_end": 6}),
    ]

    result = stamp_chunk_identity(source, chunks, source_version="source-v1")

    assert (result[0].metadata["char_start"], result[0].metadata["char_end"]) == (7, 12)
    assert "char_start" not in result[1].metadata
    assert "char_end" not in result[1].metadata


def test_legacy_chunk_is_not_given_fake_adjacency():
    legacy = Document(text="old indexed content", metadata={"document_id": "s"})

    normalized = normalize_knowledge_metadata(legacy)

    assert "source_version" not in normalized
    assert "unit_id" not in normalized
    assert "chunk_ordinal" not in normalized
    assert "previous_chunk_id" not in normalized
    assert "next_chunk_id" not in normalized
