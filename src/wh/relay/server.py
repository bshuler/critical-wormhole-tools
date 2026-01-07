"""
Combined relay server that runs both mailbox and transit relay.

This makes `wh` completely self-contained - no external infrastructure needed.
"""

import asyncio
import logging
import signal

from .mailbox import MailboxServer
from .transit import TransitRelay

logger = logging.getLogger(__name__)


class RelayServer:
    """
    Combined wormhole relay server.

    Runs both the mailbox (rendezvous) and transit (data relay) servers
    in a single process.

    Example:
        server = RelayServer(mailbox_port=4000, transit_port=4001)
        await server.serve_forever()
    """

    def __init__(
        self,
        host: str = "0.0.0.0",
        mailbox_port: int = 4000,
        transit_port: int = 4001,
        app_id: str = "wh.tools/v1",
    ):
        self.host = host
        self.mailbox_port = mailbox_port
        self.transit_port = transit_port

        self.mailbox = MailboxServer(
            host=host,
            port=mailbox_port,
            app_id=app_id,
        )

        self.transit = TransitRelay(
            host=host,
            port=transit_port,
        )

        self._running = False

    async def start(self) -> None:
        """Start both relay servers."""
        await self.mailbox.start()
        await self.transit.start()
        self._running = True

        logger.info(
            f"Relay server started:\n"
            f"  Mailbox: ws://{self.host}:{self.mailbox_port}/v1\n"
            f"  Transit: tcp://{self.host}:{self.transit_port}"
        )

    async def stop(self) -> None:
        """Stop both relay servers."""
        self._running = False
        await self.mailbox.stop()
        await self.transit.stop()
        logger.info("Relay server stopped")

    async def serve_forever(self) -> None:
        """Run the relay server until interrupted."""
        await self.start()

        # Set up signal handlers
        loop = asyncio.get_event_loop()
        stop_event = asyncio.Event()

        def signal_handler():
            logger.info("Shutdown signal received")
            stop_event.set()

        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, signal_handler)
            except NotImplementedError:
                # Windows doesn't support add_signal_handler
                pass

        try:
            await stop_event.wait()
        except asyncio.CancelledError:
            pass
        finally:
            await self.stop()

    def get_stats(self) -> dict:
        """Get relay statistics."""
        return {
            "mailbox": {
                "nameplates": len(self.mailbox.nameplates),
                "mailboxes": len(self.mailbox.mailboxes),
                "clients": len(self.mailbox.clients),
            },
            "transit": self.transit.stats.copy(),
        }


async def run_relay(
    host: str = "0.0.0.0",
    mailbox_port: int = 4000,
    transit_port: int = 4001,
    verbose: bool = False,
) -> None:
    """
    Run a wormhole relay server.

    Args:
        host: Host to bind to
        mailbox_port: Port for mailbox (WebSocket) server
        transit_port: Port for transit (TCP) relay
        verbose: Enable verbose logging
    """
    if verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    server = RelayServer(
        host=host,
        mailbox_port=mailbox_port,
        transit_port=transit_port,
    )

    await server.serve_forever()
