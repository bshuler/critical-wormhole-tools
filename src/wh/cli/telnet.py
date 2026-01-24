"""
wh telnet - Raw TCP connection through wormhole.

Provides telnet-like interactive connection through wormhole for debugging
and testing network services.
"""

import asyncio
import click
import sys
import struct
from typing import Optional

from wh.core.wormhole_manager import WormholeManager
from wh.core.protocol import StreamingProtocol, StreamingProtocolFactory


# Telnet protocol messages (over wormhole)
MSG_CONNECT = 0x01      # Request connection: host_len + host + port
MSG_CONNECT_OK = 0x02   # Connection successful
MSG_CONNECT_FAIL = 0x03 # Connection failed: error_len + error
MSG_DATA = 0x04         # Data: data
MSG_CLOSE = 0x05        # Close connection


class TelnetProtocol:
    """
    Protocol for raw TCP connections through wormhole.

    Provides telnet-like functionality for interactive debugging.
    """

    def __init__(
        self,
        on_status: Optional[callable] = None,
        on_data: Optional[callable] = None,
        is_server: bool = False,
    ):
        self.on_status = on_status
        self.on_data_callback = on_data
        self.is_server = is_server

        self._protocol: Optional[StreamingProtocol] = None
        self._buffer = b""
        self._done = asyncio.Event()
        self._connected = asyncio.Event()
        self._connect_result: Optional[bool] = None
        self._connect_error: Optional[str] = None

        # Server-side: connection to target
        self._target_reader: Optional[asyncio.StreamReader] = None
        self._target_writer: Optional[asyncio.StreamWriter] = None

    def _status(self, msg: str) -> None:
        if self.on_status:
            self.on_status(msg)

    def _send_message(self, msg_type: int, data: bytes = b"") -> None:
        """Send a control message."""
        if not self._protocol:
            return
        # Format: type (1) + data_len (4) + data
        header = struct.pack(">BI", msg_type, len(data))
        self._protocol.send(header + data)

    def _on_data(self, data: bytes) -> None:
        """Handle incoming data from wormhole."""
        self._buffer += data
        self._process_buffer()

    def _process_buffer(self) -> None:
        """Process complete messages from buffer."""
        while len(self._buffer) >= 5:  # Minimum message size: type + length
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
        """Handle connection request (server side)."""
        if len(payload) < 3:
            self._send_message(MSG_CONNECT_FAIL, b"Invalid request")
            return

        host_len = payload[0]
        if len(payload) < 1 + host_len + 2:
            self._send_message(MSG_CONNECT_FAIL, b"Invalid request")
            return

        host = payload[1:1 + host_len].decode()
        port = struct.unpack(">H", payload[1 + host_len:3 + host_len])[0]

        try:
            self._status(f"Connecting to {host}:{port}...")
            self._target_reader, self._target_writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=30.0
            )
            self._send_message(MSG_CONNECT_OK)
            self._status(f"Connected to {host}:{port}")

            # Start forwarding from target to wormhole
            asyncio.create_task(self._forward_from_target())

        except asyncio.TimeoutError:
            error = f"Connection to {host}:{port} timed out"
            self._status(error)
            self._send_message(MSG_CONNECT_FAIL, error.encode())
        except Exception as e:
            error = f"Connection failed: {e}"
            self._status(error)
            self._send_message(MSG_CONNECT_FAIL, str(e).encode())

    def _handle_connect_ok(self) -> None:
        """Handle connect success (client side)."""
        self._connect_result = True
        self._connected.set()

    def _handle_connect_fail(self, payload: bytes) -> None:
        """Handle connect failure (client side)."""
        self._connect_result = False
        self._connect_error = payload.decode() if payload else "Connection failed"
        self._connected.set()

    def _handle_data(self, data: bytes) -> None:
        """Handle data message."""
        if self.is_server:
            # Forward to target
            if self._target_writer:
                self._target_writer.write(data)
                asyncio.create_task(self._drain_target())
        else:
            # Pass to callback (display to user)
            if self.on_data_callback:
                self.on_data_callback(data)

    async def _drain_target(self) -> None:
        """Drain target writer."""
        try:
            if self._target_writer:
                await self._target_writer.drain()
        except Exception:
            pass

    def _handle_close(self) -> None:
        """Handle close message."""
        self._done.set()
        if self._target_writer:
            self._target_writer.close()

    async def _forward_from_target(self) -> None:
        """Forward data from target connection to wormhole."""
        try:
            while self._target_reader:
                data = await self._target_reader.read(4096)
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
        if self._target_writer:
            self._target_writer.close()

    async def connect(self, host: str, port: int) -> bool:
        """
        Request connection to host:port (client side).

        Returns True on success, False on failure.
        """
        # Send connect request
        host_bytes = host.encode()
        payload = bytes([len(host_bytes)]) + host_bytes + struct.pack(">H", port)
        self._send_message(MSG_CONNECT, payload)

        # Wait for response
        try:
            await asyncio.wait_for(self._connected.wait(), timeout=35.0)
            return self._connect_result
        except asyncio.TimeoutError:
            self._connect_error = "Connection request timed out"
            return False

    def send_data(self, data: bytes) -> None:
        """Send data to remote (client side)."""
        self._send_message(MSG_DATA, data)

    def close(self) -> None:
        """Close the connection."""
        self._send_message(MSG_CLOSE)
        self._done.set()

    async def run_server(self, manager: WormholeManager) -> None:
        """
        Run as telnet server (responder).

        Accepts connection requests and forwards traffic to target hosts.
        """
        endpoint = manager.listener_for("wh-telnet")

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
        self._status("Waiting for client connection...")

        await connected.wait()
        self._status("Client connected, ready to accept connections")

        # Wait until done
        await self._done.wait()

    async def run_client(self, manager: WormholeManager, host: str, port: int) -> bool:
        """
        Run as telnet client (initiator).

        Connects to the specified host:port through the wormhole peer.
        Returns True if connection was established.
        """
        endpoint = manager.connector_for("wh-telnet")

        connected = asyncio.Event()

        def on_connected():
            self._protocol._connected = True
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

        self._status(f"Connecting to {host}:{port}...")
        return await self.connect(host, port)


@click.command("telnet")
@click.argument("target", required=False)
@click.argument("port", type=int, required=False)
@click.option("-l", "--listen", is_flag=True, help="Listen mode (accept telnet connections)")
@click.option("-c", "--code", default=None, help="Wormhole code to connect with")
@click.option("-e", "--escape", default="]", help="Escape character (default: ])")
@click.option("-v", "--verbose", is_flag=True, help="Verbose output")
@click.pass_context
def telnet(
    ctx: click.Context,
    target: Optional[str],
    port: Optional[int],
    listen: bool,
    code: Optional[str],
    escape: str,
    verbose: bool,
) -> None:
    """
    Raw TCP connection through wormhole.

    Provides telnet-like interactive connection for debugging and testing
    network services through a wormhole tunnel.

    In listen mode, accepts connection requests from the peer and forwards
    them to the specified host:port.

    In client mode, connects through the peer to the specified host:port.

    \b
    Examples:
        # Remote: Accept telnet connections
        wh telnet -l

        # Local: Connect to remote service through wormhole
        wh telnet -c 7-guitar-sunset example.com 80

        # Test HTTP manually
        wh telnet -c 7-guitar-sunset example.com 80
        GET / HTTP/1.1
        Host: example.com
        [press Enter twice]

        # Connect to WNS address
        wh telnet -c wh://abc123.wns localhost 22
    """
    if listen:
        # Server mode
        pass
    elif not code:
        raise click.UsageError("CODE is required when not in listen mode (use -c/--code)")
    elif not target or port is None:
        raise click.UsageError("HOST and PORT are required when not in listen mode")

    relay_url = ctx.obj.get("relay") if ctx.obj else None
    transit_relay = ctx.obj.get("transit") if ctx.obj else None
    code_length = ctx.obj.get("code_length", 2) if ctx.obj else 2

    def status(msg: str) -> None:
        if verbose:
            click.echo(f"[telnet] {msg}", err=True)

    async def run_telnet():
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
                    click.echo(f"Telnet gateway listening on code: {manager.code}", err=True)
                    click.echo("Waiting for peer...", err=True)

                    await manager.dilate()
                    click.echo("Peer connected", err=True)

                    telnet_proto = TelnetProtocol(
                        on_status=status,
                        is_server=True,
                    )
                    await telnet_proto.run_server(manager)

                else:
                    # Client mode
                    await manager.create_and_set_code(code)
                    if verbose:
                        click.echo(f"Connecting to: {code}", err=True)

                    await manager.dilate()

                    def on_data(data: bytes) -> None:
                        # Write received data to stdout
                        sys.stdout.buffer.write(data)
                        sys.stdout.buffer.flush()

                    telnet_proto = TelnetProtocol(
                        on_status=status,
                        on_data=on_data,
                        is_server=False,
                    )

                    if not await telnet_proto.run_client(manager, target, port):
                        raise click.ClickException(
                            f"Connection failed: {telnet_proto._connect_error}"
                        )

                    click.echo(f"Connected to {target}:{port}", err=True)
                    click.echo(f"Escape character is 'Ctrl+{escape}'", err=True)
                    click.echo("", err=True)

                    # Interactive mode: read from stdin, send to remote
                    escape_char = ord(escape.upper()) - ord('A') + 1  # Ctrl+char

                    async def read_stdin():
                        loop = asyncio.get_event_loop()
                        while not telnet_proto._done.is_set():
                            try:
                                # Read in non-blocking way
                                data = await loop.run_in_executor(
                                    None,
                                    lambda: sys.stdin.buffer.read(1)
                                )
                                if not data:
                                    break

                                # Check for escape character
                                if len(data) == 1 and data[0] == escape_char:
                                    click.echo("\nConnection closed.", err=True)
                                    telnet_proto.close()
                                    break

                                telnet_proto.send_data(data)
                            except Exception:
                                break

                    # Run stdin reader and wait for done
                    stdin_task = asyncio.create_task(read_stdin())
                    done_task = asyncio.create_task(telnet_proto._done.wait())

                    await asyncio.wait(
                        [stdin_task, done_task],
                        return_when=asyncio.FIRST_COMPLETED
                    )

                    # Clean up
                    stdin_task.cancel()
                    try:
                        await stdin_task
                    except asyncio.CancelledError:
                        pass

        except KeyboardInterrupt:
            click.echo("\n--- telnet closed ---", err=True)
        except Exception as e:
            raise click.ClickException(str(e))

    asyncio.run(run_telnet())
