from __future__ import annotations

from ktem.db.models.file_index import BaseFileChunkRelation
from sqlalchemy import select
from sqlalchemy.engine import Engine

from kotaemon.indices.stores import RelationType

from .base import BaseCRUD


class FileChunkRelationCRUD(BaseCRUD):
    """CRUD for :class:`~ktem.db.models.file_index.BaseFileChunkRelation`."""

    def __init__(
        self, engine: Engine, index_model: type[BaseFileChunkRelation]
    ) -> None:
        super().__init__(engine)
        self._index_model = index_model

    def add_relations(
        self,
        source_id: str,
        target_ids: list[str],
        relation_type: RelationType,
    ) -> None:
        """Insert source-to-chunk relations."""
        if not source_id:
            raise ValueError("source_id must not be empty")
        if not target_ids:
            return
        self.session.add_all(
            [
                self._index_model(
                    source_id=source_id,
                    target_id=target_id,
                    relation_type=relation_type,
                )
                for target_id in target_ids
            ]
        )
        self.commit()

    def list_target_ids(
        self,
        source_id: str,
        relation_type: RelationType,
    ) -> list[str]:
        """Return target ids for one source and relation type."""
        if not source_id:
            raise ValueError("source_id must not be empty")
        return list(
            self.session.scalars(
                select(self._index_model.target_id).where(
                    self._index_model.source_id == source_id,
                    self._index_model.relation_type == relation_type,
                )
            ).all()
        )

    def list_target_ids_for_sources(
        self,
        source_ids: list[str],
        relation_type: RelationType,
    ) -> list[str]:
        """Return target ids for many sources and one relation type."""
        if not source_ids:
            return []
        return [
            row.target_id
            for row in self.session.scalars(
                select(self._index_model).where(
                    self._index_model.relation_type == relation_type,
                    self._index_model.source_id.in_(source_ids),
                )
            ).all()
        ]

    def delete_by_source(self, source_id: str) -> tuple[list[str], list[str]]:
        """Delete all relations for *source_id*.

        Returns:
            ``(vector_target_ids, document_target_ids)`` collected before delete.
        """
        if not source_id:
            raise ValueError("source_id must not be empty")
        vs_ids: list[str] = []
        ds_ids: list[str] = []
        for row in self.session.scalars(
            select(self._index_model).where(self._index_model.source_id == source_id)
        ).all():
            if row.relation_type == "vector":
                vs_ids.append(row.target_id)
            elif row.relation_type == "document":
                ds_ids.append(row.target_id)
            self.session.delete(row)
        self.commit()
        return vs_ids, ds_ids
