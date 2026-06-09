from typing import Any

from ktem.db.models import LLMTable
from sqlalchemy import select, update

from kotaemon.llms.chats.factory import LLMVendor

from .base import BaseCRUD


class LLMCRUD(BaseCRUD):
    """CRUD operations for the LLMTable."""

    def clear_defaults(self) -> None:
        """Set all LLM rows to non-default within the current tx."""
        self.session.execute(update(LLMTable).values(default=False))

    def create(
        self,
        name: str,
        vendor: LLMVendor,
        spec: dict[str, Any],
        *,
        default: bool = False,
    ) -> LLMTable:
        """Insert a new LLM entry.

        If *default* is True all other entries are demoted first.

        Args:
            name: unique name for this LLM.
            vendor: vendor class identifier for factory lookup.
            spec: constructor parameters for the vendor class.
            default: make this model the pool default.

        Returns:
            The newly created LLMTable row.

        Raises:
            ValueError: if an entry with *name* already exists.
        """
        if not name:
            raise ValueError("Name must not be empty")
        if self.get(name) is not None:
            raise ValueError(f"LLM '{name}' already exists")
        if default:
            self.clear_defaults()
        item = LLMTable(name=name, vendor=vendor, spec=spec, default=default)
        self.session.add(item)
        self.commit()
        self.session.refresh(item)
        return item

    def get(self, name: str) -> LLMTable | None:
        """Return the entry for *name*, or None.

        Args:
            name: primary-key name of the LLM.
        """
        return self.session.get(LLMTable, name)

    def list_all(self) -> list[LLMTable]:
        """Return all LLM entries."""
        return list(self.session.scalars(select(LLMTable)).all())

    def update(
        self,
        name: str,
        *,
        vendor: LLMVendor | None = None,
        spec: dict[str, Any] | None = None,
        default: bool | None = None,
    ) -> LLMTable:
        """Partially update an LLM entry.

        If *default* is True all other entries are demoted first.

        Args:
            name: primary-key name of the entry to update.
            vendor: new vendor class id; unchanged when None.
            spec: new spec; unchanged when None.
            default: new default flag; unchanged when None.

        Returns:
            The updated LLMTable row.

        Raises:
            ValueError: if no entry with *name* exists.
        """
        item = self.get(name)
        if item is None:
            raise ValueError(f"LLM '{name}' not found")
        if default is True:
            self.clear_defaults()
        if vendor is not None:
            item.vendor = vendor
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
            name: primary-key name of the LLM.

        Raises:
            ValueError: if no entry with *name* exists.
        """
        item = self.get(name)
        if item is None:
            raise ValueError(f"LLM '{name}' not found")
        self.session.delete(item)
        self.commit()
