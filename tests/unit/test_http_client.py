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
