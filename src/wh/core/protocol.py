"""
Base protocols for streaming data over wormhole subchannels.

These protocols handle bidirectional data flow between local stdin/stdout
and the wormhole connection.
"""

from typing import Callable, Optional, Any
import asyncio
from twisted.internet.protocol import Protocol, Factory
from twisted.internet.interfaces import ITransport


class StreamingProtocol(Protocol):
    """
    Base protocol for bidirectional streaming over wormhole subchannels.

    Provides:
    - Data buffering and flow control
    - Backpressure handling via IProducer/IConsumer
    - Clean disconnection handling
    """

    def __init__(
        self,
        on_data: Optional[Callable[[bytes], None]] = None,
        on_connection_made: Optional[Callable[[], None]] = None,
        on_connection_lost: Optional[Callable[[Optional[Exception]], None]] = None,
    ):
        """
        Initialize StreamingProtocol.

        Args:
            on_data: Callback when data is received.
            on_connection_made: Callback when connection is established.
            on_connection_lost: Callback when connection is lost.
        """
        self.on_data_callback = on_data
        self.on_connection_made_callback = on_connection_made
        self.on_connection_lost_callback = on_connection_lost
        self.transport: Optional[ITransport] = None
        self._connected = False

    def connectionMade(self) -> None:
        """Called when connection is established."""
        self._connected = True
        if self.on_connection_made_callback:
            self.on_connection_made_callback()

    def dataReceived(self, data: bytes) -> None:
        """Handle incoming data from peer."""
        if self.on_data_callback:
            self.on_data_callback(data)

    def connectionLost(self, reason: Any = None) -> None:
        """Handle disconnection."""
        self._connected = False
        if self.on_connection_lost_callback:
            exc = reason.value if reason and hasattr(reason, 'value') else None
            self.on_connection_lost_callback(exc)

    def send(self, data: bytes) -> None:
        """Send data to peer."""
        if self.transport and self._connected:
            self.transport.write(data)

    def close(self) -> None:
        """Close the connection."""
        if self.transport:
            self.transport.loseConnection()

    @property
    def is_connected(self) -> bool:
        """Check if connected."""
        return self._connected


class StreamingProtocolFactory(Factory):
    """Factory for creating StreamingProtocol instances."""

    protocol = StreamingProtocol

    def __init__(
        self,
        on_data: Optional[Callable[[bytes], None]] = None,
        on_connection_made: Optional[Callable[[], None]] = None,
        on_connection_lost: Optional[Callable[[Optional[Exception]], None]] = None,
    ):
        self.on_data = on_data
        self.on_connection_made = on_connection_made
        self.on_connection_lost = on_connection_lost

    def buildProtocol(self, addr: Any) -> StreamingProtocol:
        """Build a new protocol instance."""
        p = self.protocol(
            on_data=self.on_data,
            on_connection_made=self.on_connection_made,
            on_connection_lost=self.on_connection_lost,
        )
        p.factory = self
        return p


class BidirectionalPipe:
    """
    Netcat-style bidirectional pipe over a wormhole subchannel.

    Connects local stdin/stdout to the wormhole for simple
    bidirectional data transfer between two endpoints.

    Example:
        pipe = BidirectionalPipe()
        await pipe.run(manager)
        # Now stdin goes to peer, peer's data comes to stdout
    """

    def __init__(
        self,
        stdin: Optional[Any] = None,
        stdout: Optional[Any] = None,
        on_status: Optional[Callable[[str], None]] = None,
    ):
        """
        Initialize BidirectionalPipe.

        Args:
            stdin: Input stream (default: sys.stdin.buffer)
            stdout: Output stream (default: sys.stdout.buffer)
            on_status: Callback for status messages
        """
        self.stdin = stdin
        self.stdout = stdout
        self.on_status = on_status
        self._protocol: Optional[StreamingProtocol] = None
        self._read_task: Optional[asyncio.Task] = None
        self._done = asyncio.Event()

    def _status(self, message: str) -> None:
        """Send status update."""
        if self.on_status:
            self.on_status(message)

    def _get_stdin(self) -> Any:
        """Get stdin stream."""
        if self.stdin is not None:
            return self.stdin
        import sys
        return sys.stdin.buffer

    def _get_stdout(self) -> Any:
        """Get stdout stream."""
        if self.stdout is not None:
            return self.stdout
        import sys
        return sys.stdout.buffer

    async def _pump_stdin(self) -> None:
        """Continuously read from stdin and send to peer."""
        loop = asyncio.get_event_loop()
        stdin = self._get_stdin()

        try:
            # Try to use asyncio reader for stdin (Unix only, non-blocking)
            import sys
            import os
            if hasattr(os, 'set_blocking') and stdin == sys.stdin.buffer:
                try:
                    # Make stdin non-blocking and use asyncio reader
                    os.set_blocking(stdin.fileno(), False)
                    reader = asyncio.StreamReader()
                    protocol = asyncio.StreamReaderProtocol(reader)
                    await loop.connect_read_pipe(lambda: protocol, stdin)

                    while not self._done.is_set():
                        try:
                            data = await asyncio.wait_for(reader.read(4096), timeout=0.5)
                            if not data:
                                self._status("EOF on stdin")
                                if self._protocol and self._protocol.transport:
                                    self._protocol.transport.loseWriteConnection()
                                break
                            if self._protocol:
                                self._protocol.send(data)
                        except asyncio.TimeoutError:
                            continue  # Check _done flag and continue
                    return
                except (OSError, NotImplementedError):
                    # Fall back to executor-based reading
                    pass

            # Fallback: Use executor with timeout-based reads
            import select
            while not self._done.is_set():
                # Use select to check if stdin has data (with timeout for signal handling)
                if hasattr(select, 'select'):
                    try:
                        readable, _, _ = select.select([stdin], [], [], 0.5)
                        if not readable:
                            continue  # Timeout - check for signals
                    except (ValueError, OSError):
                        # stdin might be closed or not selectable
                        pass

                # Read with a small timeout via executor
                try:
                    data = await asyncio.wait_for(
                        loop.run_in_executor(None, stdin.read, 4096),
                        timeout=0.5
                    )
                except asyncio.TimeoutError:
                    continue  # Check _done flag and continue

                if not data:
                    self._status("EOF on stdin")
                    if self._protocol and self._protocol.transport:
                        self._protocol.transport.loseWriteConnection()
                    break
                if self._protocol:
                    self._protocol.send(data)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            self._status(f"stdin error: {e}")
        finally:
            self._done.set()

    def _on_data(self, data: bytes) -> None:
        """Handle data received from peer."""
        stdout = self._get_stdout()
        try:
            stdout.write(data)
            stdout.flush()
        except Exception as e:
            self._status(f"stdout error: {e}")

    def _on_connection_lost(self, exc: Optional[Exception]) -> None:
        """Handle connection lost."""
        self._status("Connection closed")
        self._done.set()

    async def run_with_protocol(self, protocol: StreamingProtocol) -> None:
        """
        Run the pipe with an already-connected protocol.

        Args:
            protocol: A connected StreamingProtocol.
        """
        self._protocol = protocol
        protocol.on_data_callback = self._on_data
        protocol.on_connection_lost_callback = self._on_connection_lost

        # Start reading from stdin
        self._read_task = asyncio.create_task(self._pump_stdin())

        # Wait for connection to close
        await self._done.wait()

        # Cancel stdin reader if still running
        if self._read_task and not self._read_task.done():
            self._read_task.cancel()
            try:
                await self._read_task
            except asyncio.CancelledError:
                pass

    async def run_as_initiator(
        self,
        manager: Any,
        protocol_name: str = "wh-nc",
        shutdown_event: Optional[asyncio.Event] = None,
    ) -> None:
        """
        Run as the initiating side (connects to peer).

        Args:
            manager: WormholeManager instance (must be dilated).
            protocol_name: Name of the subprotocol to use.
            shutdown_event: Optional event to signal shutdown.
        """
        from twisted.internet import defer

        # Connect to peer's listening endpoint
        endpoint = manager.connector_for(protocol_name)

        connected = asyncio.Event()
        protocol_holder = [None]

        def on_connected():
            connected.set()

        factory = StreamingProtocolFactory(
            on_data=self._on_data,
            on_connection_made=on_connected,
            on_connection_lost=self._on_connection_lost,
        )

        # Connect using the endpoint
        d = endpoint.connect(factory)

        future = asyncio.get_event_loop().create_future()

        def callback(protocol):
            protocol_holder[0] = protocol
            self._protocol = protocol
            if not future.done():
                future.set_result(protocol)

        def errback(failure):
            if not future.done():
                future.set_exception(failure.value)

        d.addCallbacks(callback, errback)

        await future
        await connected.wait()

        self._status("Connected to peer")

        # Run the bidirectional pipe
        self._read_task = asyncio.create_task(self._pump_stdin())

        # Wait for done or shutdown
        if shutdown_event:
            done_task = asyncio.create_task(self._done.wait())
            shutdown_task = asyncio.create_task(shutdown_event.wait())
            await asyncio.wait(
                [done_task, shutdown_task],
                return_when=asyncio.FIRST_COMPLETED
            )
            if shutdown_event.is_set():
                self._done.set()
        else:
            await self._done.wait()

        if self._read_task and not self._read_task.done():
            self._read_task.cancel()
            try:
                await self._read_task
            except asyncio.CancelledError:
                pass

    async def run_as_listener(
        self,
        manager: Any,
        protocol_name: str = "wh-nc",
        shutdown_event: Optional[asyncio.Event] = None,
    ) -> None:
        """
        Run as the listening side (accepts connection from peer).

        Args:
            manager: WormholeManager instance (must be dilated).
            protocol_name: Name of the subprotocol to use.
            shutdown_event: Optional event to signal shutdown.
        """
        # Listen for peer's connection
        endpoint = manager.listener_for(protocol_name)

        connected = asyncio.Event()

        def on_connected():
            connected.set()

        factory = StreamingProtocolFactory(
            on_data=self._on_data,
            on_connection_made=on_connected,
            on_connection_lost=self._on_connection_lost,
        )

        # Start listening
        d = endpoint.listen(factory)

        future = asyncio.get_event_loop().create_future()

        def callback(port):
            if not future.done():
                future.set_result(port)

        def errback(failure):
            if not future.done():
                future.set_exception(failure.value)

        d.addCallbacks(callback, errback)

        port = await future
        self._status("Listening for peer connection...")

        # Wait for connection or shutdown
        if shutdown_event:
            connected_task = asyncio.create_task(connected.wait())
            shutdown_task = asyncio.create_task(shutdown_event.wait())
            done, pending = await asyncio.wait(
                [connected_task, shutdown_task],
                return_when=asyncio.FIRST_COMPLETED
            )
            for task in pending:
                task.cancel()
            if shutdown_event.is_set():
                return
        else:
            await connected.wait()

        self._status("Peer connected")

        # Run the bidirectional pipe
        self._read_task = asyncio.create_task(self._pump_stdin())

        # Wait for done or shutdown
        if shutdown_event:
            done_task = asyncio.create_task(self._done.wait())
            shutdown_task = asyncio.create_task(shutdown_event.wait())
            await asyncio.wait(
                [done_task, shutdown_task],
                return_when=asyncio.FIRST_COMPLETED
            )
            if shutdown_event.is_set():
                self._done.set()
        else:
            await self._done.wait()

        if self._read_task and not self._read_task.done():
            self._read_task.cancel()
            try:
                await self._read_task
            except asyncio.CancelledError:
                pass


class PipeProtocolFactory(Factory):
    """Factory that tracks the created protocol for BidirectionalPipe."""

    def __init__(self, pipe: BidirectionalPipe):
        self.pipe = pipe
        self.protocol: Optional[StreamingProtocol] = None

    def buildProtocol(self, addr: Any) -> StreamingProtocol:
        """Build protocol and register with pipe."""
        self.protocol = StreamingProtocol(
            on_data=self.pipe._on_data,
            on_connection_made=lambda: None,
            on_connection_lost=self.pipe._on_connection_lost,
        )
        self.pipe._protocol = self.protocol
        return self.protocol
