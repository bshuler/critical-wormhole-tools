"""
WNS DHT - Kademlia-based distributed hash table for code discovery.

The DHT allows servers to publish their current wormhole codes and clients
to discover them without any centralized infrastructure.

Key design:
    - Key: sha256(wns_address) - derived from the WNS address
    - Value: JSON-encoded signed CodeAdvertisement
    - TTL: 5 minutes (servers republish periodically)

Namespace Encryption (optional):
    When a relay URL is provided, advertisements are encrypted:
    - DHT Key: namespace_dht_key(address, relay_url) - prevents correlation
    - Value: encrypt_for_namespace(advertisement, relay_url)
    - Only users who know the relay URL can discover addresses
"""

import asyncio
import hashlib
import logging
from typing import Optional, Callable, List, Tuple
from dataclasses import dataclass

from kademlia.network import Server as KademliaServer

from wh.wns.advertisement import CodeAdvertisement
from wh.wns.namespace import (
    namespace_dht_key,
    encrypt_for_namespace,
    decrypt_for_namespace,
)


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


def address_to_dht_key(address: str, relay_url: Optional[str] = None) -> bytes:
    """
    Convert a WNS address to a DHT key.

    If relay_url is provided, the key is namespace-scoped for privacy.
    """
    if relay_url:
        return namespace_dht_key(address, relay_url)
    return hashlib.sha256(address.encode("utf-8")).digest()


@dataclass
class DHTConfig:
    """Configuration for DHT node."""

    port: int = DEFAULT_DHT_PORT
    bootstrap_nodes: List[Tuple[str, int]] = None  # type: ignore
    ttl_seconds: int = DEFAULT_TTL_SECONDS
    republish_interval: int = DEFAULT_REPUBLISH_INTERVAL
    relay_url: Optional[str] = None  # For namespace encryption
    encrypt_advertisements: bool = False  # Enable namespace encryption

    def __post_init__(self):
        if self.bootstrap_nodes is None:
            self.bootstrap_nodes = DEFAULT_BOOTSTRAP_NODES.copy()
        # Auto-enable encryption if relay_url is provided
        if self.relay_url and not self.encrypt_advertisements:
            self.encrypt_advertisements = True


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

        If namespace encryption is enabled (via config.relay_url), the
        advertisement will be encrypted and stored under a namespace-scoped key.

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

        # Convert to DHT key (namespace-scoped if relay_url configured)
        key = address_to_dht_key(advertisement.address, self.config.relay_url)

        # Prepare value - encrypt if configured
        json_value = advertisement.to_json()
        if self.config.encrypt_advertisements and self.config.relay_url:
            value = encrypt_for_namespace(json_value.encode("utf-8"), self.config.relay_url)
            logger.debug(f"Publishing encrypted to DHT: {advertisement.address}")
        else:
            value = json_value
            logger.debug(f"Publishing to DHT: {advertisement.address} -> {advertisement.code}")

        # Store in DHT
        await self._server.set(key, value)

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

        If relay_url is provided (or configured), looks up using namespace-scoped
        key and decrypts the result.

        Args:
            address: The WNS address to look up (without wh:// prefix)
            relay_url: Optional relay URL for namespace lookup (overrides config)

        Returns:
            The code advertisement if found and valid, None otherwise
        """
        if not self._running or not self._server:
            raise RuntimeError("DHT node not running")

        # Use provided relay_url or fall back to config
        effective_relay = relay_url or self.config.relay_url

        # Convert to DHT key (namespace-scoped if relay provided)
        key = address_to_dht_key(address, effective_relay)

        # Lookup in DHT
        logger.debug(f"Looking up in DHT: {address}" + (f" (namespace: {effective_relay[:30]}...)" if effective_relay else ""))
        value = await self._server.get(key)

        if value is None:
            logger.debug(f"Not found in DHT: {address}")
            return None

        try:
            # Decrypt if namespace encryption is used
            if effective_relay and isinstance(value, bytes):
                decrypted = decrypt_for_namespace(value, effective_relay)
                if decrypted is None:
                    logger.warning(f"Failed to decrypt advertisement for {address}")
                    return None
                json_value = decrypted.decode("utf-8")
            else:
                json_value = value if isinstance(value, str) else value.decode("utf-8")

            # Parse and verify the advertisement
            ad = CodeAdvertisement.from_json(json_value)

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

    Supports namespace encryption for privacy-preserving lookups.
    """

    def __init__(
        self,
        bootstrap_nodes: Optional[List[Tuple[str, int]]] = None,
        relay_urls: Optional[List[str]] = None,
    ):
        """
        Initialize DHT client.

        Args:
            bootstrap_nodes: DHT bootstrap nodes
            relay_urls: List of relay URLs to try for namespace lookups.
                       If provided, lookups will try each namespace in order.
        """
        self.bootstrap_nodes = bootstrap_nodes or DEFAULT_BOOTSTRAP_NODES.copy()
        self.relay_urls = relay_urls or []
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
            relay_url: Specific relay URL for namespace lookup.
                      If None and relay_urls configured, tries each in order.

        Returns:
            CodeAdvertisement if found, None otherwise
        """
        if not self._running or not self._server:
            raise RuntimeError("DHT client not running")

        # If specific relay provided, use it
        if relay_url:
            return await self._lookup_in_namespace(address, relay_url)

        # If relay_urls configured, try each namespace
        if self.relay_urls:
            for url in self.relay_urls:
                ad = await self._lookup_in_namespace(address, url)
                if ad:
                    return ad
            # Also try unencrypted as fallback
            return await self._lookup_in_namespace(address, None)

        # No namespaces configured, do plain lookup
        return await self._lookup_in_namespace(address, None)

    async def _lookup_in_namespace(
        self,
        address: str,
        relay_url: Optional[str],
    ) -> Optional[CodeAdvertisement]:
        """Look up in a specific namespace (or unencrypted if relay_url is None)."""
        key = address_to_dht_key(address, relay_url)
        value = await self._server.get(key)

        if value is None:
            return None

        try:
            # Decrypt if namespace is specified
            if relay_url and isinstance(value, bytes):
                decrypted = decrypt_for_namespace(value, relay_url)
                if decrypted is None:
                    return None
                json_value = decrypted.decode("utf-8")
            else:
                json_value = value if isinstance(value, str) else value.decode("utf-8")

            ad = CodeAdvertisement.from_json(json_value)
            if ad.verify(expected_address=address) and not ad.is_expired():
                return ad
        except Exception:
            pass

        return None

    async def lookup_multi_namespace(
        self,
        address: str,
    ) -> Optional[Tuple[CodeAdvertisement, Optional[str]]]:
        """
        Look up in all configured namespaces, returning the result and which namespace.

        Returns:
            Tuple of (advertisement, relay_url) if found, None otherwise.
            relay_url is None if found in unencrypted namespace.
        """
        if not self._running or not self._server:
            raise RuntimeError("DHT client not running")

        # Try each configured namespace
        for url in self.relay_urls:
            ad = await self._lookup_in_namespace(address, url)
            if ad:
                return (ad, url)

        # Try unencrypted
        ad = await self._lookup_in_namespace(address, None)
        if ad:
            return (ad, None)

        return None

    async def __aenter__(self) -> "WNSDHTClient":
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.stop()
