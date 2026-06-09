from __future__ import annotations

from typing import Literal, Protocol

RelationType = Literal["document", "vector"]


class FileSourceStore(Protocol):
    """Persistence for indexed source files (paths, URLs, metadata)."""

    def find_id_by_name(self, name: str, *, user_id: int) -> str | None:
        """Return an existing source id for *name*, or None."""

    def create_from_url(self, url: str, path_hash: str, *, user_id: int) -> str:
        """Persist a URL source and return its id."""

    def create_from_file(
        self, name: str, path_hash: str, size: int, *, user_id: int
    ) -> str:
        """Persist a file source and return its id."""

    def update_note(self, file_id: str, *, tokens: int | None, loader: str) -> None:
        """Merge token count and loader name into the source note."""

    def delete_source(self, file_id: str) -> None:
        """Remove the source row for *file_id*."""


class ChunkRelationStore(Protocol):
    """Persistence for source-file to chunk / vector id relations."""

    def add_relations(
        self,
        source_id: str,
        target_ids: list[str],
        relation_type: RelationType,
    ) -> None:
        """Record relations between a source file and chunk targets."""

    def list_target_ids(self, source_id: str, relation_type: RelationType) -> list[str]:
        """Return target ids linked to *source_id* with *relation_type*."""

    def list_target_ids_for_sources(
        self, source_ids: list[str], relation_type: RelationType
    ) -> list[str]:
        """Return target ids for many sources with *relation_type*."""

    def delete_by_source(self, source_id: str) -> tuple[list[str], list[str]]:
        """Delete all relations for *source_id*.

        Returns:
            ``(vector_target_ids, document_target_ids)`` before deletion.
        """
