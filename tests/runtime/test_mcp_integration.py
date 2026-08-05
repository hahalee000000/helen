"""Integration tests for MCP client and registry."""

import json
import sys
import tempfile
from pathlib import Path

import pytest

from helen.runtime.mcp import (
    MCPClient,
    MCPToolRegistry,
    MCPServerError,
    MCPToolError,
)


# Path to mock server
MOCK_SERVER_PATH = Path(__file__).parent / "mock_mcp_server.py"


class TestMCPClient:
    """Test MCP client communication."""

    def test_start_and_shutdown(self):
        """Test starting and shutting down a mock MCP server."""
        client = MCPClient(
            name="test",
            command=sys.executable,
            args=[str(MOCK_SERVER_PATH)],
        )

        try:
            client.start()
            assert client._is_running
        finally:
            client.shutdown()
            assert not client._is_running

    def test_list_tools(self):
        """Test listing tools from mock server."""
        client = MCPClient(
            name="test",
            command=sys.executable,
            args=[str(MOCK_SERVER_PATH)],
        )

        try:
            client.start()
            tools = client.list_tools()

            assert len(tools) == 2
            tool_names = {t["name"] for t in tools}
            assert tool_names == {"echo", "add"}
        finally:
            client.shutdown()

    def test_call_tool_echo(self):
        """Test calling echo tool."""
        client = MCPClient(
            name="test",
            command=sys.executable,
            args=[str(MOCK_SERVER_PATH)],
        )

        try:
            client.start()
            result = client.call_tool("echo", {"message": "Hello, MCP!"})

            assert "output" in result
            assert result["output"] == "Echo: Hello, MCP!"
        finally:
            client.shutdown()

    def test_call_tool_add(self):
        """Test calling add tool."""
        client = MCPClient(
            name="test",
            command=sys.executable,
            args=[str(MOCK_SERVER_PATH)],
        )

        try:
            client.start()
            result = client.call_tool("add", {"a": 5, "b": 3})

            assert "result" in result
            assert result["result"] == 8
        finally:
            client.shutdown()

    def test_call_unknown_tool(self):
        """Test calling unknown tool returns error in result."""
        client = MCPClient(
            name="test",
            command=sys.executable,
            args=[str(MOCK_SERVER_PATH)],
        )

        try:
            client.start()
            # Mock server returns error in result, not as JSON-RPC error
            result = client.call_tool("unknown_tool", {})
            assert "error" in result
        finally:
            client.shutdown()

    def test_invalid_command(self):
        """Test that invalid command raises error."""
        client = MCPClient(
            name="test",
            command="nonexistent_command_xyz",
            args=[],
        )

        with pytest.raises(MCPServerError):
            client.start()


class TestMCPToolRegistry:
    """Test MCP tool registry integration."""

    def test_initialize_and_get_tools(self, tmp_path):
        """Test initializing registry and getting tool schemas."""
        # Create .mcp.json
        config_data = {
            "mcpServers": {
                "mock": {
                    "command": sys.executable,
                    "args": [str(MOCK_SERVER_PATH)],
                }
            }
        }
        config_path = tmp_path / ".mcp.json"
        config_path.write_text(json.dumps(config_data))

        registry = MCPToolRegistry()

        try:
            registry.initialize(config_path)
            assert registry._initialized

            tools = registry.get_tool_schemas()
            assert len(tools) == 2

            tool_names = {t["function"]["name"] for t in tools}
            assert tool_names == {"echo", "add"}
        finally:
            registry.shutdown()

    def test_dispatch_tool(self, tmp_path):
        """Test dispatching tool calls through registry."""
        # Create .mcp.json
        config_data = {
            "mcpServers": {
                "mock": {
                    "command": sys.executable,
                    "args": [str(MOCK_SERVER_PATH)],
                }
            }
        }
        config_path = tmp_path / ".mcp.json"
        config_path.write_text(json.dumps(config_data))

        registry = MCPToolRegistry()

        try:
            registry.initialize(config_path)

            # Call echo tool
            result_json = registry.dispatch("echo", {"message": "Test"})
            result = json.loads(result_json)

            assert "output" in result
            assert result["output"] == "Echo: Test"
        finally:
            registry.shutdown()

    def test_dispatch_unknown_tool(self, tmp_path):
        """Test dispatching unknown tool returns error."""
        # Create .mcp.json
        config_data = {
            "mcpServers": {
                "mock": {
                    "command": sys.executable,
                    "args": [str(MOCK_SERVER_PATH)],
                }
            }
        }
        config_path = tmp_path / ".mcp.json"
        config_path.write_text(json.dumps(config_data))

        registry = MCPToolRegistry()

        try:
            registry.initialize(config_path)

            result_json = registry.dispatch("unknown_tool", {})
            result = json.loads(result_json)

            assert "error" in result
        finally:
            registry.shutdown()

    def test_initialize_without_config(self, tmp_path):
        """Test that initializing without config file is safe."""
        config_path = tmp_path / ".mcp.json"
        # Don't create the file

        registry = MCPToolRegistry()
        registry.initialize(config_path)

        # Should not crash, but not initialized
        assert not registry._initialized

        tools = registry.get_tool_schemas()
        assert len(tools) == 0


class TestMCPIntegration:
    """Test end-to-end MCP integration with tools.py."""

    def test_tools_py_integration(self, tmp_path, monkeypatch):
        """Test that MCP tools are accessible via tools.py."""
        from helen.runtime import tools

        # Create .mcp.json
        config_data = {
            "mcpServers": {
                "mock": {
                    "command": sys.executable,
                    "args": [str(MOCK_SERVER_PATH)],
                }
            }
        }
        config_path = tmp_path / ".mcp.json"
        config_path.write_text(json.dumps(config_data))

        # Change to tmp directory
        monkeypatch.chdir(tmp_path)

        # Reset MCP registry
        tools._mcp_registry = None

        try:
            # Get tool schemas (should auto-initialize MCP)
            schemas = tools.get_tool_schemas()

            # Should include built-in tools + MCP tools
            tool_names = {s["function"]["name"] for s in schemas}
            assert "echo" in tool_names
            assert "add" in tool_names
            assert "web_search" in tool_names  # Built-in

            # Dispatch MCP tool
            result_json = tools.dispatch_tool("echo", {"message": "Integration test"})
            result = json.loads(result_json)

            assert result["output"] == "Echo: Integration test"

        finally:
            # Cleanup
            tools.shutdown_mcp()
            tools._mcp_registry = None
