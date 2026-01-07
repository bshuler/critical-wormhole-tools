"""
WormholeManager - Central abstraction for Magic Wormhole connections.

Manages wormhole lifecycle, code allocation, and dilation for streaming.
Supports both ephemeral wormhole codes and persistent WNS addresses.
"""

import logging
from typing import Optional, Callable, Any, Tuple
import asyncio
from twisted.internet import defer
from twisted.internet.defer import inlineCallbacks
from wormhole import create

from wh.wns.identity import is_wns_address, parse_wns_address


logger = logging.getLogger(__name__)


class WormholeManager:
    """
    Manages Magic Wormhole connection lifecycle with Dilation support.

    Provides:
    - Code generation/input (7-guitar-sunset format)
    - Automatic dilation for streaming
    - Subchannel management
    - Connection durability

    Example usage:
        # Initiator (generates code)
        manager = WormholeManager()
        code = await manager.create_and_allocate_code()
        print(f"Share this code: {code}")
        endpoints = await manager.dilate()

        # Responder (uses code)
        manager = WormholeManager()
        await manager.create_and_set_code("7-guitar-sunset")
        endpoints = await manager.dilate()
    """

    DEFAULT_APPID = "wh.tools/v1"
    DEFAULT_RELAY = "ws://relay.magic-wormhole.io:4000/v1"
    DEFAULT_TRANSIT_RELAY = "tcp:transit.magic-wormhole.io:4001"

    def __init__(
        self,
        appid: Optional[str] = None,
        relay_url: Optional[str] = None,
        transit_relay: Optional[str] = None,
        code_length: int = 2,
        on_status: Optional[Callable[[str], None]] = None,
    ):
        """
        Initialize WormholeManager.

        Args:
            appid: Application ID for wormhole namespace isolation.
            relay_url: Mailbox relay URL.
            transit_relay: Transit relay for data transfer.
            code_length: Number of words in code (default 2 = number-word-word).
            on_status: Callback for status updates.
        """
        self.appid = appid or self.DEFAULT_APPID
        self.relay_url = relay_url or self.DEFAULT_RELAY
        self.transit_relay = transit_relay or self.DEFAULT_TRANSIT_RELAY
        self.code_length = code_length
        self.on_status = on_status

        self._wormhole: Optional[Any] = None
        self._code: Optional[str] = None
        self._wns_address: Optional[str] = None  # Original WNS address if used
        self._dilated: bool = False
        self._dilated_wormhole: Optional[Any] = None  # DilatedWormhole object
        self._versions: Optional[dict] = None

    def _status(self, message: str) -> None:
        """Send status update if callback registered."""
        if self.on_status:
            self.on_status(message)

    def _get_event_loop(self):
        """Get or create an event loop for the current thread."""
        try:
            return asyncio.get_event_loop()
        except RuntimeError:
            # No event loop in this thread, create one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop

    async def _resolve_wns_address(self, address: str) -> str:
        """
        Resolve a WNS address to a wormhole code.

        Args:
            address: WNS address (e.g., "wh://abc123.wns" or "abc123")

        Returns:
            The wormhole code to connect with.

        Raises:
            ValueError: If address cannot be resolved.
        """
        from wh.wns.discovery import Discovery

        self._status(f"Resolving WNS address: {address}")

        async with Discovery() as discovery:
            ad = await discovery.lookup_and_cache(address)

            if not ad:
                raise ValueError(f"Could not resolve WNS address: {address}")

            self._status(f"Resolved to code: {ad.code}")
            logger.info(f"WNS {address} -> {ad.code}")

            return ad.code

    async def _deferred_to_future(self, d: defer.Deferred) -> Any:
        """Convert a Twisted Deferred to an asyncio Future."""
        loop = self._get_event_loop()
        future = loop.create_future()

        def callback(result):
            if not future.done():
                loop.call_soon_threadsafe(future.set_result, result)

        def errback(failure):
            if not future.done():
                loop.call_soon_threadsafe(future.set_exception, failure.value)

        d.addCallbacks(callback, errback)
        return await future

    @inlineCallbacks
    def create_and_allocate_code_deferred(self):
        """
        Create wormhole and generate a new code (Twisted Deferred version).

        Returns:
            Deferred that fires with the allocated wormhole code.
        """
        from twisted.internet import reactor

        self._status("Creating wormhole...")
        self._wormhole = create(
            self.appid,
            self.relay_url,
            reactor,
            versions={"wh.tools/v1": {}},
            dilation=True,
        )

        self._status("Allocating code...")
        yield self._wormhole.allocate_code(self.code_length)

        self._code = yield self._wormhole.get_code()
        self._status(f"Code allocated: {self._code}")

        return self._code

    async def create_and_allocate_code(self) -> str:
        """
        Create wormhole and generate a new code (initiator side).

        Returns:
            The allocated wormhole code (e.g., "7-guitar-sunset").
        """
        d = self.create_and_allocate_code_deferred()
        return await self._deferred_to_future(d)

    @inlineCallbacks
    def create_and_set_code_deferred(self, code: str):
        """
        Create wormhole with existing code (Twisted Deferred version).

        Args:
            code: The wormhole code to connect with.
        """
        from twisted.internet import reactor

        self._status("Creating wormhole...")
        self._wormhole = create(
            self.appid,
            self.relay_url,
            reactor,
            versions={"wh.tools/v1": {}},
            dilation=True,
        )

        self._status(f"Setting code: {code}")
        self._wormhole.set_code(code)
        self._code = code

        # Yield to make this a proper generator for @inlineCallbacks
        yield defer.succeed(None)
        return None

    async def create_and_set_code(self, code_or_address: str) -> None:
        """
        Create wormhole with existing code, WNS address, or alias (responder side).

        Accepts:
        - Regular wormhole codes: "7-guitar-sunset"
        - WNS addresses: "wh://abc123.wns"
        - Local aliases: "laptop" (if defined via `wh alias add`)

        WNS addresses and aliases are automatically resolved to wormhole codes.

        Args:
            code_or_address: The wormhole code, WNS address, or alias to connect with.
        """
        from wh.wns.aliases import AliasStore

        code = code_or_address

        # First, check if it's a local alias
        store = AliasStore()
        resolved = store.resolve(code_or_address)
        if resolved:
            self._status(f"Resolved alias '{code_or_address}' -> {resolved}")
            code_or_address = resolved

        # Check if this is a WNS address (or was resolved to one)
        if is_wns_address(code_or_address):
            self._wns_address = code_or_address
            code = await self._resolve_wns_address(code_or_address)
        else:
            code = code_or_address

        d = self.create_and_set_code_deferred(code)
        return await self._deferred_to_future(d)

    @inlineCallbacks
    def verify_connection_deferred(self):
        """
        Wait for the connection to be established (Twisted Deferred version).

        Returns:
            Deferred that fires with peer's advertised versions.
        """
        if not self._wormhole:
            raise RuntimeError("Wormhole not created")

        self._status("Waiting for peer...")
        self._versions = yield self._wormhole.get_versions()
        self._status("Connected to peer")

        return self._versions

    async def verify_connection(self) -> dict:
        """
        Wait for the connection to be established and get peer versions.

        Returns:
            Dictionary of peer's advertised versions.
        """
        d = self.verify_connection_deferred()
        return await self._deferred_to_future(d)

    @inlineCallbacks
    def dilate_deferred(self):
        """
        Dilate the wormhole for streaming (Twisted Deferred version).

        Returns:
            Deferred that fires with DilatedWormhole object.
        """
        if not self._wormhole:
            raise RuntimeError("Wormhole not created")

        self._status("Dilating wormhole...")

        # Get versions first to ensure connection is established
        if not self._versions:
            yield self.verify_connection_deferred()

        # Dilate for streaming - returns DilatedWormhole object
        self._dilated_wormhole = self._wormhole.dilate()

        # Wait for dilation to complete
        yield self._dilated_wormhole.when_dilated()

        self._dilated = True
        self._status("Wormhole dilated, ready for streaming")

        return self._dilated_wormhole

    async def dilate(self) -> Any:
        """
        Dilate the wormhole for streaming communication.

        Dilation provides reliable, ordered, bidirectional streaming
        through the wormhole, suitable for tunneling protocols like SSH.

        Returns:
            DilatedWormhole object with methods:
            - connector_for(name): Get client endpoint for protocol
            - listener_for(name): Get server endpoint for protocol
        """
        d = self.dilate_deferred()
        return await self._deferred_to_future(d)

    @property
    def code(self) -> Optional[str]:
        """Get the current wormhole code."""
        return self._code

    @property
    def wns_address(self) -> Optional[str]:
        """Get the WNS address if one was used to connect."""
        return self._wns_address

    @property
    def is_dilated(self) -> bool:
        """Check if wormhole has been dilated."""
        return self._dilated

    @property
    def dilated_wormhole(self) -> Optional[Any]:
        """Get the DilatedWormhole object if dilated."""
        return self._dilated_wormhole

    def connector_for(self, protocol_name: str = "wh") -> Any:
        """
        Get a client endpoint for connecting to peer.

        Args:
            protocol_name: Name of the subprotocol (default "wh")

        Returns:
            IStreamClientEndpoint for creating subchannels
        """
        if not self._dilated_wormhole:
            raise RuntimeError("Wormhole not dilated")
        return self._dilated_wormhole.connector_for(protocol_name)

    def listener_for(self, protocol_name: str = "wh") -> Any:
        """
        Get a server endpoint for accepting connections from peer.

        Args:
            protocol_name: Name of the subprotocol (default "wh")

        Returns:
            IStreamServerEndpoint for listening on subchannels
        """
        if not self._dilated_wormhole:
            raise RuntimeError("Wormhole not dilated")
        return self._dilated_wormhole.listener_for(protocol_name)

    @inlineCallbacks
    def close_deferred(self):
        """Gracefully close the wormhole (Twisted Deferred version)."""
        if self._wormhole:
            self._status("Closing wormhole...")
            try:
                yield self._wormhole.close()
            except Exception:
                pass  # Ignore errors during close
            self._wormhole = None
            self._dilated = False
            self._dilated_wormhole = None
            self._code = None
            self._wns_address = None
            self._status("Wormhole closed")

        return None

    async def close(self) -> None:
        """Gracefully close the wormhole connection."""
        d = self.close_deferred()
        return await self._deferred_to_future(d)

    async def __aenter__(self) -> "WormholeManager":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit - close wormhole."""
        await self.close()
