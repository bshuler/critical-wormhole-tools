"""Unit tests for relay server module."""

import pytest


class TestRelayServer:
    """Tests for RelayServer class."""

    def test_init_defaults(self):
        """Test RelayServer initialization with defaults."""
        from wh.relay.server import RelayServer

        server = RelayServer()

        assert server.host == "0.0.0.0"
        assert server.mailbox_port == 4000
        assert server.transit_port == 4001
        assert server._running is False

    def test_init_custom_ports(self):
        """Test RelayServer with custom ports."""
        from wh.relay.server import RelayServer

        server = RelayServer(
            host="127.0.0.1",
            mailbox_port=5000,
            transit_port=5001,
        )

        assert server.host == "127.0.0.1"
        assert server.mailbox_port == 5000
        assert server.transit_port == 5001

    def test_running_flag_before_start(self):
        """Test _running is False before start."""
        from wh.relay.server import RelayServer

        server = RelayServer()
        assert server._running is False

    def test_mailbox_and_transit_created(self):
        """Test mailbox and transit objects are created."""
        from wh.relay.server import RelayServer

        server = RelayServer()

        assert server.mailbox is not None
        assert server.transit is not None

    def test_get_stats(self):
        """Test get_stats returns dict with expected keys."""
        from wh.relay.server import RelayServer

        server = RelayServer()
        stats = server.get_stats()

        assert "mailbox" in stats
        assert "transit" in stats
        assert "nameplates" in stats["mailbox"]
        assert "mailboxes" in stats["mailbox"]
        assert "clients" in stats["mailbox"]


class TestRelayServerAsync:
    """Async tests for RelayServer."""

    @pytest.mark.asyncio
    async def test_stop_before_start(self):
        """Test stop is safe to call before start."""
        from wh.relay.server import RelayServer

        server = RelayServer()
        await server.stop()  # Should not raise
        assert server._running is False

    @pytest.mark.asyncio
    async def test_start_stop_cycle(self):
        """Test starting and stopping the server."""
        from wh.relay.server import RelayServer

        server = RelayServer(
            host="127.0.0.1",
            mailbox_port=14000,  # Use high ports to avoid conflicts
            transit_port=14001,
        )

        try:
            await server.start()
            assert server._running is True
        finally:
            await server.stop()
            assert server._running is False


class TestRunRelay:
    """Tests for run_relay function."""

    def test_run_relay_exists(self):
        """Test run_relay function exists."""
        from wh.relay.server import run_relay

        assert callable(run_relay)


class TestRelayServerProperties:
    """Additional tests for RelayServer properties."""

    def test_mailbox_port(self):
        """Test mailbox port property."""
        from wh.relay.server import RelayServer

        server = RelayServer(mailbox_port=6000)
        assert server.mailbox_port == 6000

    def test_transit_port(self):
        """Test transit port property."""
        from wh.relay.server import RelayServer

        server = RelayServer(transit_port=6001)
        assert server.transit_port == 6001

    def test_host_property(self):
        """Test host property."""
        from wh.relay.server import RelayServer

        server = RelayServer(host="192.168.1.100")
        assert server.host == "192.168.1.100"


class TestRelayServerStats:
    """Tests for relay server statistics."""

    def test_stats_transit_keys(self):
        """Test transit stats have expected keys."""
        from wh.relay.server import RelayServer

        server = RelayServer()
        stats = server.get_stats()

        assert "connections" in stats["transit"]
        assert "bytes_relayed" in stats["transit"]

    def test_stats_after_init(self):
        """Test stats are zero after initialization."""
        from wh.relay.server import RelayServer

        server = RelayServer()
        stats = server.get_stats()

        assert stats["transit"]["connections"] == 0
        assert stats["transit"]["bytes_relayed"] == 0


class TestRelayServerMailbox:
    """Tests for relay server mailbox component."""

    def test_mailbox_app_id(self):
        """Test mailbox has correct app ID."""
        from wh.relay.server import RelayServer

        server = RelayServer()

        # Mailbox should have default app_id
        assert server.mailbox.app_id is not None

    def test_mailbox_empty_nameplates(self):
        """Test mailbox starts with no nameplates."""
        from wh.relay.server import RelayServer

        server = RelayServer()

        assert len(server.mailbox.nameplates) == 0

    def test_mailbox_empty_mailboxes(self):
        """Test mailbox starts with no mailboxes."""
        from wh.relay.server import RelayServer

        server = RelayServer()

        assert len(server.mailbox.mailboxes) == 0


class TestRelayServerTransit:
    """Tests for relay server transit component."""

    def test_transit_timeout(self):
        """Test transit has default timeout."""
        from wh.relay.server import RelayServer

        server = RelayServer()

        assert server.transit.timeout > 0

    def test_transit_empty_pending(self):
        """Test transit starts with no pending connections."""
        from wh.relay.server import RelayServer

        server = RelayServer()

        assert len(server.transit.pending) == 0
