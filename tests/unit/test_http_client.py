"""Unit tests for HTTP client module."""

import pytest
from unittest.mock import MagicMock


class TestHTTPResponse:
    """Tests for HTTPResponse dataclass."""

    def test_init(self):
        """Test HTTPResponse initialization."""
        from wh.http.client import HTTPResponse

        response = HTTPResponse(
            status_code=200,
            reason="OK",
            headers={"Content-Type": "application/json"},
            body=b'{"key": "value"}',
        )

        assert response.status_code == 200
        assert response.reason == "OK"
        assert response.headers == {"Content-Type": "application/json"}
        assert response.body == b'{"key": "value"}'


class TestWormholeHTTPClient:
    """Tests for WormholeHTTPClient class."""

    def test_init(self):
        """Test client initialization."""
        from wh.http.client import WormholeHTTPClient

        manager = MagicMock()
        client = WormholeHTTPClient(manager)

        assert client.manager is manager
        assert client._protocol is None

    @pytest.mark.asyncio
    async def test_request_not_dilated(self):
        """Test request raises when not dilated."""
        from wh.http.client import WormholeHTTPClient

        manager = MagicMock()
        manager.is_dilated = False

        client = WormholeHTTPClient(manager)

        with pytest.raises(RuntimeError, match="must be dilated"):
            await client.request("GET", "http://example.com")

    def test_parse_response_json_only(self):
        """Test parsing response with JSON only (no body)."""
        from wh.http.client import WormholeHTTPClient

        manager = MagicMock()
        client = WormholeHTTPClient(manager)

        data = b'{"status_code": 200, "reason": "OK", "headers": {}}'
        result = client._parse_response(data)

        assert result["status_code"] == 200
        assert result["reason"] == "OK"
        assert result["body"] == b""

    def test_parse_response_with_body(self):
        """Test parsing response with JSON and body."""
        from wh.http.client import WormholeHTTPClient

        manager = MagicMock()
        client = WormholeHTTPClient(manager)

        data = b'{"status_code": 200, "reason": "OK", "headers": {}}\nBody content here'
        result = client._parse_response(data)

        assert result["status_code"] == 200
        assert result["body"] == b"Body content here"


class TestHTTPProxyHandler:
    """Tests for HTTPProxyHandler class."""

    def test_init(self):
        """Test handler initialization."""
        from wh.http.client import HTTPProxyHandler

        manager = MagicMock()
        handler = HTTPProxyHandler(manager)

        assert handler.manager is manager


class TestHTTPResponseAdditional:
    """Additional tests for HTTPResponse."""

    def test_response_404(self):
        """Test 404 response."""
        from wh.http.client import HTTPResponse

        response = HTTPResponse(
            status_code=404,
            reason="Not Found",
            headers={},
            body=b"Resource not found",
        )

        assert response.status_code == 404
        assert response.reason == "Not Found"

    def test_response_with_multiple_headers(self):
        """Test response with multiple headers."""
        from wh.http.client import HTTPResponse

        response = HTTPResponse(
            status_code=200,
            reason="OK",
            headers={
                "Content-Type": "text/html",
                "Content-Length": "1234",
                "X-Custom-Header": "value",
            },
            body=b"<html></html>",
        )

        assert len(response.headers) == 3
        assert response.headers["Content-Length"] == "1234"


class TestWormholeHTTPClientAdditional:
    """Additional tests for WormholeHTTPClient."""

    def test_parse_response_binary_body(self):
        """Test parsing response with binary body."""
        from wh.http.client import WormholeHTTPClient

        manager = MagicMock()
        client = WormholeHTTPClient(manager)

        # Binary body (like an image)
        data = b'{"status_code": 200, "reason": "OK", "headers": {}}\n' + bytes(
            [0x89, 0x50, 0x4E, 0x47]
        )
        result = client._parse_response(data)

        assert result["body"] == bytes([0x89, 0x50, 0x4E, 0x47])

    def test_parse_response_multiline_body(self):
        """Test parsing response with multiline body."""
        from wh.http.client import WormholeHTTPClient

        manager = MagicMock()
        client = WormholeHTTPClient(manager)

        data = b'{"status_code": 200, "reason": "OK", "headers": {}}\nLine 1\nLine 2\nLine 3'
        result = client._parse_response(data)

        assert result["body"] == b"Line 1\nLine 2\nLine 3"


class TestHTTPResponseEmpty:
    """Tests for empty or minimal responses."""

    def test_response_no_content(self):
        """Test 204 No Content response."""
        from wh.http.client import HTTPResponse

        response = HTTPResponse(
            status_code=204,
            reason="No Content",
            headers={},
            body=b"",
        )

        assert response.status_code == 204
        assert response.body == b""

    def test_response_redirect(self):
        """Test redirect response."""
        from wh.http.client import HTTPResponse

        response = HTTPResponse(
            status_code=302,
            reason="Found",
            headers={"Location": "http://new-url.com"},
            body=b"",
        )

        assert response.status_code == 302
        assert response.headers["Location"] == "http://new-url.com"


class TestHTTPResponseErrors:
    """Tests for error responses."""

    def test_response_server_error(self):
        """Test 500 Internal Server Error."""
        from wh.http.client import HTTPResponse

        response = HTTPResponse(
            status_code=500,
            reason="Internal Server Error",
            headers={},
            body=b"Server error occurred",
        )

        assert response.status_code == 500
        assert response.reason == "Internal Server Error"

    def test_response_bad_request(self):
        """Test 400 Bad Request."""
        from wh.http.client import HTTPResponse

        response = HTTPResponse(
            status_code=400,
            reason="Bad Request",
            headers={"Content-Type": "application/json"},
            body=b'{"error": "Invalid input"}',
        )

        assert response.status_code == 400

    def test_response_unauthorized(self):
        """Test 401 Unauthorized."""
        from wh.http.client import HTTPResponse

        response = HTTPResponse(
            status_code=401,
            reason="Unauthorized",
            headers={"WWW-Authenticate": "Bearer"},
            body=b"",
        )

        assert response.status_code == 401

    def test_response_forbidden(self):
        """Test 403 Forbidden."""
        from wh.http.client import HTTPResponse

        response = HTTPResponse(
            status_code=403,
            reason="Forbidden",
            headers={},
            body=b"Access denied",
        )

        assert response.status_code == 403


class TestHTTPProxyHandlerMethods:
    """Tests for HTTPProxyHandler methods."""

    def test_handler_manager_property(self):
        """Test handler has manager property."""
        from wh.http.client import HTTPProxyHandler

        manager = MagicMock()
        handler = HTTPProxyHandler(manager)

        assert handler.manager == manager


class TestWormholeHTTPClientProtocol:
    """Tests for WormholeHTTPClient protocol handling."""

    def test_protocol_initially_none(self):
        """Test protocol is None after initialization."""
        from wh.http.client import WormholeHTTPClient

        manager = MagicMock()
        client = WormholeHTTPClient(manager)

        assert client._protocol is None

    def test_manager_stored(self):
        """Test manager is stored correctly."""
        from wh.http.client import WormholeHTTPClient

        manager = MagicMock()
        manager.some_property = "test_value"

        client = WormholeHTTPClient(manager)

        assert client.manager.some_property == "test_value"


class TestParseResponseEdgeCases:
    """Tests for edge cases in response parsing."""

    def test_parse_response_empty_headers(self):
        """Test parsing with empty headers dict."""
        from wh.http.client import WormholeHTTPClient

        manager = MagicMock()
        client = WormholeHTTPClient(manager)

        data = b'{"status_code": 200, "reason": "OK", "headers": {}}'
        result = client._parse_response(data)

        assert result["headers"] == {}

    def test_parse_response_with_headers(self):
        """Test parsing with headers."""
        from wh.http.client import WormholeHTTPClient

        manager = MagicMock()
        client = WormholeHTTPClient(manager)

        data = b'{"status_code": 200, "reason": "OK", "headers": {"X-Test": "value"}}'
        result = client._parse_response(data)

        assert result["headers"]["X-Test"] == "value"
