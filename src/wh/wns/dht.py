"""
WNS DHT - Kademlia-based distributed hash table for code discovery.

The DHT allows servers to publish their current wormhole codes and clients
to discover them without any centralized infrastructure.

Key design:
    - Key: sha256(wns_address) - derived from the WNS address
    - Value: JSON-encoded signed CodeAdvertisement
    - TTL: 5 minutes (servers republish periodically)
"""

import asyncio
import hashlib
import logging
from typing import Optional, Callable, List, Tuple
from dataclasses import dataclass

from kademlia.network import Server as KademliaServer

from wh.wns.advertisement import CodeAdvertisement


logger = logging.getLogger(__name__)

# Default DHT configuration
DEFAULT_DHT_PORT = 8469  # "WH" in phone keypad
DEFAULT_TTL_SECONDS = 300  # 5 minutes
DEFAULT_REPUBLISH_INTERVAL = 240  # 4 minutes (before TTL expires)

# Bootstrap nodes - these can be configured
# In production, we'd use well-known stable nodes
DEFAULT_BOOTSTRAP_NODES: List[Tuple[str, int]] = [
    # TODO: Set up public bootstrap nodes
    # ("bootstrap1.wns.example.com", 8469),
    # ("bootstrap2.wns.example.com", 8469),
]


def address_to_dht_key(address: str) -> bytes:
    """Convert a WNS address to a DHT key."""
    return hashlib.sha256(address.encode("utf-8")).digest()


@dataclass
class DHTConfig:
    """Configuration for DHT node."""

    port: int = DEFAULT_DHT_PORT
    bootstrap_nodes: List[Tuple[str, int]] = None  # type: ignore
    ttl_seconds: int = DEFAULT_TTL_SECONDS
    republish_interval: int = DEFAULT_REPUBLISH_INTERVAL

    def __post_init__(self):
        if self.bootstrap_nodes is None:
            self.bootstrap_nodes = DEFAULT_BOOTSTRAP_NODES.copy()


class WNSDHTNode:
    """
    A DHT node for publishing and discovering WNS code advertisements.

    This wraps the Kademlia library to provide WNS-specific functionality.
    """

    def __init__(self, config: Optional[DHTConfig] = None):
        """Initialize DHT node."""
        self.config = config or DHTConfig()
        self._server: Optional[KademliaServer] = None
        self._running = False
        self._republish_task: Optional[asyncio.Task] = None
        self._published_ads: dict[str, CodeAdvertisement] = {}
        self._on_republish: Optional[Callable[[str], CodeAdvertisement]] = None

    async def start(self, port: Optional[int] = None) -> None:
        """Start the DHT node and join the network."""
        if self._running:
            return

        port = port or self.config.port
        self._server = KademliaServer()

        # Listen on the specified port
        await self._server.listen(port)
        logger.info(f"DHT node listening on port {port}")

        # Bootstrap to the network
        if self.config.bootstrap_nodes:
            logger.info(f"Bootstrapping to {len(self.config.bootstrap_nodes)} nodes")
            await self._server.bootstrap(self.config.bootstrap_nodes)

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

        # Stop the server
        if self._server:
            self._server.stop()
            self._server = None

        self._running = False
        logger.info("DHT node stopped")

    @property
    def is_running(self) -> bool:
        """Check if the DHT node is running."""
        return self._running

    async def publish(self, advertisement: CodeAdvertisement) -> bool:
        """
        Publish a code advertisement to the DHT.

        Args:
            advertisement: The signed code advertisement to publish

        Returns:
            True if published successfully
        """
        if not self._running or not self._server:
            raise RuntimeError("DHT node not running")

        # Verify the advertisement before publishing
        if not advertisement.verify():
            raise ValueError("Cannot publish invalid advertisement")

        # Convert to DHT key and value
        key = address_to_dht_key(advertisement.address)
        value = advertisement.to_json()

        # Store in DHT
        logger.debug(f"Publishing to DHT: {advertisement.address} -> {advertisement.code}")
        await self._server.set(key, value)

        # Track for republishing
        self._published_ads[advertisement.address] = advertisement

        return True

    async def lookup(self, address: str) -> Optional[CodeAdvertisement]:
        """
        Look up a code advertisement in the DHT.

        Args:
            address: The WNS address to look up (without wh:// prefix)

        Returns:
            The code advertisement if found and valid, None otherwise
        """
        if not self._running or not self._server:
            raise RuntimeError("DHT node not running")

        # Convert to DHT key
        key = address_to_dht_key(address)

        # Lookup in DHT
        logger.debug(f"Looking up in DHT: {address}")
        value = await self._server.get(key)

        if value is None:
            logger.debug(f"Not found in DHT: {address}")
            return None

        try:
            # Parse and verify the advertisement
            ad = CodeAdvertisement.from_json(value)

            # Verify signature and address match
            if not ad.verify(expected_address=address):
                logger.warning(f"Invalid advertisement for {address}")
                return None

            # Check if expired
            if ad.is_expired():
                logger.debug(f"Expired advertisement for {address}")
                return None

            logger.debug(f"Found in DHT: {address} -> {ad.code}")
            return ad

        except Exception as e:
            logger.warning(f"Failed to parse advertisement for {address}: {e}")
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

                        if ad:
                            await self.publish(ad)
                            logger.debug(f"Republished: {address}")
                    except Exception as e:
                        logger.warning(f"Failed to republish {address}: {e}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in republish loop: {e}")

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
    """

    def __init__(self, bootstrap_nodes: Optional[List[Tuple[str, int]]] = None):
        """Initialize DHT client."""
        self.bootstrap_nodes = bootstrap_nodes or DEFAULT_BOOTSTRAP_NODES.copy()
        self._server: Optional[KademliaServer] = None
        self._running = False

    async def start(self) -> None:
        """Start the DHT client."""
        if self._running:
            return

        self._server = KademliaServer()

        # Listen on random port (we don't need incoming connections)
        await self._server.listen(0)

        # Bootstrap to network
        if self.bootstrap_nodes:
            await self._server.bootstrap(self.bootstrap_nodes)

        self._running = True

    async def stop(self) -> None:
        """Stop the DHT client."""
        if self._server:
            self._server.stop()
            self._server = None
        self._running = False

    async def lookup(self, address: str) -> Optional[CodeAdvertisement]:
        """Look up a code advertisement."""
        if not self._running or not self._server:
            raise RuntimeError("DHT client not running")

        key = address_to_dht_key(address)
        value = await self._server.get(key)

        if value is None:
            return None

        try:
            ad = CodeAdvertisement.from_json(value)
            if ad.verify(expected_address=address) and not ad.is_expired():
                return ad
        except Exception:
            pass

        return None

    async def __aenter__(self) -> "WNSDHTClient":
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.stop()
