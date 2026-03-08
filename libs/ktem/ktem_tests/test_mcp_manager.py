from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from ktem.mcp.db import MCPTable
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from ktem.mcp.manager import MCPManager
    from pytest_mock.plugin import MockerFixture


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def test_engine():
    """Create an in-memory SQLite engine with MCPTable schema."""
    engine = create_engine("sqlite:///:memory:")
    MCPTable.metadata.create_all(engine)
    return engine


@pytest.fixture
def manager(test_engine, mocker: MockerFixture) -> MCPManager:
    """Fresh MCPManager with a mocked in-memory DB for each test."""
    mocker.patch("ktem.mcp.manager.engine", test_engine)
    from ktem.mcp.manager import MCPManager

    return MCPManager()


# ---------------------------------------------------------------------------
# MCPManager.add tests
# ---------------------------------------------------------------------------


def test_add_and_retrieve(manager: MCPManager) -> None:
    """add() persists data; get() and info() reflect it."""
    manager.add("server1", {"command": "uvx", "args": ["mcp-server-fetch"]})
    assert manager.info()["server1"]["config"]["command"] == "uvx"
    entry = manager.get("server1")
    assert entry is not None
    assert entry["name"] == "server1"


def test_add_multiple(manager: MCPManager) -> None:
    """Multiple servers can be added."""
    manager.add("s1", {"command": "cmd1"})
    manager.add("s2", {"command": "cmd2"})
    assert set(manager.info().keys()) == {"s1", "s2"}


@pytest.mark.parametrize("name", ["", "   "])
def test_add_empty_or_whitespace_name_raises(
    manager: MCPManager,
    name: str,
) -> None:
    """Empty or whitespace-only name raises ValueError."""
    with pytest.raises(ValueError, match="Name must not be empty"):
        manager.add(name, {})


def test_add_whitespace_name_is_stripped(manager: MCPManager) -> None:
    """Whitespace in name is stripped."""
    manager.add("  server1  ", {"command": "uvx"})
    assert "server1" in manager.info()


def test_add_complex_config_stored_correctly(manager: MCPManager) -> None:
    """Complex config with nested data is stored correctly."""
    config = {
        "command": "uvx",
        "env": {"JIRA_URL": "https://example.atlassian.net"},
        "enabled_tools": ["jira_search"],
    }
    manager.add("atlassian", config)
    entry = manager.get("atlassian")
    assert entry is not None
    stored = entry["config"]
    assert stored["env"]["JIRA_URL"] == "https://example.atlassian.net"
    assert stored["enabled_tools"] == ["jira_search"]


# ---------------------------------------------------------------------------
# MCPManager.update and delete tests
# ---------------------------------------------------------------------------


def test_update_changes_config(manager: MCPManager) -> None:
    """update() changes config for specified server only."""
    manager.add("s1", {"command": "cmd1"})
    manager.add("s2", {"command": "cmd2"})
    manager.update("s1", {"command": "updated"})
    assert manager.info()["s1"]["config"]["command"] == "updated"
    assert manager.info()["s2"]["config"]["command"] == "cmd2"  # untouched


def test_update_nonexistent_raises(manager: MCPManager) -> None:
    """Updating nonexistent server raises ValueError."""
    with pytest.raises(ValueError, match="not found"):
        manager.update("ghost", {})


def test_delete_removes_entry(manager: MCPManager) -> None:
    """delete() removes the specified entry."""
    manager.add("s1", {})
    manager.add("s2", {})
    manager.delete("s1")
    assert "s1" not in manager.info()
    assert "s2" in manager.info()


def test_delete_nonexistent_is_noop(manager: MCPManager) -> None:
    """Deleting nonexistent server is a no-op."""
    manager.delete("ghost")  # must not raise
    assert len(manager.info()) == 0


# ---------------------------------------------------------------------------
# MCPManager.get_enabled_tools tests
# ---------------------------------------------------------------------------


def test_get_enabled_tools_only_servers_with_filter(manager: MCPManager) -> None:
    """Only servers with enabled_tools are listed."""
    manager.add("no_filter", {"command": "uvx"})
    manager.add("with_filter", {"command": "uvx", "enabled_tools": ["tool_a"]})
    choices = manager.get_enabled_tools()
    assert "[MCP] no_filter" not in choices
    assert "[MCP] with_filter" in choices


def test_get_enabled_tools_empty_when_no_servers(manager: MCPManager) -> None:
    """Returns empty list when no servers configured."""
    assert manager.get_enabled_tools() == []


# ---------------------------------------------------------------------------
# MCPManager.load tests
# ---------------------------------------------------------------------------


def test_load_picks_up_external_db_changes(
    manager: MCPManager,
    test_engine,
) -> None:
    """load() refreshes from database, picking up external changes."""
    manager.add("server1", {})
    with Session(test_engine) as session:
        session.add(MCPTable(name="external", config={"command": "ext"}))
        session.commit()

    assert "external" not in manager.info()  # not yet refreshed
    manager.load()
    assert "external" in manager.info()
