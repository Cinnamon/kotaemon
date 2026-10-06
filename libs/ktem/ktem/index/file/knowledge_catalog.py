"""SQL-backed catalog for visible knowledge sources and their stored chunks."""

import unicodedata
from collections.abc import Mapping, Sequence
from typing import Callable

from ktem.db.engine import engine
from sqlalchemy import select
from sqlalchemy.orm import Session

from kotaemon.indices.knowledge.planning.query_planner import (
    KnowledgeSource,
    normalize_logical_path,
)
from kotaemon.indices.knowledge.schema import SUPPORTED_SOURCE_TYPES


class KnowledgeCatalog:
    """Read canonical knowledge metadata through existing Source/Index tables.

    ``private`` mirrors the file-index setting. The caller-supplied allowlist is
    always intersected with the visible SQL rows, so it cannot widen visibility.
    """

    def __init__(
        self,
        Source,
        Index,
        *,
        private: bool = False,
        user_id: str | None = None,
        session_factory: Callable[[], Session] | None = None,
    ):
        self.Source = Source
        self.Index = Index
        self.private = private
        self.user_id = user_id
        self.session_factory = session_factory or (lambda: Session(engine))

    def list_sources(
        self, allowed_source_ids: Sequence[str] | None = None
    ) -> list[KnowledgeSource]:
        allowed = self._normalize_allowed_ids(allowed_source_ids)
        if allowed_source_ids is not None and not allowed:
            return []
        if self.private and not self.user_id:
            return []

        statement = select(self.Source)
        if self.private:
            statement = statement.where(self.Source.user == self.user_id)
        if allowed is not None:
            statement = statement.where(self.Source.id.in_(allowed))

        with self.session_factory() as session:
            rows = session.execute(statement).scalars().all()
            return [self._to_source(row) for row in rows if self._source_id(row)]

    def resolve_source_ids(
        self,
        *,
        path: str | None = None,
        source_type: str | None = None,
        entity_filters: Mapping[str, object] | None = None,
        allowed_source_ids: Sequence[str] | None = None,
    ) -> tuple[str, ...]:
        normalized_path = normalize_logical_path(path) if path is not None else None
        normalized_source_type = (
            source_type.strip().lower() if isinstance(source_type, str) else source_type
        )
        if (
            normalized_source_type is not None
            and normalized_source_type not in SUPPORTED_SOURCE_TYPES
        ):
            raise ValueError(f"Unsupported source type: {source_type}")
        filters = self._normalize_entity_filters(entity_filters)
        sources = self.list_sources(allowed_source_ids)
        available_entity_keys = {key for source in sources for key in source.entity}
        unsupported_keys = sorted(set(filters) - available_entity_keys)
        if unsupported_keys:
            raise ValueError(
                f"Unsupported entity filter: {', '.join(unsupported_keys)}"
            )
        matches = []
        for source in sources:
            if normalized_path is not None and source.virtual_path != normalized_path:
                continue
            if (
                normalized_source_type is not None
                and source.source_type != normalized_source_type
            ):
                continue
            if not all(
                key in source.entity
                and self._normalize_scalar(source.entity[key])
                == self._normalize_scalar(value)
                for key, value in filters.items()
            ):
                continue
            matches.append(source.source_id)
        return tuple(sorted(matches))

    def chunk_ids(
        self, source_ids: Sequence[str], *, relation_type: str = "document"
    ) -> dict[str, tuple[str, ...]]:
        requested = self._normalize_allowed_ids(source_ids) or set()
        if not requested or self.private and not self.user_id:
            return {}

        statement = (
            select(self.Index.source_id, self.Index.target_id)
            .join(self.Source, self.Index.source_id == self.Source.id)
            .where(
                self.Index.source_id.in_(requested),
                self.Index.relation_type == relation_type,
            )
        )
        if self.private:
            statement = statement.where(self.Source.user == self.user_id)

        grouped: dict[str, set[str]] = {}
        with self.session_factory() as session:
            for source_id, target_id in session.execute(statement).all():
                if (
                    isinstance(source_id, str)
                    and isinstance(target_id, str)
                    and target_id
                ):
                    grouped.setdefault(source_id, set()).add(target_id)

        return {
            source_id: tuple(sorted(chunk_ids))
            for source_id, chunk_ids in sorted(grouped.items())
        }

    def source_ids_for_chunk_ids(
        self,
        chunk_ids: Sequence[str],
        *,
        allowed_source_ids: Sequence[str] | None = None,
    ) -> dict[str, tuple[str, ...]]:
        """Resolve chunk IDs through document relations and visible SQL sources."""
        requested_chunks = self._normalize_allowed_ids(chunk_ids) or set()
        allowed = self._normalize_allowed_ids(allowed_source_ids)
        if (
            not requested_chunks
            or allowed_source_ids is not None
            and not allowed
            or self.private
            and not self.user_id
        ):
            return {}

        statement = (
            select(self.Index.target_id, self.Index.source_id)
            .join(self.Source, self.Index.source_id == self.Source.id)
            .where(
                self.Index.target_id.in_(requested_chunks),
                self.Index.relation_type == "document",
            )
        )
        if self.private:
            statement = statement.where(self.Source.user == self.user_id)
        if allowed is not None:
            statement = statement.where(self.Index.source_id.in_(allowed))

        grouped: dict[str, set[str]] = {}
        with self.session_factory() as session:
            for target_id, source_id in session.execute(statement).all():
                if (
                    isinstance(target_id, str)
                    and isinstance(source_id, str)
                    and target_id in requested_chunks
                    and (allowed is None or source_id in allowed)
                ):
                    grouped.setdefault(target_id, set()).add(source_id)

        return {
            chunk_id: tuple(sorted(source_ids))
            for chunk_id, source_ids in sorted(grouped.items())
        }

    @staticmethod
    def _normalize_allowed_ids(source_ids):
        if source_ids is None:
            return None
        if isinstance(source_ids, str):
            source_ids = [source_ids]
        try:
            return {str(source_id) for source_id in source_ids if source_id is not None}
        except TypeError:
            raise ValueError("allowed_source_ids must be a sequence") from None

    @staticmethod
    def _source_id(row):
        value = getattr(row, "id", None)
        return value if isinstance(value, str) and value else None

    @classmethod
    def _to_source(cls, row):
        source_id = cls._source_id(row)
        note = getattr(row, "note", None)
        knowledge = note.get("knowledge") if isinstance(note, Mapping) else None
        if not isinstance(knowledge, Mapping):
            knowledge = {}

        source_type = knowledge.get("source_type")
        if source_type not in SUPPORTED_SOURCE_TYPES:
            source_type = None

        virtual_path = knowledge.get("virtual_path")
        if isinstance(virtual_path, str):
            try:
                virtual_path = normalize_logical_path(virtual_path)
            except ValueError:
                virtual_path = None
        else:
            virtual_path = None

        document_name = knowledge.get("document_name")
        if (
            not isinstance(document_name, str)
            or not document_name.strip()
            or "/" in document_name
            or "\\" in document_name
            or "\x00" in document_name
        ):
            document_name = None
        else:
            document_name = document_name.strip()

        raw_entity = knowledge.get("entity")
        entity = {}
        if isinstance(raw_entity, Mapping):
            for key, value in raw_entity.items():
                if not isinstance(key, str) or not key.strip():
                    continue
                if isinstance(value, str) and value.strip():
                    entity[key.strip()] = value.strip()
                elif isinstance(value, (bool, int, float)):
                    entity[key.strip()] = str(value)

        return KnowledgeSource(
            source_id=source_id,
            source_type=source_type,
            virtual_path=virtual_path,
            document_name=document_name,
            entity=entity,
            source_name=(
                getattr(row, "name", None)
                if isinstance(getattr(row, "name", None), str)
                else None
            ),
        )

    @staticmethod
    def _normalize_entity_filters(filters):
        if filters is None:
            return {}
        if not isinstance(filters, Mapping):
            raise ValueError("Entity filters must be a mapping")
        normalized = {}
        for key, value in filters.items():
            if not isinstance(key, str) or not key.strip():
                raise ValueError("Entity filter keys must be non-empty strings")
            if isinstance(value, str) and value.strip():
                normalized[key.strip()] = value.strip()
            elif isinstance(value, (bool, int, float)):
                normalized[key.strip()] = str(value)
            else:
                raise ValueError(f"Entity filter {key!r} must be a scalar value")
        return normalized

    @staticmethod
    def _normalize_scalar(value):
        return unicodedata.normalize("NFKC", str(value)).casefold().strip()
