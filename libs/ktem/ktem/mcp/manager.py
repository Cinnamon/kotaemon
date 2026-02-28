"""Manager for MCP server configurations.

Provides CRUD operations on the MCPTable.
All tool building/discovery logic lives in kotaemon.agents.tools.mcp.
"""

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import MCPTable, engine

logger = logging.getLogger(__name__)


class MCPManager:
    """Manages MCP server configurations stored in the database."""

    def __init__(self):
        self._configs: dict[str, dict] = {}
        self.load()

    def load(self):
        """Reload configurations from the database."""
        self._info = {}
        with Session(engine) as session:
            stmt = select(MCPTable)
            items = session.execute(stmt)
            for (item,) in items:
                self._info[item.name] = {
                    "name": item.name,
                    "config": item.config,
                }

    def info(self) -> dict:
        """Return all MCP server configurations."""
        return self._info

    def get(self, name: str) -> dict | None:
        """Get a single configuration by name."""
        return self._info.get(name)

    def add(self, name: str, config: dict):
        """Add a new MCP server configuration."""
        name = name.strip()
        if not name:
            raise ValueError("Name must not be empty")

        with Session(engine) as session:
            item = MCPTable(name=name, config=config)
            session.add(item)
            session.commit()

        self.load()

    def update(self, name: str, config: dict):
        """Update an existing MCP server configuration."""
        if not name:
            raise ValueError("Name must not be empty")

        with Session(engine) as session:
            item = session.query(MCPTable).filter_by(name=name).first()
            if not item:
                raise ValueError(f"MCP server '{name}' not found")
            item.config = config  # type: ignore[assignment]
            session.commit()

        self.load()

    def delete(self, name: str):
        """Delete an MCP server configuration."""
        with Session(engine) as session:
            item = session.query(MCPTable).filter_by(name=name).first()
            if item:
                session.delete(item)
                session.commit()

        self.load()

    def get_enabled_tools(self) -> list[str]:
        """Return tool choice names for all MCP servers."""
        choices = []
        for name, entry in self._info.items():
            config = entry.get("config", {})
            enabled_tools = config.get("enabled_tools", None)
            if enabled_tools is not None:
                choices.append(f"[MCP] {name}")
        return choices


mcp_manager = MCPManager()
