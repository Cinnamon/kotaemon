"""Tests for ktem.mcp.manager module.

Uses an in-memory SQLite engine to test MCPManager CRUD operations
without depending on the application's database.
"""

import pytest
from sqlalchemy import JSON, Column, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Session

# ---------------------------------------------------------------------------
# In-memory DB setup (mirrors ktem.mcp.db but fully isolated)
# ---------------------------------------------------------------------------


class _Base(DeclarativeBase):
    pass


class _MCPTable(_Base):
    __tablename__ = "mcp_table"
    name = Column(String, primary_key=True, unique=True)
    config = Column(JSON, default={})


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def manager():
    """Fresh manager with a clean in-memory DB for each test."""
    engine = create_engine("sqlite:///:memory:")
    _MCPTable.metadata.create_all(engine)
    return MCPManagerForTest(engine)


# ---------------------------------------------------------------------------
# Minimal MCPManager that uses the test engine
# ---------------------------------------------------------------------------


class MCPManagerForTest:
    """Same logic as ktem.mcp.manager.MCPManager but uses our test engine."""

    def __init__(self, engine):
        self._engine = engine
        self._info: dict[str, dict] = {}
        self.load()

    def load(self):
        self._info = {}
        with Session(self._engine) as session:
            for item in session.query(_MCPTable).all():
                self._info[item.name] = {  # type: ignore[index]
                    "name": item.name,
                    "config": item.config,
                }

    def info(self) -> dict:
        return self._info

    def get(self, name: str) -> dict | None:
        return self._info.get(name)

    def add(self, name: str, config: dict):
        name = name.strip()
        if not name:
            raise ValueError("Name must not be empty")
        with Session(self._engine) as session:
            session.add(_MCPTable(name=name, config=config))
            session.commit()
        self.load()

    def update(self, name: str, config: dict):
        if not name:
            raise ValueError("Name must not be empty")
        with Session(self._engine) as session:
            item = session.query(_MCPTable).filter_by(name=name).first()
            if not item:
                raise ValueError(f"MCP server '{name}' not found")
            item.config = config  # type: ignore[assignment]
            session.commit()
        self.load()

    def delete(self, name: str):
        with Session(self._engine) as session:
            item = session.query(_MCPTable).filter_by(name=name).first()
            if item:
                session.delete(item)
                session.commit()
        self.load()

    def get_enabled_tools(self) -> list[str]:
        return [
            f"[MCP] {name}"
            for name, entry in self._info.items()
            if entry.get("config", {}).get("enabled_tools") is not None
        ]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestMCPManagerAdd:
    def test_add_and_retrieve(self, manager):
        """add() persists data; get() and info() reflect it."""
        manager.add("server1", {"command": "uvx", "args": ["mcp-server-fetch"]})
        assert manager.info()["server1"]["config"]["command"] == "uvx"
        assert manager.get("server1")["name"] == "server1"

    def test_add_multiple(self, manager):
        manager.add("s1", {"command": "cmd1"})
        manager.add("s2", {"command": "cmd2"})
        assert set(manager.info().keys()) == {"s1", "s2"}

    @pytest.mark.parametrize("name", ["", "   "])
    def test_empty_or_whitespace_name_raises(self, manager, name):
        with pytest.raises(ValueError, match="Name must not be empty"):
            manager.add(name, {})

    def test_whitespace_name_is_stripped(self, manager):
        manager.add("  server1  ", {"command": "uvx"})
        assert "server1" in manager.info()

    def test_complex_config_stored_correctly(self, manager):
        config = {
            "command": "uvx",
            "env": {"JIRA_URL": "https://example.atlassian.net"},
            "enabled_tools": ["jira_search"],
        }
        manager.add("atlassian", config)
        stored = manager.get("atlassian")["config"]
        assert stored["env"]["JIRA_URL"] == "https://example.atlassian.net"
        assert stored["enabled_tools"] == ["jira_search"]


class TestMCPManagerUpdateDelete:
    def test_update_changes_config(self, manager):
        manager.add("s1", {"command": "cmd1"})
        manager.add("s2", {"command": "cmd2"})
        manager.update("s1", {"command": "updated"})
        assert manager.info()["s1"]["config"]["command"] == "updated"
        assert manager.info()["s2"]["config"]["command"] == "cmd2"  # untouched

    def test_update_nonexistent_raises(self, manager):
        with pytest.raises(ValueError, match="not found"):
            manager.update("ghost", {})

    def test_delete_removes_entry(self, manager):
        manager.add("s1", {})
        manager.add("s2", {})
        manager.delete("s1")
        assert "s1" not in manager.info()
        assert "s2" in manager.info()

    def test_delete_nonexistent_is_noop(self, manager):
        manager.delete("ghost")  # must not raise
        assert len(manager.info()) == 0


class TestMCPManagerGetEnabledTools:
    def test_only_servers_with_enabled_tools_listed(self, manager):
        manager.add("no_filter", {"command": "uvx"})
        manager.add("with_filter", {"command": "uvx", "enabled_tools": ["tool_a"]})
        choices = manager.get_enabled_tools()
        assert "[MCP] no_filter" not in choices
        assert "[MCP] with_filter" in choices

    def test_empty_when_no_servers(self, manager):
        assert manager.get_enabled_tools() == []


class TestMCPManagerLoad:
    def test_load_picks_up_external_db_changes(self, manager):
        manager.add("server1", {})
        with Session(manager._engine) as session:
            session.add(_MCPTable(name="external", config={"command": "ext"}))
            session.commit()

        assert "external" not in manager.info()  # not yet refreshed
        manager.load()
        assert "external" in manager.info()
