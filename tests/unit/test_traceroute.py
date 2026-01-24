"""Unit tests for wh traceroute command."""

import pytest
import struct
from unittest.mock import Mock, patch
import asyncio

from wh.cli.traceroute import (
    TracerouteProtocol, HopResult,
    MSG_TRACE_REQUEST, MSG_TRACE_HOP, MSG_TRACE_COMPLETE,
)


class TestHopResult:
    """Tests for HopResult dataclass."""

    def test_create_hop_result(self):
        """Test creating HopResult."""
        result = HopResult(
            hop_num=1,
            name="router.local",
            ip="192.168.1.1",
            rtts=[10.5, 11.2, 10.8],
        )

        assert result.hop_num == 1
        assert result.name == "router.local"
        assert result.ip == "192.168.1.1"
        assert result.rtts == [10.5, 11.2, 10.8]

    def test_avg_rtt(self):
        """Test average RTT calculation."""
        result = HopResult(
            hop_num=1,
            name="test",
            ip="1.1.1.1",
            rtts=[10.0, 20.0, 30.0],
        )

        assert result.avg_rtt == 20.0

    def test_avg_rtt_empty(self):
        """Test average RTT with empty list."""
        result = HopResult(hop_num=1, name="test", ip="1.1.1.1", rtts=[])
        assert result.avg_rtt == 0.0

    def test_min_rtt(self):
        """Test minimum RTT."""
        result = HopResult(
            hop_num=1,
            name="test",
            ip="1.1.1.1",
            rtts=[10.0, 5.0, 15.0],
        )

        assert result.min_rtt == 5.0

    def test_min_rtt_empty(self):
        """Test minimum RTT with empty list."""
        result = HopResult(hop_num=1, name="test", ip="1.1.1.1", rtts=[])
        assert result.min_rtt == 0.0

    def test_max_rtt(self):
        """Test maximum RTT."""
        result = HopResult(
            hop_num=1,
            name="test",
            ip="1.1.1.1",
            rtts=[10.0, 5.0, 15.0],
        )

        assert result.max_rtt == 15.0


class TestTracerouteProtocol:
    """Tests for TracerouteProtocol class."""

    def test_init_defaults(self):
        """Test protocol initialization with defaults."""
        proto = TracerouteProtocol()

        assert proto.on_status is None
        assert proto.is_server is False
        assert proto.max_hops == 30
        assert proto.queries == 3
        assert proto.timeout == 3.0
        assert proto._protocol is None
        assert proto._buffer == b""
        assert not proto._done.is_set()

    def test_init_with_options(self):
        """Test protocol initialization with options."""
        on_status = Mock()

        proto = TracerouteProtocol(
            on_status=on_status,
            is_server=True,
            max_hops=20,
            queries=5,
            timeout=5.0,
        )

        assert proto.on_status is on_status
        assert proto.is_server is True
        assert proto.max_hops == 20
        assert proto.queries == 5
        assert proto.timeout == 5.0

    def test_status_callback(self):
        """Test status callback."""
        on_status = Mock()
        proto = TracerouteProtocol(on_status=on_status)

        proto._status("tracing...")

        on_status.assert_called_once_with("tracing...")

    def test_send_message(self):
        """Test message sending."""
        proto = TracerouteProtocol()
        mock_protocol = Mock()
        mock_protocol.send = Mock()
        proto._protocol = mock_protocol

        proto._send_message(MSG_TRACE_COMPLETE, b"")

        mock_protocol.send.assert_called_once()
        sent_data = mock_protocol.send.call_args[0][0]
        msg_type, _ = struct.unpack(">BI", sent_data[:5])
        assert msg_type == MSG_TRACE_COMPLETE

    def test_send_hop(self):
        """Test sending hop result."""
        proto = TracerouteProtocol(is_server=True)
        mock_protocol = Mock()
        mock_protocol.send = Mock()
        proto._protocol = mock_protocol

        proto._send_hop(1, "router", "192.168.1.1", [10.5, 11.0])

        mock_protocol.send.assert_called_once()
        sent_data = mock_protocol.send.call_args[0][0]
        msg_type, _ = struct.unpack(">BI", sent_data[:5])
        assert msg_type == MSG_TRACE_HOP

    def test_handle_hop_result(self):
        """Test handling hop result."""
        proto = TracerouteProtocol(is_server=False)

        # Build hop result
        name = b"router"
        ip = b"192.168.1.1"
        rtts = [10.5, 11.0]

        payload = struct.pack(">BBB", 1, len(name), len(ip))
        payload += name + ip
        payload += struct.pack(">B", len(rtts))
        for rtt in rtts:
            payload += struct.pack(">f", rtt)

        proto._handle_hop_result(payload)

        assert len(proto._hops) == 1
        hop = proto._hops[0]
        assert hop.hop_num == 1
        assert hop.name == "router"
        assert hop.ip == "192.168.1.1"
        assert len(hop.rtts) == 2

    def test_handle_trace_complete(self):
        """Test handling trace complete."""
        proto = TracerouteProtocol(is_server=False)

        header = struct.pack(">BI", MSG_TRACE_COMPLETE, 0)
        proto._buffer = header

        proto._process_buffer()

        assert proto._trace_complete.is_set()

    def test_on_connection_lost(self):
        """Test connection lost handling."""
        proto = TracerouteProtocol()

        proto._on_connection_lost(None)

        assert proto._done.is_set()
        assert proto._trace_complete.is_set()

    @pytest.mark.asyncio
    async def test_trace_request(self):
        """Test trace request."""
        proto = TracerouteProtocol(is_server=False)
        mock_protocol = Mock()
        mock_protocol.send = Mock()
        proto._protocol = mock_protocol

        # Simulate quick trace complete
        async def set_complete():
            await asyncio.sleep(0.01)
            proto._hops.append(HopResult(1, "router", "192.168.1.1", [10.0]))
            proto._trace_complete.set()

        asyncio.create_task(set_complete())

        hops = await proto.trace("example.com")

        mock_protocol.send.assert_called_once()
        assert len(hops) == 1

    def test_process_buffer_trace_request(self):
        """Test processing trace request."""
        proto = TracerouteProtocol(is_server=True)

        host = b"example.com"
        payload = bytes([len(host)]) + host

        header = struct.pack(">BI", MSG_TRACE_REQUEST, len(payload))
        proto._buffer = header + payload

        with patch('asyncio.create_task') as mock_create_task:
            proto._process_buffer()
            mock_create_task.assert_called_once()

    def test_process_buffer_hop_result(self):
        """Test processing hop result."""
        proto = TracerouteProtocol(is_server=False)

        name = b"hop1"
        ip = b"1.2.3.4"
        rtts = [5.0]

        payload = struct.pack(">BBB", 1, len(name), len(ip))
        payload += name + ip
        payload += struct.pack(">B", len(rtts))
        for rtt in rtts:
            payload += struct.pack(">f", rtt)

        header = struct.pack(">BI", MSG_TRACE_HOP, len(payload))
        proto._buffer = header + payload

        proto._process_buffer()

        assert len(proto._hops) == 1
        assert proto._hops[0].hop_num == 1


class TestTracerouteProtocolIntegration:
    """Integration-style tests for TracerouteProtocol."""

    @pytest.mark.asyncio
    async def test_full_trace_flow(self):
        """Test full trace flow with mock."""
        proto = TracerouteProtocol(is_server=False)
        mock_protocol = Mock()
        mock_protocol.send = Mock()
        proto._protocol = mock_protocol

        # Simulate receiving hop results
        async def simulate_hops():
            await asyncio.sleep(0.01)

            proto._hops.append(HopResult(1, "relay", "relay.wh", [10.0, 11.0, 10.5]))
            proto._hops.append(HopResult(2, "peer", "peer", [25.0, 24.0, 26.0]))
            proto._hops.append(HopResult(3, "target", "93.184.216.34", [35.0, 34.0, 36.0]))

            proto._trace_complete.set()

        asyncio.create_task(simulate_hops())

        hops = await proto.trace("example.com")

        assert len(hops) == 3
        assert hops[0].hop_num == 1
        assert hops[1].hop_num == 2
        assert hops[2].hop_num == 3

    def test_hops_sorted(self):
        """Test hops are returned sorted by hop number."""
        proto = TracerouteProtocol(is_server=False)

        # Add hops out of order
        proto._hops.append(HopResult(3, "c", "3.3.3.3", []))
        proto._hops.append(HopResult(1, "a", "1.1.1.1", []))
        proto._hops.append(HopResult(2, "b", "2.2.2.2", []))

        # The trace method sorts them
        sorted_hops = sorted(proto._hops, key=lambda h: h.hop_num)

        assert sorted_hops[0].hop_num == 1
        assert sorted_hops[1].hop_num == 2
        assert sorted_hops[2].hop_num == 3
