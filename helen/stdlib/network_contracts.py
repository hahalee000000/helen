"""Network module contracts for Helen stdlib.

This module defines the interface for HTTP operations.
"""

from typing import Any


class NetworkContract:
    """Contract for network operations."""
    
    @staticmethod
    def http_get(url: str, headers: dict[str, str] | None = None) -> dict[str, Any]:
        """Send an HTTP GET request.
        
        Args:
            url: The URL to request
            headers: Optional HTTP headers
            
        Returns:
            Dict with keys:
                - status: int (HTTP status code)
                - headers: dict (response headers)
                - body: str (response body)
                
        Raises:
            RuntimeError: If request fails
        """
        ...
    
    @staticmethod
    def http_post(url: str, data: str | dict | None = None, 
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
        ...
    
    @staticmethod
    def http_put(url: str, data: str | dict | None = None,
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
        ...
    
    @staticmethod
    def http_delete(url: str, headers: dict[str, str] | None = None) -> dict[str, Any]:
        """Send an HTTP DELETE request.
        
        Args:
            url: The URL to request
            headers: Optional HTTP headers
            
        Returns:
            Dict with keys: status, headers, body
            
        Raises:
            RuntimeError: If request fails
        """
        ...
    
    @staticmethod
    def http_download(url: str, path: str) -> str:
        """Download a file from URL to local path.
        
        Args:
            url: The URL to download from
            path: Local file path to save to
            
        Returns:
            The path where file was saved
            
        Raises:
            RuntimeError: If download fails
        """
        ...
