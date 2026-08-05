"""MCP (Model Context Protocol) client for Helen.

This module provides MCP client support, allowing Helen to discover
and call tools from external MCP servers.

Usage:
    from helen.runtime.mcp import MCPToolRegistry

    registry = MCPToolRegistry()
    registry.initialize(Path(".mcp.json"))

    # Get tool schemas
    tools = registry.get_tool_schemas()

    # Call a tool
    result = registry.dispatch("echo", {"message": "Hello"})

    # Cleanup
    registry.shutdown()
"""

from .client import MCPClient
from .config import MCPConfig, MCPServerConfig
from .exceptions import MCPError, MCPServerError, MCPTimeoutError, MCPToolError
from .registry import MCPToolRegistry
from .server_manager import MCPServerManager

__all__ = [
    # Core classes
    "MCPClient",
    "MCPConfig",
    "MCPServerConfig",
    "MCPServerManager",
    "MCPToolRegistry",
    # Exceptions
    "MCPError",
    "MCPServerError",
    "MCPTimeoutError",
    "MCPToolError",
]
