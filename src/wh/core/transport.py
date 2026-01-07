"""
Transport adapters for bridging Twisted and asyncio.

These adapters allow asyncio-based libraries (like AsyncSSH) to work
over Twisted's transports (which wormhole dilation provides).
"""

from typing import Any, Optional, Tuple, Callable
import asyncio


class AsyncioTransportAdapter:
    """
    Adapts a Twisted ITransport to an asyncio-compatible transport.

    This bridges Twisted's transport interface to what asyncio protocols
    expect, enabling AsyncSSH to operate over wormhole subchannels.
    """

    def __init__(self, twisted_transport: Any):
        """
        Initialize adapter.

        Args:
            twisted_transport: A Twisted ITransport instance.
        """
        self._transport = twisted_transport
        self._protocol: Optional[Any] = None
        self._closing = False
        self._write_buffer: list[bytes] = []

    def get_extra_info(self, name: str, default: Any = None) -> Any:
        """
        Provide socket-like info that asyncio protocols expect.

        Args:
            name: Info key to look up.
            default: Default value if not found.

        Returns:
            The requested info or default.
        """
        if name == 'peername':
            return ('wormhole', 0)
        if name == 'sockname':
            return ('wormhole', 0)
        if name == 'socket':
            return None
        if name == 'compression':
            return None
        if name == 'cipher':
            return None
        if name == 'peercert':
            return None
        if name == 'sslcontext':
            return None
        return default

    def is_closing(self) -> bool:
        """Check if transport is closing."""
        return self._closing

    def close(self) -> None:
        """Close the transport."""
        if not self._closing:
            self._closing = True
            if self._transport:
                self._transport.loseConnection()

    def write(self, data: bytes) -> None:
        """Write data to the transport."""
        if not self._closing and self._transport:
            self._transport.write(data)

    def writelines(self, data: list[bytes]) -> None:
        """Write multiple chunks of data."""
        for chunk in data:
            self.write(chunk)

    def write_eof(self) -> None:
        """Signal end of write stream."""
        if self._transport and hasattr(self._transport, 'loseWriteConnection'):
            self._transport.loseWriteConnection()

    def can_write_eof(self) -> bool:
        """Check if write EOF is supported."""
        return True

    def get_write_buffer_size(self) -> int:
        """Get current write buffer size."""
        return 0

    def get_write_buffer_limits(self) -> Tuple[int, int]:
        """Get write buffer limits (low, high)."""
        return (0, 0)

    def set_write_buffer_limits(
        self, high: Optional[int] = None, low: Optional[int] = None
    ) -> None:
        """Set write buffer limits."""
        pass

    def abort(self) -> None:
        """Abort the transport immediately."""
        self._closing = True
        if self._transport:
            self._transport.abortConnection()

    def set_protocol(self, protocol: Any) -> None:
        """Set the protocol."""
        self._protocol = protocol

    def get_protocol(self) -> Any:
        """Get the protocol."""
        return self._protocol


class TwistedProtocolAdapter:
    """
    Bridges an asyncio protocol to work with a Twisted transport.

    This allows asyncio protocols (like those in AsyncSSH) to receive
    data from and send data through Twisted transports.
    """

    def __init__(
        self,
        asyncio_protocol: Any,
        loop: Optional[asyncio.AbstractEventLoop] = None,
    ):
        """
        Initialize adapter.

        Args:
            asyncio_protocol: An asyncio protocol instance.
            loop: Event loop to use.
        """
        self.protocol = asyncio_protocol
        self.loop = loop or asyncio.get_event_loop()
        self.transport: Optional[Any] = None
        self._asyncio_transport: Optional[AsyncioTransportAdapter] = None

    def makeConnection(self, transport: Any) -> None:
        """Called when Twisted connection is made."""
        self.transport = transport
        self._asyncio_transport = AsyncioTransportAdapter(transport)

        # Notify the asyncio protocol
        self.loop.call_soon(
            self.protocol.connection_made,
            self._asyncio_transport
        )

    def dataReceived(self, data: bytes) -> None:
        """Called when Twisted receives data."""
        self.loop.call_soon(self.protocol.data_received, data)

    def connectionLost(self, reason: Any = None) -> None:
        """Called when Twisted connection is lost."""
        exc = reason.value if reason and hasattr(reason, 'value') else None
        self.loop.call_soon(self.protocol.connection_lost, exc)


class DuplexPipe:
    """
    A simple duplex pipe for testing and in-memory communication.

    Creates two connected endpoints where data written to one
    appears on the other.
    """

    def __init__(self):
        self._a_to_b: asyncio.Queue[bytes] = asyncio.Queue()
        self._b_to_a: asyncio.Queue[bytes] = asyncio.Queue()
        self._closed = False

    def get_endpoints(self) -> Tuple["PipeEndpoint", "PipeEndpoint"]:
        """Get both endpoints of the pipe."""
        return (
            PipeEndpoint(self._a_to_b, self._b_to_a, self._close),
            PipeEndpoint(self._b_to_a, self._a_to_b, self._close),
        )

    def _close(self) -> None:
        """Close the pipe."""
        self._closed = True


class PipeEndpoint:
    """One endpoint of a DuplexPipe."""

    def __init__(
        self,
        read_queue: asyncio.Queue,
        write_queue: asyncio.Queue,
        close_callback: Callable[[], None],
    ):
        self._read_queue = read_queue
        self._write_queue = write_queue
        self._close_callback = close_callback
        self._closed = False

    async def read(self, n: int = -1) -> bytes:
        """Read data from the pipe."""
        if self._closed:
            return b''
        try:
            return await self._read_queue.get()
        except Exception:
            return b''

    def write(self, data: bytes) -> None:
        """Write data to the pipe."""
        if not self._closed:
            self._write_queue.put_nowait(data)

    def close(self) -> None:
        """Close this endpoint."""
        self._closed = True
        self._close_callback()

    def is_closing(self) -> bool:
        """Check if closing."""
        return self._closed

    def get_extra_info(self, name: str, default: Any = None) -> Any:
        """Get extra info."""
        if name == 'peername':
            return ('pipe', 0)
        if name == 'sockname':
            return ('pipe', 0)
        return default
