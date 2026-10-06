"""Stable source-version and ordered adjacency metadata for knowledge chunks."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Sequence

from kotaemon.base import Document

from ..metadata import CHUNK_IDENTITY_METADATA_KEYS, normalize_knowledge_metadata
from .base import semantic_unit_identity

_LOCATOR_KEYS = (
    "page_label",
    "page_number",
    "page",
    "sheet_name",
    "row_number",
    "slide_number",
    "element_ordinal",
    "unit_ordinal",
    "parser_unit_ordinal",
    "heading",
    "category",
    "category_depth",
)
_INTERNAL_UNIT_ORDINAL = "_parser_unit_ordinal"
_SEMANTIC_UNIT_GROUP_ID = "_semantic_unit_group_id"
_SOURCE_UNIT_TEXT = "source_unit_text"


def source_version_for_bytes(content: bytes) -> str:
    """Return the SHA-256 source version for already available bytes."""
    return hashlib.sha256(content).hexdigest()


def source_version_for_path(path: Path) -> str:
    """Hash a source file incrementally so large uploads are not read at once."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as source_file:
        while block := source_file.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def _canonical_json(value) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _identity_value(metadata: dict, keys: Sequence[str]) -> dict:
    return {
        key: metadata[key]
        for key in keys
        if key in metadata and metadata[key] not in (None, "", [], {})
    }


def _locator_identity(metadata: dict) -> dict:
    return _identity_value(metadata, _LOCATOR_KEYS)


def _verified_offsets(source: Document, chunk: Document, metadata: dict) -> dict:
    start = metadata.get("char_start")
    end = metadata.get("char_end")
    if (
        not isinstance(start, int)
        or isinstance(start, bool)
        or not isinstance(end, int)
        or isinstance(end, bool)
    ):
        return {}
    source_metadata = dict(source.metadata or {})
    unit_text = source_metadata.get(_SOURCE_UNIT_TEXT)
    if not isinstance(unit_text, str):
        unit_text = source.text
    if 0 <= start <= end <= len(unit_text) and unit_text[start:end] == chunk.text:
        return {"char_start": start, "char_end": end}
    return {}


def _group_parent(
    source_metadata: dict, chunk_metadata: dict, source_id: str, chunk_id: str
) -> str:
    """Use parent IDs only to group one call; never persist them in unit IDs."""
    semantic_parent = chunk_metadata.get(_SEMANTIC_UNIT_GROUP_ID)
    if semantic_parent:
        return str(semantic_parent)
    chunk_parent = chunk_metadata.get("parent_id")
    own_chunk_id = chunk_metadata.get("chunk_id", chunk_id)
    if chunk_parent and str(chunk_parent) != str(own_chunk_id):
        return str(chunk_parent)
    return str(
        source_metadata.get("parent_id")
        or source_metadata.get("file_id")
        or source_metadata.get("document_id")
        or source_id
    )


def stamp_chunk_identity(
    source: Document,
    chunks: Sequence[Document],
    *,
    source_version: str,
) -> list[Document]:
    """Stamp ordered chunks with a stable source unit and in-unit neighbors.

    Chunk IDs are owned by the splitter and remain unchanged. Existing semantic
    parent IDs are used only to group chunks from this call; the persisted unit
    identity uses source version, locators, semantic names, and source order.
    """
    if not chunks:
        return []

    source_metadata = dict(source.metadata or {})
    source_id = str(
        source_metadata.get("file_id")
        or source_metadata.get("document_id")
        or source_metadata.get("virtual_path")
        or source_metadata.get("document_name")
        or "source"
    )
    parser_ordinal = source_metadata.get(
        _INTERNAL_UNIT_ORDINAL,
        source_metadata.get(
            "parser_unit_ordinal", source_metadata.get("unit_ordinal", 0)
        ),
    )

    # Preserve first-emitted order. The semantic parent may be a random UUID,
    # but it is deliberately absent from the descriptor used to persist IDs.
    groups: dict[tuple[str, bytes], list[int]] = {}
    descriptors: dict[tuple[str, bytes], dict] = {}
    for index, chunk in enumerate(chunks):
        raw_metadata = dict(chunk.metadata or {})
        combined_metadata = {**source_metadata, **raw_metadata}
        semantic = semantic_unit_identity(combined_metadata)
        locator = _locator_identity(combined_metadata)
        group_parent = _group_parent(
            source_metadata, raw_metadata, source_id, chunk.doc_id
        )
        group_key = (
            group_parent,
            _canonical_json({"semantic": semantic, "locator": locator}),
        )
        groups.setdefault(group_key, []).append(index)
        descriptors.setdefault(
            group_key,
            {
                "semantic": semantic,
                "locator": locator,
                "parser_unit_ordinal": parser_ordinal,
            },
        )

    occurrence_by_descriptor: defaultdict[bytes, int] = defaultdict(int)
    unit_ids: dict[tuple[str, bytes], str] = {}
    for group_key, descriptor in descriptors.items():
        stable_descriptor = _canonical_json(descriptor)
        occurrence = occurrence_by_descriptor[stable_descriptor]
        occurrence_by_descriptor[stable_descriptor] += 1
        unit_ids[group_key] = hashlib.sha256(
            b"knowledge-unit:v1\0"
            + source_version.encode("utf-8")
            + b"\0"
            + stable_descriptor
            + b"\0"
            + str(occurrence).encode("ascii")
        ).hexdigest()

    stamped = list(chunks)
    for group_key, indices in groups.items():
        unit_id = unit_ids[group_key]
        for ordinal, index in enumerate(indices):
            chunk = stamped[index]
            raw_metadata = dict(chunk.metadata or {})
            explicit_offsets = _verified_offsets(source, chunk, raw_metadata)
            metadata = dict(normalize_knowledge_metadata(chunk))
            for key in CHUNK_IDENTITY_METADATA_KEYS:
                metadata.pop(key, None)
            metadata.pop(_INTERNAL_UNIT_ORDINAL, None)
            metadata.pop(_SEMANTIC_UNIT_GROUP_ID, None)
            metadata.pop(_SOURCE_UNIT_TEXT, None)
            metadata.update(
                source_version=source_version,
                unit_id=unit_id,
                chunk_ordinal=ordinal,
            )
            metadata.update(explicit_offsets)
            if ordinal > 0:
                metadata["previous_chunk_id"] = stamped[indices[ordinal - 1]].doc_id
            if ordinal + 1 < len(indices):
                metadata["next_chunk_id"] = stamped[indices[ordinal + 1]].doc_id
            chunk.metadata = metadata

    return stamped
