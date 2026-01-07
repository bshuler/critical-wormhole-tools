"""
wh ping - Measure round-trip latency through wormhole connection.

Similar to traditional ping, but measures latency through the wormhole tunnel.
"""

import asyncio
import click
import struct
import time
import statistics
from typing import Optional, List

from wh.core.wormhole_manager import WormholeManager
from wh.core.protocol import StreamingProtocol, StreamingProtocolFactory


# Ping packet format:
# - 1 byte: type (0x01 = request, 0x02 = reply)
# - 2 bytes: sequence number (big-endian)
# - 8 bytes: timestamp (double, seconds since epoch)
# - N bytes: padding
PING_REQUEST = 0x01
PING_REPLY = 0x02
PING_HEADER_SIZE = 11  # 1 + 2 + 8


class PingProtocol:
    """
    Protocol for ping/pong latency measurement.

    Sends timestamped packets and measures round-trip time when replies arrive.
    """

    def __init__(
        self,
        count: int = 4,
        interval: float = 1.0,
        timeout: float = 5.0,
        size: int = 64,
        on_status: Optional[callable] = None,
        is_server: bool = False,
    ):
        self.count = count
        self.interval = interval
        self.timeout = timeout
        self.size = size  # Total packet size including header
        self.on_status = on_status
        self.is_server = is_server

        self._protocol: Optional[StreamingProtocol] = None
        self._seq = 0
        self._pending: dict = {}  # seq -> send_time
        self._rtts: List[float] = []
        self._sent = 0
        self._received = 0
        self._done = asyncio.Event()
        self._buffer = b""

    def _status(self, msg: str) -> None:
        if self.on_status:
            self.on_status(msg)

    def _make_packet(self, ptype: int, seq: int, timestamp: float) -> bytes:
        """Create a ping packet."""
        header = struct.pack(">BHd", ptype, seq, timestamp)
        padding_size = max(0, self.size - PING_HEADER_SIZE)
        padding = b"\x00" * padding_size
        return header + padding

    def _parse_packet(self, data: bytes) -> Optional[tuple]:
        """Parse a ping packet. Returns (type, seq, timestamp) or None."""
        if len(data) < PING_HEADER_SIZE:
            return None
        ptype, seq, timestamp = struct.unpack(">BHd", data[:PING_HEADER_SIZE])
        return (ptype, seq, timestamp)

    def _on_data(self, data: bytes) -> None:
        """Handle incoming data."""
        self._buffer += data

        # Process complete packets
        while len(self._buffer) >= self.size:
            packet = self._buffer[:self.size]
            self._buffer = self._buffer[self.size:]

            parsed = self._parse_packet(packet)
            if not parsed:
                continue

            ptype, seq, timestamp = parsed

            if self.is_server:
                # Server: reply to requests
                if ptype == PING_REQUEST:
                    reply = self._make_packet(PING_REPLY, seq, timestamp)
                    if self._protocol:
                        self._protocol.send(reply)
            else:
                # Client: process replies
                if ptype == PING_REPLY:
                    recv_time = time.time()
                    if seq in self._pending:
                        send_time = self._pending.pop(seq)
                        rtt = (recv_time - send_time) * 1000  # Convert to ms
                        self._rtts.append(rtt)
                        self._received += 1
                        self._status(
                            f"{self.size} bytes from peer: seq={seq} time={rtt:.2f} ms"
                        )

    def _on_connection_lost(self, exc: Optional[Exception]) -> None:
        """Handle disconnection."""
        self._done.set()

    async def run_client(self, manager: WormholeManager) -> dict:
        """
        Run as ping client (sender).

        Returns statistics dict with min/avg/max/stddev RTT.
        """
        endpoint = manager.connector_for("wh-ping")

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

        self._status(f"PING peer via wormhole: {self.size} bytes of data")

        # Send pings
        for i in range(self.count):
            if self._done.is_set():
                break

            self._seq = i
            send_time = time.time()
            self._pending[i] = send_time

            packet = self._make_packet(PING_REQUEST, i, send_time)
            self._protocol.send(packet)
            self._sent += 1

            # Wait for reply or timeout
            try:
                await asyncio.wait_for(
                    self._wait_for_reply(i),
                    timeout=self.timeout
                )
            except asyncio.TimeoutError:
                if i in self._pending:
                    del self._pending[i]
                    self._status(f"Request timeout for seq {i}")

            # Wait interval before next ping (unless last)
            if i < self.count - 1 and not self._done.is_set():
                await asyncio.sleep(self.interval)

        # Close connection
        if self._protocol:
            self._protocol.close()

        return self._get_statistics()

    async def _wait_for_reply(self, seq: int) -> None:
        """Wait for a specific reply."""
        while seq in self._pending and not self._done.is_set():
            await asyncio.sleep(0.01)

    def _get_statistics(self) -> dict:
        """Calculate and return statistics."""
        stats = {
            "transmitted": self._sent,
            "received": self._received,
            "loss_percent": 0.0,
            "min_ms": 0.0,
            "avg_ms": 0.0,
            "max_ms": 0.0,
            "stddev_ms": 0.0,
        }

        if self._sent > 0:
            stats["loss_percent"] = ((self._sent - self._received) / self._sent) * 100

        if self._rtts:
            stats["min_ms"] = min(self._rtts)
            stats["max_ms"] = max(self._rtts)
            stats["avg_ms"] = statistics.mean(self._rtts)
            if len(self._rtts) > 1:
                stats["stddev_ms"] = statistics.stdev(self._rtts)

        return stats

    async def run_server(self, manager: WormholeManager) -> None:
        """
        Run as ping server (responder).

        Simply echoes back ping requests as replies.
        """
        endpoint = manager.listener_for("wh-ping")

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
        self._status("Listening for ping requests...")

        await connected.wait()
        self._status("Peer connected, responding to pings")

        # Wait until connection is lost
        await self._done.wait()


@click.command("ping")
@click.argument("code", required=False)
@click.option("-l", "--listen", is_flag=True, help="Listen mode (respond to pings)")
@click.option("-c", "--count", default=4, help="Number of pings to send (default: 4)")
@click.option("-i", "--interval", default=1.0, help="Interval between pings in seconds (default: 1)")
@click.option("-W", "--timeout", default=5.0, help="Timeout for each ping in seconds (default: 5)")
@click.option("-s", "--size", default=64, help="Packet size in bytes (default: 64)")
@click.option("-v", "--verbose", is_flag=True, help="Verbose output")
@click.pass_context
def ping(
    ctx: click.Context,
    code: Optional[str],
    listen: bool,
    count: int,
    interval: float,
    timeout: float,
    size: int,
    verbose: bool,
) -> None:
    """
    Measure round-trip latency through wormhole.

    Similar to traditional ping, but measures latency through the wormhole tunnel
    including connection establishment, encryption, and relay overhead.

    \b
    Examples:
        # Listen for pings (responder)
        wh ping -l

        # Ping a peer
        wh ping 7-guitar-sunset

        # Ping with 10 packets, 0.5s interval
        wh ping -c 10 -i 0.5 7-guitar-sunset

        # Ping a WNS address
        wh ping wh://abc123.wns
    """
    if not listen and not code:
        raise click.UsageError("CODE is required when not in listen mode")

    relay_url = ctx.obj.get("relay") if ctx.obj else None

    def status(msg: str) -> None:
        if verbose or not msg.startswith(" "):
            click.echo(msg, err=True)

    async def run_ping():
        manager = WormholeManager(
            relay_url=relay_url,
            on_status=status if verbose else None,
        )

        try:
            async with manager:
                if listen:
                    # Server mode
                    await manager.create_and_allocate_code()
                    click.echo(f"Listening on code: {manager.code}", err=True)
                    click.echo("Waiting for peer to connect...", err=True)

                    await manager.establish()

                    ping_proto = PingProtocol(
                        on_status=click.echo,
                        is_server=True,
                        size=size,
                    )
                    await ping_proto.run_server(manager)
                else:
                    # Client mode
                    await manager.create_and_set_code(code)

                    if verbose:
                        click.echo(f"Connecting to: {code}", err=True)

                    await manager.establish()

                    ping_proto = PingProtocol(
                        count=count,
                        interval=interval,
                        timeout=timeout,
                        size=size,
                        on_status=click.echo,
                        is_server=False,
                    )

                    stats = await ping_proto.run_client(manager)

                    # Print statistics
                    click.echo("")
                    click.echo(f"--- wormhole ping statistics ---")
                    click.echo(
                        f"{stats['transmitted']} packets transmitted, "
                        f"{stats['received']} received, "
                        f"{stats['loss_percent']:.1f}% packet loss"
                    )

                    if stats['received'] > 0:
                        click.echo(
                            f"rtt min/avg/max/stddev = "
                            f"{stats['min_ms']:.3f}/"
                            f"{stats['avg_ms']:.3f}/"
                            f"{stats['max_ms']:.3f}/"
                            f"{stats['stddev_ms']:.3f} ms"
                        )

        except KeyboardInterrupt:
            click.echo("\n--- interrupted ---", err=True)
        except Exception as e:
            raise click.ClickException(str(e))

    asyncio.run(run_ping())
