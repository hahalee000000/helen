"""MCP (Model Context Protocol) configuration loader.

Loads MCP server configuration from .mcp.json files.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class MCPServerConfig:
    """Configuration for a single MCP server.

    Attributes:
        name: Server name (from .mcp.json key)
        command: Command to start the server (e.g., "node", "python")
        args: Command arguments (e.g., ["server.js", "--stdio"])
        cwd: Working directory for the server process
        env_vars: Environment variables to pass to the server
        tool_timeout_sec: Timeout for tool calls in seconds
    """

    name: str
    command: str
    args: list[str] = field(default_factory=list)
    cwd: str | None = None
    env_vars: dict[str, str] | None = None
    tool_timeout_sec: int = 60


@dataclass
class MCPConfig:
    """Configuration for all MCP servers in a project.

    Attributes:
        servers: List of MCP server configurations
    """

    servers: list[MCPServerConfig] = field(default_factory=list)

    @classmethod
    def from_file(cls, path: Path) -> "MCPConfig":
        """Load MCP configuration from .mcp.json file.

        Args:
            path: Path to .mcp.json file

        Returns:
            MCPConfig instance with loaded servers

        Notes:
            - Returns empty config if file doesn't exist (no error)
            - Logs warning if JSON parsing fails
            - Skips servers without required 'command' field
        """
        if not path.exists():
            logger.debug("MCP config file not found: %s", path)
            return cls(servers=[])

        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            logger.warning("Failed to parse .mcp.json at %s: %s", path, e)
            return cls(servers=[])
        except OSError as e:
            logger.warning("Failed to read .mcp.json at %s: %s", path, e)
            return cls(servers=[])

        servers = []
        mcp_servers = data.get("mcpServers", {})

        for name, config in mcp_servers.items():
            # Validate required fields
            if not isinstance(config, dict):
                logger.warning("MCP server '%s' config is not a dict, skipping", name)
                continue

            if "command" not in config:
                logger.warning("MCP server '%s' missing 'command' field, skipping", name)
                continue

            # Extract configuration
            command = config["command"]
            args = config.get("args", [])
            cwd = config.get("cwd")
            env_vars = config.get("env_vars")
            tool_timeout_sec = config.get("tool_timeout_sec", 60)

            # Validate types
            if not isinstance(command, str):
                logger.warning("MCP server '%s' 'command' must be a string, skipping", name)
                continue

            if not isinstance(args, list):
                logger.warning("MCP server '%s' 'args' must be a list, skipping", name)
                continue

            if cwd is not None and not isinstance(cwd, str):
                logger.warning("MCP server '%s' 'cwd' must be a string, skipping", name)
                continue

            if env_vars is not None and not isinstance(env_vars, dict):
                logger.warning("MCP server '%s' 'env_vars' must be a dict, skipping", name)
                continue

            # Resolve cwd relative to config file directory
            if cwd is not None:
                cwd_path = Path(cwd)
                if not cwd_path.is_absolute():
                    # Relative to config file directory
                    cwd = str(path.parent / cwd_path)

            servers.append(
                MCPServerConfig(
                    name=name,
                    command=command,
                    args=args,
                    cwd=cwd,
                    env_vars=env_vars,
                    tool_timeout_sec=tool_timeout_sec,
                )
            )

        logger.info("Loaded %d MCP server(s) from %s", len(servers), path)
        return cls(servers=servers)
