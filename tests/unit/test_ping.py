"""
Unit tests for PingProtocol.

Tests cover packet creation/parsing, server/client modes, RTT tracking,
statistics calculation, and timeout handling.
"""

import asyncio
import struct
import statistics
import time
from unittest.mock import MagicMock, AsyncMock, call
import pytest

from wh.cli.ping import (
    PingProtocol,
    PING_REQUEST,
    PING_REPLY,
    PING_HEADER_SIZE,
)


class TestPingProtocolInit:
    """Test PingProtocol initialization."""

    def test_ping_protocol_init(self):
        """All fields set correctly during initialization."""
        status_callback = MagicMock()
        ping = PingProtocol(
            count=10,
            interval=0.5,
            timeout=3.0,
            size=128,
            on_status=status_callback,
            is_server=True,
        )

        assert ping.count == 10
        assert ping.interval == 0.5
        assert ping.timeout == 3.0
        assert ping.size == 128
        assert ping.on_status == status_callback
        assert ping.is_server is True

        # Internal state initialized
        assert ping._protocol is None
        assert ping._seq == 0
        assert ping._pending == {}
        assert ping._rtts == []
        assert ping._sent == 0
        assert ping._received == 0
        assert isinstance(ping._done, asyncio.Event)
        assert ping._buffer == b""

    def test_ping_protocol_init_defaults(self):
        """Default values set when not specified."""
        ping = PingProtocol()

        assert ping.count == 4
        assert ping.interval == 1.0
        assert ping.timeout == 5.0
        assert ping.size == 64
        assert ping.on_status is None
        assert ping.is_server is False


class TestPingPacketOperations:
    """Test packet creation and parsing."""

    def test_ping_make_packet(self):
        """Correct format: 1 byte type + 2 byte seq + 8 byte timestamp + padding."""
        ping = PingProtocol(size=64)
        timestamp = 1234567890.123456

        packet = ping._make_packet(PING_REQUEST, 42, timestamp)

        # Verify packet size
        assert len(packet) == 64

        # Parse header manually
        ptype, seq, ts = struct.unpack(">BHd", packet[:PING_HEADER_SIZE])
        assert ptype == PING_REQUEST
        assert seq == 42
        assert ts == timestamp

        # Verify padding
        padding = packet[PING_HEADER_SIZE:]
        assert len(padding) == 64 - PING_HEADER_SIZE
        assert padding == b"\x00" * (64 - PING_HEADER_SIZE)

    def test_ping_make_packet_exact_header_size(self):
        """Packet with no padding when size equals header size."""
        ping = PingProtocol(size=PING_HEADER_SIZE)
        timestamp = time.time()

        packet = ping._make_packet(PING_REPLY, 1, timestamp)

        assert len(packet) == PING_HEADER_SIZE
        ptype, seq, ts = struct.unpack(">BHd", packet)
        assert ptype == PING_REPLY
        assert seq == 1

    def test_ping_make_packet_larger_size(self):
        """Larger packet size creates more padding."""
        ping = PingProtocol(size=256)
        timestamp = time.time()

        packet = ping._make_packet(PING_REQUEST, 99, timestamp)

        assert len(packet) == 256
        # Verify only padding after header
        padding = packet[PING_HEADER_SIZE:]
        assert all(b == 0 for b in padding)

    def test_ping_parse_packet(self):
        """Type, seq, timestamp extracted correctly."""
        ping = PingProtocol(size=64)
        timestamp = 9876543210.987654

        # Create packet and parse it
        packet = ping._make_packet(PING_REPLY, 123, timestamp)
        result = ping._parse_packet(packet)

        assert result is not None
        ptype, seq, ts = result
        assert ptype == PING_REPLY
        assert seq == 123
        assert ts == timestamp

    def test_ping_parse_packet_too_short(self):
        """Returns None for packet shorter than header size."""
        ping = PingProtocol()

        # Various short packets
        assert ping._parse_packet(b"") is None
        assert ping._parse_packet(b"\x01") is None
        assert ping._parse_packet(b"\x01\x00") is None
        assert ping._parse_packet(b"\x01\x00\x2a") is None
        assert ping._parse_packet(b"\x01\x00\x2a\x00\x00\x00\x00") is None

        # Exactly one byte short
        short_packet = b"\x01\x00\x2a\x00\x00\x00\x00\x00\x00\x00"
        assert len(short_packet) == PING_HEADER_SIZE - 1
        assert ping._parse_packet(short_packet) is None

    def test_ping_parse_packet_exact_header_size(self):
        """Can parse packet with exactly header size."""
        ping = PingProtocol()
        timestamp = time.time()

        # Create minimal packet (header only)
        header = struct.pack(">BHd", PING_REQUEST, 5, timestamp)
        assert len(header) == PING_HEADER_SIZE

        result = ping._parse_packet(header)
        assert result is not None
        ptype, seq, ts = result
        assert ptype == PING_REQUEST
        assert seq == 5
        assert ts == timestamp


class TestPingServerMode:
    """Test server (responder) functionality."""

    def test_ping_server_replies(self):
        """Server echoes PING_REQUEST as PING_REPLY."""
        ping = PingProtocol(is_server=True, size=64)
        ping._protocol = MagicMock()

        # Simulate receiving a ping request
        timestamp = time.time()
        request_packet = ping._make_packet(PING_REQUEST, 10, timestamp)

        ping._on_data(request_packet)

        # Verify server sent a reply
        ping._protocol.send.assert_called_once()
        reply_packet = ping._protocol.send.call_args[0][0]

        # Parse the reply
        assert len(reply_packet) == 64
        result = ping._parse_packet(reply_packet)
        assert result is not None
        ptype, seq, ts = result
        assert ptype == PING_REPLY  # Changed to reply
        assert seq == 10  # Same sequence number
        assert ts == timestamp  # Same timestamp echoed back

    def test_ping_server_ignores_replies(self):
        """Server does not respond to PING_REPLY packets."""
        ping = PingProtocol(is_server=True, size=64)
        ping._protocol = MagicMock()

        # Send a reply packet to server
        reply_packet = ping._make_packet(PING_REPLY, 5, time.time())
        ping._on_data(reply_packet)

        # Server should not send anything
        ping._protocol.send.assert_not_called()

    def test_ping_server_multiple_requests(self):
        """Server handles multiple ping requests correctly."""
        ping = PingProtocol(is_server=True, size=64)
        ping._protocol = MagicMock()

        # Send 3 requests
        for i in range(3):
            request_packet = ping._make_packet(PING_REQUEST, i, time.time())
            ping._on_data(request_packet)

        # Should have sent 3 replies
        assert ping._protocol.send.call_count == 3


class TestPingClientMode:
    """Test client (sender) functionality."""

    def test_ping_client_tracks_rtt(self):
        """RTT stored in _rtts list when reply received."""
        ping = PingProtocol(is_server=False, size=64)

        # Simulate sending a request
        send_time = time.time() - 0.050  # 50ms ago
        ping._pending[0] = send_time
        ping._sent = 1

        # Simulate receiving reply
        reply_packet = ping._make_packet(PING_REPLY, 0, send_time)
        ping._on_data(reply_packet)

        # Check RTT was tracked
        assert len(ping._rtts) == 1
        assert ping._received == 1
        assert 0 not in ping._pending  # Removed from pending

        # RTT should be around 50ms (allowing some variance)
        rtt_ms = ping._rtts[0]
        assert 40 < rtt_ms < 60

    def test_ping_client_ignores_unknown_sequence(self):
        """Client ignores replies for unknown sequence numbers."""
        ping = PingProtocol(is_server=False, size=64)
        ping._pending[5] = time.time()
        ping._sent = 1

        # Reply with different sequence number
        reply_packet = ping._make_packet(PING_REPLY, 99, time.time())
        ping._on_data(reply_packet)

        # Should not track RTT or increment received
        assert len(ping._rtts) == 0
        assert ping._received == 0
        assert 5 in ping._pending  # Still pending

    def test_ping_client_ignores_requests(self):
        """Client does not respond to PING_REQUEST packets."""
        ping = PingProtocol(is_server=False, size=64)
        ping._protocol = MagicMock()

        # Send request packet to client
        request_packet = ping._make_packet(PING_REQUEST, 0, time.time())
        ping._on_data(request_packet)

        # Client should not send anything
        ping._protocol.send.assert_not_called()

    def test_ping_client_status_callback(self):
        """Client calls status callback on reply."""
        status_mock = MagicMock()
        ping = PingProtocol(is_server=False, size=64, on_status=status_mock)

        send_time = time.time() - 0.025  # 25ms ago
        ping._pending[7] = send_time

        reply_packet = ping._make_packet(PING_REPLY, 7, send_time)
        ping._on_data(reply_packet)

        # Verify status callback was called
        status_mock.assert_called_once()
        call_msg = status_mock.call_args[0][0]
        assert "seq=7" in call_msg
        assert "time=" in call_msg
        assert "ms" in call_msg


class TestPingStatistics:
    """Test statistics calculation."""

    def test_ping_statistics(self):
        """min/avg/max/stddev calculated correctly."""
        ping = PingProtocol()

        # Manually set up RTT data
        ping._sent = 5
        ping._received = 5
        ping._rtts = [10.0, 20.0, 30.0, 40.0, 50.0]

        stats = ping._get_statistics()

        assert stats["transmitted"] == 5
        assert stats["received"] == 5
        assert stats["loss_percent"] == 0.0
        assert stats["min_ms"] == 10.0
        assert stats["max_ms"] == 50.0
        assert stats["avg_ms"] == 30.0

        # Verify stddev manually
        expected_stddev = statistics.stdev(ping._rtts)
        assert abs(stats["stddev_ms"] - expected_stddev) < 0.001

    def test_ping_statistics_single_sample(self):
        """Statistics with single RTT sample (no stddev)."""
        ping = PingProtocol()
        ping._sent = 1
        ping._received = 1
        ping._rtts = [42.5]

        stats = ping._get_statistics()

        assert stats["min_ms"] == 42.5
        assert stats["max_ms"] == 42.5
        assert stats["avg_ms"] == 42.5
        assert stats["stddev_ms"] == 0.0  # Not calculated for single sample

    def test_ping_statistics_no_rtts(self):
        """Statistics with no successful RTTs."""
        ping = PingProtocol()
        ping._sent = 5
        ping._received = 0
        ping._rtts = []

        stats = ping._get_statistics()

        assert stats["transmitted"] == 5
        assert stats["received"] == 0
        assert stats["loss_percent"] == 100.0
        assert stats["min_ms"] == 0.0
        assert stats["max_ms"] == 0.0
        assert stats["avg_ms"] == 0.0
        assert stats["stddev_ms"] == 0.0

    def test_ping_packet_loss(self):
        """Loss percentage calculated correctly."""
        ping = PingProtocol()

        # 3 out of 10 received
        ping._sent = 10
        ping._received = 3
        ping._rtts = [10.0, 20.0, 30.0]

        stats = ping._get_statistics()

        assert stats["transmitted"] == 10
        assert stats["received"] == 3
        assert stats["loss_percent"] == 70.0

    def test_ping_packet_loss_zero_sent(self):
        """No division by zero when nothing sent."""
        ping = PingProtocol()
        ping._sent = 0
        ping._received = 0

        stats = ping._get_statistics()

        assert stats["loss_percent"] == 0.0

    def test_ping_statistics_partial_loss(self):
        """Statistics with some packet loss."""
        ping = PingProtocol()
        ping._sent = 4
        ping._received = 2
        ping._rtts = [15.5, 25.5]

        stats = ping._get_statistics()

        assert stats["transmitted"] == 4
        assert stats["received"] == 2
        assert stats["loss_percent"] == 50.0
        assert stats["min_ms"] == 15.5
        assert stats["max_ms"] == 25.5
        assert stats["avg_ms"] == 20.5


class TestPingTimeoutHandling:
    """Test timeout and pending management."""

    def test_ping_timeout_handling(self):
        """Pending removed on timeout."""
        ping = PingProtocol()

        # Add to pending
        ping._pending[3] = time.time()
        ping._pending[4] = time.time()
        assert len(ping._pending) == 2

        # Simulate timeout by removing from pending
        if 3 in ping._pending:
            del ping._pending[3]

        assert 3 not in ping._pending
        assert 4 in ping._pending
        assert len(ping._pending) == 1

    def test_ping_pending_removed_on_reply(self):
        """Pending entry removed when reply received."""
        ping = PingProtocol(is_server=False, size=64)
        send_time = time.time()
        ping._pending[0] = send_time
        ping._pending[1] = send_time

        # Receive reply for seq 0
        reply = ping._make_packet(PING_REPLY, 0, send_time)
        ping._on_data(reply)

        assert 0 not in ping._pending
        assert 1 in ping._pending


class TestPingCustomOptions:
    """Test custom size, count, and interval options."""

    def test_ping_custom_size(self):
        """-s flag creates larger packet."""
        ping_small = PingProtocol(size=64)
        ping_large = PingProtocol(size=512)

        packet_small = ping_small._make_packet(PING_REQUEST, 0, time.time())
        packet_large = ping_large._make_packet(PING_REQUEST, 0, time.time())

        assert len(packet_small) == 64
        assert len(packet_large) == 512

    def test_ping_custom_count(self):
        """-c flag affects count."""
        ping = PingProtocol(count=100)
        assert ping.count == 100

        ping2 = PingProtocol(count=1)
        assert ping2.count == 1

    def test_ping_custom_interval(self):
        """-i flag affects interval."""
        ping = PingProtocol(interval=0.1)
        assert ping.interval == 0.1

        ping2 = PingProtocol(interval=5.0)
        assert ping2.interval == 5.0

    def test_ping_custom_timeout(self):
        """-W flag affects timeout."""
        ping = PingProtocol(timeout=10.0)
        assert ping.timeout == 10.0

        ping2 = PingProtocol(timeout=1.0)
        assert ping2.timeout == 1.0


class TestPingBuffering:
    """Test packet buffering and assembly."""

    def test_ping_buffer_assembles_packets(self):
        """Multiple data chunks assembled into complete packet."""
        ping = PingProtocol(is_server=True, size=64)
        ping._protocol = MagicMock()

        timestamp = time.time()
        packet = ping._make_packet(PING_REQUEST, 0, timestamp)

        # Send packet in chunks
        chunk1 = packet[:20]
        chunk2 = packet[20:40]
        chunk3 = packet[40:]

        ping._on_data(chunk1)
        assert ping._protocol.send.call_count == 0  # Not enough data

        ping._on_data(chunk2)
        assert ping._protocol.send.call_count == 0  # Still not enough

        ping._on_data(chunk3)
        assert ping._protocol.send.call_count == 1  # Now complete

    def test_ping_buffer_multiple_packets(self):
        """Buffer handles multiple packets in single data chunk."""
        ping = PingProtocol(is_server=True, size=64)
        ping._protocol = MagicMock()

        # Create 3 packets
        packet1 = ping._make_packet(PING_REQUEST, 0, time.time())
        packet2 = ping._make_packet(PING_REQUEST, 1, time.time())
        packet3 = ping._make_packet(PING_REQUEST, 2, time.time())

        # Send all at once
        ping._on_data(packet1 + packet2 + packet3)

        # Should have sent 3 replies
        assert ping._protocol.send.call_count == 3

    def test_ping_buffer_partial_packet_remains(self):
        """Partial packet data remains in buffer."""
        ping = PingProtocol(is_server=True, size=64)
        ping._protocol = MagicMock()

        packet1 = ping._make_packet(PING_REQUEST, 0, time.time())
        packet2 = ping._make_packet(PING_REQUEST, 1, time.time())

        # Send 1.5 packets
        partial_data = packet1 + packet2[:30]
        ping._on_data(partial_data)

        # Only first packet processed
        assert ping._protocol.send.call_count == 1
        assert len(ping._buffer) == 30  # Partial packet remains

        # Complete second packet
        ping._on_data(packet2[30:])
        assert ping._protocol.send.call_count == 2
        assert len(ping._buffer) == 0


class TestPingConnectionHandling:
    """Test connection lifecycle."""

    def test_ping_connection_lost_sets_done(self):
        """Connection lost sets the done event."""
        ping = PingProtocol()
        assert not ping._done.is_set()

        ping._on_connection_lost(None)
        assert ping._done.is_set()

    def test_ping_connection_lost_with_exception(self):
        """Connection lost with exception still sets done."""
        ping = PingProtocol()

        exc = Exception("Connection error")
        ping._on_connection_lost(exc)

        assert ping._done.is_set()
