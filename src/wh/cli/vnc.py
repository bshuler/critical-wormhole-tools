"""
wh vnc - VNC desktop sharing through wormhole.

Provides VNC tunneling for remote desktop access through wormhole.
"""

import asyncio
import click
import struct
from typing import Optional

from wh.core.wormhole_manager import WormholeManager
from wh.core.protocol import StreamingProtocol, StreamingProtocolFactory


# VNC protocol messages (for tunneling)
MSG_CONNECT = 0x01
MSG_CONNECT_OK = 0x02
MSG_CONNECT_FAIL = 0x03
MSG_DATA = 0x04
MSG_CLOSE = 0x05


# Default VNC port
DEFAULT_VNC_PORT = 5900


class VNCProtocol:
    """
    VNC tunneling protocol over wormhole.

    Provides VNC connection tunneling for remote desktop access.
    """

    def __init__(
        self,
        on_status: Optional[callable] = None,
        is_server: bool = False,
        vnc_host: str = "localhost",
        vnc_port: int = DEFAULT_VNC_PORT,
        vnc_display: int = 0,
    ):
        self.on_status = on_status
        self.is_server = is_server
        self.vnc_host = vnc_host
        self.vnc_port = vnc_port + vnc_display
        self.vnc_display = vnc_display

        self._protocol: Optional[StreamingProtocol] = None
        self._buffer = b""
        self._done = asyncio.Event()
        self._connected = asyncio.Event()
        self._vnc_connected = asyncio.Event()

        # VNC connection
        self._vnc_reader: Optional[asyncio.StreamReader] = None
        self._vnc_writer: Optional[asyncio.StreamWriter] = None

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
        # Connect to local VNC server
        try:
            self._status(f"Connecting to VNC server at {self.vnc_host}:{self.vnc_port}...")
            self._vnc_reader, self._vnc_writer = await asyncio.wait_for(
                asyncio.open_connection(self.vnc_host, self.vnc_port),
                timeout=10.0
            )
            self._send_message(MSG_CONNECT_OK)
            self._status("Connected to VNC server")
            self._vnc_connected.set()

            # Start forwarding from VNC to wormhole
            asyncio.create_task(self._forward_from_vnc())

        except asyncio.TimeoutError:
            error = "Connection to VNC server timed out"
            self._status(error)
            self._send_message(MSG_CONNECT_FAIL, error.encode())
        except ConnectionRefusedError:
            error = f"VNC server refused connection on port {self.vnc_port}"
            self._status(error)
            self._send_message(MSG_CONNECT_FAIL, error.encode())
        except Exception as e:
            error = f"VNC connection failed: {e}"
            self._status(error)
            self._send_message(MSG_CONNECT_FAIL, str(e).encode())

    def _handle_connect_ok(self) -> None:
        """Handle connect success (client side)."""
        self._vnc_connected.set()

    def _handle_connect_fail(self, payload: bytes) -> None:
        """Handle connect failure (client side)."""
        error = payload.decode() if payload else "Connection failed"
        self._status(f"VNC connection failed: {error}")
        self._done.set()

    def _handle_data(self, data: bytes) -> None:
        """Handle data message."""
        if self.is_server:
            # Forward to VNC server
            if self._vnc_writer:
                self._vnc_writer.write(data)
                asyncio.create_task(self._drain_vnc())
        else:
            # Forward to local client
            if self._vnc_writer:
                self._vnc_writer.write(data)
                asyncio.create_task(self._drain_vnc())

    async def _drain_vnc(self) -> None:
        """Drain VNC writer."""
        try:
            if self._vnc_writer:
                await self._vnc_writer.drain()
        except Exception:
            pass

    def _handle_close(self) -> None:
        """Handle close message."""
        self._done.set()
        if self._vnc_writer:
            self._vnc_writer.close()

    async def _forward_from_vnc(self) -> None:
        """Forward data from VNC server to wormhole."""
        try:
            while self._vnc_reader and not self._done.is_set():
                data = await self._vnc_reader.read(8192)
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
        if self._vnc_writer:
            self._vnc_writer.close()

    async def _handle_local_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """Handle local VNC client connection."""
        self._vnc_reader = reader
        self._vnc_writer = writer

        # Request connection to remote VNC server
        self._send_message(MSG_CONNECT)

        # Wait for connection confirmation
        try:
            await asyncio.wait_for(self._vnc_connected.wait(), timeout=15.0)
        except asyncio.TimeoutError:
            self._status("VNC connection timed out")
            writer.close()
            return

        self._status("VNC tunnel established")

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
        """Run as VNC tunnel server."""
        endpoint = manager.listener_for("wh-vnc")

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
        self._status(f"VNC tunnel ready, will forward to {self.vnc_host}:{self.vnc_port}")

        await connected.wait()
        self._status("Client connected")

        await self._done.wait()

    async def run_client(self, manager: WormholeManager, local_port: int = 5901) -> int:
        """
        Run as VNC tunnel client.

        Returns the local port to connect to.
        """
        endpoint = manager.connector_for("wh-vnc")

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

        # Start local server for VNC client to connect to
        self._local_server = await asyncio.start_server(
            self._handle_local_client,
            "127.0.0.1",
            local_port,
        )
        self._local_port = local_port

        return local_port


@click.command("vnc")
@click.argument("target", required=False)
@click.option("-l", "--listen", is_flag=True, help="Listen mode (run VNC tunnel server)")
@click.option("-c", "--code", default=None, help="Wormhole code to connect with")
@click.option("-d", "--display", default=0, type=int, help="VNC display number (default: 0, i.e., port 5900)")
@click.option("-H", "--vnc-host", default="localhost", help="VNC server host (server mode, default: localhost)")
@click.option("-p", "--local-port", default=5901, type=int, help="Local port to listen on (client mode, default: 5901)")
@click.option("-v", "--verbose", is_flag=True, help="Verbose output")
@click.pass_context
def vnc(
    ctx: click.Context,
    target: Optional[str],
    listen: bool,
    code: Optional[str],
    display: int,
    vnc_host: str,
    local_port: int,
    verbose: bool,
) -> None:
    """
    VNC desktop sharing through wormhole.

    Tunnels VNC connections through wormhole for secure remote desktop access.
    The server side connects to a local VNC server, and the client side
    provides a local port for VNC clients to connect to.

    \b
    Examples:
        # Remote: Start VNC tunnel (assuming VNC server on :0)
        wh vnc -l

        # Remote: With specific display number
        wh vnc -l -d 1

        # Local: Connect and start tunnel
        wh vnc -c 7-guitar-sunset

        # Local: Then connect your VNC viewer to localhost:5901
        # e.g., vncviewer localhost:5901

        # Local: With custom local port
        wh vnc -c CODE -p 5902

        # Connect to WNS address
        wh vnc -c wh://abc123.wns

    Note: You need a VNC server running on the remote machine (e.g., x11vnc,
    TightVNC, TigerVNC) and a VNC client on the local machine.
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
            click.echo(f"[vnc] {msg}", err=True)

    async def run_vnc():
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
                    click.echo(f"VNC tunnel listening on code: {manager.code}", err=True)
                    click.echo(f"Will forward to VNC server at {vnc_host}:{DEFAULT_VNC_PORT + display}", err=True)

                    await manager.dilate()

                    vnc_proto = VNCProtocol(
                        on_status=status,
                        is_server=True,
                        vnc_host=vnc_host,
                        vnc_port=DEFAULT_VNC_PORT,
                        vnc_display=display,
                    )
                    await vnc_proto.run_server(manager)

                else:
                    # Client mode
                    await manager.create_and_set_code(code)
                    if verbose:
                        click.echo(f"Connecting to: {code}", err=True)

                    await manager.dilate()

                    vnc_proto = VNCProtocol(
                        on_status=status,
                        is_server=False,
                    )
                    actual_port = await vnc_proto.run_client(manager, local_port)

                    click.echo("VNC tunnel ready!", err=True)
                    click.echo(f"Connect your VNC viewer to: localhost:{actual_port}", err=True)
                    click.echo("", err=True)
                    click.echo("Example commands:", err=True)
                    click.echo(f"  vncviewer localhost:{actual_port}", err=True)
                    click.echo(f"  open vnc://localhost:{actual_port}  (macOS)", err=True)
                    click.echo("", err=True)
                    click.echo("Press Ctrl+C to stop the tunnel", err=True)

                    await vnc_proto._done.wait()

        except KeyboardInterrupt:
            click.echo("\n--- VNC tunnel closed ---", err=True)
        except Exception as e:
            raise click.ClickException(str(e))

    asyncio.run(run_vnc())
