"""Tests for MCP configuration loading."""

import json
import tempfile
from pathlib import Path

import pytest

from helen.runtime.mcp.config import MCPConfig, MCPServerConfig


class TestMCPConfig:
    """Test MCP configuration loading."""

    def test_load_config_file_not_found(self):
        """Test loading from non-existent file returns empty config."""
        config_path = Path("/nonexistent/.mcp.json")
        config = MCPConfig.from_file(config_path)

        assert len(config.servers) == 0

    def test_load_config_empty_file(self, tmp_path):
        """Test loading empty config file."""
        config_path = tmp_path / ".mcp.json"
        config_path.write_text("{}")

        config = MCPConfig.from_file(config_path)

        assert len(config.servers) == 0

    def test_load_config_single_server(self, tmp_path):
        """Test loading config with single server."""
        config_data = {
            "mcpServers": {
                "test-server": {
                    "command": "node",
                    "args": ["server.js", "--stdio"],
                    "cwd": "/tmp",
                    "tool_timeout_sec": 30,
                }
            }
        }

        config_path = tmp_path / ".mcp.json"
        config_path.write_text(json.dumps(config_data))

        config = MCPConfig.from_file(config_path)

        assert len(config.servers) == 1
        server = config.servers[0]
        assert server.name == "test-server"
        assert server.command == "node"
        assert server.args == ["server.js", "--stdio"]
        assert server.cwd == "/tmp"
        assert server.tool_timeout_sec == 30

    def test_load_config_multiple_servers(self, tmp_path):
        """Test loading config with multiple servers."""
        config_data = {
            "mcpServers": {
                "server1": {
                    "command": "python",
                    "args": ["server1.py"],
                },
                "server2": {
                    "command": "node",
                    "args": ["server2.js"],
                },
            }
        }

        config_path = tmp_path / ".mcp.json"
        config_path.write_text(json.dumps(config_data))

        config = MCPConfig.from_file(config_path)

        assert len(config.servers) == 2
        names = {s.name for s in config.servers}
        assert names == {"server1", "server2"}

    def test_load_config_missing_command(self, tmp_path):
        """Test that servers without 'command' field are skipped."""
        config_data = {
            "mcpServers": {
                "valid-server": {
                    "command": "node",
                    "args": ["server.js"],
                },
                "invalid-server": {
                    "args": ["server.js"],
                    # Missing 'command'
                },
            }
        }

        config_path = tmp_path / ".mcp.json"
        config_path.write_text(json.dumps(config_data))

        config = MCPConfig.from_file(config_path)

        assert len(config.servers) == 1
        assert config.servers[0].name == "valid-server"

    def test_load_config_invalid_json(self, tmp_path):
        """Test that invalid JSON returns empty config."""
        config_path = tmp_path / ".mcp.json"
        config_path.write_text("{invalid json")

        config = MCPConfig.from_file(config_path)

        assert len(config.servers) == 0

    def test_load_config_default_values(self, tmp_path):
        """Test that default values are applied."""
        config_data = {
            "mcpServers": {
                "test-server": {
                    "command": "node",
                }
            }
        }

        config_path = tmp_path / ".mcp.json"
        config_path.write_text(json.dumps(config_data))

        config = MCPConfig.from_file(config_path)

        assert len(config.servers) == 1
        server = config.servers[0]
        assert server.args == []
        assert server.cwd is None
        assert server.env_vars is None
        assert server.tool_timeout_sec == 60  # Default

    def test_load_config_relative_cwd(self, tmp_path):
        """Test that relative cwd is resolved to absolute path."""
        config_data = {
            "mcpServers": {
                "test-server": {
                    "command": "node",
                    "cwd": "./subdir",
                }
            }
        }

        config_path = tmp_path / ".mcp.json"
        config_path.write_text(json.dumps(config_data))

        config = MCPConfig.from_file(config_path)

        assert len(config.servers) == 1
        server = config.servers[0]
        # Should be resolved to absolute path relative to config file
        assert Path(server.cwd).is_absolute()
        assert server.cwd == str(tmp_path / "subdir")
