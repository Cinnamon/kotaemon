"""MCP Tool for kotaemon agents.

Bridges the MCP SDK's tool schema with kotaemon's BaseTool abstraction
so MCP tools can be seamlessly used by ReAct/ReWOO agents.

This module contains:
- MCPTool: BaseTool wrapper for individual MCP server tools
- Tool discovery/creation functions for building MCPTool instances from config
- Config parsing utilities
"""

import asyncio
import json
import logging
import shlex
from typing import Any, Optional, Type

from pydantic import BaseModel, Field, create_model

from .base import BaseTool

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# JSON Schema → Pydantic helpers
# ---------------------------------------------------------------------------


def _json_schema_type_to_python(json_type: str) -> type:
    """Map JSON Schema types to Python types."""
    mapping: dict[str, type] = {
        "string": str,
        "integer": int,
        "number": float,
        "boolean": bool,
        "object": dict,
        "array": list,
    }
    return mapping.get(json_type, str)


def build_args_model(tool_name: str, input_schema: dict) -> Type[BaseModel]:
    """Build a Pydantic model from MCP tool's JSON Schema input_schema."""
    properties = input_schema.get("properties", {})
    required = set(input_schema.get("required", []))
    fields: dict[str, Any] = {}
    for prop_name, prop_info in properties.items():
        python_type = _json_schema_type_to_python(prop_info.get("type", "string"))
        description = prop_info.get("description", "")
        if prop_name in required:
            fields[prop_name] = (python_type, Field(..., description=description))
        else:
            default = prop_info.get("default", None)
            fields[prop_name] = (
                Optional[python_type],
                Field(default=default, description=description),
            )

    model_name = f"MCPArgs_{tool_name}"
    return create_model(model_name, **fields)


# ---------------------------------------------------------------------------
# Config parsing
# ---------------------------------------------------------------------------


def parse_mcp_config(config: dict) -> dict:
    """Parse a JSON config into normalised transport/command/args/env.

    Handles the case where the user puts the full command string
    (e.g. ``"npx -y mcp-remote https://..."`` ) into the command field.

    Returns a dict with keys: transport, command, args, env.
    """
    transport = config.get("transport", "stdio")
    command = config.get("command", "")
    args = config.get("args", [])
    env = config.get("env", {})
    url = config.get("url", "")

    # If stdio and args is empty but command has spaces, split it
    if transport == "stdio" and not args and " " in command:
        parts = shlex.split(command)
        command = parts[0]
        args = parts[1:]

    return {
        "transport": transport,
        "command": command if transport == "stdio" else url,
        "args": args,
        "env": env,
    }


# ---------------------------------------------------------------------------
# Tool discovery & creation
# ---------------------------------------------------------------------------


def _make_tool(parsed: dict, tool_info: Any) -> "MCPTool":
    """Build an MCPTool from MCP tool info."""
    input_schema = tool_info.inputSchema if hasattr(tool_info, "inputSchema") else {}
    args_model = (
        build_args_model(tool_info.name, input_schema) if input_schema else None
    )

    return MCPTool(
        name=tool_info.name,
        description=tool_info.description or f"MCP tool: {tool_info.name}",
        args_schema=args_model,
        server_transport=parsed["transport"],
        server_command=parsed["command"],
        server_args=parsed.get("args", []),
        server_env=parsed.get("env", {}),
        mcp_tool_name=tool_info.name,
    )


async def _async_discover_tools(parsed: dict) -> list["MCPTool"]:
    """Async: connect to an MCP server and return MCPTool wrappers."""
    from mcp import ClientSession
    from mcp.client.sse import sse_client
    from mcp.client.stdio import StdioServerParameters, stdio_client

    tools: list[MCPTool] = []
    transport = parsed["transport"]

    if transport == "stdio":
        server_params = StdioServerParameters(
            command=parsed["command"],
            args=parsed.get("args", []),
            env=parsed.get("env") or None,
        )
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.list_tools()
                for tool_info in result.tools:
                    tools.append(_make_tool(parsed, tool_info))
    elif transport == "sse":
        async with sse_client(url=parsed["command"]) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.list_tools()
                for tool_info in result.tools:
                    tools.append(_make_tool(parsed, tool_info))

    return tools


def _run_async(coro: Any) -> Any:
    """Run an async coroutine from a sync context, handling event loops."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, coro).result()
        else:
            return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


def create_tools_from_config(
    config: dict,
    enabled_tools: Optional[list[str]] = None,
) -> list["MCPTool"]:
    """Create MCPTool instances from an MCP server config dict.

    Args:
        config: MCP server JSON config with keys like transport, command, etc.
        enabled_tools: If provided, only return tools whose names are in this
            list.  If ``None`` or empty, return all discovered tools.

    Returns:
        List of MCPTool instances ready for use by agents.
    """
    parsed = parse_mcp_config(config)
    tools = _run_async(_async_discover_tools(parsed))

    if enabled_tools:
        tools = [t for t in tools if t.mcp_tool_name in enabled_tools]

    return tools


async def async_discover_tools_info(config: dict) -> list[dict]:
    """Connect to an MCP server and return raw tool info dicts.

    Returns a list of dicts with keys: name, description.
    Useful for UI display without instantiating full MCPTool objects.
    """
    from mcp import ClientSession
    from mcp.client.sse import sse_client
    from mcp.client.stdio import StdioServerParameters, stdio_client

    parsed = parse_mcp_config(config)
    transport = parsed["transport"]
    tool_infos: list[dict] = []

    if transport == "stdio":
        server_params = StdioServerParameters(
            command=parsed["command"],
            args=parsed.get("args", []),
            env=parsed.get("env") or None,
        )
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.list_tools()
                for t in result.tools:
                    tool_infos.append(
                        {
                            "name": t.name,
                            "description": t.description or "",
                        }
                    )
    elif transport == "sse":
        async with sse_client(url=parsed["command"]) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.list_tools()
                for t in result.tools:
                    tool_infos.append(
                        {
                            "name": t.name,
                            "description": t.description or "",
                        }
                    )

    return tool_infos


def discover_tools_info(config: dict) -> list[dict]:
    """Sync wrapper around async_discover_tools_info."""
    return _run_async(async_discover_tools_info(config))


def format_tool_list(
    tool_infos: list[dict],
    enabled_tools: Optional[list[str]] = None,
) -> str:
    """Format tool info dicts into a readable HTML string.

    Args:
        tool_infos: List of dicts with 'name' and 'description' keys.
        enabled_tools: If provided, marks which tools are enabled.
    """
    lines = [f"✅ Connected! Found <b>{len(tool_infos)}</b> tool(s):<br>"]
    for t in tool_infos:
        desc = (t.get("description") or "No description")[:120]
        if enabled_tools is not None:
            check = "✅" if t["name"] in enabled_tools else "⬜"
            lines.append(f"&nbsp;&nbsp;{check} <b>{t['name']}</b> — {desc}<br>")
        else:
            lines.append(f"&nbsp;&nbsp;• <b>{t['name']}</b> — {desc}<br>")
    if enabled_tools is not None:
        enabled_count = sum(1 for t in tool_infos if t["name"] in enabled_tools)
        lines.append(
            f"<br><i>{enabled_count}/{len(tool_infos)} tool(s) enabled. "
            'Add <code>"enabled_tools": ["tool_name", ...]</code> '
            "to your config JSON to limit tools.</i>"
        )
    else:
        lines.append(
            "<br><i>All tools enabled. Add "
            '<code>"enabled_tools": ["tool_name", ...]</code> '
            "to your config JSON to limit tools.</i>"
        )
    return "".join(lines)


# ---------------------------------------------------------------------------
# MCPTool class
# ---------------------------------------------------------------------------


class MCPTool(BaseTool):
    """A kotaemon BaseTool wrapper around a single MCP server tool.

    This tool holds the MCP server configuration and establishes
    a connection to invoke the tool on demand.

    Example usage::

        tool = MCPTool(
            name="search",
            description="Search the web",
            server_transport="stdio",
            server_command="uvx",
            server_args=["mcp-server-fetch"],
            mcp_tool_name="fetch",
        )
        result = tool.run("https://example.com")
    """

    name: str = ""
    description: str = ""
    args_schema: Optional[Type[BaseModel]] = None

    # MCP server connection details
    server_transport: str = "stdio"
    server_command: str = ""
    server_args: list[str] = []
    server_env: dict[str, str] = {}

    # The original MCP tool name (on the server)
    mcp_tool_name: str = ""

    def _run_tool(self, *args: Any, **kwargs: Any) -> str:
        """Invoke the MCP tool by establishing a session."""
        return _run_async(self._arun_tool(*args, **kwargs))

    async def _arun_tool(self, *args: Any, **kwargs: Any) -> str:
        """Async implementation that connects to the MCP server and calls
        the tool."""
        from mcp import ClientSession
        from mcp.client.sse import sse_client
        from mcp.client.stdio import StdioServerParameters, stdio_client

        # Build tool arguments
        if args and isinstance(args[0], str):
            try:
                tool_args = json.loads(args[0])
            except json.JSONDecodeError:
                # If not JSON, assume single string argument
                if self.args_schema:
                    first_field = next(iter(self.args_schema.model_fields.keys()))
                    tool_args = {first_field: args[0]}
                else:
                    tool_args = {"input": args[0]}
        else:
            tool_args = kwargs

        if self.server_transport == "stdio":
            cmd = self.server_command
            cmd_args = self.server_args
            # Auto-split if full command string with no separate args
            if not cmd_args and " " in cmd:
                parts = shlex.split(cmd)
                cmd = parts[0]
                cmd_args = parts[1:]

            server_params = StdioServerParameters(
                command=cmd,
                args=cmd_args,
                env=self.server_env if self.server_env else None,
            )
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(self.mcp_tool_name, tool_args)
                    return self._format_result(result)
        elif self.server_transport == "sse":
            async with sse_client(url=self.server_command) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(self.mcp_tool_name, tool_args)
                    return self._format_result(result)
        else:
            return f"Unsupported transport: {self.server_transport}"

    def _format_result(self, result: Any) -> str:
        """Format MCP CallToolResult into a string."""
        if result.isError:
            return f"MCP Tool Error: {result.content}"

        parts = []
        for content in result.content:
            if hasattr(content, "text"):
                parts.append(content.text)
            elif hasattr(content, "data"):
                parts.append(f"[Binary data: {content.mimeType}]")
            else:
                parts.append(str(content))
        return "\n".join(parts)
