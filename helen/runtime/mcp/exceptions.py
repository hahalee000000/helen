"""MCP (Model Context Protocol) client exceptions.

Defines exception hierarchy for MCP-related errors.
"""


class MCPError(Exception):
    """Base exception for MCP-related errors."""

    pass


class MCPServerError(MCPError):
    """Error starting or communicating with MCP server.

    Raised when:
    - Server process fails to start
    - Communication with server fails
    - Server returns an error response
    """

    pass


class MCPToolError(MCPError):
    """Error calling an MCP tool.

    Raised when:
    - Tool not found on server
    - Tool execution fails
    - Tool returns an error result
    """

    pass


class MCPTimeoutError(MCPError):
    """Timeout waiting for MCP server response.

    Raised when:
    - Server does not respond within timeout period
    - Connection hangs
    """

    pass
