"""
WNS Persistent Server - Long-running server with automatic code re-advertisement.

The WNS server:
1. Loads or creates a WNS identity
2. Starts a wormhole listener
3. Publishes the current code to DHT
4. When a client disconnects, generates a new code and re-publishes
5. Repeats until shutdown

This enables persistent addressing where the identity (wh://xxx.wns) stays
the same but the underlying wormhole code changes on each connection.
"""

import asyncio
import logging
import signal
from pathlib import Path
from typing import Optional, Callable, Any
from enum import Enum

from wh.wns.identity import WNSIdentity, WNSIdentityStore
from wh.wns.advertisement import CodeAdvertisement
from wh.wns.dht import WNSDHTNode, DHTConfig
from wh.core.wormhole_manager import WormholeManager


logger = logging.getLogger(__name__)


class ServiceType(Enum):
    """Type of service to run on the WNS server."""
    SSH = "ssh"
    HTTP = "http"
    NC = "nc"
    PORT = "port"


class WNSServer:
    """
    Persistent WNS server that handles connections and re-advertises codes.

    Usage:
        server = WNSServer(identity, service_type=ServiceType.SSH)
        await server.run()
    """

    def __init__(
        self,
        identity: WNSIdentity,
        service_type: ServiceType = ServiceType.SSH,
        port: Optional[int] = None,
        relay_url: Optional[str] = None,
        transit_relay: Optional[str] = None,
        dht_config: Optional[DHTConfig] = None,
        on_status: Optional[Callable[[str], None]] = None,
        advertise_to_file: bool = True,
    ):
        """
        Initialize WNS server.

        Args:
            identity: The WNS identity to use (must have private key)
            service_type: Type of service to run
            port: Port for port-forwarding mode
            relay_url: Custom wormhole relay URL
            transit_relay: Custom transit relay
            dht_config: DHT configuration
            on_status: Callback for status messages
            advertise_to_file: Also write advertisement to file
        """
        if not identity.can_sign:
            raise ValueError("Identity must have private key")

        self.identity = identity
        self.service_type = service_type
        self.port = port
        self.relay_url = relay_url
        self.transit_relay = transit_relay
        self.dht_config = dht_config or DHTConfig()
        self.on_status = on_status
        self.advertise_to_file = advertise_to_file

        self._running = False
        self._shutdown_event = asyncio.Event()
        self._dht_node: Optional[WNSDHTNode] = None
        self._current_code: Optional[str] = None
        self._connection_count = 0

    def _status(self, message: str) -> None:
        """Send status update."""
        logger.info(message)
        if self.on_status:
            self.on_status(message)

    async def _publish_advertisement(self, code: str) -> None:
        """Publish current code advertisement."""
        ad = CodeAdvertisement.create(
            identity=self.identity,
            code=code,
            ttl_seconds=self.dht_config.ttl_seconds,
        )

        # Publish to DHT
        if self._dht_node and self._dht_node.is_running:
            try:
                await self._dht_node.publish(ad)
                self._status(f"Published to DHT: {code}")
            except Exception as e:
                logger.warning(f"Failed to publish to DHT: {e}")

        # Write to file
        if self.advertise_to_file:
            try:
                ad_dir = Path.home() / ".wh" / "advertise"
                ad_dir.mkdir(parents=True, exist_ok=True)
                ad_file = ad_dir / f"{self.identity.address}.json"
                with open(ad_file, "w") as f:
                    f.write(ad.to_json())
                self._status(f"Wrote advertisement to: {ad_file}")
            except Exception as e:
                logger.warning(f"Failed to write advertisement file: {e}")

    async def _run_service(self, manager: WormholeManager) -> None:
        """Run the appropriate service based on service_type."""
        if self.service_type == ServiceType.SSH:
            await self._run_ssh_service(manager)
        elif self.service_type == ServiceType.HTTP:
            await self._run_http_service(manager)
        elif self.service_type == ServiceType.NC:
            await self._run_nc_service(manager)
        elif self.service_type == ServiceType.PORT:
            await self._run_port_service(manager)
        else:
            raise ValueError(f"Unknown service type: {self.service_type}")

    async def _run_ssh_service(self, manager: WormholeManager) -> None:
        """Run SSH server service."""
        from wh.ssh.server import WormholeSSHServer

        ssh_server = WormholeSSHServer(manager, on_status=self._status)
        await ssh_server.run()

    async def _run_http_service(self, manager: WormholeManager) -> None:
        """Run HTTP proxy service."""
        from wh.http.client import HTTPProxyHandler

        handler = HTTPProxyHandler(manager)
        await handler.run()

    async def _run_nc_service(self, manager: WormholeManager) -> None:
        """Run netcat-style service."""
        import sys
        from wh.core.protocol import BidirectionalPipe

        pipe = BidirectionalPipe(
            stdin=sys.stdin.buffer,
            stdout=sys.stdout.buffer,
            on_status=self._status,
        )
        await pipe.run_as_listener(manager, shutdown_event=self._shutdown_event)

    async def _run_port_service(self, manager: WormholeManager) -> None:
        """Run port forwarding service."""
        if not self.port:
            raise ValueError("Port required for port forwarding mode")

        from wh.ssh.server import WormholePortForwarder

        forwarder = WormholePortForwarder(
            manager,
            local_port=self.port,
            on_status=self._status,
        )
        await forwarder.run()

    async def _connection_loop(self) -> None:
        """Main loop: create wormhole, serve, repeat."""
        while not self._shutdown_event.is_set():
            self._connection_count += 1

            # Create wormhole manager
            manager = WormholeManager(
                relay_url=self.relay_url,
                transit_relay=self.transit_relay,
                on_status=self._status,
            )

            try:
                # Allocate code
                code = await manager.create_and_allocate_code()
                self._current_code = code

                if self._connection_count == 1:
                    self._status(f"Listening as: {self.identity.full_address}")

                self._status(f"Current code: {code}")

                # Publish to DHT
                await self._publish_advertisement(code)

                # Dilate for streaming
                await manager.dilate()

                # Wait for connection and serve
                self._status("Waiting for connection...")

                try:
                    await self._run_service(manager)
                except asyncio.CancelledError:
                    break

                self._status("Connection closed")

            except Exception as e:
                if not self._shutdown_event.is_set():
                    logger.error(f"Error in connection loop: {e}")
                    await asyncio.sleep(1)  # Brief pause before retry

            finally:
                try:
                    await manager.close()
                except Exception:
                    pass

    async def run(self) -> None:
        """
        Run the server until shutdown.

        This is the main entry point. Call this to start serving.
        """
        self._running = True
        self._shutdown_event.clear()

        self._status(f"Starting WNS server: {self.identity.full_address}")

        # Start DHT node
        try:
            self._dht_node = WNSDHTNode(self.dht_config)
            await self._dht_node.start()
            self._status("Joined DHT network")
        except Exception as e:
            logger.warning(f"Failed to start DHT: {e}")
            self._dht_node = None

        try:
            # Run connection loop
            await self._connection_loop()

        finally:
            # Cleanup
            if self._dht_node:
                await self._dht_node.stop()
            self._running = False
            self._status("Server stopped")

    def shutdown(self) -> None:
        """Signal the server to shut down."""
        self._status("Shutting down...")
        self._shutdown_event.set()

    @property
    def is_running(self) -> bool:
        """Check if server is running."""
        return self._running

    @property
    def current_code(self) -> Optional[str]:
        """Get the current wormhole code."""
        return self._current_code

    @property
    def address(self) -> str:
        """Get the WNS address."""
        return self.identity.full_address


async def run_wns_server(
    identity_address: Optional[str] = None,
    service_type: str = "ssh",
    port: Optional[int] = None,
    relay_url: Optional[str] = None,
    on_status: Optional[Callable[[str], None]] = None,
) -> None:
    """
    Convenience function to run a WNS server.

    Args:
        identity_address: WNS address to use (default: first/default identity)
        service_type: Service type ("ssh", "http", "nc", "port")
        port: Port for port forwarding mode
        relay_url: Custom wormhole relay URL
        on_status: Status callback
    """
    # Load identity
    store = WNSIdentityStore()

    if identity_address:
        identity = store.load_identity(identity_address)
        if not identity:
            raise ValueError(f"Identity not found: {identity_address}")
    else:
        identity = store.get_default_identity()
        if not identity:
            raise ValueError("No identity found. Create one with: wh identity create")

    # Parse service type
    svc_type = ServiceType(service_type.lower())

    # Create and run server
    server = WNSServer(
        identity=identity,
        service_type=svc_type,
        port=port,
        relay_url=relay_url,
        on_status=on_status,
    )

    # Handle signals
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, server.shutdown)

    await server.run()
