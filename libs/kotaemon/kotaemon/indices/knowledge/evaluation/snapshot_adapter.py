"""Adapt an already reviewed local snapshot to the public knowledge runtime."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any, Literal, Mapping, Sequence

from kotaemon.base import Document
from kotaemon.embeddings import BaseEmbeddings
from kotaemon.indices.knowledge.chunking.registry import get_chunk_strategy
from kotaemon.indices.knowledge.metadata import infer_source_type
from kotaemon.indices.knowledge.planning.query_planner import KnowledgeSource
from kotaemon.indices.knowledge.planning.retrieval_plan import RetrievalPlan
from kotaemon.indices.knowledge.retrieval.contracts import RetrievalPolicy
from kotaemon.indices.knowledge.runtime.index import (
    KnowledgeRuntime,
    build_knowledge_runtime,
)
from kotaemon.indices.knowledge.retrieval.knowledge_service import KnowledgeService
from kotaemon.indices.rankings import BaseReranking
from kotaemon.indices.splitters import TokenSplitter

from .local_ingest import DraftChunk
from .local_snapshot import LocalSnapshot


@dataclass(frozen=True)
class UnresolvedChunkOffsets:
    source_id: str
    unit_id: str
    locator: Mapping[str, Any]
    candidate_spans: tuple[tuple[int, int], ...]


class SnapshotCatalog:
    """Visibility-aware in-memory source catalog for a reviewed snapshot."""

    def __init__(
        self,
        sources: Sequence[KnowledgeSource],
        chunk_map: Mapping[str, Sequence[str]],
        chunk_to_source: Mapping[str, str] | None = None,
    ):
        self._sources = tuple(sources)
        self._chunk_map = {key: tuple(value) for key, value in chunk_map.items()}
        owners = dict(chunk_to_source or {})
        for source_id, chunk_ids in self._chunk_map.items():
            for chunk_id in chunk_ids:
                if chunk_id in owners and owners[chunk_id] != source_id:
                    raise ValueError(f"Chunk {chunk_id!r} has multiple sources")
                owners[chunk_id] = source_id
        self._chunk_to_source = owners

    def list_sources(self, allowed_source_ids=None):
        if allowed_source_ids is None:
            return list(self._sources)
        allowed = set(allowed_source_ids)
        return [source for source in self._sources if source.source_id in allowed]

    def chunk_ids(self, source_ids, relation_type="document"):
        if relation_type != "document":
            raise ValueError("The snapshot catalog supports document chunks only")
        return {
            source_id: list(self._chunk_map.get(source_id, ()))
            for source_id in source_ids
        }

    def source_ids_for_chunk_ids(
        self, chunk_ids: Sequence[str], *, allowed_source_ids=None
    ) -> dict[str, tuple[str, ...]]:
        allowed = None if allowed_source_ids is None else set(allowed_source_ids)
        owners = {}
        for chunk_id in dict.fromkeys(chunk_ids):
            source_id = self._chunk_to_source.get(chunk_id)
            if source_id is not None and (allowed is None or source_id in allowed):
                owners[chunk_id] = (source_id,)
        return owners


class _GlobalIdentityPlanner:
    """Keep snapshot queries unchanged while preserving explicit constraints."""

    def plan(
        self,
        query: str,
        catalog,
        *,
        path: str | None = None,
        source_types: Sequence[str] | None = None,
        filters: Mapping[str, Any] | None = None,
        allowed_source_ids: Sequence[str] | None = None,
    ) -> RetrievalPlan:
        del catalog, allowed_source_ids
        return RetrievalPlan(
            query=query,
            semantic_query=query,
            source_types=tuple(source_types or ()),
            virtual_paths=() if path is None else (path,),
            metadata_filters=dict(filters or {}),
            confidence=0.0,
            reason="global identity plan; caller constraints remain enforced",
            source_ids=None,
        )


@dataclass
class SnapshotRuntime(KnowledgeRuntime):
    chunk_to_source: Mapping[str, str] = field(default_factory=dict)
    source_labels: Mapping[str, str] = field(default_factory=dict)
    locators: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    chunk_map: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    source_types: Mapping[str, str] = field(default_factory=dict)
    draft_chunks: Mapping[str, DraftChunk] = field(default_factory=dict)
    unresolved_offsets: Mapping[str, UnresolvedChunkOffsets] = field(
        default_factory=dict
    )


def _snapshot_catalog(
    snapshot: LocalSnapshot,
    chunk_map: Mapping[str, Sequence[str]],
    chunk_to_source: Mapping[str, str],
) -> SnapshotCatalog:
    return SnapshotCatalog(
        [
            KnowledgeSource(
                source_id=source["source_id"],
                source_type=infer_source_type({}, "source" + source["suffix"]),
                virtual_path="/",
                entity={},
                document_name=source["relative_path"].rsplit("/", 1)[-1],
                source_name=source["relative_path"],
            )
            for source in snapshot.selected_sources
        ],
        chunk_map,
        chunk_to_source,
    )


def _text_spans(source_text: str, chunk_text: str) -> tuple[tuple[int, int], ...]:
    spans = []
    start = source_text.find(chunk_text)
    while start >= 0:
        spans.append((start, start + len(chunk_text)))
        start = source_text.find(chunk_text, start + 1)
    return tuple(spans)


def build_snapshot_documents(
    snapshot: LocalSnapshot,
    *,
    chunking_mode: Literal["token", "registry"] = "token",
) -> tuple[
    list[Document],
    dict[str, str],
    dict[str, tuple[str, ...]],
    dict[str, str],
    dict[str, DraftChunk],
    dict[str, UnresolvedChunkOffsets],
    dict[str, Mapping[str, Any]],
]:
    """Convert approved unit text using the old v2 token/registry split rules."""
    if not isinstance(snapshot, LocalSnapshot):
        raise TypeError("snapshot must be a validated LocalSnapshot")
    if chunking_mode not in ("token", "registry"):
        raise ValueError("chunking_mode must be 'token' or 'registry'")

    source_by_id = {source["source_id"]: source for source in snapshot.selected_sources}
    units = [
        unit
        for unit in snapshot.records["source_units"]
        if unit["source_id"] in source_by_id
    ]
    if not units:
        raise ValueError("The reviewed snapshot has no selected source units")

    token_splitter = TokenSplitter(
        chunk_size=1024,
        chunk_overlap=256,
        separator="\n\n",
        backup_separators=["\n", ".", " ", "\u200b"],
    )
    strategies = {}
    chunks: list[Document] = []
    chunk_to_source: dict[str, str] = {}
    source_chunks: dict[str, list[str]] = {}
    source_types: dict[str, str] = {}
    draft_chunks: dict[str, DraftChunk] = {}
    unresolved_offsets: dict[str, UnresolvedChunkOffsets] = {}
    locators: dict[str, Mapping[str, Any]] = {}

    for unit in units:
        source_id = unit["source_id"]
        source = source_by_id[source_id]
        source_type = infer_source_type({}, "source" + source["suffix"])
        source_types[source_id] = source_type
        metadata = {
            "source_id": source_id,
            "unit_id": unit["unit_id"],
            "unit_ordinal": unit["unit_ordinal"],
            "document_id": source_id,
            "virtual_path": "/",
            "source_type": source_type,
            "section_path": [],
            "entity": {},
            **dict(unit["locator"]),
        }
        source_document = Document(
            text=unit["normalized_text"],
            id_=unit["unit_id"],
            metadata=metadata,
        )
        if chunking_mode == "registry":
            strategy = strategies.get(source_type)
            if strategy is None:
                strategy = get_chunk_strategy(source_type, token_splitter)
                strategies[source_type] = strategy
        else:
            strategy = get_chunk_strategy("other", token_splitter)

        split_documents = strategy.split(source_document)
        local_unit_chunks: list[Document] = []
        for ordinal, split_document in enumerate(split_documents):
            if not split_document.text:
                continue
            chunk_id = (
                "local-"
                + hashlib.sha256(
                    f"{unit['unit_id']}\0{ordinal}\0{split_document.text}".encode(
                        "utf-8"
                    )
                ).hexdigest()[:24]
            )
            chunk_metadata = dict(split_document.metadata or {})
            chunk_metadata.update(
                source_id=source_id,
                unit_id=unit["unit_id"],
                unit_ordinal=unit["unit_ordinal"],
                source_version=source["sha256"],
                source_type=source_type,
                virtual_path="/",
                document_id=source_id,
                chunk_id=chunk_id,
                parent_id=unit["unit_id"],
                chunk_ordinal=len(local_unit_chunks),
            )
            spans = _text_spans(unit["normalized_text"], split_document.text)
            if len(spans) == 1:
                start, end = spans[0]
                chunk_metadata.update(char_start=start, char_end=end)
                draft_chunks[chunk_id] = DraftChunk(
                    chunk_id=chunk_id,
                    source_id=source_id,
                    relative_path=unit["relative_path"],
                    unit_id=unit["unit_id"],
                    unit_ordinal=unit["unit_ordinal"],
                    chunk_ordinal=len(local_unit_chunks),
                    locator=dict(unit["locator"]),
                    text=split_document.text,
                    char_start=start,
                    char_end=end,
                )
            else:
                unresolved_offsets[chunk_id] = UnresolvedChunkOffsets(
                    source_id=source_id,
                    unit_id=unit["unit_id"],
                    locator=dict(unit["locator"]),
                    candidate_spans=spans,
                )
            locators[chunk_id] = dict(unit["locator"])
            local_unit_chunks.append(
                Document(
                    text=split_document.text,
                    id_=chunk_id,
                    metadata=chunk_metadata,
                )
            )

        for ordinal, chunk in enumerate(local_unit_chunks):
            if ordinal:
                chunk.metadata["previous_chunk_id"] = local_unit_chunks[
                    ordinal - 1
                ].doc_id
            if ordinal + 1 < len(local_unit_chunks):
                chunk.metadata["next_chunk_id"] = local_unit_chunks[ordinal + 1].doc_id
            chunk.metadata["chunk_ordinal"] = ordinal
            chunks.append(chunk)
            chunk_id = chunk.doc_id
            chunk_to_source[chunk_id] = source_id
            source_chunks.setdefault(source_id, []).append(chunk_id)

    if not chunks:
        raise ValueError("The reviewed snapshot produced no non-empty chunks")
    if len(chunk_to_source) != len(chunks):
        raise ValueError("Chunk generation produced duplicate chunk IDs")
    chunk_map = {
        source_id: tuple(sorted(ids)) for source_id, ids in source_chunks.items()
    }
    return (
        chunks,
        chunk_to_source,
        chunk_map,
        source_types,
        draft_chunks,
        unresolved_offsets,
        locators,
    )


def build_snapshot_runtime(
    snapshot: LocalSnapshot,
    *,
    embedding: BaseEmbeddings,
    reranker: BaseReranking | None,
    policy: RetrievalPolicy,
    chunking_mode: Literal["token", "registry"] = "token",
    lexical: bool = False,
) -> SnapshotRuntime:
    """Build a private in-memory index from reviewed snapshot units."""
    (
        documents,
        chunk_to_source,
        chunk_map,
        source_types,
        draft_chunks,
        unresolved_offsets,
        locators,
    ) = build_snapshot_documents(snapshot, chunking_mode=chunking_mode)
    sources_by_id = {
        source["source_id"]: source for source in snapshot.selected_sources
    }
    catalog = SnapshotCatalog(
        [
            KnowledgeSource(
                source_id=source["source_id"],
                source_type=infer_source_type({}, "source" + source["suffix"]),
                virtual_path="/",
                entity={},
                document_name=source["relative_path"].rsplit("/", 1)[-1],
                source_name=source["relative_path"],
            )
            for source in snapshot.selected_sources
        ],
        chunk_map,
        chunk_to_source,
    )
    runtime = build_knowledge_runtime(
        documents,
        catalog=catalog,
        embedding=embedding,
        reranker=reranker,
        policy=policy,
        lexical=lexical,
    )
    runtime.service.planner = _GlobalIdentityPlanner()
    runtime.config = {
        **runtime.config,
        "chunking_mode": chunking_mode,
        "snapshot_fingerprint": snapshot.fingerprint,
    }
    return SnapshotRuntime(
        service=runtime.service,
        docstore=runtime.docstore,
        catalog=catalog,
        documents=runtime.documents,
        vector_store=runtime.vector_store,
        embedding=runtime.embedding,
        policy=runtime.policy,
        config=runtime.config,
        chunk_to_source=chunk_to_source,
        source_labels={
            source_id: source["relative_path"]
            for source_id, source in sources_by_id.items()
        },
        locators=locators,
        chunk_map=chunk_map,
        source_types=source_types,
        draft_chunks=draft_chunks,
        unresolved_offsets=unresolved_offsets,
    )


def build_snapshot_replay_runtime(
    snapshot: LocalSnapshot,
    *,
    policy: RetrievalPolicy,
    chunking_mode: Literal["token", "registry"],
    lexical: bool,
    lexical_status: str,
    reranker_available: bool,
) -> SnapshotRuntime:
    """Build snapshot metadata for authenticated trace replay without indexing."""
    (
        documents,
        chunk_to_source,
        chunk_map,
        source_types,
        draft_chunks,
        unresolved_offsets,
        locators,
    ) = build_snapshot_documents(snapshot, chunking_mode=chunking_mode)
    sources_by_id = {
        source["source_id"]: source for source in snapshot.selected_sources
    }
    catalog = _snapshot_catalog(snapshot, chunk_map, chunk_to_source)
    retriever = SimpleNamespace(
        rerankers=([object()] if reranker_available else [])
    )
    service = KnowledgeService(
        planner=_GlobalIdentityPlanner(),
        catalog=catalog,
        retriever=retriever,
        docstore=None,
    )
    config = {
        "retrieval_policy": {
            "enabled": policy.enabled,
            "candidate_k": policy.candidate_k,
            "max_fused_candidates": policy.max_fused_candidates,
            "max_variants": policy.max_variants,
            "dense_weight": policy.dense_weight,
            "lexical_weight": policy.lexical_weight,
            "rrf_k": policy.rrf_k,
        },
        "lexical_requested": lexical,
        "lexical_status": lexical_status,
        "chunking_mode": chunking_mode,
        "snapshot_fingerprint": snapshot.fingerprint,
    }
    return SnapshotRuntime(
        service=service,
        docstore=None,
        catalog=catalog,
        documents=tuple(documents),
        vector_store=None,
        embedding=None,
        policy=policy,
        config=config,
        chunk_to_source=chunk_to_source,
        source_labels={
            source_id: source["relative_path"]
            for source_id, source in sources_by_id.items()
        },
        locators=locators,
        chunk_map=chunk_map,
        source_types=source_types,
        draft_chunks=draft_chunks,
        unresolved_offsets=unresolved_offsets,
    )
