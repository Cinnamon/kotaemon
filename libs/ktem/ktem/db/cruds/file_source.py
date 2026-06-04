from __future__ import annotations

from ktem.db.models.file_index import BaseFileSource
from sqlalchemy import delete, select
from sqlalchemy.engine import Engine

from .base import BaseCRUD


class FileSourceCRUD(BaseCRUD):
    """CRUD for a per-collection :class:`~ktem.db.models.file_index.BaseFileSource`."""

    def __init__(
        self,
        engine: Engine,
        source_model: type[BaseFileSource],
        *,
        private: bool = False,
    ) -> None:
        super().__init__(engine)
        self._source_model = source_model
        self._private = private

    def get_id_by_name(self, name: str, *, user_id: int) -> str | None:
        """Return the source id for *name*, or None if not indexed."""
        if not name:
            raise ValueError("Name must not be empty")
        cond = (
            (self._source_model.name == name, self._source_model.user == str(user_id))
            if self._private
            else (self._source_model.name == name,)
        )
        item = self.session.scalars(select(self._source_model).where(*cond)).first()
        if item is None:
            return None
        return item.id

    def create_url(self, url: str, path_hash: str, *, user_id: int) -> str:
        """Insert a URL source row and return its id."""
        if not url:
            raise ValueError("URL must not be empty")
        item = self._source_model(
            name=url,
            path=path_hash,
            size=0,
            user=str(user_id),
        )
        self.session.add(item)
        self.commit()
        self.session.refresh(item)
        return item.id

    def create_file(
        self,
        name: str,
        path_hash: str,
        size: int,
        *,
        user_id: int,
    ) -> str:
        """Insert a file source row and return its id."""
        if not name:
            raise ValueError("Name must not be empty")
        item = self._source_model(
            name=name,
            path=path_hash,
            size=size,
            user=str(user_id),
        )
        self.session.add(item)
        self.commit()
        self.session.refresh(item)
        return item.id

    def update_note(
        self,
        file_id: str,
        *,
        tokens: int | None,
        loader: str,
    ) -> None:
        """Merge token count and loader into the source note JSON."""
        if not file_id:
            raise ValueError("file_id must not be empty")
        item = self.session.scalars(
            select(self._source_model).where(self._source_model.id == file_id)
        ).first()
        if item is None:
            return
        if tokens is not None:
            item.note["tokens"] = tokens
        item.note["loader"] = loader
        self.session.add(item)
        self.commit()

    def delete(self, file_id: str) -> None:
        """Delete the source row for *file_id*."""
        if not file_id:
            raise ValueError("file_id must not be empty")
        self.session.execute(
            delete(self._source_model).where(self._source_model.id == file_id)
        )
        self.commit()
