"""MCP (Model Context Protocol) client implementation.

Implements JSON-RPC 2.0 over stdio communication with MCP servers.
"""

from __future__ import annotations

import json
import logging
import queue
import subprocess
import threading
from dataclasses import dataclass, field
from typing import Any

from .exceptions import MCPError, MCPServerError, MCPTimeoutError, MCPToolError

logger = logging.getLogger(__name__)


@dataclass
class MCPClient:
    """MCP client that communicates with a server via JSON-RPC over stdio.

    The client spawns a subprocess for the MCP server and communicates
    via stdin/stdout using line-delimited JSON-RPC messages.

    Usage:
        client = MCPClient(name="test", command="node", args=["server.js"])
        client.start()
        tools = client.list_tools()
        result = client.call_tool("echo", {"message": "Hello"})
        client.shutdown()

    Attributes:
        name: Server name (for logging)
        command: Command to start the server
        args: Command arguments
        cwd: Working directory
        env: Environment variables
        timeout: Request timeout in seconds
    """

    name: str
    command: str
    args: list[str] = field(default_factory=list)
    cwd: str | None = None
    env: dict[str, str] | None = None
    timeout: int = 60

    # Internal state
    _process: subprocess.Popen | None = field(default=None, repr=False)
    _request_id: int = field(default=0, repr=False)
    _pending_requests: dict[int, queue.Queue] = field(default_factory=dict, repr=False)
    _reader_thread: threading.Thread | None = field(default=None, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    _is_running: bool = field(default=False, repr=False)

    def start(self) -> None:
        """Start the MCP server process and initialize the connection.

        Raises:
            MCPServerError: If server fails to start
        """
        if self._is_running:
            logger.warning("MCP server '%s' is already running", self.name)
            return

        try:
            # Start server process with line-buffered stdio
            self._process = subprocess.Popen(
                [self.command] + self.args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=self.cwd,
                env=self.env,
                text=True,
                bufsize=1,  # Line buffered
            )
        except FileNotFoundError as e:
            raise MCPServerError(
                f"Failed to start MCP server '{self.name}': "
                f"command '{self.command}' not found"
            ) from e
        except Exception as e:
            raise MCPServerError(
                f"Failed to start MCP server '{self.name}': {e}"
            ) from e

        # Start reader thread to handle responses
        self._reader_thread = threading.Thread(
            target=self._read_responses,
            daemon=True,
            name=f"mcp-reader-{self.name}",
        )
        self._reader_thread.start()
        self._is_running = True

        # Send initialize request
        try:
            self._send_request("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "helen",
                    "version": "1.33.0",
                },
            })
            logger.info("Started MCP server '%s'", self.name)
        except Exception as e:
            self.shutdown()
            raise MCPServerError(
                f"Failed to initialize MCP server '{self.name}': {e}"
            ) from e

    def _read_responses(self) -> None:
        """Read JSON-RPC responses from stdout in a background thread.

        This thread continuously reads lines from the server's stdout,
        parses them as JSON-RPC messages, and dispatches responses to
        the appropriate pending request queue.
        """
        try:
            for line in self._process.stdout:
                line = line.strip()
                if not line:
                    continue

                try:
                    message = json.loads(line)
                    msg_id = message.get("id")

                    if msg_id is not None and msg_id in self._pending_requests:
                        # Response to a request
                        self._pending_requests[msg_id].put(message)
                    else:
                        # Notification or unknown message
                        logger.debug("MCP server '%s' sent: %s", self.name, message)
                except json.JSONDecodeError as e:
                    logger.warning(
                        "MCP server '%s' sent invalid JSON: %s (line: %s)",
                        self.name, e, line[:100]
                    )
        except Exception as e:
            if self._is_running:
                logger.error("MCP reader thread for '%s' failed: %s", self.name, e)

    def _send_request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        """Send a JSON-RPC request and wait for response.

        Args:
            method: RPC method name
            params: Method parameters

        Returns:
            Response result

        Raises:
            MCPServerError: If request fails to send
            MCPTimeoutError: If no response within timeout
            MCPServerError: If server returns error
        """
        if not self._is_running or self._process is None:
            raise MCPServerError(f"MCP server '{self.name}' is not running")

        # Generate request ID
        with self._lock:
            self._request_id += 1
            request_id = self._request_id

        # Build request
        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params,
        }

        # Create response queue
        response_queue: queue.Queue = queue.Queue()
        self._pending_requests[request_id] = response_queue

        # Send request
        try:
            request_json = json.dumps(request, ensure_ascii=False) + "\n"
            self._process.stdin.write(request_json)
            self._process.stdin.flush()
        except Exception as e:
            del self._pending_requests[request_id]
            raise MCPServerError(
                f"Failed to send request to MCP server '{self.name}': {e}"
            ) from e

        # Wait for response
        try:
            response = response_queue.get(timeout=self.timeout)
        except queue.Empty:
            del self._pending_requests[request_id]
            raise MCPTimeoutError(
                f"Timeout waiting for response from MCP server '{self.name}'"
            )
        finally:
            if request_id in self._pending_requests:
                del self._pending_requests[request_id]

        # Check for error
        if "error" in response:
            error = response["error"]
            error_msg = error.get("message", "Unknown error")
            error_code = error.get("code", -1)
            raise MCPServerError(
                f"MCP server '{self.name}' error (code {error_code}): {error_msg}"
            )

        return response.get("result", {})

    def list_tools(self) -> list[dict[str, Any]]:
        """List available tools from the MCP server.

        Returns:
            List of tool schemas

        Raises:
            MCPServerError: If request fails
            MCPTimeoutError: If timeout
        """
        result = self._send_request("tools/list", {})
        return result.get("tools", [])

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Call a tool on the MCP server.

        Args:
            name: Tool name
            arguments: Tool arguments

        Returns:
            Tool result

        Raises:
            MCPToolError: If tool call fails
            MCPTimeoutError: If timeout
        """
        try:
            result = self._send_request("tools/call", {
                "name": name,
                "arguments": arguments,
            })
            return result
        except MCPError as e:
            raise MCPToolError(f"Tool '{name}' call failed: {e}") from e
        except Exception as e:
            raise MCPToolError(f"Tool '{name}' call failed: {e}") from e

    def shutdown(self) -> None:
        """Shutdown the MCP server and terminate the process.

        Sends a shutdown request, then terminates the process.
        Falls back to kill() if graceful shutdown fails.
        """
        if not self._is_running:
            return

        self._is_running = False

        # Send shutdown request (best effort)
        if self._process is not None:
            try:
                self._send_request("shutdown", {})
            except Exception as e:
                logger.debug("Shutdown request failed for '%s': %s", self.name, e)

        # Terminate process
        if self._process is not None:
            try:
                self._process.terminate()
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning(
                    "MCP server '%s' did not exit, killing", self.name
                )
                self._process.kill()
                self._process.wait()
            except Exception as e:
                logger.error("Failed to terminate MCP server '%s': %s", self.name, e)

        self._process = None
        self._pending_requests.clear()
        logger.info("Shutdown MCP server '%s'", self.name)
