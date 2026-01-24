"""Unit tests for wh nmap command."""

import pytest
import struct
from unittest.mock import Mock, patch
import asyncio

from wh.cli.nmap import (
    NmapProtocol, PortResult, parse_ports,
    MSG_SCAN_REQUEST, MSG_SCAN_RESULT, MSG_SCAN_COMPLETE,
    COMMON_PORTS, SERVICE_NAMES,
)


class TestPortResult:
    """Tests for PortResult dataclass."""

    def test_create_port_result(self):
        """Test creating PortResult."""
        result = PortResult(
            port=80,
            state="open",
            service="http",
            latency_ms=15.5,
        )

        assert result.port == 80
        assert result.state == "open"
        assert result.service == "http"
        assert result.latency_ms == 15.5


class TestParsePorts:
    """Tests for parse_ports function."""

    def test_parse_common(self):
        """Test parsing 'common' keyword."""
        ports = parse_ports("common")
        assert ports == sorted(COMMON_PORTS)

    def test_parse_single_port(self):
        """Test parsing single port."""
        ports = parse_ports("80")
        assert ports == [80]

    def test_parse_multiple_ports(self):
        """Test parsing multiple ports."""
        ports = parse_ports("22,80,443")
        assert ports == [22, 80, 443]

    def test_parse_port_range(self):
        """Test parsing port range."""
        ports = parse_ports("1-5")
        assert ports == [1, 2, 3, 4, 5]

    def test_parse_mixed(self):
        """Test parsing mixed format."""
        ports = parse_ports("22,80-82,443")
        assert ports == [22, 80, 81, 82, 443]

    def test_parse_with_spaces(self):
        """Test parsing with spaces."""
        ports = parse_ports("22, 80, 443")
        assert ports == [22, 80, 443]

    def test_parse_invalid_port(self):
        """Test parsing invalid port."""
        ports = parse_ports("invalid")
        assert ports == []

    def test_parse_out_of_range_port(self):
        """Test parsing out of range port."""
        ports = parse_ports("0,65536,70000")
        assert ports == []

    def test_parse_valid_and_invalid(self):
        """Test parsing mix of valid and invalid."""
        ports = parse_ports("80,invalid,443")
        assert ports == [80, 443]

    def test_parse_large_range(self):
        """Test parsing large range is limited."""
        ports = parse_ports("1-65535")
        assert len(ports) == 65535
        assert ports[0] == 1
        assert ports[-1] == 65535


class TestNmapProtocol:
    """Tests for NmapProtocol class."""

    def test_init_defaults(self):
        """Test protocol initialization with defaults."""
        proto = NmapProtocol()

        assert proto.on_status is None
        assert proto.is_server is False
        assert proto.timeout == 3.0
        assert proto.concurrency == 100
        assert proto._protocol is None
        assert proto._buffer == b""
        assert not proto._done.is_set()

    def test_init_with_options(self):
        """Test protocol initialization with options."""
        on_status = Mock()

        proto = NmapProtocol(
            on_status=on_status,
            is_server=True,
            timeout=5.0,
            concurrency=50,
        )

        assert proto.on_status is on_status
        assert proto.is_server is True
        assert proto.timeout == 5.0
        assert proto.concurrency == 50

    def test_status_callback(self):
        """Test status callback."""
        on_status = Mock()
        proto = NmapProtocol(on_status=on_status)

        proto._status("scanning...")

        on_status.assert_called_once_with("scanning...")

    def test_send_message(self):
        """Test message sending."""
        proto = NmapProtocol()
        mock_protocol = Mock()
        mock_protocol.send = Mock()
        proto._protocol = mock_protocol

        proto._send_message(MSG_SCAN_COMPLETE, b"")

        mock_protocol.send.assert_called_once()
        sent_data = mock_protocol.send.call_args[0][0]
        msg_type, data_len = struct.unpack(">BI", sent_data[:5])
        assert msg_type == MSG_SCAN_COMPLETE

    def test_handle_scan_result(self):
        """Test handling scan result."""
        proto = NmapProtocol(is_server=False)

        # Build scan result: port(2) + state(1) + service_len(1) + latency(4) + service
        port = 80
        state = 1  # open
        service = b"http"
        latency = 15.5

        payload = struct.pack(">HBBf", port, state, len(service), latency) + service

        proto._handle_scan_result(payload)

        assert 80 in proto._results
        result = proto._results[80]
        assert result.port == 80
        assert result.state == "open"
        assert result.service == "http"
        assert result.latency_ms == pytest.approx(15.5, rel=0.01)

    def test_handle_scan_complete(self):
        """Test handling scan complete."""
        proto = NmapProtocol(is_server=False)

        header = struct.pack(">BI", MSG_SCAN_COMPLETE, 0)
        proto._buffer = header

        proto._process_buffer()

        assert proto._scan_complete.is_set()

    def test_on_connection_lost(self):
        """Test connection lost handling."""
        proto = NmapProtocol()

        proto._on_connection_lost(None)

        assert proto._done.is_set()
        assert proto._scan_complete.is_set()

    @pytest.mark.asyncio
    async def test_scan_request(self):
        """Test scan request."""
        proto = NmapProtocol(is_server=False)
        mock_protocol = Mock()
        mock_protocol.send = Mock()
        proto._protocol = mock_protocol

        # Simulate quick scan complete
        async def set_complete():
            await asyncio.sleep(0.01)
            proto._scan_complete.set()

        asyncio.create_task(set_complete())

        await proto.scan("localhost", [80, 443])

        # Verify request was sent
        mock_protocol.send.assert_called_once()

    def test_process_buffer_scan_request(self):
        """Test processing scan request message."""
        proto = NmapProtocol(is_server=True)

        host = b"localhost"
        ports = [80, 443]

        payload = bytes([len(host)]) + host
        payload += struct.pack(">I", len(ports))
        for port in ports:
            payload += struct.pack(">H", port)

        header = struct.pack(">BI", MSG_SCAN_REQUEST, len(payload))
        proto._buffer = header + payload

        with patch('asyncio.create_task') as mock_create_task:
            proto._process_buffer()
            mock_create_task.assert_called_once()

    def test_process_buffer_scan_result(self):
        """Test processing scan result message."""
        proto = NmapProtocol(is_server=False)

        # Build result
        payload = struct.pack(">HBBf", 22, 1, 3, 10.0) + b"ssh"
        header = struct.pack(">BI", MSG_SCAN_RESULT, len(payload))
        proto._buffer = header + payload

        proto._process_buffer()

        assert 22 in proto._results
        assert proto._results[22].state == "open"
        assert proto._results[22].service == "ssh"


class TestServiceNames:
    """Tests for service name constants."""

    def test_common_services(self):
        """Test common services are defined."""
        assert SERVICE_NAMES[22] == "ssh"
        assert SERVICE_NAMES[80] == "http"
        assert SERVICE_NAMES[443] == "https"
        assert SERVICE_NAMES[3306] == "mysql"
        assert SERVICE_NAMES[5432] == "postgresql"

    def test_common_ports_list(self):
        """Test common ports list."""
        assert 22 in COMMON_PORTS
        assert 80 in COMMON_PORTS
        assert 443 in COMMON_PORTS
        assert len(COMMON_PORTS) > 10


class TestNmapProtocolIntegration:
    """Integration-style tests for NmapProtocol."""

    @pytest.mark.asyncio
    async def test_full_scan_flow(self):
        """Test full scan flow with mock."""
        proto = NmapProtocol(is_server=False)
        mock_protocol = Mock()
        mock_protocol.send = Mock()
        proto._protocol = mock_protocol

        # Simulate receiving results
        async def simulate_results():
            await asyncio.sleep(0.01)

            # Add some results
            proto._results[22] = PortResult(22, "open", "ssh", 5.0)
            proto._results[80] = PortResult(80, "closed", "", 0.0)
            proto._results[443] = PortResult(443, "open", "https", 8.0)

            proto._scan_complete.set()

        asyncio.create_task(simulate_results())

        results = await proto.scan("example.com", [22, 80, 443])

        assert len(results) == 3
        assert results[22].state == "open"
        assert results[80].state == "closed"
        assert results[443].state == "open"

    def test_state_mapping(self):
        """Test state byte to string mapping."""
        proto = NmapProtocol(is_server=False)

        # Test open state (1)
        payload = struct.pack(">HBBf", 80, 1, 0, 0.0)
        proto._handle_scan_result(payload)
        assert proto._results[80].state == "open"

        # Test closed state (2)
        payload = struct.pack(">HBBf", 81, 2, 0, 0.0)
        proto._handle_scan_result(payload)
        assert proto._results[81].state == "closed"

        # Test filtered state (3)
        payload = struct.pack(">HBBf", 82, 3, 0, 0.0)
        proto._handle_scan_result(payload)
        assert proto._results[82].state == "filtered"
