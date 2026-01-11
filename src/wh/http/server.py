"""
HTTP File Server over Wormhole - Compatible with browser extension.

Serves local files through wormhole using the same protocol the
browser extension expects:

Request (JSON):
{
  "type": "http_request",
  "method": "GET",
  "path": "/",
  "headers": {...}
}

Response (JSON):
{
  "status_code": 200,
  "headers": {...},
  "body": "<html>..."
}
"""

import json
import mimetypes
from pathlib import Path
from typing import Any


class HTTPFileServer:
    """
    HTTP file server that works with the browser extension.

    Serves files from a local directory over wormhole connection.
    """

    def __init__(self, wormhole_manager: Any, serve_dir: str):
        """
        Initialize file server.

        Args:
            wormhole_manager: WormholeManager instance
            serve_dir: Directory to serve files from
        """
        self.manager = wormhole_manager
        self.serve_dir = Path(serve_dir).resolve()

        if not self.serve_dir.is_dir():
            raise ValueError(f"Not a directory: {serve_dir}")

    async def run(self) -> None:
        """
        Start serving files.

        Listens for HTTP requests and responds with file contents.
        """
        print(f"Serving files from: {self.serve_dir}", flush=True)
        print("Waiting for requests...", flush=True)

        while True:
            try:
                # Receive request
                print("[HTTPFileServer] Calling receive_message()...", flush=True)
                request_data = await self.manager.receive_message()
                print(f"[HTTPFileServer] Received: {len(request_data) if request_data else 0} bytes", flush=True)

                if request_data is None:
                    print("Connection closed")
                    break

                # Parse JSON request
                try:
                    if isinstance(request_data, bytes):
                        request_data = request_data.decode('utf-8')
                    request = json.loads(request_data)
                except json.JSONDecodeError as e:
                    print(f"Invalid JSON request: {e}")
                    await self._send_error(400, "Bad Request", f"Invalid JSON: {e}")
                    continue

                # Handle request
                if request.get("type") == "http_request":
                    await self._handle_http_request(request)
                else:
                    await self._send_error(400, "Bad Request", "Unknown request type")

            except Exception as e:
                import traceback
                print(f"Error handling request: {e}", flush=True)
                traceback.print_exc()
                try:
                    await self._send_error(500, "Internal Server Error", str(e))
                except Exception:
                    pass

    async def _handle_http_request(self, request: dict) -> None:
        """Handle an HTTP request."""
        method = request.get("method", "GET")
        path = request.get("path", "/")

        print(f"Request: {method} {path}")

        # Security: prevent path traversal
        try:
            # Strip query parameters from path
            # Query params should be handled separately if needed
            path_without_query = path.split('?')[0]

            # Normalize and resolve path
            clean_path = path_without_query.lstrip("/")
            print(f"  clean_path: {clean_path}")
            if not clean_path:
                clean_path = "index.html"

            # Handle paths without extension - try adding .html
            file_path = self.serve_dir / clean_path
            print(f"  file_path: {file_path}")
            print(f"  file_path.exists(): {file_path.exists()}")
            print(f"  file_path.is_file(): {file_path.is_file() if file_path.exists() else 'N/A'}")

            # Try exact path first, but only if it's a file (not a directory)
            if not file_path.is_file():
                # Try with .html extension
                html_path = self.serve_dir / (clean_path + ".html")
                print(f"  trying html_path: {html_path}")
                print(f"  html_path.exists(): {html_path.exists()}")
                if html_path.is_file():
                    file_path = html_path
                else:
                    # Try index.html in directory
                    index_path = self.serve_dir / clean_path / "index.html"
                    print(f"  trying index_path: {index_path}")
                    print(f"  index_path.exists(): {index_path.exists()}")
                    if index_path.is_file():
                        file_path = index_path

            # Resolve to absolute and check it's within serve_dir
            file_path = file_path.resolve()
            print(f"  resolved file_path: {file_path}")
            print(f"  serve_dir: {self.serve_dir}")
            print(f"  within serve_dir: {str(file_path).startswith(str(self.serve_dir))}")

            if not str(file_path).startswith(str(self.serve_dir)):
                print(f"  ERROR: Path traversal detected!")
                await self._send_error(403, "Forbidden", "Path traversal not allowed")
                return

            if not file_path.exists():
                print(f"  ERROR: File does not exist!")
                await self._send_error(404, "Not Found", f"File not found: {path}")
                return

            print(f"  is_file: {file_path.is_file()}")
            if not file_path.is_file():
                print(f"  ERROR: Not a file!")
                await self._send_error(403, "Forbidden", "Not a file")
                return

            # Read file
            content = file_path.read_text(encoding='utf-8')

            # Determine content type
            content_type, _ = mimetypes.guess_type(str(file_path))
            if content_type is None:
                content_type = "text/html"

            # Send response
            response = {
                "status_code": 200,
                "headers": {
                    "Content-Type": content_type,
                    "Content-Length": str(len(content)),
                },
                "body": content
            }

            await self._send_response(response)
            print(f"Served: {file_path} ({len(content)} bytes)")

        except Exception as e:
            print(f"Error serving {path}: {e}")
            await self._send_error(500, "Internal Server Error", str(e))

    async def _send_response(self, response: dict) -> None:
        """Send JSON response."""
        response_json = json.dumps(response)
        await self.manager.send_message(response_json.encode('utf-8'))

    async def _send_error(self, status_code: int, reason: str, message: str) -> None:
        """Send error response."""
        response = {
            "status_code": status_code,
            "headers": {"Content-Type": "text/html"},
            "body": f"<html><body><h1>{status_code} {reason}</h1><p>{message}</p></body></html>"
        }
        await self._send_response(response)
