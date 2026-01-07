"""
Mailbox server for wormhole rendezvous.

This implements the mailbox protocol that allows two clients to find
each other and exchange messages for PAKE key agreement.

Protocol:
1. Client claims a nameplate (e.g., "7")
2. Client opens a mailbox associated with that nameplate
3. Clients exchange messages through the mailbox
4. After key agreement, clients may establish direct/transit connection
"""

import asyncio
import json
import logging
import secrets
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from weakref import WeakSet

logger = logging.getLogger(__name__)


@dataclass
class Message:
    """A message stored in a mailbox."""
    id: str
    side: str
    phase: str
    body: str
    timestamp: float = field(default_factory=time.time)


@dataclass
class Mailbox:
    """A mailbox where two clients exchange messages."""
    id: str
    sides: Set[str] = field(default_factory=set)
    messages: List[Message] = field(default_factory=list)
    created: float = field(default_factory=time.time)

    def add_message(self, side: str, phase: str, body: str) -> Message:
        """Add a message to the mailbox."""
        msg = Message(
            id=secrets.token_hex(8),
            side=side,
            phase=phase,
            body=body,
        )
        self.messages.append(msg)
        return msg

    def get_messages(self, exclude_side: Optional[str] = None) -> List[Message]:
        """Get messages, optionally excluding a specific side."""
        if exclude_side:
            return [m for m in self.messages if m.side != exclude_side]
        return self.messages.copy()


@dataclass
class Nameplate:
    """A nameplate that maps a short code to a mailbox."""
    id: str
    mailbox_id: str
    sides: Set[str] = field(default_factory=set)
    created: float = field(default_factory=time.time)


class MailboxServer:
    """
    WebSocket-based mailbox server for wormhole rendezvous.

    This server handles:
    - Nameplate allocation and claiming
    - Mailbox creation and message exchange
    - Client notifications when new messages arrive
    """

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 4000,
        app_id: str = "wh.tools/v1",
    ):
        self.host = host
        self.port = port
        self.app_id = app_id

        # State
        self.nameplates: Dict[str, Nameplate] = {}
        self.mailboxes: Dict[str, Mailbox] = {}
        self.clients: WeakSet = WeakSet()
        self.client_subscriptions: Dict[str, Set] = {}  # mailbox_id -> set of writers

        # Nameplate allocation
        self._next_nameplate = 1
        self._nameplate_lock = asyncio.Lock()

        self._server = None
        self._running = False

    async def start(self) -> None:
        """Start the mailbox server."""
        try:
            import websockets
        except ImportError:
            raise ImportError(
                "websockets package required for relay server. "
                "Install with: pip install websockets"
            )

        self._server = await websockets.serve(
            self._handle_client,
            self.host,
            self.port,
        )
        self._running = True
        logger.info(f"Mailbox server listening on ws://{self.host}:{self.port}/v1")

    async def stop(self) -> None:
        """Stop the mailbox server."""
        self._running = False
        if self._server:
            self._server.close()
            await self._server.wait_closed()

    async def serve_forever(self) -> None:
        """Run the server until interrupted."""
        await self.start()
        try:
            await asyncio.Future()  # Run forever
        except asyncio.CancelledError:
            pass
        finally:
            await self.stop()

    async def _handle_client(self, websocket) -> None:
        """Handle a client WebSocket connection."""
        client_state = {
            "side": None,
            "app_id": None,
            "nameplate": None,
            "mailbox": None,
        }

        try:
            self.clients.add(websocket)

            # Send welcome message
            await self._send(websocket, {
                "type": "welcome",
                "welcome": {
                    "current_cli_version": "0.14.0",
                    "motd": "Welcome to wh relay server",
                },
            })

            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self._handle_message(websocket, data, client_state)
                except json.JSONDecodeError:
                    await self._send_error(websocket, "Invalid JSON")
                except Exception as e:
                    logger.exception(f"Error handling message: {e}")
                    await self._send_error(websocket, str(e))

        except Exception as e:
            logger.debug(f"Client disconnected: {e}")

        finally:
            self.clients.discard(websocket)
            # Clean up subscriptions
            mailbox_id = client_state.get("mailbox")
            if mailbox_id and mailbox_id in self.client_subscriptions:
                self.client_subscriptions[mailbox_id].discard(websocket)

    async def _handle_message(self, websocket, data: dict, state: dict) -> None:
        """Handle a client message."""
        msg_type = data.get("type")

        if msg_type == "bind":
            await self._handle_bind(websocket, data, state)
        elif msg_type == "allocate":
            await self._handle_allocate(websocket, data, state)
        elif msg_type == "claim":
            await self._handle_claim(websocket, data, state)
        elif msg_type == "release":
            await self._handle_release(websocket, data, state)
        elif msg_type == "open":
            await self._handle_open(websocket, data, state)
        elif msg_type == "add":
            await self._handle_add(websocket, data, state)
        elif msg_type == "close":
            await self._handle_close(websocket, data, state)
        elif msg_type == "list":
            await self._handle_list(websocket, data, state)
        elif msg_type == "ping":
            await self._send(websocket, {"type": "pong", "pong": data.get("ping", 0)})
        else:
            await self._send_error(websocket, f"Unknown message type: {msg_type}")

    async def _handle_bind(self, websocket, data: dict, state: dict) -> None:
        """Handle bind (identify client)."""
        state["app_id"] = data.get("appid", self.app_id)
        state["side"] = data.get("side", secrets.token_hex(8))

        await self._send(websocket, {"type": "ack"})

    async def _handle_allocate(self, websocket, data: dict, state: dict) -> None:
        """Handle allocate (get a new nameplate)."""
        async with self._nameplate_lock:
            nameplate_id = str(self._next_nameplate)
            self._next_nameplate += 1

        mailbox_id = secrets.token_hex(16)

        self.nameplates[nameplate_id] = Nameplate(
            id=nameplate_id,
            mailbox_id=mailbox_id,
        )
        self.mailboxes[mailbox_id] = Mailbox(id=mailbox_id)

        await self._send(websocket, {
            "type": "allocated",
            "nameplate": nameplate_id,
        })

    async def _handle_claim(self, websocket, data: dict, state: dict) -> None:
        """Handle claim (claim a nameplate)."""
        nameplate_id = data.get("nameplate")
        side = state.get("side")

        if not nameplate_id:
            await self._send_error(websocket, "Missing nameplate")
            return

        if nameplate_id not in self.nameplates:
            # Create new nameplate if it doesn't exist
            mailbox_id = secrets.token_hex(16)
            self.nameplates[nameplate_id] = Nameplate(
                id=nameplate_id,
                mailbox_id=mailbox_id,
            )
            self.mailboxes[mailbox_id] = Mailbox(id=mailbox_id)

        nameplate = self.nameplates[nameplate_id]
        nameplate.sides.add(side)
        state["nameplate"] = nameplate_id

        await self._send(websocket, {
            "type": "claimed",
            "mailbox": nameplate.mailbox_id,
        })

    async def _handle_release(self, websocket, data: dict, state: dict) -> None:
        """Handle release (release a nameplate)."""
        nameplate_id = data.get("nameplate") or state.get("nameplate")

        if nameplate_id and nameplate_id in self.nameplates:
            nameplate = self.nameplates[nameplate_id]
            side = state.get("side")
            if side:
                nameplate.sides.discard(side)

            # Remove nameplate if no sides remain
            if not nameplate.sides:
                del self.nameplates[nameplate_id]

        state["nameplate"] = None
        await self._send(websocket, {"type": "released"})

    async def _handle_open(self, websocket, data: dict, state: dict) -> None:
        """Handle open (open a mailbox)."""
        mailbox_id = data.get("mailbox")
        side = state.get("side")

        if not mailbox_id:
            await self._send_error(websocket, "Missing mailbox")
            return

        if mailbox_id not in self.mailboxes:
            self.mailboxes[mailbox_id] = Mailbox(id=mailbox_id)

        mailbox = self.mailboxes[mailbox_id]
        mailbox.sides.add(side)
        state["mailbox"] = mailbox_id

        # Subscribe to mailbox updates
        if mailbox_id not in self.client_subscriptions:
            self.client_subscriptions[mailbox_id] = set()
        self.client_subscriptions[mailbox_id].add(websocket)

        # Send existing messages
        for msg in mailbox.get_messages():
            await self._send(websocket, {
                "type": "message",
                "side": msg.side,
                "phase": msg.phase,
                "body": msg.body,
                "id": msg.id,
            })

    async def _handle_add(self, websocket, data: dict, state: dict) -> None:
        """Handle add (add a message to mailbox)."""
        mailbox_id = state.get("mailbox")
        side = state.get("side")
        phase = data.get("phase")
        body = data.get("body")

        if not mailbox_id:
            await self._send_error(websocket, "No mailbox open")
            return

        if mailbox_id not in self.mailboxes:
            await self._send_error(websocket, "Mailbox not found")
            return

        mailbox = self.mailboxes[mailbox_id]
        msg = mailbox.add_message(side, phase, body)

        # Notify all subscribers
        notification = {
            "type": "message",
            "side": msg.side,
            "phase": msg.phase,
            "body": msg.body,
            "id": msg.id,
        }

        subscribers = self.client_subscriptions.get(mailbox_id, set())
        for subscriber in list(subscribers):
            try:
                await self._send(subscriber, notification)
            except Exception:
                subscribers.discard(subscriber)

    async def _handle_close(self, websocket, data: dict, state: dict) -> None:
        """Handle close (close a mailbox)."""
        mailbox_id = state.get("mailbox")
        mood = data.get("mood", "happy")

        if mailbox_id:
            # Unsubscribe
            if mailbox_id in self.client_subscriptions:
                self.client_subscriptions[mailbox_id].discard(websocket)

            # Remove from mailbox
            if mailbox_id in self.mailboxes:
                mailbox = self.mailboxes[mailbox_id]
                side = state.get("side")
                if side:
                    mailbox.sides.discard(side)

                # Delete mailbox if empty
                if not mailbox.sides:
                    del self.mailboxes[mailbox_id]

        state["mailbox"] = None
        await self._send(websocket, {"type": "closed"})

    async def _handle_list(self, websocket, data: dict, state: dict) -> None:
        """Handle list (list active nameplates)."""
        nameplates = [
            {"id": np.id}
            for np in self.nameplates.values()
            if len(np.sides) < 2  # Only show available nameplates
        ]

        await self._send(websocket, {
            "type": "nameplates",
            "nameplates": nameplates,
        })

    async def _send(self, websocket, data: dict) -> None:
        """Send a message to a client."""
        await websocket.send(json.dumps(data))

    async def _send_error(self, websocket, message: str) -> None:
        """Send an error message."""
        await self._send(websocket, {
            "type": "error",
            "error": message,
        })
