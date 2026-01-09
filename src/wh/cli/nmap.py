"""
wh nmap - Port scanning through wormhole.

Scans ports on hosts accessible through the wormhole peer.
"""

import asyncio
import click
import struct
import time
from typing import Optional, List, Dict, Set
from dataclasses import dataclass

from wh.core.wormhole_manager import WormholeManager
from wh.core.protocol import StreamingProtocol, StreamingProtocolFactory


# Nmap protocol messages
MSG_SCAN_REQUEST = 0x01    # Scan request: host + ports
MSG_SCAN_RESULT = 0x02     # Scan result: port states
MSG_SCAN_COMPLETE = 0x03   # Scan complete


# Well-known ports for service detection
COMMON_PORTS = [
    21, 22, 23, 25, 53, 80, 110, 111, 135, 139, 143, 443, 445, 993, 995,
    1723, 3306, 3389, 5432, 5900, 6379, 8080, 8443, 27017
]

SERVICE_NAMES = {
    21: "ftp",
    22: "ssh",
    23: "telnet",
    25: "smtp",
    53: "dns",
    80: "http",
    110: "pop3",
    111: "rpcbind",
    135: "msrpc",
    139: "netbios-ssn",
    143: "imap",
    443: "https",
    445: "microsoft-ds",
    993: "imaps",
    995: "pop3s",
    1723: "pptp",
    3306: "mysql",
    3389: "ms-wbt-server",
    5432: "postgresql",
    5900: "vnc",
    6379: "redis",
    8080: "http-proxy",
    8443: "https-alt",
    27017: "mongodb",
}


@dataclass
class PortResult:
    """Result of a port scan."""
    port: int
    state: str  # "open", "closed", "filtered"
    service: str = ""
    latency_ms: float = 0.0


class NmapProtocol:
    """
    Port scanning protocol over wormhole.
    """

    def __init__(
        self,
        on_status: Optional[callable] = None,
        is_server: bool = False,
        timeout: float = 3.0,
        concurrency: int = 100,
    ):
        self.on_status = on_status
        self.is_server = is_server
        self.timeout = timeout
        self.concurrency = concurrency

        self._protocol: Optional[StreamingProtocol] = None
        self._buffer = b""
        self._done = asyncio.Event()
        self._connected = asyncio.Event()

        # Results
        self._results: Dict[int, PortResult] = {}
        self._scan_complete = asyncio.Event()

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

            if msg_type == MSG_SCAN_REQUEST:
                asyncio.create_task(self._handle_scan_request(payload))
            elif msg_type == MSG_SCAN_RESULT:
                self._handle_scan_result(payload)
            elif msg_type == MSG_SCAN_COMPLETE:
                self._scan_complete.set()

    async def _handle_scan_request(self, payload: bytes) -> None:
        """Handle scan request (server side)."""
        if len(payload) < 1:
            return

        host_len = payload[0]
        if len(payload) < 1 + host_len + 4:
            return

        host = payload[1:1 + host_len].decode()
        num_ports = struct.unpack(">I", payload[1 + host_len:5 + host_len])[0]

        offset = 5 + host_len
        ports = []
        for _ in range(num_ports):
            if offset + 2 > len(payload):
                break
            port = struct.unpack(">H", payload[offset:offset + 2])[0]
            ports.append(port)
            offset += 2

        self._status(f"Scanning {host} ports {len(ports)} ports...")

        # Scan ports with concurrency limit
        semaphore = asyncio.Semaphore(self.concurrency)

        async def scan_port(port: int) -> PortResult:
            async with semaphore:
                start = time.time()
                try:
                    reader, writer = await asyncio.wait_for(
                        asyncio.open_connection(host, port),
                        timeout=self.timeout
                    )
                    latency = (time.time() - start) * 1000
                    writer.close()
                    try:
                        await writer.wait_closed()
                    except Exception:
                        pass
                    service = SERVICE_NAMES.get(port, "")
                    return PortResult(port, "open", service, latency)
                except asyncio.TimeoutError:
                    return PortResult(port, "filtered")
                except ConnectionRefusedError:
                    return PortResult(port, "closed")
                except Exception:
                    return PortResult(port, "filtered")

        tasks = [scan_port(p) for p in ports]
        results = await asyncio.gather(*tasks)

        # Send results
        for result in results:
            state_byte = {"open": 1, "closed": 2, "filtered": 3}.get(result.state, 0)
            service_bytes = result.service.encode()
            result_data = struct.pack(
                ">HBBf",
                result.port,
                state_byte,
                len(service_bytes),
                result.latency_ms
            ) + service_bytes
            self._send_message(MSG_SCAN_RESULT, result_data)

        self._send_message(MSG_SCAN_COMPLETE)
        self._status(f"Scan complete: {len(results)} ports scanned")

    def _handle_scan_result(self, payload: bytes) -> None:
        """Handle scan result (client side)."""
        if len(payload) < 6:
            return

        port, state_byte, service_len, latency = struct.unpack(">HBBf", payload[:8])
        service = payload[8:8 + service_len].decode() if service_len > 0 else ""

        state = {1: "open", 2: "closed", 3: "filtered"}.get(state_byte, "unknown")

        self._results[port] = PortResult(port, state, service, latency)

    def _on_connection_lost(self, exc: Optional[Exception]) -> None:
        """Handle disconnection."""
        self._done.set()
        self._scan_complete.set()

    async def scan(self, host: str, ports: List[int]) -> Dict[int, PortResult]:
        """
        Request port scan (client side).

        Returns dict of port -> PortResult.
        """
        self._results = {}
        self._scan_complete.clear()

        # Build request
        host_bytes = host.encode()
        payload = bytes([len(host_bytes)]) + host_bytes
        payload += struct.pack(">I", len(ports))
        for port in ports:
            payload += struct.pack(">H", port)

        self._send_message(MSG_SCAN_REQUEST, payload)

        # Wait for completion
        try:
            await asyncio.wait_for(self._scan_complete.wait(), timeout=300.0)
        except asyncio.TimeoutError:
            pass

        return self._results

    async def run_server(self, manager: WormholeManager) -> None:
        """Run as scan server."""
        endpoint = manager.listener_for("wh-nmap")

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
        self._status("Scanner ready, waiting for client...")

        await connected.wait()
        self._status("Client connected, ready to scan")

        await self._done.wait()

    async def run_client(self, manager: WormholeManager) -> "NmapProtocol":
        """Run as scan client."""
        endpoint = manager.connector_for("wh-nmap")

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

        return self


def parse_ports(port_spec: str) -> List[int]:
    """Parse port specification like '22,80,443' or '1-1024' or 'common'."""
    if port_spec.lower() == "common":
        return COMMON_PORTS.copy()

    ports: Set[int] = set()

    for part in port_spec.split(","):
        part = part.strip()
        if "-" in part:
            try:
                start, end = part.split("-", 1)
                start = int(start.strip())
                end = int(end.strip())
                for p in range(start, min(end + 1, 65536)):
                    if 1 <= p <= 65535:
                        ports.add(p)
            except ValueError:
                continue
        else:
            try:
                p = int(part)
                if 1 <= p <= 65535:
                    ports.add(p)
            except ValueError:
                continue

    return sorted(ports)


@click.command("nmap")
@click.argument("target", required=False)
@click.option("-l", "--listen", is_flag=True, help="Listen mode (run scan server)")
@click.option("-c", "--code", default=None, help="Wormhole code to connect with")
@click.option("-p", "--ports", default="common", help="Ports to scan (e.g., '22,80,443', '1-1024', or 'common')")
@click.option("-T", "--timeout", default=3.0, help="Timeout per port in seconds (default: 3)")
@click.option("--concurrency", default=100, help="Max concurrent connections (default: 100)")
@click.option("-v", "--verbose", is_flag=True, help="Verbose output")
@click.option("-oN", "--output", default=None, help="Output file")
@click.pass_context
def nmap(
    ctx: click.Context,
    target: Optional[str],
    listen: bool,
    code: Optional[str],
    ports: str,
    timeout: float,
    concurrency: int,
    verbose: bool,
    output: Optional[str],
) -> None:
    """
    Port scanning through wormhole.

    Scans ports on hosts accessible through the wormhole peer.
    The server side performs the actual scanning from its network.

    \b
    Examples:
        # Remote: Start scan server
        wh nmap -l

        # Local: Scan common ports on a host
        wh nmap -c 7-guitar-sunset scanme.nmap.org

        # Scan specific ports
        wh nmap -c CODE -p 22,80,443,8080 example.com

        # Scan port range
        wh nmap -c CODE -p 1-1024 example.com

        # Scan with output file
        wh nmap -c CODE -oN scan.txt example.com

        # Faster scanning with higher concurrency
        wh nmap -c CODE --concurrency 200 -p 1-65535 target.com
    """
    if listen:
        pass
    elif not code:
        raise click.UsageError("CODE is required when not in listen mode (use -c/--code)")
    elif not target:
        raise click.UsageError("TARGET is required when not in listen mode")

    relay_url = ctx.obj.get("relay") if ctx.obj else None
    transit_relay = ctx.obj.get("transit") if ctx.obj else None
    code_length = ctx.obj.get("code_length", 2) if ctx.obj else 2

    def status(msg: str) -> None:
        if verbose:
            click.echo(f"[nmap] {msg}", err=True)

    async def run_nmap():
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
                    click.echo(f"Scanner listening on code: {manager.code}", err=True)

                    await manager.establish()

                    nmap_proto = NmapProtocol(
                        on_status=status,
                        is_server=True,
                        timeout=timeout,
                        concurrency=concurrency,
                    )
                    await nmap_proto.run_server(manager)

                else:
                    # Client mode
                    await manager.create_and_set_code(code)
                    if verbose:
                        click.echo(f"Connecting to: {code}", err=True)

                    await manager.establish()

                    nmap_proto = NmapProtocol(
                        on_status=status,
                        is_server=False,
                    )
                    await nmap_proto.run_client(manager)

                    # Parse ports
                    port_list = parse_ports(ports)
                    if not port_list:
                        raise click.ClickException("No valid ports specified")

                    click.echo(f"\nStarting Nmap scan of {target}", err=True)
                    click.echo(f"Scanning {len(port_list)} ports...\n", err=True)

                    start_time = time.time()
                    results = await nmap_proto.scan(target, port_list)
                    scan_time = time.time() - start_time

                    # Display results
                    output_lines = []
                    output_lines.append(f"Nmap scan report for {target}")
                    output_lines.append(f"Scanned {len(port_list)} ports in {scan_time:.2f}s")
                    output_lines.append("")

                    # Count states
                    open_ports = [r for r in results.values() if r.state == "open"]
                    closed_ports = [r for r in results.values() if r.state == "closed"]
                    filtered_ports = [r for r in results.values() if r.state == "filtered"]

                    if not open_ports:
                        output_lines.append("No open ports found.")
                    else:
                        output_lines.append("PORT      STATE    SERVICE      LATENCY")
                        for result in sorted(open_ports, key=lambda r: r.port):
                            port_str = f"{result.port}/tcp"
                            service = result.service or "unknown"
                            latency = f"{result.latency_ms:.1f}ms" if result.latency_ms > 0 else ""
                            output_lines.append(
                                f"{port_str:<9} {result.state:<8} {service:<12} {latency}"
                            )

                    output_lines.append("")
                    output_lines.append(
                        f"Summary: {len(open_ports)} open, "
                        f"{len(closed_ports)} closed, "
                        f"{len(filtered_ports)} filtered"
                    )

                    # Print output
                    for line in output_lines:
                        click.echo(line)

                    # Save to file if requested
                    if output:
                        with open(output, "w") as f:
                            f.write("\n".join(output_lines) + "\n")
                        click.echo(f"\nResults saved to {output}", err=True)

        except KeyboardInterrupt:
            click.echo("\n--- scan interrupted ---", err=True)
        except Exception as e:
            raise click.ClickException(str(e))

    asyncio.run(run_nmap())
