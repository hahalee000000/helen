"""Tests for Network stdlib module."""

import pytest
from unittest.mock import patch, Mock
import json


class TestHttpGet:
    """Tests for http_get function."""
    
    def test_http_get_exists(self):
        """Test that http_get function exists in stdlib."""
        from helen.stdlib import stdlib
        assert stdlib.lookup("http_get") is not None
    
    def test_http_get_simple(self):
        """Test simple GET request."""
        from helen.stdlib import stdlib
        http_get = stdlib.lookup("http_get").fn
        
        # Mock urllib.request.urlopen
        mock_response = Mock()
        mock_response.status = 200
        mock_response.headers = {"Content-Type": "text/plain"}
        mock_response.read.return_value = b"Hello, World!"
        
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value.__enter__ = Mock(return_value=mock_response)
            mock_urlopen.return_value.__exit__ = Mock(return_value=False)
            
            result = http_get("https://example.com")
            
            assert result["status"] == 200
            assert result["body"] == "Hello, World!"
            assert "headers" in result
    
    def test_http_get_with_headers(self):
        """Test GET request with custom headers."""
        from helen.stdlib import stdlib
        http_get = stdlib.lookup("http_get").fn
        
        mock_response = Mock()
        mock_response.status = 200
        mock_response.headers = {}
        mock_response.read.return_value = b"OK"
        
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value.__enter__ = Mock(return_value=mock_response)
            mock_urlopen.return_value.__exit__ = Mock(return_value=False)
            
            result = http_get("https://example.com", {"Authorization": "Bearer token"})
            
            # Verify the request was made
            assert mock_urlopen.called
            request = mock_urlopen.call_args[0][0]
            assert request.get_header("Authorization") == "Bearer token"
    
    def test_http_get_error_handling(self):
        """Test GET request error handling."""
        from helen.stdlib import stdlib
        http_get = stdlib.lookup("http_get").fn
        
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = Exception("Network error")
            
            with pytest.raises(Exception):
                http_get("https://invalid.example.com")


class TestHttpPost:
    """Tests for http_post function."""
    
    def test_http_post_exists(self):
        """Test that http_post function exists."""
        from helen.stdlib import stdlib
        assert stdlib.lookup("http_post") is not None
    
    def test_http_post_with_string_data(self):
        """Test POST request with string data."""
        from helen.stdlib import stdlib
        http_post = stdlib.lookup("http_post").fn
        
        mock_response = Mock()
        mock_response.status = 201
        mock_response.headers = {}
        mock_response.read.return_value = b"Created"
        
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value.__enter__ = Mock(return_value=mock_response)
            mock_urlopen.return_value.__exit__ = Mock(return_value=False)
            
            result = http_post("https://example.com/api", "data=value")
            
            assert result["status"] == 201
            assert result["body"] == "Created"
    
    def test_http_post_with_dict_data(self):
        """Test POST request with dict data (auto JSON encode)."""
        from helen.stdlib import stdlib
        http_post = stdlib.lookup("http_post").fn
        
        mock_response = Mock()
        mock_response.status = 200
        mock_response.headers = {}
        mock_response.read.return_value = b'{"success": true}'
        
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value.__enter__ = Mock(return_value=mock_response)
            mock_urlopen.return_value.__exit__ = Mock(return_value=False)
            
            result = http_post("https://example.com/api", {"key": "value"})
            
            # Verify JSON encoding
            request = mock_urlopen.call_args[0][0]
            assert request.data == b'{"key": "value"}'
            assert request.get_header("Content-type") == "application/json"


class TestHttpPut:
    """Tests for http_put function."""
    
    def test_http_put_exists(self):
        """Test that http_put function exists."""
        from helen.stdlib import stdlib
        assert stdlib.lookup("http_put") is not None


class TestHttpDelete:
    """Tests for http_delete function."""
    
    def test_http_delete_exists(self):
        """Test that http_delete function exists."""
        from helen.stdlib import stdlib
        assert stdlib.lookup("http_delete") is not None


class TestHttpDownload:
    """Tests for http_download function."""
    
    def test_http_download_exists(self):
        """Test that http_download function exists."""
        from helen.stdlib import stdlib
        assert stdlib.lookup("http_download") is not None
    
    def test_http_download_file(self):
        """Test downloading a file."""
        from helen.stdlib import stdlib
        http_download = stdlib.lookup("http_download").fn
        
        mock_response = Mock()
        mock_response.read.return_value = b"File content"
        
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value.__enter__ = Mock(return_value=mock_response)
            mock_urlopen.return_value.__exit__ = Mock(return_value=False)
            
            with patch("builtins.open", create=True) as mock_open:
                result = http_download("https://example.com/file.txt", "/tmp/test.txt")
                
                assert result == "/tmp/test.txt"
                mock_open.assert_called_once()


class TestUrlOperations:
    """Tests for URL operations."""
    
    def test_url_parse_exists(self):
        """Test that url_parse function exists."""
        from helen.stdlib import stdlib
        assert stdlib.lookup("url_parse") is not None
    
    def test_url_parse_simple(self):
        """Test parsing a simple URL."""
        from helen.stdlib import stdlib
        url_parse = stdlib.lookup("url_parse").fn
        
        result = url_parse("https://example.com:8080/path?query=value#fragment")
        
        assert result["scheme"] == "https"
        assert result["host"] == "example.com"
        assert result["port"] == 8080
        assert result["path"] == "/path"
        assert result["query"] == "query=value"
        assert result["fragment"] == "fragment"
    
    def test_url_build_exists(self):
        """Test that url_build function exists."""
        from helen.stdlib import stdlib
        assert stdlib.lookup("url_build") is not None
    
    def test_url_build_simple(self):
        """Test building a URL."""
        from helen.stdlib import stdlib
        url_build = stdlib.lookup("url_build").fn
        
        result = url_build("https", "example.com", "/path", "query=value")
        
        assert result == "https://example.com/path?query=value"
