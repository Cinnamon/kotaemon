from typing import Any, Optional

from ktem.db.models import Index
from sqlalchemy import select

from .base import BaseCRUD


class IndexCRUD(BaseCRUD):
    """CRUD operations for the Index (collection) table."""

    def create(
        self,
        name: str,
        index_type: str,
        config: dict[str, Any],
    ) -> Index:
        """Insert a new index entry.

        Args:
            name: unique collection name.
            index_type: registry key for the index class.
            config: constructor kwargs for the index.

        Returns:
            The newly created Index row.

        Raises:
            ValueError: if *name* is empty or already exists.
        """
        if not name:
            raise ValueError("Name must not be empty")
        if self.get_by_name(name) is not None:
            raise ValueError(f'Index "{name}" already exists')
        item = Index(name=name, index_type=index_type, config=config)
        self.session.add(item)
        self.commit()
        self.session.refresh(item)
        return item

    def get(self, id: int) -> Index | None:
        """Return the index with the given *id*, or None."""
        return self.session.get(Index, id)

    def get_by_name(self, name: str) -> Index | None:
        """Return the index with the given *name*, or None."""
        stmt = select(Index).where(Index.name == name)
        return self.session.scalars(stmt).one_or_none()

    def list_all(self) -> list[Index]:
        """Return all index entries."""
        return list(self.session.scalars(select(Index)).all())

    def update(
        self,
        id: int,
        *,
        name: Optional[str] = None,
        config: Optional[dict[str, Any]] = None,
    ) -> Index:
        """Partially update an index entry.

        Raises:
            ValueError: if no entry with *id* exists.
        """
        item = self.get(id)
        if item is None:
            raise ValueError(f"Index with id {id} does not exist")
        if name is not None:
            item.name = name
        if config is not None:
            item.config = config
        self.commit()
        self.session.refresh(item)
        return item

    def delete(self, id: int) -> None:
        """Delete the index with the given *id*.

        Raises:
            ValueError: if no entry with *id* exists.
        """
        item = self.get(id)
        if item is None:
            raise ValueError(f"Index with id {id} does not exist")
        self.session.delete(item)
        self.commit()
