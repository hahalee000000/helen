"""MCP (Model Context Protocol) server manager.

Manages multiple MCP server instances and their tools.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from .client import MCPClient
from .config import MCPConfig
from .exceptions import MCPError, MCPServerError

logger = logging.getLogger(__name__)


class MCPServerManager:
    """Manages multiple MCP server instances.

    The manager is responsible for:
    - Loading configuration from .mcp.json
    - Starting and stopping MCP servers
    - Discovering tools from all servers
    - Routing tool calls to the appropriate server

    Usage:
        manager = MCPServerManager()
        manager.load_config(Path(".mcp.json"))
        manager.start_all()

        # Get all MCP tools
        tools = manager.get_all_tools()

        # Call a tool
        result = manager.call_tool("echo", {"message": "Hello"})

        # Cleanup
        manager.shutdown_all()
    """

    def __init__(self) -> None:
        """Initialize the server manager."""
        self._clients: dict[str, MCPClient] = {}
        self._tool_mapping: dict[str, str] = {}  # tool_name -> server_name

    def load_config(self, config_path: Path) -> None:
        """Load MCP configuration from .mcp.json file.

        Args:
            config_path: Path to .mcp.json file
        """
        config = MCPConfig.from_file(config_path)

        for server_config in config.servers:
            client = MCPClient(
                name=server_config.name,
                command=server_config.command,
                args=server_config.args,
                cwd=server_config.cwd,
                env=server_config.env_vars,
                timeout=server_config.tool_timeout_sec,
            )
            self._clients[server_config.name] = client

        logger.info(
            "Loaded configuration for %d MCP server(s)", len(self._clients)
        )

    def start_all(self) -> None:
        """Start all MCP servers and discover their tools.

        Servers that fail to start are logged and skipped.
        Tool name conflicts are logged as warnings (first server wins).
        """
        for name, client in self._clients.items():
            try:
                client.start()

                # Discover tools
                tools = client.list_tools()
                for tool in tools:
                    tool_name = tool["name"]
                    if tool_name in self._tool_mapping:
                        logger.warning(
                            "MCP tool '%s' from server '%s' conflicts with "
                            "server '%s' (first server wins)",
                            tool_name,
                            name,
                            self._tool_mapping[tool_name],
                        )
                    else:
                        self._tool_mapping[tool_name] = name
                        logger.info(
                            "Discovered MCP tool '%s' from server '%s'",
                            tool_name,
                            name,
                        )

            except MCPError as e:
                logger.error("Failed to start MCP server '%s': %s", name, e)
                # Continue with other servers

    def get_all_tools(self) -> list[dict[str, Any]]:
        """Get OpenAI-format tool schemas for all MCP tools.

        Returns:
            List of tool schemas in OpenAI function calling format
        """
        tools = []

        for server_name, client in self._clients.items():
            try:
                mcp_tools = client.list_tools()
                for tool in mcp_tools:
                    # Convert MCP tool schema to OpenAI format
                    openai_tool = {
                        "type": "function",
                        "function": {
                            "name": tool["name"],
                            "description": tool.get("description", ""),
                            "parameters": tool.get("inputSchema", {}),
                        },
                    }
                    tools.append(openai_tool)
            except MCPError as e:
                logger.error(
                    "Failed to list tools from MCP server '%s': %s",
                    server_name,
                    e,
                )

        return tools

    def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Call an MCP tool by name.

        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments

        Returns:
            Tool result

        Raises:
            MCPError: If tool not found or call fails
        """
        server_name = self._tool_mapping.get(tool_name)
        if server_name is None:
            raise MCPError(f"Unknown MCP tool: {tool_name}")

        client = self._clients.get(server_name)
        if client is None:
            raise MCPError(f"MCP server '{server_name}' not found")

        return client.call_tool(tool_name, arguments)

    def shutdown_all(self) -> None:
        """Shutdown all MCP servers.

        Best-effort shutdown; errors are logged but don't prevent
        other servers from being shut down.
        """
        for name, client in self._clients.items():
            try:
                client.shutdown()
            except Exception as e:
                logger.error("Failed to shutdown MCP server '%s': %s", name, e)

        self._clients.clear()
        self._tool_mapping.clear()
        logger.info("All MCP servers shut down")
