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
