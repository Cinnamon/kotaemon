"""Manager for MCP server configurations.

Provides CRUD operations on the MCPTable.
All tool building/discovery logic lives in kotaemon.agents.tools.mcp.
"""

import logging

from ktem.db.cruds import MCPCRUD
from ktem.db.engine import engine

logger = logging.getLogger(__name__)

MCP_TOOL_PREFIX = "[MCP] "


class MCPManager:
    """Manages MCP server configurations stored in the database."""

    def __init__(self):
        self._configs: dict[str, dict] = {}
        self.load()

    def load(self):
        """Reload configurations from the database."""
        self._info = {}
        with MCPCRUD(engine) as crud:
            for item in crud.list_all():
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
        with MCPCRUD(engine) as crud:
            crud.create(name=name, config=config)
        self.load()

    def update(self, name: str, config: dict):
        """Update an existing MCP server configuration."""
        with MCPCRUD(engine) as crud:
            crud.update(name, config)
        self.load()

    def delete(self, name: str):
        """Delete an MCP server configuration."""
        with MCPCRUD(engine) as crud:
            try:
                crud.delete(name)
            except ValueError:
                pass
        self.load()

    def list_registered_mcp_servers(self) -> list[str]:
        """Return tool choice names for all registered MCP servers."""
        return [f"{MCP_TOOL_PREFIX}{name}" for name in self._info]


mcp_manager = MCPManager()
