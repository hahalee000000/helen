"""Network module for Helen stdlib.

Provides HTTP operations for web requests.
"""

from __future__ import annotations

import json
import urllib.request
import urllib.error
import urllib.parse
from typing import Any


def _http_get(url: str, headers: dict[str, str] | None = None) -> dict[str, Any]:
    """Send an HTTP GET request.

    Args:
        url: The URL to request
        headers: Optional HTTP headers

    Returns:
        Dict with keys: status, headers, body

    Raises:
        RuntimeError: If request fails
    """
    return _http_request("GET", url, headers=headers)


def _http_post(url: str, data: str | dict | None = None,
               headers: dict[str, str] | None = None) -> dict[str, Any]:
    """Send an HTTP POST request.

    Args:
        url: The URL to request
        data: Request body (string or dict for JSON)
        headers: Optional HTTP headers

    Returns:
        Dict with keys: status, headers, body

    Raises:
        RuntimeError: If request fails
    """
    return _http_request("POST", url, data=data, headers=headers)


def _http_put(url: str, data: str | dict | None = None,
              headers: dict[str, str] | None = None) -> dict[str, Any]:
    """Send an HTTP PUT request.

    Args:
        url: The URL to request
        data: Request body (string or dict for JSON)
        headers: Optional HTTP headers

    Returns:
        Dict with keys: status, headers, body

    Raises:
        RuntimeError: If request fails
    """
    return _http_request("PUT", url, data=data, headers=headers)


def _http_delete(url: str, headers: dict[str, str] | None = None) -> dict[str, Any]:
    """Send an HTTP DELETE request.

    Args:
        url: The URL to request
        headers: Optional HTTP headers

    Returns:
        Dict with keys: status, headers, body

    Raises:
        RuntimeError: If request fails
    """
    return _http_request("DELETE", url, headers=headers)


def _http_request(method: str, url: str, data: str | dict | None = None,
                  headers: dict[str, str] | None = None,
                  timeout: int = 30) -> dict[str, Any]:
    """Internal HTTP request implementation.

    Args:
        method: HTTP method (GET, POST, PUT, DELETE)
        url: The URL to request
        data: Request body
        headers: HTTP headers
        timeout: Request timeout in seconds

    Returns:
        Dict with status, headers, body

    Raises:
        RuntimeError: If request fails
    """
    # Prepare request data
    request_data = None
    if data is not None:
        if isinstance(data, dict):
            request_data = json.dumps(data).encode("utf-8")
            if headers is None:
                headers = {}
            headers["Content-type"] = "application/json"
        else:
            request_data = data.encode("utf-8")

    # Create request
    req = urllib.request.Request(url, data=request_data, method=method)

    # Add headers
    if headers:
        for key, value in headers.items():
            req.add_header(key, value)

    # Default User-Agent
    if not any(h.lower() == "user-agent" for h in (headers or {}).keys()):
        req.add_header("User-Agent", "Helen/1.0")

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            # Read response
            body = response.read().decode("utf-8")

            # Extract headers
            response_headers = {}
            for key, value in response.headers.items():
                response_headers[key] = value

            return {
                "status": response.status,
                "headers": response_headers,
                "body": body,
            }

    except urllib.error.HTTPError as e:
        # HTTP error (4xx, 5xx)
        body = e.read().decode("utf-8") if e.fp else ""
        return {
            "status": e.code,
            "headers": dict(e.headers) if e.headers else {},
            "body": body,
        }

    except urllib.error.URLError as e:
        raise RuntimeError(f"URL error: {e.reason}") from e

    except TimeoutError as e:
        raise RuntimeError(f"Request timed out after {timeout}s") from e

    except Exception as e:
        raise RuntimeError(f"HTTP request failed: {e}") from e


def _http_download(url: str, path: str) -> str:
    """Download a file from URL to local path.

    Args:
        url: The URL to download from
        path: Local file path to save to

    Returns:
        The path where file was saved

    Raises:
        RuntimeError: If download fails
    """
    try:
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "Helen/1.0")

        with urllib.request.urlopen(req, timeout=60) as response:
            with open(path, "wb") as f:
                while True:
                    chunk = response.read(8192)
                    if not chunk:
                        break
                    f.write(chunk)

        return path

    except RuntimeError:
        raise
    except Exception as e:
        raise RuntimeError(f"Download failed: {e}") from e


def _url_parse(url: str) -> dict[str, Any]:
    """Parse a URL into components.

    Args:
        url: The URL to parse

    Returns:
        Dict with keys: scheme, host, port, path, query, fragment
    """
    parsed = urllib.parse.urlparse(url)

    # Extract port from netloc
    host = parsed.hostname or ""
    port = parsed.port

    return {
        "scheme": parsed.scheme,
        "host": host,
        "port": port,
        "path": parsed.path,
        "query": parsed.query,
        "fragment": parsed.fragment,
    }


def _url_build(scheme: str, host: str, path: str = "",
               query: str = "") -> str:
    """Build a URL from components.

    Args:
        scheme: URL scheme (http, https)
        host: Hostname
        path: URL path
        query: Query string

    Returns:
        The constructed URL
    """
    url = f"{scheme}://{host}"

    if path:
        if not path.startswith("/"):
            path = "/" + path
        url += path

    if query:
        url += "?" + query

    return url


def _url_encode(s: str) -> str:
    """URL-encode a string.

    Args:
        s: String to encode

    Returns:
        URL-encoded string
    """
    return urllib.parse.quote(s, safe="")


def _url_decode(s: str) -> str:
    """URL-decode a string.

    Args:
        s: URL-encoded string

    Returns:
        Decoded string
    """
    return urllib.parse.unquote(s)
