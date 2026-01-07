"""
WormholeTunnel - AsyncSSH tunnel adapter for wormhole connections.

Routes SSH traffic through wormhole dilation subchannels.
"""

from typing import Any, Optional, Tuple, Callable
import asyncio
import socket


class WormholeTunnel:
    """
    AsyncSSH tunnel adapter for wormhole connections.

    Creates a local socket that bridges to the wormhole subchannel,
    allowing asyncssh to connect through normal TCP.
    """

    def __init__(self, wormhole_manager: Any):
        """Initialize tunnel with a dilated WormholeManager."""
        self._manager = wormhole_manager
        self._loop = asyncio.get_event_loop()

    async def create_connection(
        self,
        protocol_factory: Callable[[], Any],
        host: str,
        port: int,
    ) -> Tuple[Any, Any]:
        """
        Create a connection through the wormhole tunnel.

        Called by asyncssh.connect() when tunnel= is specified.
        """
        if not self._manager.is_dilated:
            raise RuntimeError("Wormhole must be dilated before creating tunnel")

        # Create socket pair for local bridging
        local_sock, remote_sock = socket.socketpair()
        local_sock.setblocking(False)
        remote_sock.setblocking(False)

        # Connect to peer via wormhole and bridge to the socket pair
        await self._connect_wormhole_bridge(remote_sock)

        # Create the SSH protocol
        protocol = protocol_factory()

        # Create asyncio transport using the local end of socket pair
        transport, _ = await self._loop.create_connection(
            lambda: _BridgeProtocol(protocol),
            sock=local_sock,
        )

        return transport, protocol

    async def _connect_wormhole_bridge(self, local_sock: socket.socket) -> None:
        """Connect to peer via wormhole and bridge data to local socket."""
        endpoint = self._manager.connector_for("wh-ssh")

        from twisted.internet.protocol import Factory, Protocol

        loop = self._loop
        connected = asyncio.Event()

        class BridgeProtocol(Protocol):
            """Bridge wormhole subchannel to local socket."""

            def __init__(self):
                self._local_sock = local_sock
                self._reader_task = None

            def connectionMade(self):
                # Start reading from local socket and forwarding to wormhole
                self._reader_task = asyncio.ensure_future(self._forward_local_to_wormhole())
                connected.set()

            def dataReceived(self, data: bytes):
                """Forward data from wormhole to local socket."""
                try:
                    self._local_sock.send(data)
                except BlockingIOError:
                    pass  # Socket buffer full
                except Exception:
                    pass

            async def _forward_local_to_wormhole(self):
                """Forward data from local socket to wormhole."""
                try:
                    while True:
                        data = await loop.sock_recv(self._local_sock, 65536)
                        if not data:
                            break
                        self.transport.write(data)
                except Exception:
                    pass

            def connectionLost(self, reason=None):
                if self._reader_task:
                    self._reader_task.cancel()
                try:
                    self._local_sock.close()
                except:
                    pass

        class BridgeFactory(Factory):
            def buildProtocol(self, addr):
                return BridgeProtocol()

        # Connect to peer
        d = endpoint.connect(BridgeFactory())

        future = loop.create_future()
        d.addCallback(lambda p: future.set_result(p) if not future.done() else None)
        d.addErrback(lambda f: future.set_exception(f.value) if not future.done() else None)

        await future
        await connected.wait()


class _BridgeProtocol(asyncio.Protocol):
    """Asyncio protocol that forwards to the SSH protocol."""

    def __init__(self, target_protocol: Any):
        self._target = target_protocol
        self._transport = None

    def connection_made(self, transport: Any) -> None:
        self._transport = transport
        self._target.connection_made(transport)

    def data_received(self, data: bytes) -> None:
        self._target.data_received(data)

    def eof_received(self) -> Optional[bool]:
        if hasattr(self._target, 'eof_received'):
            return self._target.eof_received()
        return False

    def connection_lost(self, exc: Optional[Exception]) -> None:
        self._target.connection_lost(exc)
