"""Framework-independent search, read, and list operations for knowledge."""

from __future__ import annotations

import unicodedata
from collections.abc import Mapping, Sequence
from typing import Any

from kotaemon.base import Document, RetrievedDocument
from kotaemon.indices.knowledge.planning.query_planner import (
    KnowledgeSource,
    normalize_logical_path,
)
from kotaemon.indices.knowledge.retrieval.contracts import (
    EnrichedQuery,
    RetrievalPolicy,
)
from kotaemon.indices.knowledge.schema import SUPPORTED_SOURCE_TYPES

from .trace import trace_event


class _BoundedCatalog:
    """A planner view containing only sources that passed caller constraints."""

    def __init__(self, sources: Sequence[KnowledgeSource]):
        self._sources = tuple(sources)

    def list_sources(self, allowed_source_ids=None):
        if allowed_source_ids is None:
            return list(self._sources)
        allowed = set(allowed_source_ids)
        return [source for source in self._sources if source.source_id in allowed]


class KnowledgeService:
    """Compose deterministic planning, SQL catalog scoping, and VectorRetrieval.

    The service does not import SQLAlchemy or know how a catalog is persisted.
    Its catalog is responsible for filtering sources by the current index
    visibility rules. ``allowed_source_ids=None`` searches all sources exposed
    by that catalog; an empty allowlist is an explicit request for no access.
    """

    def __init__(self, *, planner, catalog, retriever, docstore):
        self.planner = planner
        self.catalog = catalog
        self.retriever = retriever
        self.docstore = docstore

    def search(
        self,
        query: str,
        *,
        path: str | None = None,
        source_types: Sequence[str] | None = None,
        filters: Mapping[str, Any] | None = None,
        top_k: int = 10,
        allowed_source_ids: Sequence[str] | None = None,
        trace: Any | None = None,
        enriched_query: EnrichedQuery | None = None,
        retrieval_policy: RetrievalPolicy | None = None,
    ) -> list[RetrievedDocument]:
        """Search within visible sources and preserve their mandatory constraints."""
        trace_event(trace, "request", original_query=query)
        if allowed_source_ids is not None and not self._normalize_ids(
            allowed_source_ids
        ):
            trace_event(
                trace,
                "explicit_filters",
                path=path,
                source_types=source_types,
                metadata_filters=filters,
            )
            trace_event(
                trace,
                "source_scope",
                visible_ids=[],
                mandatory_ids=[],
                planned_ids=None,
            )
            trace_event(
                trace,
                "chunk_scope",
                visible_ids=[],
                mandatory_ids=[],
                planned_ids=None,
            )
            trace_event(trace, "no_search", reason="empty_visibility")
            return []

        visible_sources = self._visible_sources(allowed_source_ids)
        if not visible_sources:
            trace_event(
                trace,
                "explicit_filters",
                path=path,
                source_types=source_types,
                metadata_filters=filters,
            )
            trace_event(
                trace,
                "source_scope",
                visible_ids=[],
                mandatory_ids=[],
                planned_ids=None,
            )
            trace_event(
                trace,
                "chunk_scope",
                visible_ids=[],
                mandatory_ids=[],
                planned_ids=None,
            )
            trace_event(trace, "no_search", reason="no_visible_sources")
            return []

        (
            normalized_path,
            normalized_types,
            normalized_filters,
            mandatory_sources,
        ) = self._resolve_constraints(
            visible_sources,
            path=path,
            source_types=source_types,
            filters=filters,
        )
        trace_event(
            trace,
            "explicit_filters",
            path=normalized_path,
            source_types=(list(normalized_types) if source_types is not None else None),
            metadata_filters=normalized_filters,
        )

        mandatory_ids = [source.source_id for source in mandatory_sources]
        if not mandatory_ids:
            trace_event(
                trace,
                "source_scope",
                visible_ids=[source.source_id for source in visible_sources],
                mandatory_ids=[],
                planned_ids=None,
            )
            trace_event(
                trace,
                "chunk_scope",
                visible_ids=[],
                mandatory_ids=[],
                planned_ids=None,
            )
            trace_event(trace, "no_search", reason="explicit_filters_no_match")
            return []

        bounded_catalog = _BoundedCatalog(mandatory_sources)
        plan = self.planner.plan(
            query,
            bounded_catalog,
            source_types=(normalized_types if source_types is not None else None),
            filters=(normalized_filters if filters is not None else None),
            allowed_source_ids=mandatory_ids,
        )

        visible_ids = [source.source_id for source in visible_sources]
        chunk_map = self.catalog.chunk_ids(visible_ids, relation_type="document")
        mandatory_chunks = self._flatten_chunks(mandatory_ids, chunk_map)
        visible_chunks = self._flatten_chunks(visible_ids, chunk_map)

        planned_source_ids = getattr(plan, "source_ids", None)
        if planned_source_ids is None:
            planned_ids = None
            planned_chunks = None
        else:
            mandatory_set = set(mandatory_ids)
            planned_ids = [
                source_id
                for source_id in self._normalize_ids(planned_source_ids)
                if source_id in mandatory_set
            ]
            planned_chunks = self._flatten_chunks(planned_ids, chunk_map)

        trace_event(trace, "plan", plan=plan.to_dict())
        trace_event(
            trace,
            "source_scope",
            visible_ids=visible_ids,
            mandatory_ids=mandatory_ids,
            planned_ids=planned_ids,
        )
        trace_event(
            trace,
            "chunk_scope",
            visible_ids=visible_chunks,
            mandatory_ids=mandatory_chunks,
            planned_ids=planned_chunks,
        )

        retrieval_kwargs = dict(
            text=getattr(plan, "semantic_query", query),
            top_k=top_k,
            scope=planned_chunks,
            fallback_scope=mandatory_chunks,
        )
        if enriched_query is not None:
            retrieval_kwargs["enriched_query"] = enriched_query
        if retrieval_policy is not None:
            retrieval_kwargs["retrieval_policy"] = retrieval_policy
        if trace is not None:
            retrieval_kwargs["trace"] = trace
        documents = self.retriever(**retrieval_kwargs)
        authorized_chunks = set(mandatory_chunks)
        return [
            document for document in documents if document.doc_id in authorized_chunks
        ]

    def authorized_chunk_ids(
        self,
        *,
        path: str | None = None,
        source_types: Sequence[str] | None = None,
        filters: Mapping[str, Any] | None = None,
        allowed_source_ids: Sequence[str] | None = None,
    ) -> frozenset[str]:
        """Return chunks in the same hard source scope used by ``search``.

        The caller allowlist is intersected with the catalog's visible sources
        before path, type, and entity filters are resolved. This is intended for
        follow-on evidence operations that must stay within the original search
        authorization boundary.
        """
        if allowed_source_ids is not None and not self._normalize_ids(
            allowed_source_ids
        ):
            return frozenset()
        visible_sources = self._visible_sources(allowed_source_ids)
        if not visible_sources:
            return frozenset()
        _path, _types, _filters, mandatory_sources = self._resolve_constraints(
            visible_sources,
            path=path,
            source_types=source_types,
            filters=filters,
        )
        mandatory_ids = [source.source_id for source in mandatory_sources]
        if not mandatory_ids:
            return frozenset()
        chunk_map = self.catalog.chunk_ids(mandatory_ids, relation_type="document")
        return frozenset(self._flatten_chunks(mandatory_ids, chunk_map))

    def read(
        self,
        knowledge_id: str,
        *,
        allowed_source_ids: Sequence[str] | None = None,
    ) -> Document | None:
        """Read a chunk only after its SQL document relationship is authorized."""
        if not isinstance(knowledge_id, str) or not knowledge_id:
            return None
        if allowed_source_ids is not None and not self._normalize_ids(
            allowed_source_ids
        ):
            return None

        visible_sources = self._visible_sources(allowed_source_ids)
        visible_ids = [source.source_id for source in visible_sources]
        if not visible_ids:
            return None

        source_map = self.catalog.source_ids_for_chunk_ids(
            [knowledge_id], allowed_source_ids=visible_ids
        )
        source_ids = source_map.get(knowledge_id, ())
        if isinstance(source_ids, str):
            source_ids = (source_ids,)
        if not set(source_ids).intersection(visible_ids):
            return None

        documents = self.docstore.get([knowledge_id])
        if not documents:
            return None
        return next(
            (document for document in documents if document.doc_id == knowledge_id),
            None,
        )

    def list(
        self,
        path: str = "/",
        *,
        allowed_source_ids: Sequence[str] | None = None,
    ) -> list[dict[str, Any]]:
        """List source entries and immediate logical directory children.

        Each item has a ``kind`` of ``source`` or ``directory``. Source rows
        contain logical metadata and a source ID; no storage path is returned.
        Historical sources without a logical path appear as safe root filenames.
        """
        if allowed_source_ids is not None and not self._normalize_ids(
            allowed_source_ids
        ):
            return []
        normalized_path = normalize_logical_path(path)
        sources = self._visible_sources(allowed_source_ids)
        child_directories: dict[str, dict[str, Any]] = {}
        child_sources: list[dict[str, Any]] = []

        for source in sources:
            source_path = self._logical_source_path(source)
            relative = self._relative_to_directory(source_path, normalized_path)
            if relative is None or not relative:
                continue
            child_name, separator, remainder = relative.partition("/")
            child_path = self._join_path(normalized_path, child_name)
            if separator:
                child_directories[child_path] = {
                    "kind": "directory",
                    "name": child_name,
                    "path": child_path,
                }
                continue

            child_sources.append(
                {
                    "kind": "source",
                    "source_id": source.source_id,
                    "name": self._source_name(source, source_path),
                    "path": source_path,
                    "source_type": source.source_type,
                    "entity": self._safe_entity(source.entity),
                }
            )

        items = list(child_directories.values()) + child_sources
        return sorted(
            items,
            key=lambda item: (
                0 if item["kind"] == "directory" else 1,
                item["name"].casefold(),
                item.get("source_id", ""),
            ),
        )

    def chunk_ids_for_sources(self, source_ids: Sequence[str] | None) -> list[str]:
        """Resolve selected, currently visible sources to document chunk IDs.

        This small adapter hook lets the legacy UI retrieve neighboring table
        chunks without widening its selected-source boundary.
        """
        normalized_ids = self._normalize_ids(source_ids)
        if not normalized_ids:
            return []
        visible = self._visible_sources(normalized_ids)
        visible_ids = [source.source_id for source in visible]
        chunk_map = self.catalog.chunk_ids(visible_ids, relation_type="document")
        return self._flatten_chunks(visible_ids, chunk_map)

    def _visible_sources(
        self, allowed_source_ids: Sequence[str] | None
    ) -> list[KnowledgeSource]:
        allowed = (
            None
            if allowed_source_ids is None
            else set(self._normalize_ids(allowed_source_ids))
        )
        rows = self.catalog.list_sources(
            allowed_source_ids=(None if allowed is None else sorted(allowed))
        )
        visible: dict[str, KnowledgeSource] = {}
        for source in rows:
            source_id = getattr(source, "source_id", None)
            if not isinstance(source_id, str) or not source_id:
                continue
            if allowed is not None and source_id not in allowed:
                continue
            visible.setdefault(source_id, source)
        return [visible[source_id] for source_id in sorted(visible)]

    @classmethod
    def _resolve_constraints(
        cls,
        visible_sources: Sequence[KnowledgeSource],
        *,
        path: str | None,
        source_types: Sequence[str] | None,
        filters: Mapping[str, Any] | None,
    ):
        """Resolve caller constraints once for search and authorized follow-ups."""
        normalized_path = normalize_logical_path(path) if path is not None else None
        normalized_types = cls._normalize_source_types(source_types)
        normalized_filters = cls._normalize_filters(filters, visible_sources)
        mandatory_sources = [
            source
            for source in visible_sources
            if cls._matches_constraints(
                source,
                path=normalized_path,
                source_types=(normalized_types if source_types is not None else None),
                filters=normalized_filters,
            )
        ]
        return (
            normalized_path,
            normalized_types,
            normalized_filters,
            mandatory_sources,
        )

    @staticmethod
    def _normalize_ids(source_ids: Sequence[str] | None) -> list[str]:
        if source_ids is None:
            return []
        if isinstance(source_ids, str):
            source_ids = [source_ids]
        if not isinstance(source_ids, Sequence):
            raise ValueError("Source IDs must be a sequence")
        return list(
            dict.fromkeys(str(value) for value in source_ids if value is not None)
        )

    @staticmethod
    def _normalize_source_types(source_types):
        if source_types is None:
            return ()
        if isinstance(source_types, str):
            source_types = [source_types]
        if not isinstance(source_types, Sequence):
            raise ValueError("Source types must be a sequence")
        normalized = tuple(
            sorted({str(value).strip().lower() for value in source_types})
        )
        unsupported = sorted(set(normalized) - set(SUPPORTED_SOURCE_TYPES))
        if unsupported:
            raise ValueError(f"Unsupported source type: {', '.join(unsupported)}")
        return normalized

    @classmethod
    def _normalize_filters(cls, filters, sources):
        if filters is None:
            return {}
        if not isinstance(filters, Mapping):
            raise ValueError("Metadata filters must be a mapping")
        available_keys = {
            key for source in sources for key in cls._safe_entity(source.entity)
        }
        normalized = {}
        for raw_key, value in filters.items():
            key = raw_key.strip() if isinstance(raw_key, str) else ""
            if not key or key not in available_keys:
                raise ValueError(f"Unsupported metadata filter: {raw_key}")
            if isinstance(value, str):
                scalar = value.strip()
            elif isinstance(value, (int, float, bool)):
                scalar = str(value)
            else:
                scalar = ""
            if not scalar:
                raise ValueError(f"Metadata filter {key!r} must be a scalar value")
            normalized[key] = scalar
        return dict(sorted(normalized.items()))

    @classmethod
    def _matches_constraints(
        cls,
        source,
        *,
        path: str | None,
        source_types: Sequence[str] | None,
        filters: Mapping[str, str],
    ) -> bool:
        if source_types is not None and source.source_type not in source_types:
            return False
        if path is not None:
            source_path = cls._logical_source_path(source)
            if (
                path != "/"
                and source_path != path
                and not source_path.startswith(path.rstrip("/") + "/")
            ):
                return False
        entity = cls._safe_entity(source.entity)
        return all(
            key in entity
            and cls._normalize_scalar(entity[key]) == cls._normalize_scalar(value)
            for key, value in filters.items()
        )

    @staticmethod
    def _safe_entity(entity):
        if not isinstance(entity, Mapping):
            return {}
        output = {}
        for raw_key, value in entity.items():
            key = raw_key.strip() if isinstance(raw_key, str) else ""
            if not key:
                continue
            if isinstance(value, str) and value.strip():
                output[key] = value.strip()
            elif isinstance(value, (bool, int, float)):
                output[key] = str(value)
        return output

    @staticmethod
    def _normalize_scalar(value):
        return unicodedata.normalize("NFKC", str(value)).casefold().strip()

    @classmethod
    def _logical_source_path(cls, source):
        raw_path = getattr(source, "virtual_path", None)
        if isinstance(raw_path, str):
            try:
                return normalize_logical_path(raw_path)
            except ValueError:
                pass
        return "/" + cls._source_name(source, None)

    @classmethod
    def _source_name(cls, source, source_path):
        for value in (
            getattr(source, "document_name", None),
            source_path.rsplit("/", 1)[-1] if source_path else None,
            getattr(source, "source_name", None),
        ):
            name = cls._safe_filename(value)
            if name:
                return name
        return source.source_id

    @staticmethod
    def _safe_filename(value):
        if not isinstance(value, str):
            return None
        cleaned = value.replace("\\", "/").split("/")[-1].strip()
        if cleaned in {"", ".", ".."} or "\x00" in cleaned:
            return None
        return cleaned

    @staticmethod
    def _relative_to_directory(source_path, directory):
        if directory == "/":
            return source_path.lstrip("/")
        prefix = directory.rstrip("/") + "/"
        if not source_path.startswith(prefix):
            return None
        return source_path[len(prefix) :]

    @staticmethod
    def _join_path(parent, child):
        return "/" + child if parent == "/" else parent.rstrip("/") + "/" + child

    @staticmethod
    def _flatten_chunks(source_ids, chunk_map):
        return sorted(
            {
                chunk_id
                for source_id in source_ids
                for chunk_id in chunk_map.get(source_id, ())
                if isinstance(chunk_id, str) and chunk_id
            }
        )
