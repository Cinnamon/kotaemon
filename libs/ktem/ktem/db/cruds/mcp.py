from typing import Any

from ktem.mcp.db import MCPTable
from sqlalchemy import select

from .base import BaseCRUD


class MCPCRUD(BaseCRUD):
    """CRUD operations for the MCPTable."""

    def create(self, name: str, config: dict[str, Any]) -> MCPTable:
        """Insert a new MCP server configuration.

        Args:
            name: unique server name.
            config: constructor / connection kwargs.

        Returns:
            The newly created MCPTable row.

        Raises:
            ValueError: if *name* is empty or already exists.
        """
        name = name.strip()
        if not name:
            raise ValueError("Name must not be empty")
        if self.get(name) is not None:
            raise ValueError(f"MCP server '{name}' already exists")
        item = MCPTable(name=name, config=config)
        self.session.add(item)
        self.commit()
        self.session.refresh(item)
        return item

    def get(self, name: str) -> MCPTable | None:
        """Return the entry for *name*, or None."""
        return self.session.get(MCPTable, name)

    def list_all(self) -> list[MCPTable]:
        """Return all MCP server configurations."""
        return list(self.session.scalars(select(MCPTable)).all())

    def update(self, name: str, config: dict[str, Any]) -> MCPTable:
        """Replace the config for an existing MCP server.

        Args:
            name: primary-key name of the server.
            config: new configuration dict.

        Returns:
            The updated MCPTable row.

        Raises:
            ValueError: if no entry with *name* exists.
        """
        item = self.get(name)
        if item is None:
            raise ValueError(f"MCP server '{name}' not found")
        item.config = config
        self.commit()
        self.session.refresh(item)
        return item

    def delete(self, name: str) -> None:
        """Delete the MCP server with the given *name*.

        Raises:
            ValueError: if no entry with *name* exists.
        """
        item = self.get(name)
        if item is None:
            raise ValueError(f"MCP server '{name}' not found")
        self.session.delete(item)
        self.commit()
