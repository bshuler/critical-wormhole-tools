"""
PortForwarder - Forward wormhole connections to local ports.

Used by `wh listen -p PORT` to forward incoming wormhole connections
to a local TCP port.
"""

from typing import Any, Optional
import asyncio

from wh.core.protocol import StreamingProtocol


class PortForwarder:
    """
    Forwards wormhole connections to a local port.

    Example:
        manager = WormholeManager()
        code = await manager.create_and_allocate_code()
        await manager.dilate()

        forwarder = PortForwarder(manager, local_port=8080)
        await forwarder.run()
        # Now connections to the wormhole code forward to localhost:8080
    """

    def __init__(
        self,
        wormhole_manager: Any,
        local_port: int,
        local_host: str = "127.0.0.1",
    ):
        """
        Initialize port forwarder.

        Args:
            wormhole_manager: A dilated WormholeManager instance.
            local_port: Local port to forward to.
            local_host: Local host to forward to.
        """
        self.manager = wormhole_manager
        self.local_port = local_port
        self.local_host = local_host

    async def run(self) -> None:
        """
        Start accepting and forwarding connections.
        """
        endpoint = self.manager.listener_for("wh-forward")

        from twisted.internet.protocol import Factory

        forwarder = self

        class ForwarderProtocol(StreamingProtocol):
            """Protocol that forwards data to local port."""

            def __init__(self):
                super().__init__()
                self._local_writer: Optional[asyncio.StreamWriter] = None
                self._local_reader: Optional[asyncio.StreamReader] = None
                self._forward_task: Optional[asyncio.Task] = None

            def connectionMade(self) -> None:
                super().connectionMade()
                asyncio.ensure_future(self._connect_local())

            async def _connect_local(self) -> None:
                """Connect to local port and start forwarding."""
                try:
                    self._local_reader, self._local_writer = await asyncio.open_connection(
                        forwarder.local_host,
                        forwarder.local_port,
                    )
                    self._forward_task = asyncio.create_task(
                        self._forward_from_local()
                    )
                except Exception as e:
                    print(f"Failed to connect to local port: {e}")
                    self.close()

            async def _forward_from_local(self) -> None:
                """Forward data from local port to wormhole."""
                try:
                    while True:
                        data = await self._local_reader.read(4096)
                        if not data:
                            break
                        self.send(data)
                except Exception:
                    pass
                finally:
                    self.close()

            def dataReceived(self, data: bytes) -> None:
                """Forward data from wormhole to local port."""
                if self._local_writer:
                    self._local_writer.write(data)
                    asyncio.ensure_future(self._local_writer.drain())

            def connectionLost(self, reason: Any = None) -> None:
                super().connectionLost(reason)
                if self._local_writer:
                    self._local_writer.close()
                if self._forward_task:
                    self._forward_task.cancel()

        class ForwarderFactory(Factory):
            def buildProtocol(self, addr):
                return ForwarderProtocol()

        # Start listening
        from twisted.internet import defer

        d = endpoint.listen(ForwarderFactory())

        future = asyncio.get_event_loop().create_future()

        def callback(port):
            if not future.done():
                future.set_result(port)

        def errback(failure):
            if not future.done():
                future.set_exception(failure.value)

        d.addCallbacks(callback, errback)

        await future

        print(f"Forwarding to {self.local_host}:{self.local_port}")

        # Keep running
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            pass
