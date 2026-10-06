"""Source-aware chunking interfaces and semantic-unit construction."""

from collections.abc import Mapping
from typing import Any, Protocol

from kotaemon.base import Document

from ..metadata import normalize_knowledge_metadata

_SEMANTIC_IDENTITY_KEYS = (
    "section_path",
    "class_name",
    "function_name",
    "method_name",
    "symbol",
    "heading",
    "question",
    "slide_title",
)


def semantic_unit_identity(metadata: Mapping[str, Any]) -> dict[str, Any]:
    """Return stable semantic names without including generated parent IDs."""
    return {
        key: metadata[key]
        for key in _SEMANTIC_IDENTITY_KEYS
        if key in metadata and metadata[key] not in (None, "", [], {})
    }


class ChunkStrategy(Protocol):
    def split(self, document: Document) -> list[Document]:
        """Split a source document into independent knowledge units."""
        ...


def semantic_unit(document: Document, text: str, section_path: list[str]) -> Document:
    """Copy source metadata onto a unit with a distinct semantic identity."""
    unit = Document(
        text=text,
        metadata=normalize_knowledge_metadata(document),
        source=document.source,
        channel=document.channel,
        excluded_embed_metadata_keys=list(document.excluded_embed_metadata_keys),
        excluded_llm_metadata_keys=list(document.excluded_llm_metadata_keys),
    )
    unit.metadata.update(
        section_path=list(section_path),
        parent_id=unit.doc_id,
        _semantic_unit_group_id=unit.doc_id,
    )
    return unit
