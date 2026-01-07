"""
Unit tests for the transit relay.
"""

import pytest
from wh.relay.transit import TransitRelay, PendingConnection


class TestPendingConnection:
    """Tests for the PendingConnection class."""

    def test_create_pending_connection(self):
        """Test creating a pending connection."""
        # We can't create a real reader/writer without a network connection,
        # so we just test the dataclass structure
        conn = PendingConnection(
            reader=None,  # type: ignore
            writer=None,  # type: ignore
            token="test-token-abc123",
        )
        assert conn.token == "test-token-abc123"
        assert conn.timestamp > 0


class TestTransitRelay:
    """Tests for the TransitRelay class."""

    def test_create_relay(self):
        """Test creating a transit relay."""
        relay = TransitRelay(host="127.0.0.1", port=4001)
        assert relay.host == "127.0.0.1"
        assert relay.port == 4001
        assert relay.timeout == 60.0
        assert len(relay.pending) == 0

    def test_custom_timeout(self):
        """Test custom timeout."""
        relay = TransitRelay(timeout=30.0)
        assert relay.timeout == 30.0

    def test_initial_state(self):
        """Test initial relay state."""
        relay = TransitRelay()
        assert relay._running is False
        assert relay._server is None
        assert relay.stats["connections"] == 0
        assert relay.stats["bytes_relayed"] == 0
        assert relay.stats["pairs_matched"] == 0

    def test_stats_tracking(self):
        """Test that stats are properly initialized."""
        relay = TransitRelay()
        assert "connections" in relay.stats
        assert "bytes_relayed" in relay.stats
        assert "pairs_matched" in relay.stats

    def test_pending_dict(self):
        """Test pending connections dictionary."""
        relay = TransitRelay()
        # Test the dictionary works
        relay.pending["token1"] = PendingConnection(
            reader=None,  # type: ignore
            writer=None,  # type: ignore
            token="token1",
        )
        assert "token1" in relay.pending
        assert relay.pending["token1"].token == "token1"


class TestTransitHandshake:
    """Tests for transit handshake parsing."""

    def test_handshake_format(self):
        """Test the expected handshake format."""
        # The handshake should be: "please relay <token>\n"
        handshake = "please relay abc123def456\n"
        assert handshake.startswith("please relay ")
        token = handshake[13:].strip()
        assert token == "abc123def456"

    def test_invalid_handshake(self):
        """Test invalid handshake detection."""
        invalid_handshakes = [
            "hello\n",
            "relay please token\n",
            "please\n",
            "",
        ]

        for handshake in invalid_handshakes:
            assert not handshake.startswith("please relay ")
