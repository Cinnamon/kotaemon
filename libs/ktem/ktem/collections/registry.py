"""Explicit registry for collection / index types and file-index pipelines."""

from __future__ import annotations

from enum import Enum
from typing import Type

from ktem.collections.base import BaseCollection


class IndexKind(str, Enum):
    FILE = "FileIndex"


class IndexPipelineKind(str, Enum):
    INDEX = "IndexDocumentPipeline"
    RETRIEVER = "DocumentRetrievalPipeline"
    SELECTOR_UI = "FileSelector"
    INDEX_UI = "FileIndexPage"


_LEGACY_INDEX_TYPE_MAP: dict[str, IndexKind] = {
    "ktem.collections.file.FileIndex": IndexKind.FILE,
}

_LEGACY_PIPELINE_MAP: dict[str, IndexPipelineKind] = {
    "ktem.collections.file.indexing.IndexDocumentPipeline": (
        IndexPipelineKind.INDEX
    ),
    "ktem.collections.file.retriever.impl.rag.DocumentRetrievalPipeline": (
        IndexPipelineKind.RETRIEVER
    ),
    "ktem.collections.file.ui.FileSelector": IndexPipelineKind.SELECTOR_UI,
    "ktem.collections.file.ui.FileIndexPage": IndexPipelineKind.INDEX_UI,
}


def get_index_cls(value: str | IndexKind) -> type[BaseCollection]:
    from ktem.collections.file.index import FileIndex

    mp: dict[IndexKind, type[BaseCollection]] = {IndexKind.FILE: FileIndex}
    if isinstance(value, IndexKind):
        return mp[value]
    if value in _LEGACY_INDEX_TYPE_MAP:
        return mp[_LEGACY_INDEX_TYPE_MAP[value]]
    try:
        return mp[IndexKind(value)]
    except ValueError as exc:
        raise ValueError(f"Unknown index type: {value!r}") from exc


def get_pipeline_cls(value: str | IndexPipelineKind) -> type:
    from ktem.collections.file.indexing import IndexDocumentPipeline
    from ktem.collections.file.retriever.impl.rag import DocumentRetrievalPipeline
    from ktem.collections.file.ui import FileIndexPage, FileSelector

    mp = {
        IndexPipelineKind.INDEX: IndexDocumentPipeline,
        IndexPipelineKind.RETRIEVER: DocumentRetrievalPipeline,
        IndexPipelineKind.SELECTOR_UI: FileSelector,
        IndexPipelineKind.INDEX_UI: FileIndexPage,
    }
    if isinstance(value, IndexPipelineKind):
        return mp[value]
    if value in _LEGACY_PIPELINE_MAP:
        return mp[_LEGACY_PIPELINE_MAP[value]]
    try:
        return mp[IndexPipelineKind(value)]
    except ValueError as exc:
        raise ValueError(f"Unknown index pipeline: {value!r}") from exc
