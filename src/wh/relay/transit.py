"""
Transit relay for wormhole data transfer.

When two wormhole clients cannot establish a direct connection (due to
NAT, firewall, etc.), they can relay data through this server.

Protocol:
1. Client sends: "please relay <token>\n"
2. Server waits for matching token from another client
3. Once matched, server relays data bidirectionally
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple
import time

logger = logging.getLogger(__name__)


@dataclass
class PendingConnection:
    """A client waiting for a peer with matching token."""
    reader: asyncio.StreamReader
    writer: asyncio.StreamWriter
    token: str
    timestamp: float = field(default_factory=time.time)


class TransitRelay:
    """
    TCP-based transit relay for wormhole data transfer.

    Clients connect and send a handshake with a shared token.
    The relay pairs clients with matching tokens and relays
    data bidirectionally between them.
    """

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 4001,
        timeout: float = 60.0,
    ):
        self.host = host
        self.port = port
        self.timeout = timeout

        # Pending connections waiting for a peer
        self.pending: Dict[str, PendingConnection] = {}
        self._lock = asyncio.Lock()

        self._server = None
        self._running = False
        self._cleanup_task = None

        # Statistics
        self.stats = {
            "connections": 0,
            "bytes_relayed": 0,
            "pairs_matched": 0,
        }

    async def start(self) -> None:
        """Start the transit relay server."""
        self._server = await asyncio.start_server(
            self._handle_client,
            self.host,
            self.port,
        )
        self._running = True

        # Start cleanup task for stale connections
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

        logger.info(f"Transit relay listening on tcp://{self.host}:{self.port}")

    async def stop(self) -> None:
        """Stop the transit relay server."""
        self._running = False

        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        if self._server:
            self._server.close()
            await self._server.wait_closed()

        # Close pending connections
        async with self._lock:
            for conn in self.pending.values():
                conn.writer.close()
            self.pending.clear()

    async def serve_forever(self) -> None:
        """Run the server until interrupted."""
        await self.start()
        try:
            await asyncio.Future()  # Run forever
        except asyncio.CancelledError:
            pass
        finally:
            await self.stop()

    async def _handle_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """Handle a new client connection."""
        self.stats["connections"] += 1
        peer_info = writer.get_extra_info("peername")
        logger.debug(f"New transit connection from {peer_info}")

        try:
            # Read handshake line
            line = await asyncio.wait_for(
                reader.readline(),
                timeout=self.timeout,
            )

            if not line:
                logger.debug("Client disconnected before handshake")
                return

            # Parse handshake: "please relay <token>\n"
            handshake = line.decode("utf-8").strip()

            if not handshake.startswith("please relay "):
                logger.warning(f"Invalid handshake: {handshake[:50]}")
                writer.write(b"bad handshake\n")
                await writer.drain()
                return

            token = handshake[13:]  # Extract token after "please relay "

            if not token:
                logger.warning("Empty token in handshake")
                writer.write(b"bad token\n")
                await writer.drain()
                return

            # Try to find a matching peer
            peer = await self._find_or_wait_peer(token, reader, writer)

            if peer:
                # Found a peer - relay data
                await self._relay_data(reader, writer, peer[0], peer[1])
            else:
                # Timed out waiting for peer
                logger.debug(f"Timeout waiting for peer with token {token[:20]}...")

        except asyncio.TimeoutError:
            logger.debug("Client timed out during handshake")

        except Exception as e:
            logger.debug(f"Error handling transit client: {e}")

        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    async def _find_or_wait_peer(
        self,
        token: str,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> Optional[Tuple[asyncio.StreamReader, asyncio.StreamWriter]]:
        """Find a matching peer or wait for one."""
        async with self._lock:
            if token in self.pending:
                # Found a matching peer!
                peer = self.pending.pop(token)
                self.stats["pairs_matched"] += 1
                logger.debug(f"Matched pair for token {token[:20]}...")

                # Send success to both
                writer.write(b"ok\n")
                await writer.drain()
                peer.writer.write(b"ok\n")
                await peer.writer.drain()

                return (peer.reader, peer.writer)

            # No peer yet - add to pending
            self.pending[token] = PendingConnection(
                reader=reader,
                writer=writer,
                token=token,
            )

        # Wait for peer to arrive
        try:
            start = time.time()
            while self._running:
                await asyncio.sleep(0.1)

                async with self._lock:
                    if token not in self.pending:
                        # We were matched by another client
                        # The other client sent "ok\n"
                        return None

                if time.time() - start > self.timeout:
                    # Timeout - remove from pending
                    async with self._lock:
                        self.pending.pop(token, None)
                    writer.write(b"timeout\n")
                    await writer.drain()
                    return None

        except asyncio.CancelledError:
            async with self._lock:
                self.pending.pop(token, None)
            raise

        return None

    async def _relay_data(
        self,
        reader1: asyncio.StreamReader,
        writer1: asyncio.StreamWriter,
        reader2: asyncio.StreamReader,
        writer2: asyncio.StreamWriter,
    ) -> None:
        """Relay data bidirectionally between two clients."""
        logger.debug("Starting data relay between peers")

        async def relay(
            src: asyncio.StreamReader,
            dst: asyncio.StreamWriter,
            direction: str,
        ) -> None:
            try:
                while True:
                    data = await src.read(65536)
                    if not data:
                        break
                    dst.write(data)
                    await dst.drain()
                    self.stats["bytes_relayed"] += len(data)
            except Exception as e:
                logger.debug(f"Relay {direction} ended: {e}")
            finally:
                try:
                    dst.close()
                except Exception:
                    pass

        # Run both directions concurrently
        await asyncio.gather(
            relay(reader1, writer2, "1->2"),
            relay(reader2, writer1, "2->1"),
            return_exceptions=True,
        )

        logger.debug("Data relay completed")

    async def _cleanup_loop(self) -> None:
        """Periodically clean up stale pending connections."""
        while self._running:
            try:
                await asyncio.sleep(10)

                now = time.time()
                stale_tokens = []

                async with self._lock:
                    for token, conn in self.pending.items():
                        if now - conn.timestamp > self.timeout:
                            stale_tokens.append(token)

                    for token in stale_tokens:
                        conn = self.pending.pop(token, None)
                        if conn:
                            try:
                                conn.writer.write(b"timeout\n")
                                await conn.writer.drain()
                                conn.writer.close()
                            except Exception:
                                pass

                if stale_tokens:
                    logger.debug(f"Cleaned up {len(stale_tokens)} stale connections")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
