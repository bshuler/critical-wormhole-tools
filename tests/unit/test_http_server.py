"""Unit tests for HTTP file server module."""

import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock


@pytest.fixture
def mock_http_file_server(tmp_path):
    """
    Create a mock HTTP file server with test files.

    Creates a test directory structure:
    - index.html
    - style.css
    - script.js
    - data.json
    - subdir/index.html
    - binary.bin (binary file)
    """
    # Create test files
    (tmp_path / "index.html").write_text("<html><body>Home</body></html>")
    (tmp_path / "style.css").write_text("body { color: blue; }")
    (tmp_path / "script.js").write_text("console.log('test');")
    (tmp_path / "data.json").write_text('{"key": "value"}')

    # Create subdirectory with index.html
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    (subdir / "index.html").write_text("<html><body>Subdir</body></html>")

    # Create binary file
    (tmp_path / "binary.bin").write_bytes(bytes([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A]))

    return {
        "serve_dir": str(tmp_path),
        "tmp_path": tmp_path,
    }


class TestHTTPFileServerInit:
    """Tests for HTTPFileServer initialization."""

    def test_http_file_server_init(self, mock_http_file_server):
        """Test server initializes with valid directory."""
        from wh.http.server import HTTPFileServer

        manager = MagicMock()
        server = HTTPFileServer(manager, mock_http_file_server["serve_dir"])

        assert server.manager is manager
        assert server.serve_dir == Path(mock_http_file_server["serve_dir"]).resolve()

    def test_http_file_server_init_invalid_dir(self, tmp_path):
        """Test raises ValueError for non-directory."""
        from wh.http.server import HTTPFileServer

        manager = MagicMock()
        invalid_dir = tmp_path / "nonexistent"

        with pytest.raises(ValueError, match="Not a directory"):
            HTTPFileServer(manager, str(invalid_dir))

    def test_http_file_server_init_file_not_dir(self, tmp_path):
        """Test raises ValueError when path is a file, not directory."""
        from wh.http.server import HTTPFileServer

        manager = MagicMock()
        file_path = tmp_path / "somefile.txt"
        file_path.write_text("test")

        with pytest.raises(ValueError, match="Not a directory"):
            HTTPFileServer(manager, str(file_path))


class TestHandleHTTPRequest:
    """Tests for HTTP request handling."""

    @pytest.mark.asyncio
    async def test_handle_http_request_get_file(self, mock_http_file_server):
        """Test returns 200 with file content."""
        from wh.http.server import HTTPFileServer

        manager = MagicMock()
        manager.send_message = AsyncMock()

        server = HTTPFileServer(manager, mock_http_file_server["serve_dir"])

        request = {
            "type": "http_request",
            "method": "GET",
            "path": "/style.css",
            "headers": {}
        }

        await server._handle_http_request(request)

        # Verify response was sent
        assert manager.send_message.called
        response_data = manager.send_message.call_args[0][0]
        response = json.loads(response_data.decode('utf-8'))

        assert response["status_code"] == 200
        assert response["headers"]["Content-Type"] == "text/css"
        assert "body { color: blue; }" in response["body"]

    @pytest.mark.asyncio
    async def test_handle_http_request_index_html(self, mock_http_file_server):
        """Test GET / serves index.html."""
        from wh.http.server import HTTPFileServer

        manager = MagicMock()
        manager.send_message = AsyncMock()

        server = HTTPFileServer(manager, mock_http_file_server["serve_dir"])

        request = {
            "type": "http_request",
            "method": "GET",
            "path": "/",
            "headers": {}
        }

        await server._handle_http_request(request)

        response_data = manager.send_message.call_args[0][0]
        response = json.loads(response_data.decode('utf-8'))

        assert response["status_code"] == 200
        assert "<html><body>Home</body></html>" in response["body"]

    @pytest.mark.asyncio
    async def test_handle_http_request_html_extension(self, mock_http_file_server):
        """Test adds .html extension automatically."""
        from wh.http.server import HTTPFileServer

        manager = MagicMock()
        manager.send_message = AsyncMock()

        # Create a test file without .html in request
        test_file = mock_http_file_server["tmp_path"] / "about.html"
        test_file.write_text("<html><body>About</body></html>")

        server = HTTPFileServer(manager, mock_http_file_server["serve_dir"])

        request = {
            "type": "http_request",
            "method": "GET",
            "path": "/about",  # No .html extension
            "headers": {}
        }

        await server._handle_http_request(request)

        response_data = manager.send_message.call_args[0][0]
        response = json.loads(response_data.decode('utf-8'))

        assert response["status_code"] == 200
        assert "<html><body>About</body></html>" in response["body"]

    @pytest.mark.asyncio
    async def test_handle_http_request_directory_index(self, mock_http_file_server):
        """Test GET /subdir/ serves subdir/index.html."""
        from wh.http.server import HTTPFileServer

        manager = MagicMock()
        manager.send_message = AsyncMock()

        server = HTTPFileServer(manager, mock_http_file_server["serve_dir"])

        request = {
            "type": "http_request",
            "method": "GET",
            "path": "/subdir/",
            "headers": {}
        }

        await server._handle_http_request(request)

        response_data = manager.send_message.call_args[0][0]
        response = json.loads(response_data.decode('utf-8'))

        assert response["status_code"] == 200
        assert "<html><body>Subdir</body></html>" in response["body"]

    @pytest.mark.asyncio
    async def test_handle_http_request_404(self, mock_http_file_server):
        """Test returns 404 Not Found."""
        from wh.http.server import HTTPFileServer

        manager = MagicMock()
        manager.send_message = AsyncMock()

        server = HTTPFileServer(manager, mock_http_file_server["serve_dir"])

        request = {
            "type": "http_request",
            "method": "GET",
            "path": "/nonexistent.html",
            "headers": {}
        }

        await server._handle_http_request(request)

        response_data = manager.send_message.call_args[0][0]
        response = json.loads(response_data.decode('utf-8'))

        assert response["status_code"] == 404
        assert "404" in response["body"]
        assert "Not Found" in response["body"]

    @pytest.mark.asyncio
    async def test_handle_http_request_path_traversal(self, mock_http_file_server):
        """Test returns 403 Forbidden for path traversal attempts."""
        from wh.http.server import HTTPFileServer

        manager = MagicMock()
        manager.send_message = AsyncMock()

        server = HTTPFileServer(manager, mock_http_file_server["serve_dir"])

        request = {
            "type": "http_request",
            "method": "GET",
            "path": "/../../../etc/passwd",
            "headers": {}
        }

        await server._handle_http_request(request)

        response_data = manager.send_message.call_args[0][0]
        response = json.loads(response_data.decode('utf-8'))

        assert response["status_code"] == 403
        assert "Forbidden" in response["body"]
        assert "Path traversal" in response["body"]


class TestRunMethod:
    """Tests for the run() method and request processing."""

    @pytest.mark.asyncio
    async def test_handle_http_request_invalid_type(self, mock_http_file_server):
        """Test returns 400 for unknown request type."""
        from wh.http.server import HTTPFileServer

        manager = MagicMock()
        manager.receive_message = AsyncMock(side_effect=[
            json.dumps({"type": "unknown_type"}).encode('utf-8'),
            None  # End connection
        ])
        manager.send_message = AsyncMock()

        server = HTTPFileServer(manager, mock_http_file_server["serve_dir"])

        await server.run()

        # Verify error response was sent
        response_data = manager.send_message.call_args[0][0]
        response = json.loads(response_data.decode('utf-8'))

        assert response["status_code"] == 400
        assert "Bad Request" in response["body"]

    @pytest.mark.asyncio
    async def test_handle_http_request_invalid_json(self, mock_http_file_server):
        """Test returns 400 for malformed JSON."""
        from wh.http.server import HTTPFileServer

        manager = MagicMock()
        manager.receive_message = AsyncMock(side_effect=[
            b"not valid json {{{",
            None  # End connection
        ])
        manager.send_message = AsyncMock()

        server = HTTPFileServer(manager, mock_http_file_server["serve_dir"])

        await server.run()

        # Verify error response was sent
        response_data = manager.send_message.call_args[0][0]
        response = json.loads(response_data.decode('utf-8'))

        assert response["status_code"] == 400
        assert "Invalid JSON" in response["body"]

    @pytest.mark.asyncio
    async def test_run_connection_closed(self, mock_http_file_server):
        """Test run() exits gracefully when connection closes."""
        from wh.http.server import HTTPFileServer

        manager = MagicMock()
        manager.receive_message = AsyncMock(return_value=None)

        server = HTTPFileServer(manager, mock_http_file_server["serve_dir"])

        # Should exit without error
        await server.run()


class TestSendResponse:
    """Tests for response sending methods."""

    @pytest.mark.asyncio
    async def test_send_response_json(self, mock_http_file_server):
        """Test valid JSON response is sent."""
        from wh.http.server import HTTPFileServer

        manager = MagicMock()
        manager.send_message = AsyncMock()

        server = HTTPFileServer(manager, mock_http_file_server["serve_dir"])

        response = {
            "status_code": 200,
            "headers": {"Content-Type": "application/json"},
            "body": '{"test": true}'
        }

        await server._send_response(response)

        # Verify message was sent
        assert manager.send_message.called
        sent_data = manager.send_message.call_args[0][0]
        parsed = json.loads(sent_data.decode('utf-8'))

        assert parsed["status_code"] == 200
        assert parsed["body"] == '{"test": true}'

    @pytest.mark.asyncio
    async def test_send_error_response(self, mock_http_file_server):
        """Test HTML error body is returned."""
        from wh.http.server import HTTPFileServer

        manager = MagicMock()
        manager.send_message = AsyncMock()

        server = HTTPFileServer(manager, mock_http_file_server["serve_dir"])

        await server._send_error(404, "Not Found", "The requested file was not found")

        # Verify error response structure
        sent_data = manager.send_message.call_args[0][0]
        response = json.loads(sent_data.decode('utf-8'))

        assert response["status_code"] == 404
        assert response["headers"]["Content-Type"] == "text/html"
        assert "<html>" in response["body"]
        assert "404" in response["body"]
        assert "Not Found" in response["body"]
        assert "The requested file was not found" in response["body"]


class TestContentTypeDetection:
    """Tests for content type detection."""

    @pytest.mark.asyncio
    async def test_content_type_detection(self, mock_http_file_server):
        """Test correct Content-Type headers for different file types."""
        from wh.http.server import HTTPFileServer

        manager = MagicMock()
        manager.send_message = AsyncMock()

        server = HTTPFileServer(manager, mock_http_file_server["serve_dir"])

        # Test CSS file
        await server._handle_http_request({
            "type": "http_request",
            "method": "GET",
            "path": "/style.css",
            "headers": {}
        })

        response_data = manager.send_message.call_args[0][0]
        response = json.loads(response_data.decode('utf-8'))
        assert response["headers"]["Content-Type"] == "text/css"

        # Test JavaScript file
        await server._handle_http_request({
            "type": "http_request",
            "method": "GET",
            "path": "/script.js",
            "headers": {}
        })

        response_data = manager.send_message.call_args[0][0]
        response = json.loads(response_data.decode('utf-8'))
        # Could be text/javascript or application/javascript
        assert "javascript" in response["headers"]["Content-Type"]

        # Test JSON file
        await server._handle_http_request({
            "type": "http_request",
            "method": "GET",
            "path": "/data.json",
            "headers": {}
        })

        response_data = manager.send_message.call_args[0][0]
        response = json.loads(response_data.decode('utf-8'))
        assert response["headers"]["Content-Type"] == "application/json"

    @pytest.mark.asyncio
    async def test_content_type_html_default(self, mock_http_file_server):
        """Test HTML is default content type for unknown extensions."""
        from wh.http.server import HTTPFileServer

        manager = MagicMock()
        manager.send_message = AsyncMock()

        # Create file with unknown extension
        unknown_file = mock_http_file_server["tmp_path"] / "file.unknown"
        unknown_file.write_text("test content")

        server = HTTPFileServer(manager, mock_http_file_server["serve_dir"])

        await server._handle_http_request({
            "type": "http_request",
            "method": "GET",
            "path": "/file.unknown",
            "headers": {}
        })

        response_data = manager.send_message.call_args[0][0]
        response = json.loads(response_data.decode('utf-8'))

        # Default to text/html for unknown types
        assert response["headers"]["Content-Type"] == "text/html"


class TestBinaryFileHandling:
    """Tests for binary file handling."""

    @pytest.mark.asyncio
    async def test_binary_file_handling(self, mock_http_file_server):
        """Test binary file causes 500 error (KNOWN BUG)."""
        from wh.http.server import HTTPFileServer

        manager = MagicMock()
        manager.send_message = AsyncMock()

        server = HTTPFileServer(manager, mock_http_file_server["serve_dir"])

        request = {
            "type": "http_request",
            "method": "GET",
            "path": "/binary.bin",
            "headers": {}
        }

        # This will fail because read_text() is used for binary files
        await server._handle_http_request(request)

        response_data = manager.send_message.call_args[0][0]
        response = json.loads(response_data.decode('utf-8'))

        # Should return 500 error due to the bug
        assert response["status_code"] == 500
        assert "Internal Server Error" in response["body"]


class TestQueryParameters:
    """Tests for query parameter handling."""

    @pytest.mark.asyncio
    async def test_query_parameters_stripped(self, mock_http_file_server):
        """Test query parameters are stripped from path."""
        from wh.http.server import HTTPFileServer

        manager = MagicMock()
        manager.send_message = AsyncMock()

        server = HTTPFileServer(manager, mock_http_file_server["serve_dir"])

        request = {
            "type": "http_request",
            "method": "GET",
            "path": "/index.html?foo=bar&baz=qux",
            "headers": {}
        }

        await server._handle_http_request(request)

        response_data = manager.send_message.call_args[0][0]
        response = json.loads(response_data.decode('utf-8'))

        # Should successfully serve index.html, ignoring query params
        assert response["status_code"] == 200
        assert "<html><body>Home</body></html>" in response["body"]


class TestEdgeCases:
    """Tests for edge cases."""

    @pytest.mark.asyncio
    async def test_directory_without_trailing_slash(self, mock_http_file_server):
        """Test accessing directory without trailing slash."""
        from wh.http.server import HTTPFileServer

        manager = MagicMock()
        manager.send_message = AsyncMock()

        server = HTTPFileServer(manager, mock_http_file_server["serve_dir"])

        request = {
            "type": "http_request",
            "method": "GET",
            "path": "/subdir",  # No trailing slash
            "headers": {}
        }

        await server._handle_http_request(request)

        response_data = manager.send_message.call_args[0][0]
        response = json.loads(response_data.decode('utf-8'))

        # Should serve subdir/index.html
        assert response["status_code"] == 200
        assert "<html><body>Subdir</body></html>" in response["body"]

    @pytest.mark.asyncio
    async def test_empty_path(self, mock_http_file_server):
        """Test empty path defaults to index.html."""
        from wh.http.server import HTTPFileServer

        manager = MagicMock()
        manager.send_message = AsyncMock()

        server = HTTPFileServer(manager, mock_http_file_server["serve_dir"])

        request = {
            "type": "http_request",
            "method": "GET",
            "path": "",  # Empty path
            "headers": {}
        }

        await server._handle_http_request(request)

        response_data = manager.send_message.call_args[0][0]
        response = json.loads(response_data.decode('utf-8'))

        # Should serve index.html
        assert response["status_code"] == 200
        assert "<html><body>Home</body></html>" in response["body"]

    @pytest.mark.asyncio
    async def test_request_bytes_json(self, mock_http_file_server):
        """Test handling of JSON request as bytes."""
        from wh.http.server import HTTPFileServer

        manager = MagicMock()
        manager.receive_message = AsyncMock(side_effect=[
            json.dumps({"type": "http_request", "method": "GET", "path": "/index.html"}).encode('utf-8'),
            None
        ])
        manager.send_message = AsyncMock()

        server = HTTPFileServer(manager, mock_http_file_server["serve_dir"])

        await server.run()

        # Should handle bytes successfully
        response_data = manager.send_message.call_args[0][0]
        response = json.loads(response_data.decode('utf-8'))

        assert response["status_code"] == 200

    @pytest.mark.asyncio
    async def test_content_length_header(self, mock_http_file_server):
        """Test Content-Length header is set correctly."""
        from wh.http.server import HTTPFileServer

        manager = MagicMock()
        manager.send_message = AsyncMock()

        server = HTTPFileServer(manager, mock_http_file_server["serve_dir"])

        request = {
            "type": "http_request",
            "method": "GET",
            "path": "/index.html",
            "headers": {}
        }

        await server._handle_http_request(request)

        response_data = manager.send_message.call_args[0][0]
        response = json.loads(response_data.decode('utf-8'))

        assert "Content-Length" in response["headers"]
        assert int(response["headers"]["Content-Length"]) == len(response["body"])
