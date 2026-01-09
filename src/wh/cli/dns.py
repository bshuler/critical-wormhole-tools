"""
wh dns - DNS queries through wormhole.

Performs DNS lookups through the wormhole peer's network.
"""

import asyncio
import click
import struct
import socket
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
import json

from wh.core.wormhole_manager import WormholeManager
from wh.core.protocol import StreamingProtocol, StreamingProtocolFactory


# DNS protocol messages
MSG_QUERY = 0x01       # DNS query
MSG_RESPONSE = 0x02    # DNS response


# DNS record types
RECORD_TYPES = {
    "A": 1,
    "AAAA": 28,
    "CNAME": 5,
    "MX": 15,
    "NS": 2,
    "PTR": 12,
    "SOA": 6,
    "TXT": 16,
    "SRV": 33,
    "ANY": 255,
}

RECORD_TYPE_NAMES = {v: k for k, v in RECORD_TYPES.items()}


@dataclass
class DNSRecord:
    """A DNS record."""
    name: str
    type: str
    ttl: int
    value: str


@dataclass
class DNSResponse:
    """A DNS response."""
    query: str
    query_type: str
    answers: List[DNSRecord]
    authorities: List[DNSRecord]
    additionals: List[DNSRecord]
    error: str = ""


class DNSProtocol:
    """
    DNS query protocol over wormhole.
    """

    def __init__(
        self,
        on_status: Optional[callable] = None,
        is_server: bool = False,
        dns_server: str = "",
        timeout: float = 10.0,
    ):
        self.on_status = on_status
        self.is_server = is_server
        self.dns_server = dns_server or "8.8.8.8"
        self.timeout = timeout

        self._protocol: Optional[StreamingProtocol] = None
        self._buffer = b""
        self._done = asyncio.Event()
        self._connected = asyncio.Event()

        # Response handling
        self._response_future: Optional[asyncio.Future] = None

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

            if msg_type == MSG_QUERY:
                asyncio.create_task(self._handle_query(payload))
            elif msg_type == MSG_RESPONSE:
                self._handle_response(payload)

    async def _handle_query(self, payload: bytes) -> None:
        """Handle DNS query (server side)."""
        try:
            query_data = json.loads(payload.decode())
            name = query_data.get("name", "")
            qtype = query_data.get("type", "A")

            self._status(f"Query: {name} {qtype}")

            # Perform the DNS lookup using system resolver
            response = DNSResponse(
                query=name,
                query_type=qtype,
                answers=[],
                authorities=[],
                additionals=[],
            )

            try:
                if qtype == "A":
                    # Get A records
                    try:
                        ips = socket.gethostbyname_ex(name)[2]
                        for ip in ips:
                            response.answers.append(DNSRecord(name, "A", 300, ip))
                    except socket.gaierror as e:
                        response.error = str(e)

                elif qtype == "AAAA":
                    # Get AAAA records
                    try:
                        infos = socket.getaddrinfo(name, None, socket.AF_INET6)
                        seen = set()
                        for info in infos:
                            ip = info[4][0]
                            if ip not in seen:
                                seen.add(ip)
                                response.answers.append(DNSRecord(name, "AAAA", 300, ip))
                    except socket.gaierror as e:
                        response.error = str(e)

                elif qtype == "PTR":
                    # Reverse DNS lookup
                    try:
                        hostname, _, _ = socket.gethostbyaddr(name)
                        response.answers.append(DNSRecord(name, "PTR", 300, hostname))
                    except socket.herror as e:
                        response.error = str(e)

                elif qtype == "MX":
                    # MX records - try using dnspython if available
                    try:
                        import dns.resolver
                        answers = dns.resolver.resolve(name, 'MX')
                        for rdata in answers:
                            response.answers.append(
                                DNSRecord(name, "MX", 300, f"{rdata.preference} {rdata.exchange}")
                            )
                    except ImportError:
                        # Fallback: just try to get mail server
                        response.error = "MX lookup requires dnspython library"
                    except Exception as e:
                        response.error = str(e)

                elif qtype == "NS":
                    # NS records
                    try:
                        import dns.resolver
                        answers = dns.resolver.resolve(name, 'NS')
                        for rdata in answers:
                            response.answers.append(DNSRecord(name, "NS", 300, str(rdata)))
                    except ImportError:
                        response.error = "NS lookup requires dnspython library"
                    except Exception as e:
                        response.error = str(e)

                elif qtype == "TXT":
                    # TXT records
                    try:
                        import dns.resolver
                        answers = dns.resolver.resolve(name, 'TXT')
                        for rdata in answers:
                            response.answers.append(DNSRecord(name, "TXT", 300, str(rdata)))
                    except ImportError:
                        response.error = "TXT lookup requires dnspython library"
                    except Exception as e:
                        response.error = str(e)

                elif qtype == "CNAME":
                    # CNAME records
                    try:
                        import dns.resolver
                        answers = dns.resolver.resolve(name, 'CNAME')
                        for rdata in answers:
                            response.answers.append(DNSRecord(name, "CNAME", 300, str(rdata)))
                    except ImportError:
                        # Fallback using socket
                        try:
                            cname = socket.gethostbyname_ex(name)[0]
                            if cname != name:
                                response.answers.append(DNSRecord(name, "CNAME", 300, cname))
                        except Exception:
                            pass
                    except Exception as e:
                        response.error = str(e)

                elif qtype == "SOA":
                    try:
                        import dns.resolver
                        answers = dns.resolver.resolve(name, 'SOA')
                        for rdata in answers:
                            response.answers.append(
                                DNSRecord(name, "SOA", 300,
                                    f"{rdata.mname} {rdata.rname} {rdata.serial} "
                                    f"{rdata.refresh} {rdata.retry} {rdata.expire} {rdata.minimum}")
                            )
                    except ImportError:
                        response.error = "SOA lookup requires dnspython library"
                    except Exception as e:
                        response.error = str(e)

                elif qtype == "SRV":
                    try:
                        import dns.resolver
                        answers = dns.resolver.resolve(name, 'SRV')
                        for rdata in answers:
                            response.answers.append(
                                DNSRecord(name, "SRV", 300,
                                    f"{rdata.priority} {rdata.weight} {rdata.port} {rdata.target}")
                            )
                    except ImportError:
                        response.error = "SRV lookup requires dnspython library"
                    except Exception as e:
                        response.error = str(e)

                else:
                    response.error = f"Unsupported query type: {qtype}"

            except Exception as e:
                response.error = str(e)

            # Send response
            response_data = {
                "query": response.query,
                "query_type": response.query_type,
                "answers": [{"name": r.name, "type": r.type, "ttl": r.ttl, "value": r.value}
                           for r in response.answers],
                "authorities": [{"name": r.name, "type": r.type, "ttl": r.ttl, "value": r.value}
                               for r in response.authorities],
                "additionals": [{"name": r.name, "type": r.type, "ttl": r.ttl, "value": r.value}
                               for r in response.additionals],
                "error": response.error,
            }
            self._send_message(MSG_RESPONSE, json.dumps(response_data).encode())

        except Exception as e:
            error_response = {"error": str(e)}
            self._send_message(MSG_RESPONSE, json.dumps(error_response).encode())

    def _handle_response(self, payload: bytes) -> None:
        """Handle DNS response (client side)."""
        if self._response_future and not self._response_future.done():
            try:
                data = json.loads(payload.decode())
                self._response_future.set_result(data)
            except Exception as e:
                self._response_future.set_exception(e)

    def _on_connection_lost(self, exc: Optional[Exception]) -> None:
        """Handle disconnection."""
        self._done.set()
        if self._response_future and not self._response_future.done():
            self._response_future.set_exception(Exception("Connection lost"))

    async def query(self, name: str, qtype: str = "A") -> Dict[str, Any]:
        """
        Perform DNS query (client side).

        Returns dict with query results.
        """
        self._response_future = asyncio.get_event_loop().create_future()

        query_data = {"name": name, "type": qtype.upper()}
        self._send_message(MSG_QUERY, json.dumps(query_data).encode())

        try:
            return await asyncio.wait_for(self._response_future, timeout=self.timeout)
        except asyncio.TimeoutError:
            return {"error": "Query timed out"}

    async def run_server(self, manager: WormholeManager) -> None:
        """Run as DNS server."""
        endpoint = manager.listener_for("wh-dns")

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
        self._status("DNS server ready...")

        await connected.wait()
        self._status("Client connected")

        await self._done.wait()

    async def run_client(self, manager: WormholeManager) -> "DNSProtocol":
        """Run as DNS client."""
        endpoint = manager.connector_for("wh-dns")

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


@click.command("dns")
@click.argument("name", required=False)
@click.option("-l", "--listen", is_flag=True, help="Listen mode (run DNS server)")
@click.option("-c", "--code", default=None, help="Wormhole code to connect with")
@click.option("-t", "--type", "qtype", default="A",
              help="Query type (A, AAAA, CNAME, MX, NS, PTR, SOA, TXT, SRV)")
@click.option("-x", "--reverse", is_flag=True, help="Reverse DNS lookup (PTR)")
@click.option("-v", "--verbose", is_flag=True, help="Verbose output")
@click.option("--short", is_flag=True, help="Short output (just the value)")
@click.pass_context
def dns(
    ctx: click.Context,
    name: Optional[str],
    listen: bool,
    code: Optional[str],
    qtype: str,
    reverse: bool,
    verbose: bool,
    short: bool,
) -> None:
    """
    DNS queries through wormhole.

    Performs DNS lookups using the wormhole peer's DNS resolver.
    Similar to dig/nslookup but queries from the peer's network.

    \b
    Examples:
        # Remote: Start DNS server
        wh dns -l

        # Local: Query A record
        wh dns -c 7-guitar-sunset example.com

        # Query specific record type
        wh dns -c CODE -t MX example.com
        wh dns -c CODE -t AAAA example.com
        wh dns -c CODE -t TXT example.com

        # Reverse DNS lookup
        wh dns -c CODE -x 8.8.8.8

        # Short output
        wh dns -c CODE --short example.com
    """
    if listen:
        pass
    elif not code:
        raise click.UsageError("CODE is required when not in listen mode (use -c/--code)")
    elif not name:
        raise click.UsageError("NAME is required when not in listen mode")

    # Handle reverse lookup
    if reverse:
        qtype = "PTR"

    relay_url = ctx.obj.get("relay") if ctx.obj else None
    transit_relay = ctx.obj.get("transit") if ctx.obj else None
    code_length = ctx.obj.get("code_length", 2) if ctx.obj else 2

    def status(msg: str) -> None:
        if verbose:
            click.echo(f"[dns] {msg}", err=True)

    async def run_dns():
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
                    click.echo(f"DNS server listening on code: {manager.code}", err=True)

                    await manager.establish()

                    dns_proto = DNSProtocol(
                        on_status=status,
                        is_server=True,
                    )
                    await dns_proto.run_server(manager)

                else:
                    # Client mode
                    await manager.create_and_set_code(code)
                    if verbose:
                        click.echo(f"Connecting to: {code}", err=True)

                    await manager.establish()

                    dns_proto = DNSProtocol(
                        on_status=status,
                        is_server=False,
                    )
                    await dns_proto.run_client(manager)

                    # Perform query
                    result = await dns_proto.query(name, qtype)

                    if result.get("error"):
                        click.echo(f";; ERROR: {result['error']}", err=True)
                        return

                    if short:
                        # Short output: just values
                        for answer in result.get("answers", []):
                            click.echo(answer["value"])
                    else:
                        # Full output
                        click.echo(f"; <<>> wh-dns <<>> {name} {qtype}")
                        click.echo("")

                        answers = result.get("answers", [])
                        if answers:
                            click.echo(";; ANSWER SECTION:")
                            for answer in answers:
                                click.echo(
                                    f"{answer['name']}\t{answer['ttl']}\tIN\t{answer['type']}\t{answer['value']}"
                                )
                            click.echo("")

                        authorities = result.get("authorities", [])
                        if authorities:
                            click.echo(";; AUTHORITY SECTION:")
                            for auth in authorities:
                                click.echo(
                                    f"{auth['name']}\t{auth['ttl']}\tIN\t{auth['type']}\t{auth['value']}"
                                )
                            click.echo("")

                        additionals = result.get("additionals", [])
                        if additionals:
                            click.echo(";; ADDITIONAL SECTION:")
                            for add in additionals:
                                click.echo(
                                    f"{add['name']}\t{add['ttl']}\tIN\t{add['type']}\t{add['value']}"
                                )
                            click.echo("")

                        if not answers and not authorities and not additionals:
                            click.echo(";; No records found")

        except KeyboardInterrupt:
            click.echo("\n--- query interrupted ---", err=True)
        except Exception as e:
            raise click.ClickException(str(e))

    asyncio.run(run_dns())
