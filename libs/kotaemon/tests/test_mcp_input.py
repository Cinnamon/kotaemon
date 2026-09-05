import json
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from kotaemon.agents.tools.mcp import MCPTool, build_args_model


def make_tool(properties, required):
    return MCPTool(
        name="example",
        description="Example tool",
        args_schema=build_args_model(
            "example", {"properties": properties, "required": required}
        ),
    )


@pytest.mark.parametrize("as_json", [False, True])
@pytest.mark.parametrize("invoke", ["run", "__call__"])
def test_run_structured_input(as_json, invoke):
    tool = make_tool(
        {"objective": {"type": "string"}, "queries": {"type": "array"}},
        ["objective", "queries"],
    )
    arguments = {"objective": "Find public docs", "queries": ["MCP setup"]}
    with patch.object(MCPTool, "_run_tool", return_value="result") as run:
        assert (
            getattr(tool, invoke)(json.dumps(arguments) if as_json else arguments)
            == "result"
        )
    run.assert_called_once_with(**arguments)


def test_run_array_argument():
    tool = make_tool({"urls": {"type": "array"}}, ["urls"])
    with patch.object(MCPTool, "_run_tool", return_value="page") as run:
        assert tool.run('{"urls": ["https://example.com"]}') == "page"
    run.assert_called_once_with(urls=["https://example.com"])


@pytest.mark.parametrize("text", ["plain query", "123", '"quoted"', "[1, 2]"])
def test_run_preserves_single_string_input(text):
    tool = make_tool({"query": {"type": "string"}}, ["query"])
    with patch.object(MCPTool, "_run_tool", return_value="result") as run:
        assert tool.run(text) == "result"
    run.assert_called_once_with(text)


@pytest.mark.parametrize("text", ["{}", '{"urls": "not an array"}'])
def test_run_validates_before_dispatch(text):
    tool = make_tool({"urls": {"type": "array"}}, ["urls"])
    with patch.object(MCPTool, "_run_tool") as run:
        with pytest.raises(ValidationError):
            tool.run(text)
    run.assert_not_called()


@pytest.mark.parametrize("as_json", [False, True])
@pytest.mark.parametrize("queries", [["MCP setup"], None])
@pytest.mark.parametrize("required", [False, True])
def test_run_nullable_array(as_json, queries, required):
    tool = make_tool(
        {
            "urls": {"type": "array"},
            "search_queries": {
                "anyOf": [{"type": "array"}, {"type": "null"}],
                "default": None,
            },
        },
        ["urls", "search_queries"] if required else ["urls"],
    )
    arguments = {"urls": ["https://example.com"], "search_queries": queries}
    with patch.object(MCPTool, "_run_tool", return_value="page") as run:
        assert tool.run(json.dumps(arguments) if as_json else arguments) == "page"
    run.assert_called_once_with(**arguments)


def test_nullable_array_still_rejects_string():
    tool = make_tool(
        {"queries": {"anyOf": [{"type": "array"}, {"type": "null"}]}},
        [],
    )
    with patch.object(MCPTool, "_run_tool") as run:
        with pytest.raises(ValidationError):
            tool.run({"queries": "not an array"})
    run.assert_not_called()


@pytest.mark.parametrize("required", [False, True])
def test_nullable_array_presence(required):
    tool = make_tool(
        {"queries": {"anyOf": [{"type": "array"}, {"type": "null"}]}},
        ["queries"] if required else [],
    )
    with patch.object(MCPTool, "_run_tool", return_value="result") as run:
        if required:
            with pytest.raises(ValidationError):
                tool.run({})
            run.assert_not_called()
        else:
            assert tool.run({}) == "result"
            run.assert_called_once_with()


def test_discovered_tool_description_includes_input_contract():
    from types import SimpleNamespace

    from kotaemon.agents.tools.mcp import _make_tool

    schema = {
        "type": "object",
        "properties": {
            "objective": {"type": "string", "description": "Information to find"},
            "queries": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["objective", "queries"],
    }
    tool = _make_tool(
        {"transport": "stdio", "command": "example"},
        SimpleNamespace(
            name="search", description="Search the web", inputSchema=schema
        ),
    )
    assert tool.description.startswith("Search the web")
    assert "JSON object" in tool.description
    assert json.dumps(schema) in tool.description
