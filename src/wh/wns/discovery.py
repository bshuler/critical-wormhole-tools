"""
WNS Discovery - Unified interface for discovering wormhole codes.

Supports multiple discovery backends:
    - DHT (Kademlia) - primary, decentralized
    - File - local filesystem (for testing/local use)
    - HTTP - fetch from URL

Supports multiple name types:
    - Full address: wh://abc123def456.wns
    - Scoped name: wh://laptop.abc123def456.wns
    - Global name: wh://laptop.wns (first-come-first-served)
    - Local alias: laptop (resolved via AliasStore)

Clients use the Discovery class which tries backends in order.
"""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, List, Tuple

import httpx

from wh.wns.advertisement import CodeAdvertisement
from wh.wns.identity import (
    WNSIdentity,
    WNSIdentityStore,
    parse_wns_address,
    parse_scoped_wns_address,
)
from wh.wns.names import (
    NameClaim,
    NameClaimStore,
    is_global_name_address,
    parse_global_name,
    name_to_dht_key,
)


logger = logging.getLogger(__name__)


class DiscoveryBackend(ABC):
    """Abstract base class for discovery backends."""

    @abstractmethod
    async def lookup(self, address: str) -> Optional[CodeAdvertisement]:
        """
        Look up a code advertisement for an address.

        Args:
            address: The WNS address (without wh:// prefix or .wns suffix)

        Returns:
            CodeAdvertisement if found and valid, None otherwise
        """
        pass

    @abstractmethod
    async def start(self) -> None:
        """Start the backend (if needed)."""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Stop the backend."""
        pass


class DHTDiscovery(DiscoveryBackend):
    """Discovery via Kademlia DHT."""

    def __init__(self, bootstrap_nodes: Optional[List[tuple]] = None):
        from wh.wns.dht import WNSDHTClient
        self._client = WNSDHTClient(bootstrap_nodes=bootstrap_nodes)

    async def start(self) -> None:
        await self._client.start()

    async def stop(self) -> None:
        await self._client.stop()

    async def lookup(self, address: str) -> Optional[CodeAdvertisement]:
        return await self._client.lookup(address)

    async def lookup_name_claim(self, name: str) -> Optional[NameClaim]:
        """
        Look up a global name claim in the DHT.

        Args:
            name: The global name to look up

        Returns:
            NameClaim if found and valid, None otherwise
        """
        if not self._client._running or not self._client._server:
            return None

        key = name_to_dht_key(name)
        value = await self._client._server.get(key)

        if value is None:
            return None

        try:
            claim = NameClaim.from_json(value)
            if claim.verify(expected_name=name) and not claim.is_expired():
                return claim
        except Exception as e:
            logger.debug(f"Failed to parse name claim for {name}: {e}")

        return None


class FileDiscovery(DiscoveryBackend):
    """
    Discovery via local filesystem.

    Looks for advertisements in:
        ~/.wh/advertise/<address>.json
    """

    def __init__(self, base_path: Optional[Path] = None):
        if base_path is None:
            base_path = Path.home() / ".wh" / "advertise"
        self.base_path = Path(base_path)

    async def start(self) -> None:
        pass  # No setup needed

    async def stop(self) -> None:
        pass

    async def lookup(self, address: str) -> Optional[CodeAdvertisement]:
        ad_file = self.base_path / f"{address}.json"

        if not ad_file.exists():
            return None

        try:
            with open(ad_file) as f:
                ad = CodeAdvertisement.from_json(f.read())

            # Verify and check expiry
            if ad.verify(expected_address=address) and not ad.is_expired():
                return ad

        except Exception as e:
            logger.debug(f"Failed to read advertisement from {ad_file}: {e}")

        return None


class HTTPDiscovery(DiscoveryBackend):
    """
    Discovery via HTTP endpoint.

    Fetches from: {url_template.format(address=address)}

    Default template: https://{address}.wns.example.com/.well-known/wns
    """

    def __init__(
        self,
        url_template: Optional[str] = None,
        timeout: float = 10.0,
    ):
        self.url_template = url_template or "https://{address}.wns.example.com/.well-known/wns"
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def start(self) -> None:
        self._client = httpx.AsyncClient(timeout=self.timeout)

    async def stop(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def lookup(self, address: str) -> Optional[CodeAdvertisement]:
        if not self._client:
            return None

        url = self.url_template.format(address=address)

        try:
            response = await self._client.get(url)
            response.raise_for_status()

            ad = CodeAdvertisement.from_json(response.text)

            if ad.verify(expected_address=address) and not ad.is_expired():
                return ad

        except Exception as e:
            logger.debug(f"HTTP discovery failed for {address}: {e}")

        return None


class Discovery:
    """
    Unified discovery interface that tries multiple backends.

    Usage:
        async with Discovery() as discovery:
            ad = await discovery.lookup("abc123def456")
            if ad:
                code = ad.code  # Use this to connect
    """

    def __init__(
        self,
        backends: Optional[List[DiscoveryBackend]] = None,
        use_dht: bool = True,
        use_file: bool = True,
        use_http: bool = False,
        http_url_template: Optional[str] = None,
        dht_bootstrap_nodes: Optional[List[tuple]] = None,
    ):
        """
        Initialize discovery with specified backends.

        Args:
            backends: Custom list of backends (overrides other options)
            use_dht: Enable DHT discovery (default True)
            use_file: Enable file-based discovery (default True)
            use_http: Enable HTTP discovery (default False)
            http_url_template: URL template for HTTP discovery
            dht_bootstrap_nodes: Bootstrap nodes for DHT
        """
        if backends:
            self._backends = backends
        else:
            self._backends = []

            # File is fastest, try first
            if use_file:
                self._backends.append(FileDiscovery())

            # DHT is primary
            if use_dht:
                self._backends.append(DHTDiscovery(bootstrap_nodes=dht_bootstrap_nodes))

            # HTTP is fallback
            if use_http:
                self._backends.append(HTTPDiscovery(url_template=http_url_template))

        self._store = WNSIdentityStore()
        self._started = False

    async def start(self) -> None:
        """Start all backends."""
        if self._started:
            return

        for backend in self._backends:
            try:
                await backend.start()
            except Exception as e:
                logger.warning(f"Failed to start {backend.__class__.__name__}: {e}")

        self._started = True

    async def stop(self) -> None:
        """Stop all backends."""
        for backend in self._backends:
            try:
                await backend.stop()
            except Exception as e:
                logger.warning(f"Failed to stop {backend.__class__.__name__}: {e}")

        self._started = False

    async def lookup(
        self,
        address_or_name: str,
        verify_known_host: bool = True,
    ) -> Optional[CodeAdvertisement]:
        """
        Look up a code advertisement.

        Supports multiple name types:
        - Full address: wh://abc123def456.wns
        - Scoped name: wh://laptop.abc123def456.wns
        - Global name: wh://laptop.wns (looks up name claim first)

        Args:
            address_or_name: WNS address or name (with or without wh:// prefix)
            verify_known_host: If True, verify against cached public key (TOFU)

        Returns:
            CodeAdvertisement if found and valid, None otherwise
        """
        if not self._started:
            await self.start()

        # Check if it's a global name (wh://name.wns)
        global_name = parse_global_name(address_or_name)
        if global_name:
            # Look up the name claim to get the address
            address = await self._resolve_global_name(global_name)
            if not address:
                logger.warning(f"Global name not found: {global_name}")
                return None
            logger.info(f"Resolved global name {global_name} -> {address}")
        else:
            # Parse as address (may include scoped name)
            parsed = parse_wns_address(address_or_name)
            if not parsed:
                logger.warning(f"Invalid WNS address: {address_or_name}")
                return None
            address = parsed

        # Try each backend
        for backend in self._backends:
            try:
                ad = await backend.lookup(address)
                if ad:
                    # Verify against known host if we have one
                    if verify_known_host:
                        known = self._store.load_known_host(address)
                        if known and known.public_key != ad.public_key:
                            logger.warning(
                                f"Public key mismatch for {address}! "
                                "Possible impersonation attack."
                            )
                            continue  # Try next backend

                    logger.info(f"Discovered {address} -> {ad.code} via {backend.__class__.__name__}")
                    return ad

            except Exception as e:
                logger.debug(f"{backend.__class__.__name__} failed for {address}: {e}")

        return None

    async def _resolve_global_name(self, name: str) -> Optional[str]:
        """
        Resolve a global name to a WNS address.

        Checks:
        1. Local name claims first
        2. DHT for published claims
        """
        # Check local claims
        name_store = NameClaimStore()
        local_claim = name_store.load_claim(name)
        if local_claim and not local_claim.is_expired():
            logger.debug(f"Found local claim for {name}")
            return local_claim.address

        # Check DHT
        for backend in self._backends:
            if isinstance(backend, DHTDiscovery):
                claim = await backend.lookup_name_claim(name)
                if claim:
                    logger.debug(f"Found DHT claim for {name}")
                    return claim.address

        return None

    async def lookup_and_cache(
        self,
        address: str,
    ) -> Optional[CodeAdvertisement]:
        """
        Look up and cache the public key (TOFU model).

        On first connection, saves the public key to known_hosts.
        On subsequent connections, verifies against cached key.
        """
        ad = await self.lookup(address, verify_known_host=True)

        if ad:
            # Check if we have this in known_hosts
            known = self._store.load_known_host(address)
            if not known:
                # First time seeing this address - save it (TOFU)
                identity = WNSIdentity.from_public_key(ad.public_key)
                self._store.save_known_host(identity)
                logger.info(f"Added {address} to known hosts (TOFU)")

        return ad

    async def __aenter__(self) -> "Discovery":
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.stop()


async def discover_code(address: str) -> Optional[str]:
    """
    Convenience function to discover a wormhole code.

    Args:
        address: WNS address (e.g., "wh://abc123.wns" or just "abc123")

    Returns:
        The wormhole code if found, None otherwise
    """
    async with Discovery() as discovery:
        ad = await discovery.lookup_and_cache(address)
        if ad:
            return ad.code
    return None
