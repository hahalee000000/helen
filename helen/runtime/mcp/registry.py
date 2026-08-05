"""MCP (Model Context Protocol) tool registry.

Integrates MCP tools into Helen's tool system.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from .exceptions import MCPError
from .server_manager import MCPServerManager

logger = logging.getLogger(__name__)


class MCPToolRegistry:
    """Integrates MCP tools into Helen's tool system.

    The registry manages the lifecycle of MCP servers and provides
    a unified interface for discovering and calling MCP tools.

    Usage:
        registry = MCPToolRegistry()
        registry.initialize(Path(".mcp.json"))

        # Get tool schemas for LLM
        tools = registry.get_tool_schemas()

        # Dispatch tool call
        result = registry.dispatch("echo", {"message": "Hello"})

        # Cleanup
        registry.shutdown()
    """

    def __init__(self) -> None:
        """Initialize the registry."""
        self._manager = MCPServerManager()
        self._initialized = False

    def initialize(self, config_path: Path) -> None:
        """Initialize MCP servers and register tools.

        Args:
            config_path: Path to .mcp.json file

        Notes:
            - Safe to call multiple times (idempotent)
            - Errors are logged but don't raise (MCP is optional)
            - Only marked as initialized if at least one server starts
        """
        if self._initialized:
            logger.debug("MCP tool registry already initialized")
            return

        try:
            self._manager.load_config(config_path)

            # Check if any servers were loaded
            if not self._manager._clients:
                logger.debug("No MCP servers configured in %s", config_path)
                return

            self._manager.start_all()

            # Only mark as initialized if at least one server is running
            if self._manager._clients:
                self._initialized = True
                logger.info("MCP tool registry initialized")
            else:
                logger.warning("No MCP servers successfully started")
        except Exception as e:
            logger.error("Failed to initialize MCP tool registry: %s", e)
            # Don't raise — MCP is optional

    def get_tool_schemas(self) -> list[dict[str, Any]]:
        """Get OpenAI-format tool schemas for all MCP tools.

        Returns:
            List of tool schemas in OpenAI function calling format
        """
        if not self._initialized:
            return []

        return self._manager.get_all_tools()

    def dispatch(self, tool_name: str, arguments: dict[str, Any]) -> str:
        """Dispatch a tool call to the appropriate MCP server.

        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments

        Returns:
            JSON string with tool result (compatible with Helen's tool system)
        """
        if not self._initialized:
            return json.dumps(
                {"error": f"MCP tool '{tool_name}' not available (registry not initialized)"},
                ensure_ascii=False,
            )

        try:
            result = self._manager.call_tool(tool_name, arguments)
            return json.dumps(result, ensure_ascii=False)
        except MCPError as e:
            logger.error("MCP tool '%s' call failed: %s", tool_name, e)
            return json.dumps({"error": str(e)}, ensure_ascii=False)
        except Exception as e:
            logger.error("MCP tool '%s' unexpected error: %s", tool_name, e)
            return json.dumps(
                {"error": f"MCP tool '{tool_name}' failed: {e}"},
                ensure_ascii=False,
            )

    def shutdown(self) -> None:
        """Shutdown all MCP servers.

        Notes:
            - Safe to call multiple times
            - Errors are logged but don't raise
        """
        if not self._initialized:
            return

        try:
            self._manager.shutdown_all()
            self._initialized = False
            logger.info("MCP tool registry shutdown")
        except Exception as e:
            logger.error("Failed to shutdown MCP tool registry: %s", e)
