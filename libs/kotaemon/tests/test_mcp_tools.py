from types import SimpleNamespace
from unittest.mock import patch

import pytest

from kotaemon.agents.tools.mcp import (
    MCPTool,
    _json_schema_type_to_python,
    _make_tool,
    build_args_model,
    create_tools_from_config,
    format_tool_list,
    parse_mcp_config,
)

# ---------------------------------------------------------------------------
# _json_schema_type_to_python
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("json_type", "expected"),
    [
        ("string", str),
        ("integer", int),
        ("number", float),
        ("boolean", bool),
        ("object", dict),
        ("array", list),
        ("unknown_type", str),  # fallback
    ],
)
def test_json_schema_type_to_python(json_type: str, expected: type) -> None:
    """Maps JSON Schema types to Python types with fallback to str."""
    assert _json_schema_type_to_python(json_type) is expected


# ---------------------------------------------------------------------------
# build_args_model
# ---------------------------------------------------------------------------


def test_build_args_model_fields_and_name() -> None:
    """Required + optional fields and the generated model name."""
    schema = {
        "properties": {
            "url": {"type": "string", "description": "The URL to fetch"},
            "timeout": {"type": "integer", "description": "Timeout in seconds"},
        },
        "required": ["url"],
    }
    model = build_args_model("fetch", schema)
    assert model.__name__ == "MCPArgs_fetch"
    assert model.model_fields["url"].is_required()
    assert not model.model_fields["timeout"].is_required()


def test_build_args_model_optional_field_preserves_default() -> None:
    """Optional field with default preserves that default."""
    schema = {
        "properties": {
            "limit": {
                "type": "integer",
                "description": "Max results",
                "default": 10,
            },
        },
        "required": [],
    }
    assert build_args_model("search", schema).model_fields["limit"].default == 10


def test_build_args_model_empty_schema_produces_no_fields() -> None:
    """Empty schema produces model with no fields."""
    assert len(build_args_model("empty", {}).model_fields) == 0


# ---------------------------------------------------------------------------
# parse_mcp_config
# ---------------------------------------------------------------------------


def test_parse_mcp_config_full_stdio() -> None:
    """Full stdio config is parsed correctly."""
    config = {
        "transport": "stdio",
        "command": "uvx",
        "args": ["mcp-server-fetch"],
        "env": {"KEY": "value"},
    }
    parsed = parse_mcp_config(config)
    assert parsed == {
        "transport": "stdio",
        "command": "uvx",
        "args": ["mcp-server-fetch"],
        "env": {"KEY": "value"},
    }


def test_parse_mcp_config_defaults_for_empty() -> None:
    """Empty config uses defaults."""
    parsed = parse_mcp_config({})
    assert parsed["transport"] == "stdio"
    assert parsed["command"] == ""
    assert parsed["args"] == []
    assert parsed["env"] == {}


def test_parse_mcp_config_auto_split_multi_word_command() -> None:
    """stdio with no explicit args: space-delimited command is split."""
    parsed = parse_mcp_config({"command": "npx -y mcp-remote https://example.com/sse"})
    assert parsed["command"] == "npx"
    assert parsed["args"] == ["-y", "mcp-remote", "https://example.com/sse"]


def test_parse_mcp_config_no_split_when_args_provided() -> None:
    """Explicit args suppress the auto-split."""
    parsed = parse_mcp_config(
        {
            "command": "npx -y mcp-remote https://example.com/sse",
            "args": ["--flag"],
        }
    )
    assert parsed["command"] == "npx -y mcp-remote https://example.com/sse"
    assert parsed["args"] == ["--flag"]


def test_parse_mcp_config_sse_uses_url_as_command() -> None:
    """For SSE, the url field becomes the effective command."""
    parsed = parse_mcp_config(
        {
            "transport": "sse",
            "url": "http://localhost:8080/sse",
            "command": "ignored",
        }
    )
    assert parsed["transport"] == "sse"
    assert parsed["command"] == "http://localhost:8080/sse"


# ---------------------------------------------------------------------------
# _make_tool
# ---------------------------------------------------------------------------


def test_make_tool_creates_mcp_tool_with_schema() -> None:
    """_make_tool creates MCPTool with correct attributes."""
    parsed = {
        "transport": "stdio",
        "command": "uvx",
        "args": ["mcp-server-fetch"],
        "env": {},
    }
    tool_info = SimpleNamespace(
        name="fetch",
        description="Fetch a URL",
        inputSchema={
            "properties": {"url": {"type": "string", "description": "URL to fetch"}},
            "required": ["url"],
        },
    )
    tool = _make_tool(parsed, tool_info)

    assert isinstance(tool, MCPTool)
    assert tool.name == "fetch"
    assert tool.description == "Fetch a URL"
    assert tool.server_transport == "stdio"
    assert tool.server_command == "uvx"
    assert tool.server_args == ["mcp-server-fetch"]


def test_make_tool_missing_schema_and_description_uses_defaults() -> None:
    """No inputSchema -> args_schema is None; None description -> auto-generated."""
    parsed = {"transport": "stdio", "command": "uvx", "args": [], "env": {}}
    tool_info = SimpleNamespace(name="ping", description=None)
    tool = _make_tool(parsed, tool_info)
    assert tool.description == "MCP tool: ping"
    assert tool.args_schema is None


# ---------------------------------------------------------------------------
# format_tool_list
# ---------------------------------------------------------------------------


def test_format_tool_list_all_enabled_by_default() -> None:
    """All tools enabled when no filter specified."""
    tool_infos = [
        {"name": "fetch", "description": "Fetch a URL"},
        {"name": "search", "description": "Search the web"},
    ]
    result = format_tool_list(tool_infos)
    assert "2" in result
    assert "fetch" in result and "search" in result
    assert "All tools enabled" in result


def test_format_tool_list_partial_filter() -> None:
    """Partial filter shows counts and icons."""
    tool_infos = [
        {"name": "fetch", "description": "Fetch a URL"},
        {"name": "search", "description": "Search the web"},
    ]
    result = format_tool_list(tool_infos, enabled_tools=["fetch"])
    assert "1/2 tool(s) enabled" in result
    assert "✅" in result  # fetch enabled
    assert "⬜" in result  # search disabled


def test_format_tool_list_long_description_truncated() -> None:
    """Long descriptions are truncated."""
    result = format_tool_list([{"name": "tool", "description": "A" * 200}])
    assert "A" * 121 not in result


def test_format_tool_list_none_description_shows_placeholder() -> None:
    """None description shows placeholder."""
    result = format_tool_list([{"name": "tool", "description": None}])
    assert "No description" in result


# ---------------------------------------------------------------------------
# create_tools_from_config (mocked MCP server connection)
# ---------------------------------------------------------------------------


def _make_mock_tools() -> list[MCPTool]:
    """Create mock MCPTool list for testing."""
    return [
        MCPTool(
            name="fetch",
            description="Fetch",
            server_transport="stdio",
            server_command="uvx",
            mcp_tool_name="fetch",
        ),
        MCPTool(
            name="search",
            description="Search",
            server_transport="stdio",
            server_command="uvx",
            mcp_tool_name="search",
        ),
    ]


@patch("kotaemon.agents.tools.mcp._run_async")
def test_create_tools_from_config_no_filter_returns_all(mock_run_async) -> None:
    """No filter returns all tools."""
    mock_run_async.return_value = _make_mock_tools()
    tools = create_tools_from_config({"command": "uvx"})
    assert len(tools) == 2


@patch("kotaemon.agents.tools.mcp._run_async")
def test_create_tools_from_config_enabled_filter(mock_run_async) -> None:
    """Non-empty filter returns only nominated tools; empty list returns all."""
    mock_run_async.return_value = _make_mock_tools()
    filtered = create_tools_from_config({"command": "uvx"}, enabled_tools=["fetch"])
    assert len(filtered) == 1
    assert filtered[0].mcp_tool_name == "fetch"

    mock_run_async.return_value = _make_mock_tools()
    all_tools = create_tools_from_config({"command": "uvx"}, enabled_tools=[])
    assert len(all_tools) == 2


# ---------------------------------------------------------------------------
# MCPTool._format_result
# ---------------------------------------------------------------------------


@pytest.fixture
def mcp_tool() -> MCPTool:
    """Create a test MCPTool instance."""
    return MCPTool(
        name="test",
        description="Test tool",
        server_transport="stdio",
        server_command="echo",
        mcp_tool_name="test",
    )


def test_mcp_tool_format_result_text_joined(mcp_tool: MCPTool) -> None:
    """Text content is joined with newlines."""
    result = mcp_tool._format_result(
        SimpleNamespace(
            isError=False,
            content=[SimpleNamespace(text="Hello"), SimpleNamespace(text="World")],
        )
    )
    assert result == "Hello\nWorld"


def test_mcp_tool_format_result_error_flag(mcp_tool: MCPTool) -> None:
    """Error flag produces error message."""
    result = mcp_tool._format_result(
        SimpleNamespace(
            isError=True,
            content="Something went wrong",
        )
    )
    assert "MCP Tool Error" in result


def test_mcp_tool_format_result_binary_content(mcp_tool: MCPTool) -> None:
    """Binary content shows mime type placeholder."""
    result = mcp_tool._format_result(
        SimpleNamespace(
            isError=False,
            content=[SimpleNamespace(data=b"bytes", mimeType="image/png")],
        )
    )
    assert "[Binary data: image/png]" in result
