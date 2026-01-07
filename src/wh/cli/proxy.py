"""
wh proxy - SOCKS5 proxy through wormhole.

Provides a local SOCKS5 proxy that routes traffic through the wormhole connection.
"""

import asyncio
import click
import struct
import socket
from typing import Optional, Tuple

from wh.core.wormhole_manager import WormholeManager
from wh.core.protocol import StreamingProtocol


# SOCKS5 constants
SOCKS_VERSION = 0x05

# Authentication methods
AUTH_NONE = 0x00
AUTH_NO_ACCEPTABLE = 0xFF

# Commands
CMD_CONNECT = 0x01
CMD_BIND = 0x02
CMD_UDP = 0x03

# Address types
ATYP_IPV4 = 0x01
ATYP_DOMAIN = 0x03
ATYP_IPV6 = 0x04

# Reply codes
REP_SUCCESS = 0x00
REP_GENERAL_FAILURE = 0x01
REP_NOT_ALLOWED = 0x02
REP_NETWORK_UNREACHABLE = 0x03
REP_HOST_UNREACHABLE = 0x04
REP_REFUSED = 0x05
REP_TTL_EXPIRED = 0x06
REP_CMD_NOT_SUPPORTED = 0x07
REP_ATYP_NOT_SUPPORTED = 0x08


# Proxy protocol messages (over wormhole)
MSG_CONNECT = 0x01      # Request connection: host_len + host + port
MSG_CONNECT_OK = 0x02   # Connection successful
MSG_CONNECT_FAIL = 0x03 # Connection failed
MSG_DATA = 0x04         # Data: channel_id + data_len + data
MSG_CLOSE = 0x05        # Close channel


class ProxyProtocol:
    """
    Protocol for proxying connections through wormhole.

    Handles multiple concurrent connections over a single wormhole channel.
    """

    def __init__(self, on_status: Optional[callable] = None):
        self.on_status = on_status
        self._protocol: Optional[StreamingProtocol] = None
        self._channels: dict = {}  # channel_id -> {"reader": ..., "writer": ..., "pending": Future}
        self._next_channel_id = 1
        self._buffer = b""
        self._done = asyncio.Event()

    def _status(self, msg: str) -> None:
        if self.on_status:
            self.on_status(msg)

    def _send_message(self, msg_type: int, channel_id: int, data: bytes = b"") -> None:
        """Send a control message."""
        if not self._protocol:
            return
        # Format: type (1) + channel_id (2) + data_len (4) + data
        header = struct.pack(">BHI", msg_type, channel_id, len(data))
        self._protocol.send(header + data)

    def _on_data(self, data: bytes) -> None:
        """Handle incoming data from wormhole."""
        self._buffer += data
        self._process_buffer()

    def _process_buffer(self) -> None:
        """Process complete messages from buffer."""
        while len(self._buffer) >= 7:  # Minimum message size
            msg_type, channel_id, data_len = struct.unpack(">BHI", self._buffer[:7])

            if len(self._buffer) < 7 + data_len:
                break

            payload = self._buffer[7:7 + data_len]
            self._buffer = self._buffer[7 + data_len:]

            if msg_type == MSG_CONNECT:
                asyncio.create_task(self._handle_connect(channel_id, payload))
            elif msg_type == MSG_CONNECT_OK:
                self._handle_connect_ok(channel_id)
            elif msg_type == MSG_CONNECT_FAIL:
                self._handle_connect_fail(channel_id)
            elif msg_type == MSG_DATA:
                self._handle_data(channel_id, payload)
            elif msg_type == MSG_CLOSE:
                self._handle_close(channel_id)

    async def _handle_connect(self, channel_id: int, payload: bytes) -> None:
        """Handle connection request (server side)."""
        if len(payload) < 3:
            self._send_message(MSG_CONNECT_FAIL, channel_id)
            return

        host_len = payload[0]
        if len(payload) < 1 + host_len + 2:
            self._send_message(MSG_CONNECT_FAIL, channel_id)
            return

        host = payload[1:1 + host_len].decode()
        port = struct.unpack(">H", payload[1 + host_len:3 + host_len])[0]

        try:
            self._status(f"Channel {channel_id}: connecting to {host}:{port}")
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=10.0
            )
            self._channels[channel_id] = {"reader": reader, "writer": writer}
            self._send_message(MSG_CONNECT_OK, channel_id)
            self._status(f"Channel {channel_id}: connected")

            # Start forwarding from target to wormhole
            asyncio.create_task(self._forward_from_target(channel_id, reader))

        except Exception as e:
            self._status(f"Channel {channel_id}: connect failed: {e}")
            self._send_message(MSG_CONNECT_FAIL, channel_id)

    def _handle_connect_ok(self, channel_id: int) -> None:
        """Handle connect success (client side)."""
        if channel_id in self._channels:
            pending = self._channels[channel_id].get("pending")
            if pending and not pending.done():
                pending.set_result(True)

    def _handle_connect_fail(self, channel_id: int) -> None:
        """Handle connect failure (client side)."""
        if channel_id in self._channels:
            pending = self._channels[channel_id].get("pending")
            if pending and not pending.done():
                pending.set_result(False)

    def _handle_data(self, channel_id: int, data: bytes) -> None:
        """Handle data for a channel."""
        if channel_id in self._channels:
            writer = self._channels[channel_id].get("writer")
            if writer:
                writer.write(data)
                asyncio.create_task(writer.drain())

    def _handle_close(self, channel_id: int) -> None:
        """Handle channel close."""
        if channel_id in self._channels:
            ch = self._channels.pop(channel_id)
            writer = ch.get("writer")
            if writer:
                writer.close()

    async def _forward_from_target(self, channel_id: int, reader: asyncio.StreamReader) -> None:
        """Forward data from target connection to wormhole."""
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
                ch = self._channels.pop(channel_id)
                writer = ch.get("writer")
                if writer:
                    writer.close()

    async def connect(self, host: str, port: int) -> Optional[int]:
        """
        Request connection to host:port (client side).

        Returns channel_id on success, None on failure.
        """
        channel_id = self._next_channel_id
        self._next_channel_id += 1

        pending = asyncio.get_event_loop().create_future()
        self._channels[channel_id] = {"pending": pending}

        # Send connect request
        host_bytes = host.encode()
        payload = bytes([len(host_bytes)]) + host_bytes + struct.pack(">H", port)
        self._send_message(MSG_CONNECT, channel_id, payload)

        try:
            success = await asyncio.wait_for(pending, timeout=15.0)
            if success:
                return channel_id
            else:
                del self._channels[channel_id]
                return None
        except asyncio.TimeoutError:
            if channel_id in self._channels:
                del self._channels[channel_id]
            return None

    def _on_connection_lost(self, exc: Optional[Exception]) -> None:
        """Handle disconnection."""
        self._done.set()


class Socks5Server:
    """
    Local SOCKS5 server that proxies through wormhole.
    """

    def __init__(
        self,
        proxy_proto: ProxyProtocol,
        host: str = "127.0.0.1",
        port: int = 1080,
        on_status: Optional[callable] = None,
    ):
        self.proxy_proto = proxy_proto
        self.host = host
        self.port = port
        self.on_status = on_status
        self._server: Optional[asyncio.Server] = None

    def _status(self, msg: str) -> None:
        if self.on_status:
            self.on_status(msg)

    async def start(self) -> None:
        """Start the SOCKS5 server."""
        self._server = await asyncio.start_server(
            self._handle_client,
            self.host,
            self.port,
        )
        self._status(f"SOCKS5 proxy listening on {self.host}:{self.port}")

    async def _handle_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """Handle a SOCKS5 client connection."""
        try:
            # Read greeting
            data = await asyncio.wait_for(reader.read(2), timeout=30.0)
            if len(data) < 2:
                writer.close()
                return

            version, nmethods = data[0], data[1]
            if version != SOCKS_VERSION:
                writer.close()
                return

            methods = await reader.read(nmethods)

            # Select no auth
            if AUTH_NONE in methods:
                writer.write(bytes([SOCKS_VERSION, AUTH_NONE]))
                await writer.drain()
            else:
                writer.write(bytes([SOCKS_VERSION, AUTH_NO_ACCEPTABLE]))
                await writer.drain()
                writer.close()
                return

            # Read request
            data = await asyncio.wait_for(reader.read(4), timeout=30.0)
            if len(data) < 4:
                writer.close()
                return

            version, cmd, _, atyp = data

            if cmd != CMD_CONNECT:
                # Only CONNECT supported
                writer.write(bytes([SOCKS_VERSION, REP_CMD_NOT_SUPPORTED, 0x00, ATYP_IPV4, 0, 0, 0, 0, 0, 0]))
                await writer.drain()
                writer.close()
                return

            # Parse address
            if atyp == ATYP_IPV4:
                addr_data = await reader.read(4)
                host = socket.inet_ntoa(addr_data)
            elif atyp == ATYP_DOMAIN:
                length = (await reader.read(1))[0]
                host = (await reader.read(length)).decode()
            elif atyp == ATYP_IPV6:
                addr_data = await reader.read(16)
                host = socket.inet_ntop(socket.AF_INET6, addr_data)
            else:
                writer.write(bytes([SOCKS_VERSION, REP_ATYP_NOT_SUPPORTED, 0x00, ATYP_IPV4, 0, 0, 0, 0, 0, 0]))
                await writer.drain()
                writer.close()
                return

            port_data = await reader.read(2)
            port = struct.unpack(">H", port_data)[0]

            self._status(f"SOCKS5: CONNECT {host}:{port}")

            # Connect through wormhole
            channel_id = await self.proxy_proto.connect(host, port)

            if channel_id is None:
                # Connection failed
                writer.write(bytes([SOCKS_VERSION, REP_HOST_UNREACHABLE, 0x00, ATYP_IPV4, 0, 0, 0, 0, 0, 0]))
                await writer.drain()
                writer.close()
                return

            # Success reply
            writer.write(bytes([SOCKS_VERSION, REP_SUCCESS, 0x00, ATYP_IPV4, 127, 0, 0, 1, 0, 0]))
            await writer.drain()

            # Set up bidirectional forwarding
            self.proxy_proto._channels[channel_id]["writer"] = writer
            self.proxy_proto._channels[channel_id]["reader"] = reader

            # Forward from client to wormhole
            try:
                while True:
                    data = await reader.read(4096)
                    if not data:
                        break
                    self.proxy_proto._send_message(MSG_DATA, channel_id, data)
            except Exception:
                pass
            finally:
                self.proxy_proto._send_message(MSG_CLOSE, channel_id)
                if channel_id in self.proxy_proto._channels:
                    del self.proxy_proto._channels[channel_id]
                writer.close()

        except asyncio.TimeoutError:
            writer.close()
        except Exception as e:
            self._status(f"SOCKS5 error: {e}")
            writer.close()

    async def stop(self) -> None:
        """Stop the SOCKS5 server."""
        if self._server:
            self._server.close()
            await self._server.wait_closed()


@click.command("proxy")
@click.argument("code", required=False)
@click.option("-l", "--listen", is_flag=True, help="Listen mode (accept proxy connections)")
@click.option("-p", "--port", default=1080, help="Local SOCKS5 port (default: 1080)")
@click.option("-b", "--bind", default="127.0.0.1", help="Bind address (default: 127.0.0.1)")
@click.option("-v", "--verbose", is_flag=True, help="Verbose output")
@click.pass_context
def proxy(
    ctx: click.Context,
    code: Optional[str],
    listen: bool,
    port: int,
    bind: str,
    verbose: bool,
) -> None:
    """
    SOCKS5 proxy through wormhole.

    Creates a local SOCKS5 proxy server that routes all traffic through the
    wormhole connection to the peer, who forwards it to the destination.

    \b
    Examples:
        # Remote: Accept proxy connections
        wh proxy -l

        # Local: Start SOCKS5 proxy on port 1080
        wh proxy 7-guitar-sunset

        # Local: Custom port
        wh proxy -p 8080 7-guitar-sunset

        # Configure browser to use SOCKS5 proxy at 127.0.0.1:1080

        # Use with curl
        curl --socks5 127.0.0.1:1080 https://example.com

        # Connect to WNS address
        wh proxy wh://abc123.wns
    """
    if not listen and not code:
        raise click.UsageError("CODE is required when not in listen mode")

    relay_url = ctx.obj.get("relay") if ctx.obj else None

    def status(msg: str) -> None:
        if verbose:
            click.echo(f"[proxy] {msg}", err=True)

    async def run_proxy():
        manager = WormholeManager(
            relay_url=relay_url,
            on_status=status if verbose else None,
        )

        try:
            async with manager:
                if listen:
                    # Server mode - accept proxy connections
                    await manager.create_and_allocate_code()
                    click.echo(f"Proxy listening on code: {manager.code}", err=True)
                    click.echo("Waiting for peer...", err=True)

                    await manager.establish()
                    click.echo("Peer connected, proxy active", err=True)

                    # Set up proxy protocol
                    proxy_proto = ProxyProtocol(on_status=status)
                    endpoint = manager.listener_for("wh-proxy")

                    from twisted.internet.protocol import Factory

                    class ProxyServerProtocol(StreamingProtocol):
                        def __init__(self, proto):
                            super().__init__()
                            self.proxy = proto

                        def connectionMade(self):
                            super().connectionMade()
                            self.proxy._protocol = self

                        def dataReceived(self, data):
                            self.proxy._on_data(data)

                        def connectionLost(self, reason=None):
                            super().connectionLost(reason)
                            self.proxy._on_connection_lost(None)

                    class ProxyFactory(Factory):
                        def buildProtocol(self, addr):
                            return ProxyServerProtocol(proxy_proto)

                    d = endpoint.listen(ProxyFactory())
                    future = asyncio.get_event_loop().create_future()
                    d.addCallback(lambda p: future.set_result(p))
                    d.addErrback(lambda f: future.set_exception(f.value))
                    await future

                    click.echo("Ready to proxy connections, press Ctrl+C to stop", err=True)
                    await proxy_proto._done.wait()

                else:
                    # Client mode - run local SOCKS5 server
                    await manager.create_and_set_code(code)
                    click.echo(f"Connecting to: {code}", err=True)

                    await manager.establish()

                    # Set up proxy protocol
                    proxy_proto = ProxyProtocol(on_status=status)
                    endpoint = manager.connector_for("wh-proxy")

                    from twisted.internet.protocol import Factory

                    connected = asyncio.Event()

                    class ProxyClientProtocol(StreamingProtocol):
                        def __init__(self, proto):
                            super().__init__()
                            self.proxy = proto

                        def connectionMade(self):
                            super().connectionMade()
                            self.proxy._protocol = self
                            connected.set()

                        def dataReceived(self, data):
                            self.proxy._on_data(data)

                        def connectionLost(self, reason=None):
                            super().connectionLost(reason)
                            self.proxy._on_connection_lost(None)

                    class ProxyFactory(Factory):
                        def buildProtocol(self, addr):
                            return ProxyClientProtocol(proxy_proto)

                    d = endpoint.connect(ProxyFactory())
                    future = asyncio.get_event_loop().create_future()
                    d.addCallback(lambda p: future.set_result(p))
                    d.addErrback(lambda f: future.set_exception(f.value))
                    await future
                    await connected.wait()

                    # Start SOCKS5 server
                    socks = Socks5Server(
                        proxy_proto,
                        host=bind,
                        port=port,
                        on_status=status,
                    )
                    await socks.start()

                    click.echo(f"SOCKS5 proxy running on {bind}:{port}", err=True)
                    click.echo("Press Ctrl+C to stop", err=True)

                    await proxy_proto._done.wait()
                    await socks.stop()

        except KeyboardInterrupt:
            click.echo("\n--- proxy stopped ---", err=True)
        except Exception as e:
            raise click.ClickException(str(e))

    asyncio.run(run_proxy())
