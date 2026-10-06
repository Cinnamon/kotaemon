"""Normalization helpers for metadata shared by knowledge components."""

from pathlib import PurePosixPath
from typing import Any, Mapping

from llama_index.core.schema import NodeRelationship

from kotaemon.base import Document

from .schema import SUPPORTED_SOURCE_TYPES

EXTENSION_SOURCE_TYPES = {
    ".md": "markdown",
    ".markdown": "markdown",
    ".pdf": "pdf",
    ".faq": "faq",
    ".ppt": "ppt",
    ".pptx": "ppt",
    ".xls": "excel",
    ".xlsx": "excel",
    ".csv": "excel",
    ".py": "code",
    ".js": "code",
    ".jsx": "code",
    ".ts": "code",
    ".tsx": "code",
    ".java": "code",
    ".go": "code",
    ".rs": "code",
    ".c": "code",
    ".h": "code",
    ".cpp": "code",
    ".hpp": "code",
}

CHUNK_IDENTITY_METADATA_KEYS = frozenset(
    {
        "source_version",
        "unit_id",
        "chunk_ordinal",
        "previous_chunk_id",
        "next_chunk_id",
        "char_start",
        "char_end",
    }
)


def infer_source_type(metadata: Mapping[str, Any], document_name=None) -> str:
    """Return a supported explicit type or infer it from a document extension."""
    explicit = metadata.get("source_type")
    if explicit is not None:
        return explicit if explicit in SUPPORTED_SOURCE_TYPES else "other"

    name = document_name or metadata.get("file_name") or metadata.get("file_path", "")
    suffix = PurePosixPath(str(name).replace("\\", "/")).suffix.lower()
    return EXTENSION_SOURCE_TYPES.get(suffix, "other")


def normalize_virtual_path(value, document_name: str) -> str:
    """Normalize a logical path using POSIX segments without filesystem access."""
    raw = value if isinstance(value, str) and value.strip() else f"/{document_name}"
    parts = []
    for part in raw.strip().replace("\\", "/").split("/"):
        if part in {"", "."}:
            continue
        if part == "..":
            if parts:
                parts.pop()
            continue
        parts.append(part)
    return "/" + "/".join(parts) if parts else "/document"


def _first_present(*values):
    return next((value for value in values if value is not None and value != ""), None)


def normalize_knowledge_metadata(
    document: Document, overrides: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    """Return a canonical metadata copy without mutating ``document``.

    Chunk identity fields pass through when they were explicitly stamped. This
    normalizer does not synthesize identity or adjacency for legacy chunks.
    """
    metadata = dict(document.metadata or {})
    metadata.update(dict(overrides or {}))

    raw_name = metadata.get("document_name") or metadata.get("file_name")
    if not raw_name:
        raw_name = metadata.get("file_path") or "document"
    document_name = PurePosixPath(str(raw_name).replace("\\", "/")).name or "document"

    relationship = (document.relationships or {}).get(NodeRelationship.SOURCE)
    source_id = getattr(relationship, "node_id", None)

    section_path = metadata.get("section_path") or []
    if isinstance(section_path, str):
        section_path = [section_path]
    elif isinstance(section_path, (list, tuple)):
        section_path = [str(part) for part in section_path]
    else:
        section_path = []

    entity = metadata.get("entity")
    return {
        **metadata,
        "source_type": infer_source_type(metadata, document_name),
        "virtual_path": normalize_virtual_path(
            metadata.get("virtual_path"), document_name
        ),
        "document_id": _first_present(
            metadata.get("document_id"),
            metadata.get("file_id"),
            source_id,
            document.doc_id,
        ),
        "document_name": document_name,
        "section_path": list(section_path),
        "parent_id": _first_present(
            metadata.get("parent_id"), source_id, document.doc_id
        ),
        "chunk_id": document.doc_id,
        "entity": dict(entity) if isinstance(entity, Mapping) else {},
        "page": _first_present(
            metadata.get("page"),
            metadata.get("page_label"),
            metadata.get("page_number"),
        ),
        "source": metadata.get("source", document.source),
    }
