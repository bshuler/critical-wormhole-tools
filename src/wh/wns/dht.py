"""
WNS DHT - BitTorrent DHT-based peer discovery for WNS addresses.

Uses the public BitTorrent Mainline DHT (BEP 5) for decentralized discovery:
    - DHT is used for PEER DISCOVERY (finding who serves an address)
    - Actual advertisement data is exchanged via direct TCP connection
    - Cryptographic signatures prevent impersonation

How it works:
    1. Server: Announces itself as "peer" for hash(wns_address) in DHT
    2. Client: Queries DHT for "peers" serving hash(wns_address)
    3. Client: Connects directly to peer's advertisement port
    4. Client: Receives signed CodeAdvertisement, verifies signature

Security:
    - DHT nodes cannot forge advertisements (signature verification)
    - Address is cryptographically bound to public key
    - Worst case: DoS (DHT returns no peers) or privacy leak (queries visible)

Bootstrap:
    Uses public BitTorrent DHT bootstrap nodes by default:
    - router.bittorrent.com:6881
    - dht.transmissionbt.com:6881
    - router.utorrent.com:6881

    Can be configured to use custom bootstrap nodes for private networks.

Configuration:
    To use custom bootstrap nodes, set in DHTConfig:

        config = DHTConfig(
            bootstrap_nodes=[("your-node.example.com", 6881)],
            use_public_bootstrap=False,  # Disable public nodes
        )

    Or set environment variables:
        WH_DHT_BOOTSTRAP_NODES="host1:port1,host2:port2"
        WH_DHT_USE_PUBLIC_BOOTSTRAP="false"
"""

import asyncio
import hashlib
import logging
import os
import socket
import struct
from dataclasses import dataclass, field
from typing import Optional, Callable, List, Tuple, Set, Dict, Any

from wh.wns.advertisement import CodeAdvertisement


logger = logging.getLogger(__name__)

# Default ports
DEFAULT_DHT_PORT = 6881  # Standard BitTorrent DHT port
DEFAULT_ADVERTISE_PORT = 8470  # Port for serving advertisements

# Re-announce interval (DHT entries expire after ~15 minutes)
DEFAULT_ANNOUNCE_INTERVAL = 600  # 10 minutes

# Advertisement TTL
DEFAULT_TTL_SECONDS = 3600  # 1 hour
DEFAULT_REPUBLISH_INTERVAL = 300  # 5 minutes

# Public BitTorrent DHT bootstrap nodes - these are stable, well-known nodes
# that help join the global DHT network. Anyone can run their own and add here.
PUBLIC_BOOTSTRAP_NODES: List[Tuple[str, int]] = [
    ("router.bittorrent.com", 6881),
    ("dht.transmissionbt.com", 6881),
    ("router.utorrent.com", 6881),
    ("dht.aelitis.com", 6881),
]

# Additional bootstrap URLs for custom/private networks
DEFAULT_BOOTSTRAP_URLS: List[str] = [
    # Can add URLs that return JSON: {"nodes": [{"host": "...", "port": N}, ...]}
]


def wns_address_to_info_hash(address: str) -> bytes:
    """
    Convert a WNS address to a 20-byte info_hash for DHT lookup.

    The info_hash is SHA-1(SHA-256(address)), truncated to 20 bytes
    to match BitTorrent's info_hash format.

    Args:
        address: WNS address (without wh:// prefix)

    Returns:
        20-byte info_hash suitable for DHT operations
    """
    # Double-hash to prevent length extension attacks and match 20-byte format
    sha256_hash = hashlib.sha256(address.encode("utf-8")).digest()
    sha1_hash = hashlib.sha1(sha256_hash).digest()
    return sha1_hash  # 20 bytes


def parse_bootstrap_nodes_env() -> List[Tuple[str, int]]:
    """Parse bootstrap nodes from environment variable."""
    env_val = os.environ.get("WH_DHT_BOOTSTRAP_NODES", "")
    if not env_val:
        return []

    nodes = []
    for part in env_val.split(","):
        part = part.strip()
        if ":" in part:
            host, port_str = part.rsplit(":", 1)
            try:
                nodes.append((host, int(port_str)))
            except ValueError:
                logger.warning(f"Invalid bootstrap node: {part}")
        elif part:
            nodes.append((part, DEFAULT_DHT_PORT))
    return nodes


def use_public_bootstrap_env() -> bool:
    """Check if public bootstrap should be used from environment."""
    env_val = os.environ.get("WH_DHT_USE_PUBLIC_BOOTSTRAP", "").lower()
    if env_val in ("false", "0", "no"):
        return False
    return True


async def fetch_bootstrap_nodes(
    urls: Optional[List[str]] = None,
    timeout: float = 5.0,
) -> List[Tuple[str, int]]:
    """
    Fetch additional bootstrap nodes from HTTP endpoints.

    Args:
        urls: List of URLs to try
        timeout: Request timeout in seconds

    Returns:
        List of (host, port) tuples
    """
    import httpx

    urls = urls or DEFAULT_BOOTSTRAP_URLS
    if not urls:
        return []

    nodes: List[Tuple[str, int]] = []

    for url in urls:
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()

                for node in data.get("nodes", []):
                    host = node.get("host")
                    port = node.get("port", DEFAULT_DHT_PORT)
                    if host:
                        nodes.append((host, port))

                if nodes:
                    logger.info(f"Fetched {len(nodes)} bootstrap nodes from {url}")
                    return nodes

        except Exception as e:
            logger.debug(f"Failed to fetch bootstrap from {url}: {e}")
            continue

    return nodes


async def discover_local_nodes(timeout: float = 2.0) -> List[Tuple[str, int]]:
    """
    Discover DHT nodes on the local network via mDNS.

    Looks for services advertising "_wh-dht._udp.local."
    """
    nodes: List[Tuple[str, int]] = []

    try:
        from zeroconf import Zeroconf, ServiceBrowser
        from zeroconf.asyncio import AsyncZeroconf

        SERVICE_TYPE = "_wh-dht._udp.local."

        class Listener:
            def __init__(self):
                self.nodes: List[Tuple[str, int]] = []

            def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
                info = zc.get_service_info(type_, name)
                if info:
                    for addr in info.parsed_addresses():
                        self.nodes.append((addr, info.port))

            def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
                pass

            def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
                pass

        async with AsyncZeroconf() as azc:
            listener = Listener()
            browser = ServiceBrowser(azc.zeroconf, SERVICE_TYPE, listener)
            await asyncio.sleep(timeout)
            browser.cancel()
            nodes = listener.nodes

        if nodes:
            logger.info(f"Discovered {len(nodes)} local DHT nodes via mDNS")

    except ImportError:
        logger.debug("zeroconf not installed, skipping mDNS discovery")
    except Exception as e:
        logger.debug(f"mDNS discovery failed: {e}")

    return nodes


def get_all_bootstrap_nodes(
    custom_nodes: Optional[List[Tuple[str, int]]] = None,
    use_public: bool = True,
) -> List[Tuple[str, int]]:
    """
    Get bootstrap nodes combining custom and public nodes.

    Args:
        custom_nodes: User-specified bootstrap nodes
        use_public: Whether to include public BitTorrent DHT nodes

    Returns:
        Combined list of bootstrap nodes
    """
    nodes: List[Tuple[str, int]] = []
    seen: Set[Tuple[str, int]] = set()

    # Add nodes from environment variable first (highest priority)
    for node in parse_bootstrap_nodes_env():
        if node not in seen:
            nodes.append(node)
            seen.add(node)

    # Add custom nodes
    if custom_nodes:
        for node in custom_nodes:
            if node not in seen:
                nodes.append(node)
                seen.add(node)

    # Add public nodes (if enabled and not overridden by env)
    if use_public and use_public_bootstrap_env():
        for node in PUBLIC_BOOTSTRAP_NODES:
            if node not in seen:
                nodes.append(node)
                seen.add(node)

    return nodes


async def get_bootstrap_nodes(
    static_nodes: Optional[List[Tuple[str, int]]] = None,
    bootstrap_urls: Optional[List[str]] = None,
    use_mdns: bool = True,
    use_public: bool = True,
) -> List[Tuple[str, int]]:
    """
    Get all bootstrap nodes from various sources.

    Args:
        static_nodes: Manually configured nodes
        bootstrap_urls: HTTP URLs to fetch nodes from
        use_mdns: Whether to use mDNS discovery
        use_public: Whether to include public BitTorrent nodes

    Returns:
        Combined list of (host, port) tuples
    """
    nodes = get_all_bootstrap_nodes(static_nodes, use_public)
    seen = set(nodes)

    # Try HTTP bootstrap URLs
    if bootstrap_urls:
        try:
            fetched = await fetch_bootstrap_nodes(bootstrap_urls)
            for node in fetched:
                if node not in seen:
                    nodes.append(node)
                    seen.add(node)
        except Exception as e:
            logger.debug(f"HTTP bootstrap failed: {e}")

    # Try mDNS discovery
    if use_mdns:
        try:
            local = await discover_local_nodes()
            for node in local:
                if node not in seen:
                    nodes.append(node)
                    seen.add(node)
        except Exception as e:
            logger.debug(f"mDNS discovery failed: {e}")

    return nodes


def address_to_dht_key(
    address: str,
    relay_url: Optional[str] = None,
    namespace: Optional[str] = None,
) -> bytes:
    """
    Convert a WNS address to a DHT key.

    If relay_url is provided, the key is namespace-scoped for privacy.
    If namespace is provided (enterprise feature), uses namespace-prefixed key.
    """
    # Enterprise namespace takes precedence
    if namespace:
        try:
            from wh.enterprise.namespace import get_namespace_dht_key
            return get_namespace_dht_key(address, namespace)
        except ImportError:
            pass  # Enterprise module not available

    if relay_url:
        return namespace_dht_key(address, relay_url)
    return wns_address_to_info_hash(address)


def namespace_dht_key(address: str, relay_url: str) -> bytes:
    """Create a namespace-scoped DHT key for privacy."""
    combined = f"{relay_url}:{address}"
    sha256_hash = hashlib.sha256(combined.encode("utf-8")).digest()
    sha1_hash = hashlib.sha1(sha256_hash).digest()
    return sha1_hash


def encrypt_for_namespace(data: bytes, relay_url: str) -> bytes:
    """
    Encrypt data for a namespace (simple XOR with key derived from relay_url).

    Note: This is NOT strong encryption, just namespace scoping.
    For real privacy, use wormhole's end-to-end encryption.
    """
    key = hashlib.sha256(relay_url.encode()).digest()
    # Simple XOR encryption
    encrypted = bytes(data[i] ^ key[i % len(key)] for i in range(len(data)))
    return encrypted


def decrypt_for_namespace(data: bytes, relay_url: str) -> Optional[bytes]:
    """Decrypt namespace-scoped data."""
    try:
        return encrypt_for_namespace(data, relay_url)  # XOR is symmetric
    except Exception:
        return None


@dataclass
class DHTConfig:
    """
    Configuration for DHT node.

    Example - using only custom bootstrap nodes:
        config = DHTConfig(
            bootstrap_nodes=[("my-dht.example.com", 6881)],
            use_public_bootstrap=False,
        )

    Example - using public DHT with additional custom nodes:
        config = DHTConfig(
            bootstrap_nodes=[("my-extra-node.example.com", 6881)],
            use_public_bootstrap=True,  # default
        )
    """

    port: int = DEFAULT_DHT_PORT
    advertise_port: int = DEFAULT_ADVERTISE_PORT
    bootstrap_nodes: List[Tuple[str, int]] = field(default_factory=list)
    bootstrap_urls: List[str] = field(default_factory=lambda: DEFAULT_BOOTSTRAP_URLS.copy())
    use_mdns: bool = True  # Enable local network discovery
    use_public_bootstrap: bool = True  # Use public BitTorrent DHT nodes
    auto_bootstrap: bool = True  # Automatically discover bootstrap nodes
    ttl_seconds: int = DEFAULT_TTL_SECONDS
    republish_interval: int = DEFAULT_REPUBLISH_INTERVAL
    announce_interval: int = DEFAULT_ANNOUNCE_INTERVAL
    relay_url: Optional[str] = None  # For namespace encryption
    encrypt_advertisements: bool = False  # Enable namespace encryption

    def __post_init__(self):
        # Auto-enable encryption if relay_url is provided
        if self.relay_url and not self.encrypt_advertisements:
            self.encrypt_advertisements = True


class AdvertisementServer:
    """
    TCP server that serves code advertisements.

    When a client looks up an address in the DHT, they get our IP/port.
    They then connect here to get the actual signed advertisement.

    Protocol (simple line-based):
        Client: GET <address>\n
        Server: <json_advertisement>\n

    The advertisement is cryptographically signed, so clients verify
    it regardless of which DHT node told them about us.
    """

    def __init__(self, port: int = DEFAULT_ADVERTISE_PORT):
        self.port = port
        self._server: Optional[asyncio.Server] = None
        self._advertisements: Dict[str, CodeAdvertisement] = {}
        self._running = False

    def add_advertisement(self, address: str, ad: CodeAdvertisement) -> None:
        """Add or update an advertisement."""
        self._advertisements[address] = ad

    def remove_advertisement(self, address: str) -> None:
        """Remove an advertisement."""
        self._advertisements.pop(address, None)

    def get_advertisement(self, address: str) -> Optional[CodeAdvertisement]:
        """Get an advertisement by address."""
        return self._advertisements.get(address)

    async def start(self) -> int:
        """Start the advertisement server. Returns the actual port."""
        if self._running:
            return self.port

        self._server = await asyncio.start_server(
            self._handle_client,
            host="0.0.0.0",
            port=self.port,
        )

        # Get actual port (in case 0 was specified)
        addr = self._server.sockets[0].getsockname()
        self.port = addr[1]

        self._running = True
        logger.info(f"Advertisement server listening on port {self.port}")

        # Start serving in background
        asyncio.create_task(self._serve())

        return self.port

    async def _serve(self) -> None:
        """Background serving task."""
        if self._server:
            async with self._server:
                await self._server.serve_forever()

    async def stop(self) -> None:
        """Stop the server."""
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
        self._running = False

    async def _handle_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter
    ) -> None:
        """Handle a client connection."""
        try:
            # Read request (timeout 10s)
            line = await asyncio.wait_for(reader.readline(), timeout=10.0)
            if not line:
                return

            request = line.decode("utf-8").strip()

            if request.startswith("GET "):
                address = request[4:].strip()
                ad = self._advertisements.get(address)

                if ad and not ad.is_expired():
                    response = ad.to_json() + "\n"
                    writer.write(response.encode("utf-8"))
                else:
                    writer.write(b"NOT_FOUND\n")
            else:
                writer.write(b"ERROR: Unknown command\n")

            await writer.drain()

        except asyncio.TimeoutError:
            pass
        except Exception as e:
            logger.debug(f"Client handler error: {e}")
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass


class SimpleDHTNode:
    """
    A simple Kademlia-style DHT node for peer discovery.

    This is a minimal implementation that supports:
    - Bootstrap to existing nodes
    - announce_peer: Tell DHT we're serving an info_hash
    - get_peers: Query DHT for peers serving an info_hash

    Uses BEP 5 protocol (BitTorrent DHT) so we can bootstrap from
    public BitTorrent nodes.
    """

    def __init__(self, port: int = 0):
        self.port = port
        self._socket: Optional[socket.socket] = None
        self._node_id = os.urandom(20)  # 160-bit node ID
        self._routing_table: Dict[bytes, Tuple[str, int]] = {}  # node_id -> (ip, port)
        self._token = os.urandom(8)
        self._running = False
        self._task: Optional[asyncio.Task] = None

        # Announced peers: info_hash -> set of (ip, port) tuples
        self._announced: Dict[bytes, Set[Tuple[str, int]]] = {}

        # Transaction ID counter
        self._tid = 0
        self._pending: Dict[bytes, asyncio.Future] = {}

    def _next_tid(self) -> bytes:
        """Get next transaction ID."""
        self._tid = (self._tid + 1) % 65536
        return struct.pack("!H", self._tid)

    async def start(self) -> int:
        """Start the DHT node. Returns actual port."""
        if self._running:
            return self.port

        # Create UDP socket
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socket.setblocking(False)
        self._socket.bind(("0.0.0.0", self.port))

        addr = self._socket.getsockname()
        self.port = addr[1]

        self._running = True
        self._task = asyncio.create_task(self._receive_loop())

        logger.info(f"DHT node started on port {self.port}")
        return self.port

    async def stop(self) -> None:
        """Stop the DHT node."""
        self._running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        if self._socket:
            self._socket.close()
            self._socket = None

        # Cancel pending requests
        for future in self._pending.values():
            if not future.done():
                future.cancel()
        self._pending.clear()

    async def _receive_loop(self) -> None:
        """Background task to receive UDP packets."""
        loop = asyncio.get_event_loop()

        while self._running and self._socket:
            try:
                data, addr = await loop.sock_recvfrom(self._socket, 65536)
                await self._handle_message(data, addr)
            except asyncio.CancelledError:
                break
            except Exception as e:
                if self._running:
                    logger.debug(f"DHT receive error: {e}")

    async def _handle_message(self, data: bytes, addr: Tuple[str, int]) -> None:
        """Handle incoming DHT message."""
        try:
            # Parse bencode message
            msg = self._bdecode(data)
            if not isinstance(msg, dict):
                return

            msg_type = msg.get(b"y")
            tid = msg.get(b"t", b"")

            if msg_type == b"r":
                # Response
                if tid in self._pending:
                    future = self._pending.pop(tid)
                    if not future.done():
                        future.set_result(msg.get(b"r", {}))

                # Add to routing table
                response = msg.get(b"r", {})
                if b"id" in response:
                    self._routing_table[response[b"id"]] = addr

            elif msg_type == b"q":
                # Query - respond appropriately
                query = msg.get(b"q", b"")
                args = msg.get(b"a", {})

                if query == b"ping":
                    await self._send_response(tid, addr, {b"id": self._node_id})

                elif query == b"find_node":
                    await self._send_response(tid, addr, {
                        b"id": self._node_id,
                        b"nodes": self._get_closest_nodes(args.get(b"target", b""))
                    })

                elif query == b"get_peers":
                    info_hash = args.get(b"info_hash", b"")
                    peers = self._announced.get(info_hash, set())

                    if peers:
                        # Return peers
                        values = [self._encode_peer(p) for p in peers]
                        await self._send_response(tid, addr, {
                            b"id": self._node_id,
                            b"token": self._token,
                            b"values": values,
                        })
                    else:
                        # Return closest nodes
                        await self._send_response(tid, addr, {
                            b"id": self._node_id,
                            b"token": self._token,
                            b"nodes": self._get_closest_nodes(info_hash),
                        })

                elif query == b"announce_peer":
                    info_hash = args.get(b"info_hash", b"")
                    port = args.get(b"port", addr[1])

                    if info_hash not in self._announced:
                        self._announced[info_hash] = set()
                    self._announced[info_hash].add((addr[0], port))

                    await self._send_response(tid, addr, {b"id": self._node_id})

        except Exception as e:
            logger.debug(f"DHT message handling error: {e}")

    async def _send_response(
        self,
        tid: bytes,
        addr: Tuple[str, int],
        response: Dict
    ) -> None:
        """Send a response message."""
        msg = {b"t": tid, b"y": b"r", b"r": response}
        await self._send(msg, addr)

    async def _send(self, msg: Dict, addr: Tuple[str, int]) -> None:
        """Send a bencoded message."""
        if not self._socket:
            return

        data = self._bencode(msg)
        loop = asyncio.get_event_loop()
        await loop.sock_sendto(self._socket, data, addr)

    async def _query(
        self,
        addr: Tuple[str, int],
        method: bytes,
        args: Dict,
        timeout: float = 5.0
    ) -> Optional[Dict]:
        """Send a query and wait for response."""
        tid = self._next_tid()
        msg = {
            b"t": tid,
            b"y": b"q",
            b"q": method,
            b"a": {**args, b"id": self._node_id}
        }

        future: asyncio.Future = asyncio.get_event_loop().create_future()
        self._pending[tid] = future

        try:
            await self._send(msg, addr)
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            self._pending.pop(tid, None)
            return None
        except Exception:
            self._pending.pop(tid, None)
            return None

    async def bootstrap(self, nodes: List[Tuple[str, int]]) -> int:
        """Bootstrap to the DHT network. Returns number of nodes found."""
        if not nodes:
            return 0

        found_count = 0

        # Query each bootstrap node
        for host, port in nodes:
            try:
                # Resolve hostname
                infos = await asyncio.get_event_loop().getaddrinfo(
                    host, port, family=socket.AF_INET, type=socket.SOCK_DGRAM
                )
                if not infos:
                    continue

                addr = (infos[0][4][0], port)

                # Find nodes close to us
                response = await self._query(
                    addr,
                    b"find_node",
                    {b"target": self._node_id}
                )

                if response:
                    found_count += 1

                    # Parse compact node info
                    if b"nodes" in response:
                        new_nodes = self._parse_nodes(response[b"nodes"])
                        for node_id, node_addr in new_nodes:
                            self._routing_table[node_id] = node_addr

                    # Add bootstrap node
                    if b"id" in response:
                        self._routing_table[response[b"id"]] = addr

            except Exception as e:
                logger.debug(f"Bootstrap to {host}:{port} failed: {e}")

        logger.info(f"DHT bootstrapped with {len(self._routing_table)} nodes")
        return found_count

    async def announce(
        self,
        info_hash: bytes,
        port: int,
        implied_port: bool = False
    ) -> int:
        """Announce ourselves as a peer for info_hash. Returns nodes notified."""
        if len(info_hash) != 20:
            raise ValueError("info_hash must be 20 bytes")

        # First, find nodes close to this info_hash
        closest = await self._find_nodes(info_hash)

        # Announce to each
        notified = 0
        for node_id, addr in closest:
            try:
                # Get token first
                response = await self._query(addr, b"get_peers", {b"info_hash": info_hash})
                if not response:
                    continue

                token = response.get(b"token", b"")

                # Announce
                announce_args: Dict[bytes, Any] = {
                    b"info_hash": info_hash,
                    b"port": port,
                    b"token": token,
                }
                if implied_port:
                    announce_args[b"implied_port"] = 1

                result = await self._query(addr, b"announce_peer", announce_args)
                if result is not None:
                    notified += 1

            except Exception as e:
                logger.debug(f"Announce to {addr} failed: {e}")

        return notified

    async def get_peers(
        self,
        info_hash: bytes,
        max_peers: int = 50
    ) -> List[Tuple[str, int]]:
        """Find peers for an info_hash."""
        if len(info_hash) != 20:
            raise ValueError("info_hash must be 20 bytes")

        peers: Set[Tuple[str, int]] = set()
        queried: Set[Tuple[str, int]] = set()

        # Start with closest known nodes
        to_query = list(self._routing_table.values())[:8]

        while to_query and len(peers) < max_peers:
            addr = to_query.pop(0)
            if addr in queried:
                continue
            queried.add(addr)

            try:
                response = await self._query(addr, b"get_peers", {b"info_hash": info_hash})
                if not response:
                    continue

                # Check for direct peer list
                if b"values" in response:
                    for value in response[b"values"]:
                        peer = self._decode_peer(value)
                        if peer:
                            peers.add(peer)

                # Add closer nodes to query
                if b"nodes" in response:
                    for node_id, node_addr in self._parse_nodes(response[b"nodes"]):
                        if node_addr not in queried:
                            to_query.append(node_addr)

            except Exception as e:
                logger.debug(f"get_peers query failed: {e}")

        return list(peers)

    async def _find_nodes(
        self,
        target: bytes,
        count: int = 8
    ) -> List[Tuple[bytes, Tuple[str, int]]]:
        """Find nodes closest to target."""
        # Get currently known closest nodes
        sorted_nodes = sorted(
            self._routing_table.items(),
            key=lambda x: self._xor_distance(x[0], target)
        )

        closest = sorted_nodes[:count]
        queried: Set[Tuple[str, int]] = set()

        # Iteratively find closer nodes
        to_query = [addr for _, addr in closest]

        for _ in range(3):  # Max iterations
            if not to_query:
                break

            new_to_query = []
            for addr in to_query[:8]:
                if addr in queried:
                    continue
                queried.add(addr)

                try:
                    response = await self._query(addr, b"find_node", {b"target": target})
                    if not response:
                        continue

                    if b"nodes" in response:
                        for node_id, node_addr in self._parse_nodes(response[b"nodes"]):
                            self._routing_table[node_id] = node_addr
                            if node_addr not in queried:
                                new_to_query.append(node_addr)

                except Exception:
                    pass

            to_query = new_to_query

        # Return final closest
        sorted_nodes = sorted(
            self._routing_table.items(),
            key=lambda x: self._xor_distance(x[0], target)
        )
        return sorted_nodes[:count]

    def _xor_distance(self, a: bytes, b: bytes) -> int:
        """Calculate XOR distance between two node IDs."""
        return int.from_bytes(
            bytes(x ^ y for x, y in zip(a, b)),
            byteorder="big"
        )

    def _get_closest_nodes(self, target: bytes, count: int = 8) -> bytes:
        """Get compact node info for closest nodes."""
        sorted_nodes = sorted(
            self._routing_table.items(),
            key=lambda x: self._xor_distance(x[0], target)
        )[:count]

        result = b""
        for node_id, (ip, port) in sorted_nodes:
            try:
                ip_bytes = socket.inet_aton(ip)
                result += node_id + ip_bytes + struct.pack("!H", port)
            except Exception:
                pass
        return result

    def _parse_nodes(self, data: bytes) -> List[Tuple[bytes, Tuple[str, int]]]:
        """Parse compact node info."""
        nodes = []
        for i in range(0, len(data), 26):
            if i + 26 > len(data):
                break
            node_id = data[i:i+20]
            ip = socket.inet_ntoa(data[i+20:i+24])
            port = struct.unpack("!H", data[i+24:i+26])[0]
            nodes.append((node_id, (ip, port)))
        return nodes

    def _encode_peer(self, peer: Tuple[str, int]) -> bytes:
        """Encode peer as compact format."""
        ip, port = peer
        return socket.inet_aton(ip) + struct.pack("!H", port)

    def _decode_peer(self, data: bytes) -> Optional[Tuple[str, int]]:
        """Decode peer from compact format."""
        if len(data) != 6:
            return None
        ip = socket.inet_ntoa(data[:4])
        port = struct.unpack("!H", data[4:])[0]
        return (ip, port)

    # Bencode implementation
    def _bencode(self, obj: Any) -> bytes:
        """Encode object to bencode."""
        if isinstance(obj, int):
            return f"i{obj}e".encode()
        elif isinstance(obj, bytes):
            return f"{len(obj)}:".encode() + obj
        elif isinstance(obj, str):
            encoded = obj.encode()
            return f"{len(encoded)}:".encode() + encoded
        elif isinstance(obj, list):
            return b"l" + b"".join(self._bencode(x) for x in obj) + b"e"
        elif isinstance(obj, dict):
            # Keys must be sorted
            items = sorted(obj.items(), key=lambda x: x[0] if isinstance(x[0], bytes) else x[0].encode())
            return b"d" + b"".join(
                self._bencode(k) + self._bencode(v) for k, v in items
            ) + b"e"
        else:
            raise TypeError(f"Cannot bencode {type(obj)}")

    def _bdecode(self, data: bytes) -> Any:
        """Decode bencode data."""
        result, _ = self._bdecode_item(data, 0)
        return result

    def _bdecode_item(self, data: bytes, pos: int) -> Tuple[Any, int]:
        """Decode single bencode item, return (value, new_pos)."""
        if data[pos:pos+1] == b"i":
            # Integer
            end = data.index(b"e", pos)
            return int(data[pos+1:end]), end + 1

        elif data[pos:pos+1] == b"l":
            # List
            items = []
            pos += 1
            while data[pos:pos+1] != b"e":
                item, pos = self._bdecode_item(data, pos)
                items.append(item)
            return items, pos + 1

        elif data[pos:pos+1] == b"d":
            # Dict
            items = {}
            pos += 1
            while data[pos:pos+1] != b"e":
                key, pos = self._bdecode_item(data, pos)
                value, pos = self._bdecode_item(data, pos)
                items[key] = value
            return items, pos + 1

        else:
            # String (byte string)
            colon = data.index(b":", pos)
            length = int(data[pos:colon])
            start = colon + 1
            return data[start:start+length], start + length


class WNSDHTNode:
    """
    A DHT node for publishing and discovering WNS code advertisements.

    Uses the public BitTorrent DHT for peer discovery, with a local
    advertisement server for serving signed advertisements.

    Example usage:
        async with WNSDHTNode() as node:
            # Publish an advertisement
            await node.publish(advertisement)

            # Lookup an address
            ad = await node.lookup("abc123...")
    """

    def __init__(self, config: Optional[DHTConfig] = None):
        """Initialize DHT node."""
        self.config = config or DHTConfig()
        self._dht: Optional[SimpleDHTNode] = None
        self._ad_server: Optional[AdvertisementServer] = None
        self._running = False
        self._republish_task: Optional[asyncio.Task] = None
        self._announce_task: Optional[asyncio.Task] = None
        self._published_ads: Dict[str, CodeAdvertisement] = {}
        self._on_republish: Optional[Callable[[str], CodeAdvertisement]] = None

    async def start(self, port: Optional[int] = None) -> None:
        """Start the DHT node and join the network."""
        if self._running:
            return

        port = port or self.config.port

        # Start DHT node
        self._dht = SimpleDHTNode(port=port)
        await self._dht.start()

        # Start advertisement server
        self._ad_server = AdvertisementServer(port=self.config.advertise_port)
        await self._ad_server.start()

        # Get bootstrap nodes
        if self.config.auto_bootstrap:
            bootstrap_nodes = await get_bootstrap_nodes(
                static_nodes=self.config.bootstrap_nodes,
                bootstrap_urls=self.config.bootstrap_urls,
                use_mdns=self.config.use_mdns,
                use_public=self.config.use_public_bootstrap,
            )
        else:
            bootstrap_nodes = get_all_bootstrap_nodes(
                self.config.bootstrap_nodes,
                self.config.use_public_bootstrap,
            )

        # Bootstrap to the network
        if bootstrap_nodes:
            logger.info(f"Bootstrapping to {len(bootstrap_nodes)} nodes")
            await self._dht.bootstrap(bootstrap_nodes)
        else:
            logger.warning(
                "No bootstrap nodes available. DHT will operate in isolated mode. "
                "To join the network, either: "
                "1) Configure bootstrap_nodes, "
                "2) Set WH_DHT_BOOTSTRAP_NODES environment variable, or "
                "3) Enable use_public_bootstrap (default)"
            )

        self._running = True

    async def stop(self) -> None:
        """Stop the DHT node."""
        if not self._running:
            return

        # Cancel republish task
        if self._republish_task:
            self._republish_task.cancel()
            try:
                await self._republish_task
            except asyncio.CancelledError:
                pass
            self._republish_task = None

        # Cancel announce task
        if self._announce_task:
            self._announce_task.cancel()
            try:
                await self._announce_task
            except asyncio.CancelledError:
                pass
            self._announce_task = None

        # Stop DHT
        if self._dht:
            await self._dht.stop()
            self._dht = None

        # Stop advertisement server
        if self._ad_server:
            await self._ad_server.stop()
            self._ad_server = None

        self._running = False
        logger.info("DHT node stopped")

    @property
    def is_running(self) -> bool:
        """Check if the DHT node is running."""
        return self._running

    async def publish(self, advertisement: CodeAdvertisement) -> bool:
        """
        Publish a code advertisement to the DHT.

        This:
        1. Stores the advertisement in our local advertisement server
        2. Announces ourselves as a peer for this address in the DHT

        Args:
            advertisement: The signed code advertisement to publish

        Returns:
            True if published successfully
        """
        if not self._running or not self._dht or not self._ad_server:
            raise RuntimeError("DHT node not running")

        # Verify the advertisement before publishing
        if not advertisement.verify():
            raise ValueError("Cannot publish invalid advertisement")

        # Add to local advertisement server
        self._ad_server.add_advertisement(advertisement.address, advertisement)

        # Calculate info_hash for DHT
        info_hash = wns_address_to_info_hash(advertisement.address)

        # Announce ourselves as a peer
        notified = await self._dht.announce(
            info_hash,
            self._ad_server.port,
            implied_port=False
        )

        logger.debug(
            f"Published to DHT: {advertisement.address} "
            f"(notified {notified} nodes)"
        )

        # Track for republishing
        self._published_ads[advertisement.address] = advertisement

        return True

    async def lookup(
        self,
        address: str,
        relay_url: Optional[str] = None,
    ) -> Optional[CodeAdvertisement]:
        """
        Look up a code advertisement in the DHT.

        Args:
            address: The WNS address to look up (without wh:// prefix)
            relay_url: Optional relay URL for namespace lookup (overrides config)

        Returns:
            The code advertisement if found and valid, None otherwise
        """
        if not self._running or not self._dht:
            raise RuntimeError("DHT node not running")

        # Calculate info_hash
        info_hash = wns_address_to_info_hash(address)

        # Query DHT for peers
        logger.debug(f"Looking up in DHT: {address}")
        peers = await self._dht.get_peers(info_hash)

        if not peers:
            logger.debug(f"No peers found for {address}")
            return None

        # Try each peer until we get a valid advertisement
        for peer_ip, peer_port in peers:
            try:
                ad = await self._fetch_advertisement(peer_ip, peer_port, address)
                if ad:
                    # Verify signature and address match
                    if not ad.verify(expected_address=address):
                        logger.warning(f"Invalid advertisement from {peer_ip}:{peer_port}")
                        continue

                    # Check if expired
                    if ad.is_expired():
                        logger.debug(f"Expired advertisement from {peer_ip}:{peer_port}")
                        continue

                    logger.debug(f"Found valid advertisement for {address}")
                    return ad

            except Exception as e:
                logger.debug(f"Failed to fetch from {peer_ip}:{peer_port}: {e}")
                continue

        logger.debug(f"No valid advertisement found for {address}")
        return None

    async def _fetch_advertisement(
        self,
        ip: str,
        port: int,
        address: str
    ) -> Optional[CodeAdvertisement]:
        """Fetch advertisement from a peer's advertisement server."""
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(ip, port),
                timeout=5.0
            )

            try:
                # Send request
                writer.write(f"GET {address}\n".encode())
                await writer.drain()

                # Read response
                response = await asyncio.wait_for(reader.readline(), timeout=5.0)
                response_str = response.decode("utf-8").strip()

                if response_str == "NOT_FOUND":
                    return None

                if response_str.startswith("ERROR"):
                    return None

                # Parse advertisement
                return CodeAdvertisement.from_json(response_str)

            finally:
                writer.close()
                await writer.wait_closed()

        except Exception as e:
            logger.debug(f"Fetch from {ip}:{port} failed: {e}")
            return None

    def set_republish_callback(
        self, callback: Callable[[str], CodeAdvertisement]
    ) -> None:
        """
        Set a callback for generating fresh advertisements during republish.

        The callback receives the address and should return a fresh
        CodeAdvertisement with a new code if the old one was consumed.

        Args:
            callback: Function that takes an address and returns a CodeAdvertisement
        """
        self._on_republish = callback

    async def start_republishing(self) -> None:
        """Start the background republishing task."""
        if self._republish_task:
            return

        self._republish_task = asyncio.create_task(self._republish_loop())
        self._announce_task = asyncio.create_task(self._announce_loop())

    async def _republish_loop(self) -> None:
        """Background task to republish advertisements before they expire."""
        while self._running:
            try:
                await asyncio.sleep(self.config.republish_interval)

                if not self._running:
                    break

                # Republish all tracked advertisements
                for address in list(self._published_ads.keys()):
                    try:
                        if self._on_republish:
                            # Get fresh advertisement from callback
                            ad = self._on_republish(address)
                        else:
                            # Republish existing (may be stale)
                            ad = self._published_ads.get(address)

                        if ad and self._ad_server:
                            self._ad_server.add_advertisement(address, ad)
                            logger.debug(f"Republished: {address}")
                    except Exception as e:
                        logger.warning(f"Failed to republish {address}: {e}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in republish loop: {e}")

    async def _announce_loop(self) -> None:
        """Background task to re-announce in DHT periodically."""
        while self._running:
            try:
                await asyncio.sleep(self.config.announce_interval)

                if not self._running or not self._dht or not self._ad_server:
                    break

                # Re-announce all addresses
                for address in list(self._published_ads.keys()):
                    try:
                        info_hash = wns_address_to_info_hash(address)
                        await self._dht.announce(
                            info_hash,
                            self._ad_server.port,
                            implied_port=False
                        )
                        logger.debug(f"Re-announced: {address}")
                    except Exception as e:
                        logger.warning(f"Failed to re-announce {address}: {e}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in announce loop: {e}")

    async def __aenter__(self) -> "WNSDHTNode":
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.stop()


class WNSDHTClient:
    """
    A lightweight DHT client for looking up advertisements.

    This is simpler than WNSDHTNode - it only does lookups, not publishing.
    Used by clients who just need to discover server codes.

    Example usage:
        async with WNSDHTClient() as client:
            ad = await client.lookup("abc123...")
            if ad:
                print(f"Found code: {ad.code}")
    """

    def __init__(
        self,
        bootstrap_nodes: Optional[List[Tuple[str, int]]] = None,
        bootstrap_urls: Optional[List[str]] = None,
        relay_urls: Optional[List[str]] = None,
        auto_bootstrap: bool = True,
        use_mdns: bool = True,
        use_public_bootstrap: bool = True,
    ):
        """
        Initialize DHT client.

        Args:
            bootstrap_nodes: Static DHT bootstrap nodes
            bootstrap_urls: HTTP URLs to fetch bootstrap nodes from
            relay_urls: List of relay URLs to try for namespace lookups
            auto_bootstrap: Automatically discover bootstrap nodes (default True)
            use_mdns: Use mDNS for local network discovery (default True)
            use_public_bootstrap: Use public BitTorrent DHT nodes (default True)
        """
        self.bootstrap_nodes = bootstrap_nodes or []
        self.bootstrap_urls = bootstrap_urls or DEFAULT_BOOTSTRAP_URLS.copy()
        self.relay_urls = relay_urls or []
        self.auto_bootstrap = auto_bootstrap
        self.use_mdns = use_mdns
        self.use_public_bootstrap = use_public_bootstrap
        self._dht: Optional[SimpleDHTNode] = None
        self._running = False

    async def start(self) -> None:
        """Start the DHT client."""
        if self._running:
            return

        self._dht = SimpleDHTNode(port=0)  # Random port
        await self._dht.start()

        # Get bootstrap nodes
        if self.auto_bootstrap:
            bootstrap_nodes = await get_bootstrap_nodes(
                static_nodes=self.bootstrap_nodes,
                bootstrap_urls=self.bootstrap_urls,
                use_mdns=self.use_mdns,
                use_public=self.use_public_bootstrap,
            )
        else:
            bootstrap_nodes = get_all_bootstrap_nodes(
                self.bootstrap_nodes,
                self.use_public_bootstrap,
            )

        # Bootstrap to network
        if bootstrap_nodes:
            logger.info(f"DHT client bootstrapping to {len(bootstrap_nodes)} nodes")
            await self._dht.bootstrap(bootstrap_nodes)
        else:
            logger.warning("No DHT bootstrap nodes available, lookups may fail")

        self._running = True

    async def stop(self) -> None:
        """Stop the DHT client."""
        if self._dht:
            await self._dht.stop()
            self._dht = None
        self._running = False

    def add_relay_namespace(self, relay_url: str) -> None:
        """Add a relay URL for namespace lookups."""
        if relay_url not in self.relay_urls:
            self.relay_urls.append(relay_url)

    async def lookup(
        self,
        address: str,
        relay_url: Optional[str] = None,
    ) -> Optional[CodeAdvertisement]:
        """
        Look up a code advertisement.

        Args:
            address: WNS address to look up
            relay_url: Specific relay URL for namespace lookup

        Returns:
            CodeAdvertisement if found, None otherwise
        """
        if not self._running or not self._dht:
            raise RuntimeError("DHT client not running")

        # Calculate info_hash
        info_hash = wns_address_to_info_hash(address)

        # Query DHT for peers
        peers = await self._dht.get_peers(info_hash)

        if not peers:
            return None

        # Try each peer
        for peer_ip, peer_port in peers:
            try:
                ad = await self._fetch_advertisement(peer_ip, peer_port, address)
                if ad and ad.verify(expected_address=address) and not ad.is_expired():
                    return ad
            except Exception:
                continue

        return None

    async def _fetch_advertisement(
        self,
        ip: str,
        port: int,
        address: str
    ) -> Optional[CodeAdvertisement]:
        """Fetch advertisement from peer."""
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(ip, port),
                timeout=5.0
            )

            try:
                writer.write(f"GET {address}\n".encode())
                await writer.drain()

                response = await asyncio.wait_for(reader.readline(), timeout=5.0)
                response_str = response.decode("utf-8").strip()

                if response_str in ("NOT_FOUND", "") or response_str.startswith("ERROR"):
                    return None

                return CodeAdvertisement.from_json(response_str)

            finally:
                writer.close()
                await writer.wait_closed()

        except Exception:
            return None

    async def lookup_multi_namespace(
        self,
        address: str,
    ) -> Optional[Tuple[CodeAdvertisement, Optional[str]]]:
        """
        Look up in all configured namespaces.

        Returns:
            Tuple of (advertisement, relay_url) if found, None otherwise.
            relay_url is None if found in unencrypted namespace.
        """
        ad = await self.lookup(address)
        if ad:
            return (ad, None)
        return None

    async def __aenter__(self) -> "WNSDHTClient":
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.stop()
