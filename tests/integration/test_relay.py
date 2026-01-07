"""
Integration tests for the built-in relay server.

These tests verify that the relay server works correctly with actual
wormhole connections.
"""

import asyncio
import pytest
import json

# Skip all tests if websockets not installed
pytest.importorskip("websockets")


class TestMailboxIntegration:
    """Integration tests for the mailbox server."""

    @pytest.fixture
    async def mailbox_server(self):
        """Create and start a mailbox server."""
        from wh.relay.mailbox import MailboxServer

        server = MailboxServer(host="127.0.0.1", port=14000)
        await server.start()
        yield server
        await server.stop()

    @pytest.mark.asyncio
    async def test_client_connection(self, mailbox_server):
        """Test that a client can connect to the mailbox server."""
        import websockets

        async with websockets.connect("ws://127.0.0.1:14000/v1") as ws:
            # Should receive welcome message
            msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
            data = json.loads(msg)
            assert data["type"] == "welcome"
            assert "welcome" in data

    @pytest.mark.asyncio
    async def test_bind_and_allocate(self, mailbox_server):
        """Test bind and allocate flow."""
        import websockets

        async with websockets.connect("ws://127.0.0.1:14000/v1") as ws:
            # Receive welcome
            await ws.recv()

            # Bind
            await ws.send(json.dumps({
                "type": "bind",
                "appid": "test-app",
                "side": "side1",
            }))
            msg = await ws.recv()
            assert json.loads(msg)["type"] == "ack"

            # Allocate
            await ws.send(json.dumps({"type": "allocate"}))
            msg = await ws.recv()
            data = json.loads(msg)
            assert data["type"] == "allocated"
            assert "nameplate" in data

    @pytest.mark.asyncio
    async def test_claim_and_open(self, mailbox_server):
        """Test claiming a nameplate and opening a mailbox."""
        import websockets

        async with websockets.connect("ws://127.0.0.1:14000/v1") as ws:
            await ws.recv()  # welcome

            # Bind
            await ws.send(json.dumps({
                "type": "bind",
                "side": "side1",
            }))
            await ws.recv()  # ack

            # Claim nameplate
            await ws.send(json.dumps({
                "type": "claim",
                "nameplate": "42",
            }))
            msg = await ws.recv()
            data = json.loads(msg)
            assert data["type"] == "claimed"
            assert "mailbox" in data

            mailbox_id = data["mailbox"]

            # Open mailbox
            await ws.send(json.dumps({
                "type": "open",
                "mailbox": mailbox_id,
            }))

            # No response expected for open (just starts receiving messages)

    @pytest.mark.asyncio
    async def test_message_exchange(self, mailbox_server):
        """Test that two clients can exchange messages."""
        import websockets

        async with websockets.connect("ws://127.0.0.1:14000/v1") as ws1:
            await ws1.recv()  # welcome
            await ws1.send(json.dumps({"type": "bind", "side": "side1"}))
            await ws1.recv()  # ack

            # Claim and open
            await ws1.send(json.dumps({"type": "claim", "nameplate": "99"}))
            claimed = json.loads(await ws1.recv())
            mailbox_id = claimed["mailbox"]

            await ws1.send(json.dumps({"type": "open", "mailbox": mailbox_id}))

            # Second client
            async with websockets.connect("ws://127.0.0.1:14000/v1") as ws2:
                await ws2.recv()  # welcome
                await ws2.send(json.dumps({"type": "bind", "side": "side2"}))
                await ws2.recv()  # ack

                await ws2.send(json.dumps({"type": "claim", "nameplate": "99"}))
                await ws2.recv()  # claimed

                await ws2.send(json.dumps({"type": "open", "mailbox": mailbox_id}))

                # Client 1 sends a message
                await ws1.send(json.dumps({
                    "type": "add",
                    "phase": "pake",
                    "body": "test-message-from-side1",
                }))

                # Client 2 should receive it
                msg = await asyncio.wait_for(ws2.recv(), timeout=5.0)
                data = json.loads(msg)
                assert data["type"] == "message"
                assert data["side"] == "side1"
                assert data["body"] == "test-message-from-side1"


class TestTransitIntegration:
    """Integration tests for the transit relay."""

    @pytest.fixture
    async def transit_relay(self):
        """Create and start a transit relay."""
        from wh.relay.transit import TransitRelay

        relay = TransitRelay(host="127.0.0.1", port=14001, timeout=10.0)
        await relay.start()
        yield relay
        await relay.stop()

    @pytest.mark.asyncio
    async def test_client_handshake(self, transit_relay):
        """Test that a client can perform handshake."""
        reader, writer = await asyncio.open_connection("127.0.0.1", 14001)

        try:
            # Send handshake
            writer.write(b"please relay test-token-123\n")
            await writer.drain()

            # Should timeout waiting for peer (no match)
            response = await asyncio.wait_for(reader.readline(), timeout=12.0)
            assert response == b"timeout\n"
        finally:
            writer.close()
            await writer.wait_closed()

    @pytest.mark.asyncio
    async def test_peer_matching(self, transit_relay):
        """Test that two clients with same token are matched."""
        token = "shared-token-abc123"

        async def client(client_id: int, send_data: bytes, expect_data: bytes):
            reader, writer = await asyncio.open_connection("127.0.0.1", 14001)
            try:
                # Handshake
                writer.write(f"please relay {token}\n".encode())
                await writer.drain()

                # Wait for "ok"
                response = await asyncio.wait_for(reader.readline(), timeout=5.0)
                assert response == b"ok\n", f"Client {client_id}: expected 'ok', got {response}"

                # Exchange data
                writer.write(send_data)
                await writer.drain()

                received = await asyncio.wait_for(reader.read(len(expect_data)), timeout=5.0)
                assert received == expect_data, f"Client {client_id}: data mismatch"

                return True
            finally:
                writer.close()
                await writer.wait_closed()

        # Run both clients concurrently
        results = await asyncio.gather(
            client(1, b"hello from 1", b"hello from 2"),
            client(2, b"hello from 2", b"hello from 1"),
        )

        assert all(results)
        assert transit_relay.stats["pairs_matched"] >= 1

    @pytest.mark.asyncio
    async def test_invalid_handshake(self, transit_relay):
        """Test that invalid handshake is rejected."""
        reader, writer = await asyncio.open_connection("127.0.0.1", 14001)

        try:
            # Send invalid handshake
            writer.write(b"invalid handshake\n")
            await writer.drain()

            response = await asyncio.wait_for(reader.readline(), timeout=5.0)
            assert response == b"bad handshake\n"
        finally:
            writer.close()
            await writer.wait_closed()


class TestFullRelayIntegration:
    """Integration tests for the full relay server."""

    @pytest.fixture
    async def relay_server(self):
        """Create and start a full relay server."""
        from wh.relay.server import RelayServer

        server = RelayServer(
            host="127.0.0.1",
            mailbox_port=14100,
            transit_port=14101,
        )
        await server.start()
        yield server
        await server.stop()

    @pytest.mark.asyncio
    async def test_both_servers_running(self, relay_server):
        """Test that both servers are running."""
        import websockets

        # Test mailbox
        async with websockets.connect("ws://127.0.0.1:14100/v1") as ws:
            msg = await ws.recv()
            assert json.loads(msg)["type"] == "welcome"

        # Test transit - just verify we can connect
        reader, writer = await asyncio.open_connection("127.0.0.1", 14101)
        try:
            # Send handshake and verify connection works
            writer.write(b"please relay test-token\n")
            await writer.drain()
            # Connection is open - that's all we need to verify
            # Don't wait for timeout response as it would take too long
        finally:
            writer.close()
            await writer.wait_closed()

    @pytest.mark.asyncio
    async def test_stats(self, relay_server):
        """Test that stats are available."""
        stats = relay_server.get_stats()
        assert "mailbox" in stats
        assert "transit" in stats
        assert "nameplates" in stats["mailbox"]
        assert "connections" in stats["transit"]
