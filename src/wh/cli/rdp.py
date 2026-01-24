"""
wh rdp - Windows Remote Desktop through wormhole.

Provides RDP tunneling for Windows remote desktop access through wormhole.
"""

import asyncio
import click
import struct
from typing import Optional

from wh.core.wormhole_manager import WormholeManager
from wh.core.protocol import StreamingProtocol, StreamingProtocolFactory


# RDP protocol messages (for tunneling)
MSG_CONNECT = 0x01
MSG_CONNECT_OK = 0x02
MSG_CONNECT_FAIL = 0x03
MSG_DATA = 0x04
MSG_CLOSE = 0x05


# Default RDP port
DEFAULT_RDP_PORT = 3389


class RDPProtocol:
    """
    RDP tunneling protocol over wormhole.

    Provides RDP connection tunneling for Windows remote desktop access.
    """

    def __init__(
        self,
        on_status: Optional[callable] = None,
        is_server: bool = False,
        rdp_host: str = "localhost",
        rdp_port: int = DEFAULT_RDP_PORT,
    ):
        self.on_status = on_status
        self.is_server = is_server
        self.rdp_host = rdp_host
        self.rdp_port = rdp_port

        self._protocol: Optional[StreamingProtocol] = None
        self._buffer = b""
        self._done = asyncio.Event()
        self._connected = asyncio.Event()
        self._rdp_connected = asyncio.Event()

        # RDP connection
        self._rdp_reader: Optional[asyncio.StreamReader] = None
        self._rdp_writer: Optional[asyncio.StreamWriter] = None

        # Local listener for client mode
        self._local_server: Optional[asyncio.Server] = None
        self._local_port: int = 0

    def _status(self, msg: str) -> None:
        if self.on_status:
            self.on_status(msg)

    def _send_message(self, msg_type: int, data: bytes = b"") -> None:
        """Send a message."""
        if not self._protocol:
            return
        header = struct.pack(">BI", msg_type, len(data))
        self._protocol.send(header + data)

    def _on_data(self, data: bytes) -> None:
        """Handle incoming data."""
        self._buffer += data
        self._process_buffer()

    def _process_buffer(self) -> None:
        """Process complete messages."""
        while len(self._buffer) >= 5:
            msg_type, data_len = struct.unpack(">BI", self._buffer[:5])

            if len(self._buffer) < 5 + data_len:
                break

            payload = self._buffer[5:5 + data_len]
            self._buffer = self._buffer[5 + data_len:]

            if msg_type == MSG_CONNECT:
                asyncio.create_task(self._handle_connect(payload))
            elif msg_type == MSG_CONNECT_OK:
                self._handle_connect_ok()
            elif msg_type == MSG_CONNECT_FAIL:
                self._handle_connect_fail(payload)
            elif msg_type == MSG_DATA:
                self._handle_data(payload)
            elif msg_type == MSG_CLOSE:
                self._handle_close()

    async def _handle_connect(self, payload: bytes) -> None:
        """Handle connect request (server side)."""
        # Connect to local RDP server
        try:
            self._status(f"Connecting to RDP server at {self.rdp_host}:{self.rdp_port}...")
            self._rdp_reader, self._rdp_writer = await asyncio.wait_for(
                asyncio.open_connection(self.rdp_host, self.rdp_port),
                timeout=10.0
            )
            self._send_message(MSG_CONNECT_OK)
            self._status("Connected to RDP server")
            self._rdp_connected.set()

            # Start forwarding from RDP to wormhole
            asyncio.create_task(self._forward_from_rdp())

        except asyncio.TimeoutError:
            error = "Connection to RDP server timed out"
            self._status(error)
            self._send_message(MSG_CONNECT_FAIL, error.encode())
        except ConnectionRefusedError:
            error = f"RDP server refused connection on port {self.rdp_port}"
            self._status(error)
            self._send_message(MSG_CONNECT_FAIL, error.encode())
        except Exception as e:
            error = f"RDP connection failed: {e}"
            self._status(error)
            self._send_message(MSG_CONNECT_FAIL, str(e).encode())

    def _handle_connect_ok(self) -> None:
        """Handle connect success (client side)."""
        self._rdp_connected.set()

    def _handle_connect_fail(self, payload: bytes) -> None:
        """Handle connect failure (client side)."""
        error = payload.decode() if payload else "Connection failed"
        self._status(f"RDP connection failed: {error}")
        self._done.set()

    def _handle_data(self, data: bytes) -> None:
        """Handle data message."""
        if self.is_server:
            # Forward to RDP server
            if self._rdp_writer:
                self._rdp_writer.write(data)
                asyncio.create_task(self._drain_rdp())
        else:
            # Forward to local client
            if self._rdp_writer:
                self._rdp_writer.write(data)
                asyncio.create_task(self._drain_rdp())

    async def _drain_rdp(self) -> None:
        """Drain RDP writer."""
        try:
            if self._rdp_writer:
                await self._rdp_writer.drain()
        except Exception:
            pass

    def _handle_close(self) -> None:
        """Handle close message."""
        self._done.set()
        if self._rdp_writer:
            self._rdp_writer.close()

    async def _forward_from_rdp(self) -> None:
        """Forward data from RDP server to wormhole."""
        try:
            while self._rdp_reader and not self._done.is_set():
                data = await self._rdp_reader.read(8192)
                if not data:
                    break
                self._send_message(MSG_DATA, data)
        except Exception:
            pass
        finally:
            self._send_message(MSG_CLOSE)
            self._done.set()

    def _on_connection_lost(self, exc: Optional[Exception]) -> None:
        """Handle wormhole disconnection."""
        self._done.set()
        if self._rdp_writer:
            self._rdp_writer.close()

    async def _handle_local_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """Handle local RDP client connection."""
        self._rdp_reader = reader
        self._rdp_writer = writer

        # Request connection to remote RDP server
        self._send_message(MSG_CONNECT)

        # Wait for connection confirmation
        try:
            await asyncio.wait_for(self._rdp_connected.wait(), timeout=15.0)
        except asyncio.TimeoutError:
            self._status("RDP connection timed out")
            writer.close()
            return

        self._status("RDP tunnel established")

        # Forward from local client to wormhole
        try:
            while not self._done.is_set():
                data = await reader.read(8192)
                if not data:
                    break
                self._send_message(MSG_DATA, data)
        except Exception:
            pass
        finally:
            self._send_message(MSG_CLOSE)
            writer.close()

    async def run_server(self, manager: WormholeManager) -> None:
        """Run as RDP tunnel server."""
        endpoint = manager.listener_for("wh-rdp")

        connected = asyncio.Event()

        def on_connected():
            connected.set()

        factory = StreamingProtocolFactory(
            on_data=self._on_data,
            on_connection_made=on_connected,
            on_connection_lost=self._on_connection_lost,
        )

        d = endpoint.listen(factory)
        future = asyncio.get_event_loop().create_future()

        def callback(port):
            future.set_result(port)

        def errback(failure):
            future.set_exception(failure.value)

        d.addCallbacks(callback, errback)

        await future
        self._status(f"RDP tunnel ready, will forward to {self.rdp_host}:{self.rdp_port}")

        await connected.wait()
        self._status("Client connected")

        await self._done.wait()

    async def run_client(self, manager: WormholeManager, local_port: int = 13389) -> int:
        """
        Run as RDP tunnel client.

        Returns the local port to connect to.
        """
        endpoint = manager.connector_for("wh-rdp")

        connected = asyncio.Event()

        def on_connected():
            connected.set()

        factory = StreamingProtocolFactory(
            on_data=self._on_data,
            on_connection_made=on_connected,
            on_connection_lost=self._on_connection_lost,
        )

        d = endpoint.connect(factory)
        future = asyncio.get_event_loop().create_future()

        def callback(protocol):
            self._protocol = protocol
            future.set_result(protocol)

        def errback(failure):
            future.set_exception(failure.value)

        d.addCallbacks(callback, errback)

        await future
        await connected.wait()

        # Start local server for RDP client to connect to
        self._local_server = await asyncio.start_server(
            self._handle_local_client,
            "127.0.0.1",
            local_port,
        )
        self._local_port = local_port

        return local_port


@click.command("rdp")
@click.argument("target", required=False)
@click.option("-l", "--listen", is_flag=True, help="Listen mode (run RDP tunnel server)")
@click.option("-c", "--code", default=None, help="Wormhole code to connect with")
@click.option("-H", "--rdp-host", default="localhost", help="RDP server host (server mode, default: localhost)")
@click.option("-P", "--rdp-port", default=DEFAULT_RDP_PORT, type=int, help="RDP server port (server mode, default: 3389)")
@click.option("-p", "--local-port", default=13389, type=int, help="Local port to listen on (client mode, default: 13389)")
@click.option("-v", "--verbose", is_flag=True, help="Verbose output")
@click.pass_context
def rdp(
    ctx: click.Context,
    target: Optional[str],
    listen: bool,
    code: Optional[str],
    rdp_host: str,
    rdp_port: int,
    local_port: int,
    verbose: bool,
) -> None:
    """
    Windows Remote Desktop through wormhole.

    Tunnels RDP connections through wormhole for secure Windows remote desktop access.
    The server side connects to a Windows machine's RDP service, and the client side
    provides a local port for RDP clients to connect to.

    \b
    Examples:
        # Remote (on Windows machine or nearby): Start RDP tunnel
        wh rdp -l

        # Remote: Forward to a different Windows machine
        wh rdp -l -H 192.168.1.100

        # Local: Connect and start tunnel
        wh rdp -c 7-guitar-sunset

        # Local: Then connect your RDP client to localhost:13389
        # Windows: mstsc /v:localhost:13389
        # macOS: Microsoft Remote Desktop -> Add PC -> localhost:13389
        # Linux: rdesktop localhost:13389

        # Local: With custom local port
        wh rdp -c CODE -p 23389

        # Connect to WNS address
        wh rdp -c wh://abc123.wns

    Note: The remote machine must have Remote Desktop enabled and
    the Windows Firewall configured to allow RDP connections (port 3389).
    """
    if listen:
        pass
    elif not code and not target:
        raise click.UsageError("CODE is required when not in listen mode (use -c/--code)")

    # Allow target as code for backwards compatibility
    if not code and target:
        code = target

    relay_url = ctx.obj.get("relay") if ctx.obj else None
    transit_relay = ctx.obj.get("transit") if ctx.obj else None
    code_length = ctx.obj.get("code_length", 2) if ctx.obj else 2

    def status(msg: str) -> None:
        if verbose:
            click.echo(f"[rdp] {msg}", err=True)

    async def run_rdp():
        manager = WormholeManager(
            relay_url=relay_url,
            transit_relay=transit_relay,
            code_length=code_length,
            on_status=status if verbose else None,
        )

        try:
            async with manager:
                if listen:
                    # Server mode
                    await manager.create_and_allocate_code()
                    click.echo(f"RDP tunnel listening on code: {manager.code}", err=True)
                    click.echo(f"Will forward to RDP server at {rdp_host}:{rdp_port}", err=True)

                    await manager.dilate()

                    rdp_proto = RDPProtocol(
                        on_status=status,
                        is_server=True,
                        rdp_host=rdp_host,
                        rdp_port=rdp_port,
                    )
                    await rdp_proto.run_server(manager)

                else:
                    # Client mode
                    await manager.create_and_set_code(code)
                    if verbose:
                        click.echo(f"Connecting to: {code}", err=True)

                    await manager.dilate()

                    rdp_proto = RDPProtocol(
                        on_status=status,
                        is_server=False,
                    )
                    actual_port = await rdp_proto.run_client(manager, local_port)

                    click.echo("RDP tunnel ready!", err=True)
                    click.echo(f"Connect your RDP client to: localhost:{actual_port}", err=True)
                    click.echo("", err=True)
                    click.echo("Example commands:", err=True)
                    click.echo(f"  Windows:  mstsc /v:localhost:{actual_port}", err=True)
                    click.echo(f"  macOS:    open rdp://localhost:{actual_port}", err=True)
                    click.echo(f"  Linux:    rdesktop localhost:{actual_port}", err=True)
                    click.echo(f"            xfreerdp /v:localhost:{actual_port}", err=True)
                    click.echo("", err=True)
                    click.echo("Press Ctrl+C to stop the tunnel", err=True)

                    await rdp_proto._done.wait()

        except KeyboardInterrupt:
            click.echo("\n--- RDP tunnel closed ---", err=True)
        except Exception as e:
            raise click.ClickException(str(e))

    asyncio.run(run_rdp())
