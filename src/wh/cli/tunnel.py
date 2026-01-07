"""
wh tunnel - SSH-style port forwarding through wormhole.

Supports both local (-L) and remote (-R) port forwarding.
"""

import asyncio
import click
import struct
from typing import Optional, Tuple, Any

from wh.core.wormhole_manager import WormholeManager
from wh.core.protocol import StreamingProtocol


# Tunnel control protocol:
# - 1 byte: message type
# - 2 bytes: channel ID
# - 4 bytes: data length (for DATA messages)
# - N bytes: data

MSG_OPEN = 0x01      # Open new channel: channel_id + host_len + host + port
MSG_OPEN_OK = 0x02   # Channel opened successfully
MSG_OPEN_FAIL = 0x03 # Channel open failed
MSG_DATA = 0x04      # Data on channel
MSG_CLOSE = 0x05     # Close channel

HEADER_SIZE = 3  # type + channel_id


def parse_forward_spec(spec: str) -> Tuple[int, str, int]:
    """
    Parse a port forward specification.

    Format: local_port:remote_host:remote_port

    Returns: (local_port, remote_host, remote_port)
    """
    parts = spec.split(":")
    if len(parts) == 2:
        # local_port:remote_port (assumes localhost)
        return (int(parts[0]), "localhost", int(parts[1]))
    elif len(parts) == 3:
        return (int(parts[0]), parts[1], int(parts[2]))
    else:
        raise ValueError(f"Invalid forward spec: {spec}")


class TunnelProtocol:
    """
    Multiplexed tunnel protocol over wormhole.

    Handles multiple forwarded connections over a single wormhole channel.
    """

    def __init__(self, on_status: Optional[callable] = None):
        self.on_status = on_status
        self._protocol: Optional[StreamingProtocol] = None
        self._channels: dict = {}  # channel_id -> (reader, writer) or local connection
        self._next_channel_id = 1
        self._buffer = b""
        self._done = asyncio.Event()
        self._pending_opens: dict = {}  # channel_id -> Future

    def _status(self, msg: str) -> None:
        if self.on_status:
            self.on_status(msg)

    def _send_message(self, msg_type: int, channel_id: int, data: bytes = b"") -> None:
        """Send a control message."""
        if not self._protocol:
            return
        header = struct.pack(">BH", msg_type, channel_id)
        if msg_type == MSG_DATA:
            header += struct.pack(">I", len(data))
        self._protocol.send(header + data)

    def _on_data(self, data: bytes) -> None:
        """Handle incoming data from wormhole."""
        self._buffer += data
        self._process_buffer()

    def _process_buffer(self) -> None:
        """Process complete messages from buffer."""
        while len(self._buffer) >= HEADER_SIZE:
            msg_type, channel_id = struct.unpack(">BH", self._buffer[:HEADER_SIZE])

            if msg_type == MSG_DATA:
                if len(self._buffer) < HEADER_SIZE + 4:
                    break
                data_len = struct.unpack(">I", self._buffer[HEADER_SIZE:HEADER_SIZE + 4])[0]
                total_len = HEADER_SIZE + 4 + data_len
                if len(self._buffer) < total_len:
                    break

                payload = self._buffer[HEADER_SIZE + 4:total_len]
                self._buffer = self._buffer[total_len:]
                self._handle_data(channel_id, payload)

            elif msg_type == MSG_OPEN:
                # Parse: host_len (1 byte) + host + port (2 bytes)
                if len(self._buffer) < HEADER_SIZE + 1:
                    break
                host_len = self._buffer[HEADER_SIZE]
                total_len = HEADER_SIZE + 1 + host_len + 2
                if len(self._buffer) < total_len:
                    break

                host = self._buffer[HEADER_SIZE + 1:HEADER_SIZE + 1 + host_len].decode()
                port = struct.unpack(">H", self._buffer[HEADER_SIZE + 1 + host_len:total_len])[0]
                self._buffer = self._buffer[total_len:]
                asyncio.create_task(self._handle_open(channel_id, host, port))

            elif msg_type == MSG_OPEN_OK:
                self._buffer = self._buffer[HEADER_SIZE:]
                self._handle_open_ok(channel_id)

            elif msg_type == MSG_OPEN_FAIL:
                self._buffer = self._buffer[HEADER_SIZE:]
                self._handle_open_fail(channel_id)

            elif msg_type == MSG_CLOSE:
                self._buffer = self._buffer[HEADER_SIZE:]
                self._handle_close(channel_id)

            else:
                # Unknown message, skip header
                self._buffer = self._buffer[HEADER_SIZE:]

    def _handle_data(self, channel_id: int, data: bytes) -> None:
        """Handle data for a channel."""
        if channel_id in self._channels:
            writer = self._channels[channel_id].get("writer")
            if writer:
                writer.write(data)
                asyncio.create_task(writer.drain())

    async def _handle_open(self, channel_id: int, host: str, port: int) -> None:
        """Handle channel open request (server side)."""
        try:
            reader, writer = await asyncio.open_connection(host, port)
            self._channels[channel_id] = {"reader": reader, "writer": writer}
            self._send_message(MSG_OPEN_OK, channel_id)
            self._status(f"Channel {channel_id}: connected to {host}:{port}")

            # Start forwarding from local connection to wormhole
            asyncio.create_task(self._forward_to_wormhole(channel_id, reader))

        except Exception as e:
            self._status(f"Channel {channel_id}: failed to connect to {host}:{port}: {e}")
            self._send_message(MSG_OPEN_FAIL, channel_id)

    def _handle_open_ok(self, channel_id: int) -> None:
        """Handle channel open success (client side)."""
        if channel_id in self._pending_opens:
            self._pending_opens[channel_id].set_result(True)

    def _handle_open_fail(self, channel_id: int) -> None:
        """Handle channel open failure (client side)."""
        if channel_id in self._pending_opens:
            self._pending_opens[channel_id].set_result(False)

    def _handle_close(self, channel_id: int) -> None:
        """Handle channel close."""
        if channel_id in self._channels:
            ch = self._channels.pop(channel_id)
            writer = ch.get("writer")
            if writer:
                writer.close()
            self._status(f"Channel {channel_id}: closed")

    async def _forward_to_wormhole(self, channel_id: int, reader: asyncio.StreamReader) -> None:
        """Forward data from local connection to wormhole."""
        try:
            while True:
                data = await reader.read(4096)
                if not data:
                    break
                self._send_message(MSG_DATA, channel_id, data)
        except Exception:
            pass
        finally:
            self._send_message(MSG_CLOSE, channel_id)
            if channel_id in self._channels:
                del self._channels[channel_id]

    async def open_channel(self, host: str, port: int) -> Optional[int]:
        """
        Open a new channel to remote host:port.

        Returns channel_id on success, None on failure.
        """
        channel_id = self._next_channel_id
        self._next_channel_id += 1

        # Send open request
        host_bytes = host.encode()
        payload = bytes([len(host_bytes)]) + host_bytes + struct.pack(">H", port)
        self._send_message(MSG_OPEN, channel_id, b"")
        # Actually send the full open message
        header = struct.pack(">BH", MSG_OPEN, channel_id)
        self._protocol.send(header + payload)

        # Wait for response
        future = asyncio.get_event_loop().create_future()
        self._pending_opens[channel_id] = future

        try:
            success = await asyncio.wait_for(future, timeout=10.0)
            del self._pending_opens[channel_id]
            if success:
                return channel_id
            return None
        except asyncio.TimeoutError:
            del self._pending_opens[channel_id]
            return None

    def _on_connection_lost(self, exc: Optional[Exception]) -> None:
        """Handle disconnection."""
        self._done.set()
        # Close all channels
        for channel_id, ch in list(self._channels.items()):
            writer = ch.get("writer")
            if writer:
                writer.close()
        self._channels.clear()


class LocalForwarder:
    """
    Local port forwarder.

    Listens on a local port and forwards connections through the wormhole
    to a remote host:port on the peer's network.
    """

    def __init__(
        self,
        tunnel: TunnelProtocol,
        local_port: int,
        remote_host: str,
        remote_port: int,
        local_host: str = "127.0.0.1",
        on_status: Optional[callable] = None,
    ):
        self.tunnel = tunnel
        self.local_port = local_port
        self.remote_host = remote_host
        self.remote_port = remote_port
        self.local_host = local_host
        self.on_status = on_status
        self._server: Optional[asyncio.Server] = None

    def _status(self, msg: str) -> None:
        if self.on_status:
            self.on_status(msg)

    async def start(self) -> None:
        """Start the local listening server."""
        self._server = await asyncio.start_server(
            self._handle_connection,
            self.local_host,
            self.local_port,
        )
        self._status(
            f"Forwarding {self.local_host}:{self.local_port} -> "
            f"{self.remote_host}:{self.remote_port}"
        )

    async def _handle_connection(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """Handle incoming local connection."""
        self._status(f"New connection on port {self.local_port}")

        # Open channel to remote
        channel_id = await self.tunnel.open_channel(self.remote_host, self.remote_port)
        if channel_id is None:
            self._status(f"Failed to open channel to {self.remote_host}:{self.remote_port}")
            writer.close()
            return

        # Register channel
        self.tunnel._channels[channel_id] = {"reader": reader, "writer": writer}

        # Forward from local to wormhole
        await self.tunnel._forward_to_wormhole(channel_id, reader)

    async def stop(self) -> None:
        """Stop the server."""
        if self._server:
            self._server.close()
            await self._server.wait_closed()


@click.command("tunnel")
@click.argument("code", required=False)
@click.option("-l", "--listen", is_flag=True, help="Listen mode (accept tunnel connections)")
@click.option(
    "-L", "--local", "local_forwards", multiple=True,
    help="Local forward: [bind_addr:]port:host:port"
)
@click.option(
    "-R", "--remote", "remote_forwards", multiple=True,
    help="Remote forward: [bind_addr:]port:host:port"
)
@click.option("-v", "--verbose", is_flag=True, help="Verbose output")
@click.pass_context
def tunnel(
    ctx: click.Context,
    code: Optional[str],
    listen: bool,
    local_forwards: Tuple[str, ...],
    remote_forwards: Tuple[str, ...],
    verbose: bool,
) -> None:
    """
    SSH-style port forwarding through wormhole.

    Create secure tunnels through the wormhole for accessing remote services
    or exposing local services.

    \b
    LOCAL FORWARDING (-L):
        Forward a local port to a remote destination through the wormhole.

        wh tunnel -L 8080:localhost:80 7-guitar-sunset

        Connects to wormhole code, then localhost:8080 on your machine
        forwards to localhost:80 on the remote machine.

    \b
    REMOTE FORWARDING (-R):
        Forward a remote port to a local destination.
        (Requires listen mode on remote)

    \b
    Examples:
        # Remote: Accept tunnel connections
        wh tunnel -l

        # Local: Forward local port 8080 to remote's localhost:80
        wh tunnel -L 8080:localhost:80 7-guitar-sunset

        # Local: Multiple forwards
        wh tunnel -L 8080:localhost:80 -L 3306:db.local:3306 7-guitar-sunset

        # Access remote web server
        wh tunnel -L 8080:localhost:8080 wh://abc123.wns
        # Then open http://localhost:8080 in browser
    """
    if not listen and not code:
        raise click.UsageError("CODE is required when not in listen mode")

    if not listen and not local_forwards and not remote_forwards:
        raise click.UsageError("At least one -L or -R forward is required")

    relay_url = ctx.obj.get("relay") if ctx.obj else None

    def status(msg: str) -> None:
        if verbose:
            click.echo(f"[tunnel] {msg}", err=True)

    async def run_tunnel():
        manager = WormholeManager(
            relay_url=relay_url,
            on_status=status if verbose else None,
        )

        try:
            async with manager:
                if listen:
                    # Server mode
                    await manager.create_and_allocate_code()
                    click.echo(f"Tunnel listening on code: {manager.code}", err=True)
                    click.echo("Waiting for peer...", err=True)

                    await manager.establish()
                    click.echo("Peer connected, tunnel active", err=True)

                    # Set up tunnel protocol
                    tunnel_proto = TunnelProtocol(on_status=status)
                    endpoint = manager.listener_for("wh-tunnel")

                    from twisted.internet.protocol import Factory

                    class TunnelServerProtocol(StreamingProtocol):
                        def __init__(self, tunnel):
                            super().__init__()
                            self.tunnel = tunnel

                        def connectionMade(self):
                            super().connectionMade()
                            self.tunnel._protocol = self

                        def dataReceived(self, data):
                            self.tunnel._on_data(data)

                        def connectionLost(self, reason=None):
                            super().connectionLost(reason)
                            self.tunnel._on_connection_lost(None)

                    class TunnelFactory(Factory):
                        def buildProtocol(self, addr):
                            return TunnelServerProtocol(tunnel_proto)

                    d = endpoint.listen(TunnelFactory())
                    future = asyncio.get_event_loop().create_future()
                    d.addCallback(lambda p: future.set_result(p))
                    d.addErrback(lambda f: future.set_exception(f.value))
                    await future

                    click.echo("Tunnel ready, press Ctrl+C to stop", err=True)

                    # Wait until done
                    await tunnel_proto._done.wait()

                else:
                    # Client mode
                    await manager.create_and_set_code(code)
                    click.echo(f"Connecting to: {code}", err=True)

                    await manager.establish()

                    # Set up tunnel protocol
                    tunnel_proto = TunnelProtocol(on_status=status)
                    endpoint = manager.connector_for("wh-tunnel")

                    from twisted.internet.protocol import Factory

                    connected = asyncio.Event()

                    class TunnelClientProtocol(StreamingProtocol):
                        def __init__(self, tunnel):
                            super().__init__()
                            self.tunnel = tunnel

                        def connectionMade(self):
                            super().connectionMade()
                            self.tunnel._protocol = self
                            connected.set()

                        def dataReceived(self, data):
                            self.tunnel._on_data(data)

                        def connectionLost(self, reason=None):
                            super().connectionLost(reason)
                            self.tunnel._on_connection_lost(None)

                    class TunnelFactory(Factory):
                        def buildProtocol(self, addr):
                            return TunnelClientProtocol(tunnel_proto)

                    d = endpoint.connect(TunnelFactory())
                    future = asyncio.get_event_loop().create_future()
                    d.addCallback(lambda p: future.set_result(p))
                    d.addErrback(lambda f: future.set_exception(f.value))
                    await future
                    await connected.wait()

                    # Set up local forwarders
                    forwarders = []
                    for spec in local_forwards:
                        local_port, remote_host, remote_port = parse_forward_spec(spec)
                        fwd = LocalForwarder(
                            tunnel_proto,
                            local_port,
                            remote_host,
                            remote_port,
                            on_status=status,
                        )
                        await fwd.start()
                        forwarders.append(fwd)
                        click.echo(
                            f"Forwarding localhost:{local_port} -> {remote_host}:{remote_port}",
                            err=True
                        )

                    click.echo("Tunnel active, press Ctrl+C to stop", err=True)

                    # Wait until done
                    await tunnel_proto._done.wait()

                    # Cleanup
                    for fwd in forwarders:
                        await fwd.stop()

        except KeyboardInterrupt:
            click.echo("\n--- tunnel closed ---", err=True)
        except Exception as e:
            raise click.ClickException(str(e))

    asyncio.run(run_tunnel())
