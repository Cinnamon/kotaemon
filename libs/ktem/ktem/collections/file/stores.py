from __future__ import annotations

from dataclasses import dataclass

from ktem.db.cruds.file_chunk_relation import FileChunkRelationCRUD
from ktem.db.cruds.file_source import FileSourceCRUD
from ktem.db.models.file_index import BaseFileChunkRelation, BaseFileSource
from sqlalchemy.engine import Engine

from kotaemon.indices.stores import RelationType


@dataclass(kw_only=True)
class SqlAlchemyFileSourceStore:
    """SQLAlchemy-backed :class:`~kotaemon.indices.stores.FileSourceStore`.

    Delegates persistence to :class:`~ktem.db.cruds.file_source.FileSourceCRUD`.
    """

    engine: Engine
    source_model: type[BaseFileSource]
    private: bool = False

    def find_id_by_name(self, name: str, *, user_id: int) -> str | None:
        with FileSourceCRUD(
            self.engine, self.source_model, private=self.private
        ) as crud:
            return crud.get_id_by_name(name, user_id=user_id)

    def create_from_url(self, url: str, path_hash: str, *, user_id: int) -> str:
        with FileSourceCRUD(
            self.engine, self.source_model, private=self.private
        ) as crud:
            return crud.create_url(url, path_hash, user_id=user_id)

    def create_from_file(
        self, name: str, path_hash: str, size: int, *, user_id: int
    ) -> str:
        with FileSourceCRUD(
            self.engine, self.source_model, private=self.private
        ) as crud:
            return crud.create_file(name, path_hash, size, user_id=user_id)

    def update_note(self, file_id: str, *, tokens: int | None, loader: str) -> None:
        with FileSourceCRUD(
            self.engine, self.source_model, private=self.private
        ) as crud:
            crud.update_note(file_id, tokens=tokens, loader=loader)

    def delete_source(self, file_id: str) -> None:
        with FileSourceCRUD(
            self.engine, self.source_model, private=self.private
        ) as crud:
            crud.delete(file_id)


@dataclass(kw_only=True)
class SqlAlchemyChunkRelationStore:
    """SQLAlchemy-backed :class:`~kotaemon.indices.stores.ChunkRelationStore`.

    Delegates persistence to
    :class:`~ktem.db.cruds.file_chunk_relation.FileChunkRelationCRUD`.
    """

    engine: Engine
    index_model: type[BaseFileChunkRelation]

    def add_relations(
        self,
        source_id: str,
        target_ids: list[str],
        relation_type: RelationType,
    ) -> None:
        with FileChunkRelationCRUD(self.engine, self.index_model) as crud:
            crud.add_relations(source_id, target_ids, relation_type)

    def list_target_ids(self, source_id: str, relation_type: RelationType) -> list[str]:
        with FileChunkRelationCRUD(self.engine, self.index_model) as crud:
            return crud.list_target_ids(source_id, relation_type)

    def list_target_ids_for_sources(
        self, source_ids: list[str], relation_type: RelationType
    ) -> list[str]:
        with FileChunkRelationCRUD(self.engine, self.index_model) as crud:
            return crud.list_target_ids_for_sources(source_ids, relation_type)

    def delete_by_source(self, source_id: str) -> tuple[list[str], list[str]]:
        with FileChunkRelationCRUD(self.engine, self.index_model) as crud:
            return crud.delete_by_source(source_id)
