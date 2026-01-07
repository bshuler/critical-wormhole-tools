"""
WormholeHTTPClient - HTTP client that sends requests through wormhole.

The peer side runs an HTTP proxy that forwards requests to their
actual destinations.
"""

from typing import Dict, Optional, Any
from dataclasses import dataclass
import asyncio
import json

from wh.core.protocol import StreamingProtocol


@dataclass
class HTTPResponse:
    """HTTP response from a wormhole-tunneled request."""
    status_code: int
    reason: str
    headers: Dict[str, str]
    body: bytes


class WormholeHTTPClient:
    """
    HTTP client that sends requests through wormhole tunnel.

    The peer side runs `wh listen --http` which receives the HTTP
    request, makes the actual request, and returns the response.

    Protocol:
    1. Client sends JSON request metadata
    2. Client sends body (if any)
    3. Server sends JSON response metadata
    4. Server sends body

    Example:
        manager = WormholeManager()
        await manager.create_and_set_code("7-guitar-sunset")
        await manager.dilate()

        client = WormholeHTTPClient(manager)
        response = await client.request(
            method="GET",
            url="http://example.com/api",
        )
        print(response.body.decode())
    """

    def __init__(self, wormhole_manager: Any):
        """
        Initialize HTTP client.

        Args:
            wormhole_manager: A dilated WormholeManager instance.
        """
        self.manager = wormhole_manager
        self._protocol: Optional[StreamingProtocol] = None

    async def request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[bytes] = None,
        timeout: float = 30.0,
    ) -> HTTPResponse:
        """
        Send HTTP request through wormhole and get response.

        Args:
            method: HTTP method (GET, POST, etc.).
            url: Full URL to request.
            headers: Request headers.
            body: Request body.
            timeout: Request timeout in seconds.

        Returns:
            HTTPResponse with status, headers, and body.
        """
        if not self.manager.is_dilated:
            raise RuntimeError("Wormhole must be dilated")

        headers = headers or {}

        # Build request message
        request_data = {
            "type": "http_request",
            "method": method,
            "url": url,
            "headers": headers,
            "body_length": len(body) if body else 0,
        }

        # Connect to peer
        response_data = await asyncio.wait_for(
            self._send_request(request_data, body),
            timeout=timeout,
        )

        return HTTPResponse(
            status_code=response_data["status_code"],
            reason=response_data.get("reason", ""),
            headers=response_data.get("headers", {}),
            body=response_data.get("body", b""),
        )

    async def _send_request(
        self,
        request_data: dict,
        body: Optional[bytes],
    ) -> dict:
        """
        Send request and receive response.

        Args:
            request_data: Request metadata dict.
            body: Request body bytes.

        Returns:
            Response data dict including body.
        """
        endpoint = self.manager.connector_for("wh-http")

        # Set up response collection
        response_parts: list = []
        response_complete = asyncio.Event()
        response_error: list = [None]

        def on_data(data: bytes) -> None:
            response_parts.append(data)

        def on_connection_lost(exc: Optional[Exception]) -> None:
            if exc:
                response_error[0] = exc
            response_complete.set()

        from twisted.internet.protocol import Factory

        class HTTPClientProtocol(StreamingProtocol):
            pass

        class HTTPClientFactory(Factory):
            def buildProtocol(self, addr):
                p = HTTPClientProtocol(
                    on_data=on_data,
                    on_connection_lost=on_connection_lost,
                )
                return p

        # Connect
        from twisted.internet import defer

        d = endpoint.connect(HTTPClientFactory())

        future = asyncio.get_event_loop().create_future()

        def callback(proto):
            if not future.done():
                future.set_result(proto)

        def errback(failure):
            if not future.done():
                future.set_exception(failure.value)

        d.addCallbacks(callback, errback)

        protocol = await future
        self._protocol = protocol

        # Send request
        request_json = json.dumps(request_data).encode('utf-8')
        request_line = request_json + b"\n"
        protocol.send(request_line)

        if body:
            protocol.send(body)

        # Signal end of request
        protocol.send(b"\n---END---\n")

        # Wait for response
        await response_complete.wait()

        if response_error[0]:
            raise response_error[0]

        # Parse response
        response_bytes = b"".join(response_parts)
        return self._parse_response(response_bytes)

    def _parse_response(self, data: bytes) -> dict:
        """
        Parse response from proxy.

        Expected format:
        {JSON metadata}\n
        {body bytes}
        """
        # Find JSON metadata line
        newline_pos = data.find(b"\n")
        if newline_pos == -1:
            # All JSON, no body
            metadata = json.loads(data.decode('utf-8'))
            metadata["body"] = b""
            return metadata

        metadata_line = data[:newline_pos]
        body = data[newline_pos + 1:]

        metadata = json.loads(metadata_line.decode('utf-8'))
        metadata["body"] = body

        return metadata


class HTTPProxyHandler:
    """
    HTTP proxy handler for `wh listen --http`.

    Accepts HTTP requests through wormhole and forwards them
    to their actual destinations.
    """

    def __init__(self, wormhole_manager: Any):
        """
        Initialize HTTP proxy handler.

        Args:
            wormhole_manager: A dilated WormholeManager instance.
        """
        self.manager = wormhole_manager

    async def run(self) -> None:
        """
        Start accepting HTTP requests.

        Listens on the wormhole listen endpoint and handles
        incoming HTTP requests.
        """
        endpoint = self.manager.listener_for("wh-http")

        from twisted.internet.protocol import Factory

        handler = self

        class HTTPProxyProtocol(StreamingProtocol):
            def __init__(self):
                super().__init__()
                self._buffer = b""

            def dataReceived(self, data: bytes) -> None:
                self._buffer += data

                # Check for end marker
                if b"\n---END---\n" in self._buffer:
                    asyncio.ensure_future(
                        handler._handle_request(self, self._buffer)
                    )
                    self._buffer = b""

        class HTTPProxyFactory(Factory):
            def buildProtocol(self, addr):
                return HTTPProxyProtocol()

        # Start listening
        from twisted.internet import defer

        d = endpoint.listen(HTTPProxyFactory())

        future = asyncio.get_event_loop().create_future()

        def callback(port):
            if not future.done():
                future.set_result(port)

        def errback(failure):
            if not future.done():
                future.set_exception(failure.value)

        d.addCallbacks(callback, errback)

        await future

        print("HTTP proxy ready")

        # Keep running
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            pass

    async def _handle_request(
        self,
        protocol: StreamingProtocol,
        data: bytes,
    ) -> None:
        """
        Handle an incoming HTTP request.

        Args:
            protocol: The protocol to send response through.
            data: Request data including metadata and body.
        """
        try:
            # Parse request
            end_marker_pos = data.find(b"\n---END---\n")
            if end_marker_pos != -1:
                data = data[:end_marker_pos]

            newline_pos = data.find(b"\n")
            if newline_pos == -1:
                metadata_line = data
                body = b""
            else:
                metadata_line = data[:newline_pos]
                body = data[newline_pos + 1:]

            request_data = json.loads(metadata_line.decode('utf-8'))

            # Make the actual HTTP request
            import httpx

            async with httpx.AsyncClient() as client:
                response = await client.request(
                    method=request_data["method"],
                    url=request_data["url"],
                    headers=request_data.get("headers", {}),
                    content=body if body else None,
                )

            # Send response
            response_data = {
                "status_code": response.status_code,
                "reason": response.reason_phrase,
                "headers": dict(response.headers),
            }

            response_json = json.dumps(response_data).encode('utf-8')
            protocol.send(response_json + b"\n")
            protocol.send(response.content)
            protocol.close()

        except Exception as e:
            # Send error response
            error_data = {
                "status_code": 502,
                "reason": "Bad Gateway",
                "headers": {},
            }
            error_json = json.dumps(error_data).encode('utf-8')
            protocol.send(error_json + b"\n")
            protocol.send(f"Error: {e}".encode('utf-8'))
            protocol.close()
