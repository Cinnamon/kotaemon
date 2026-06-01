from typing import Any

from sqlalchemy import select, update

from ktem.db.models import EmbeddingTable

from .base import BaseCRUD


class EmbeddingCRUD(BaseCRUD):
    """CRUD operations for the EmbeddingTable."""

    def clear_defaults(self) -> None:
        """Set all embedding rows to non-default within the current tx."""
        self.session.execute(
            update(EmbeddingTable).values(default=False)
        )

    def create(
        self,
        name: str,
        spec: dict[str, Any],
        *,
        default: bool = False,
    ) -> EmbeddingTable:
        """Insert a new embedding model entry.

        If *default* is True all other entries are demoted first.

        Args:
            name: unique name for this embedding model.
            spec: serialised model specification.
            default: make this model the pool default.

        Returns:
            The newly created EmbeddingTable row.

        Raises:
            ValueError: if an entry with *name* already exists.
        """
        if not name:
            raise ValueError("Name must not be empty")
        if self.get(name) is not None:
            raise ValueError(
                f"Embedding model '{name}' already exists"
            )
        if default:
            self.clear_defaults()
        item = EmbeddingTable(name=name, spec=spec, default=default)
        self.session.add(item)
        self.commit()
        self.session.refresh(item)
        return item

    def get(self, name: str) -> EmbeddingTable | None:
        """Return the entry for *name*, or None.

        Args:
            name: primary-key name of the embedding model.
        """
        return self.session.get(EmbeddingTable, name)

    def list_all(self) -> list[EmbeddingTable]:
        """Return all embedding model entries."""
        return list(
            self.session.scalars(select(EmbeddingTable)).all()
        )

    def update(
        self,
        name: str,
        *,
        spec: dict[str, Any] | None = None,
        default: bool | None = None,
    ) -> EmbeddingTable:
        """Partially update an embedding model entry.

        If *default* is True all other entries are demoted first.

        Args:
            name: primary-key name of the entry to update.
            spec: new spec; unchanged when None.
            default: new default flag; unchanged when None.

        Returns:
            The updated EmbeddingTable row.

        Raises:
            ValueError: if no entry with *name* exists.
        """
        item = self.get(name)
        if item is None:
            raise ValueError(
                f"Embedding model '{name}' not found"
            )
        if default is True:
            self.clear_defaults()
        if spec is not None:
            item.spec = spec
        if default is not None:
            item.default = default
        self.commit()
        self.session.refresh(item)
        return item

    def delete(self, name: str) -> None:
        """Delete the entry for *name*.

        Args:
            name: primary-key name of the embedding model.

        Raises:
            ValueError: if no entry with *name* exists.
        """
        item = self.get(name)
        if item is None:
            raise ValueError(
                f"Embedding model '{name}' not found"
            )
        self.session.delete(item)
        self.commit()
