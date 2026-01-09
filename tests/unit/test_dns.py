"""Unit tests for wh dns command."""

import pytest
import struct
import json
from unittest.mock import Mock, MagicMock, AsyncMock, patch
import asyncio

from wh.cli.dns import (
    DNSProtocol, DNSRecord, DNSResponse,
    MSG_QUERY, MSG_RESPONSE,
    RECORD_TYPES, RECORD_TYPE_NAMES,
)


class TestDNSRecord:
    """Tests for DNSRecord dataclass."""

    def test_create_record(self):
        """Test creating DNSRecord."""
        record = DNSRecord(
            name="example.com",
            type="A",
            ttl=300,
            value="93.184.216.34",
        )

        assert record.name == "example.com"
        assert record.type == "A"
        assert record.ttl == 300
        assert record.value == "93.184.216.34"


class TestDNSResponse:
    """Tests for DNSResponse dataclass."""

    def test_create_response(self):
        """Test creating DNSResponse."""
        response = DNSResponse(
            query="example.com",
            query_type="A",
            answers=[DNSRecord("example.com", "A", 300, "93.184.216.34")],
            authorities=[],
            additionals=[],
        )

        assert response.query == "example.com"
        assert response.query_type == "A"
        assert len(response.answers) == 1
        assert response.error == ""

    def test_response_with_error(self):
        """Test DNSResponse with error."""
        response = DNSResponse(
            query="invalid.example",
            query_type="A",
            answers=[],
            authorities=[],
            additionals=[],
            error="NXDOMAIN",
        )

        assert response.error == "NXDOMAIN"


class TestRecordTypes:
    """Tests for DNS record type constants."""

    def test_record_types(self):
        """Test record type values."""
        assert RECORD_TYPES["A"] == 1
        assert RECORD_TYPES["AAAA"] == 28
        assert RECORD_TYPES["CNAME"] == 5
        assert RECORD_TYPES["MX"] == 15
        assert RECORD_TYPES["NS"] == 2
        assert RECORD_TYPES["TXT"] == 16

    def test_record_type_names(self):
        """Test reverse mapping."""
        assert RECORD_TYPE_NAMES[1] == "A"
        assert RECORD_TYPE_NAMES[28] == "AAAA"


class TestDNSProtocol:
    """Tests for DNSProtocol class."""

    def test_init_defaults(self):
        """Test protocol initialization with defaults."""
        proto = DNSProtocol()

        assert proto.on_status is None
        assert proto.is_server is False
        assert proto.dns_server == "8.8.8.8"
        assert proto.timeout == 10.0
        assert proto._protocol is None
        assert proto._buffer == b""
        assert not proto._done.is_set()

    def test_init_with_options(self):
        """Test protocol initialization with options."""
        on_status = Mock()

        proto = DNSProtocol(
            on_status=on_status,
            is_server=True,
            dns_server="1.1.1.1",
            timeout=5.0,
        )

        assert proto.on_status is on_status
        assert proto.is_server is True
        assert proto.dns_server == "1.1.1.1"
        assert proto.timeout == 5.0

    def test_status_callback(self):
        """Test status callback."""
        on_status = Mock()
        proto = DNSProtocol(on_status=on_status)

        proto._status("resolving...")

        on_status.assert_called_once_with("resolving...")

    def test_send_message(self):
        """Test message sending."""
        proto = DNSProtocol()
        mock_protocol = Mock()
        mock_protocol.send = Mock()
        proto._protocol = mock_protocol

        query_data = {"name": "example.com", "type": "A"}
        proto._send_message(MSG_QUERY, json.dumps(query_data).encode())

        mock_protocol.send.assert_called_once()
        sent_data = mock_protocol.send.call_args[0][0]
        msg_type, _ = struct.unpack(">BI", sent_data[:5])
        assert msg_type == MSG_QUERY

    def test_handle_response(self):
        """Test handling DNS response."""
        proto = DNSProtocol(is_server=False)
        proto._response_future = asyncio.get_event_loop().create_future()

        response = {
            "query": "example.com",
            "query_type": "A",
            "answers": [{"name": "example.com", "type": "A", "ttl": 300, "value": "1.2.3.4"}],
            "authorities": [],
            "additionals": [],
            "error": "",
        }
        payload = json.dumps(response).encode()

        proto._handle_response(payload)

        assert proto._response_future.done()
        result = proto._response_future.result()
        assert result["query"] == "example.com"
        assert len(result["answers"]) == 1

    def test_on_connection_lost(self):
        """Test connection lost handling."""
        proto = DNSProtocol()
        proto._response_future = asyncio.get_event_loop().create_future()

        proto._on_connection_lost(None)

        assert proto._done.is_set()
        assert proto._response_future.done()

    @pytest.mark.asyncio
    async def test_query(self):
        """Test DNS query."""
        proto = DNSProtocol(is_server=False)
        mock_protocol = Mock()
        mock_protocol.send = Mock()
        proto._protocol = mock_protocol

        # Simulate response
        async def simulate_response():
            await asyncio.sleep(0.01)
            if proto._response_future and not proto._response_future.done():
                proto._response_future.set_result({
                    "query": "example.com",
                    "query_type": "A",
                    "answers": [{"name": "example.com", "type": "A", "ttl": 300, "value": "93.184.216.34"}],
                    "authorities": [],
                    "additionals": [],
                    "error": "",
                })

        asyncio.create_task(simulate_response())

        result = await proto.query("example.com", "A")

        assert result["query"] == "example.com"
        assert len(result["answers"]) == 1

    @pytest.mark.asyncio
    async def test_query_timeout(self):
        """Test DNS query timeout."""
        proto = DNSProtocol(is_server=False, timeout=0.1)
        mock_protocol = Mock()
        mock_protocol.send = Mock()
        proto._protocol = mock_protocol

        result = await proto.query("example.com", "A")

        assert result["error"] == "Query timed out"

    def test_process_buffer_query(self):
        """Test processing query message."""
        proto = DNSProtocol(is_server=True)

        query_data = {"name": "example.com", "type": "A"}
        payload = json.dumps(query_data).encode()
        header = struct.pack(">BI", MSG_QUERY, len(payload))
        proto._buffer = header + payload

        with patch('asyncio.create_task') as mock_create_task:
            proto._process_buffer()
            mock_create_task.assert_called_once()

    def test_process_buffer_response(self):
        """Test processing response message."""
        proto = DNSProtocol(is_server=False)
        proto._response_future = asyncio.get_event_loop().create_future()

        response = {"query": "test.com", "answers": [], "error": ""}
        payload = json.dumps(response).encode()
        header = struct.pack(">BI", MSG_RESPONSE, len(payload))
        proto._buffer = header + payload

        proto._process_buffer()

        assert proto._response_future.done()


class TestDNSProtocolServer:
    """Tests for DNSProtocol server-side functionality."""

    @pytest.mark.asyncio
    async def test_handle_query_a_record(self):
        """Test handling A record query."""
        proto = DNSProtocol(is_server=True)
        mock_protocol = Mock()
        mock_protocol.send = Mock()
        proto._protocol = mock_protocol

        query_data = {"name": "localhost", "type": "A"}
        payload = json.dumps(query_data).encode()

        with patch('socket.gethostbyname_ex') as mock_dns:
            mock_dns.return_value = ("localhost", [], ["127.0.0.1"])
            await proto._handle_query(payload)

        mock_protocol.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_query_ptr_record(self):
        """Test handling PTR record query."""
        proto = DNSProtocol(is_server=True)
        mock_protocol = Mock()
        mock_protocol.send = Mock()
        proto._protocol = mock_protocol

        query_data = {"name": "8.8.8.8", "type": "PTR"}
        payload = json.dumps(query_data).encode()

        with patch('socket.gethostbyaddr') as mock_dns:
            mock_dns.return_value = ("dns.google", [], [])
            await proto._handle_query(payload)

        mock_protocol.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_query_unsupported_type(self):
        """Test handling unsupported record type."""
        proto = DNSProtocol(is_server=True)
        mock_protocol = Mock()
        mock_protocol.send = Mock()
        proto._protocol = mock_protocol

        query_data = {"name": "example.com", "type": "UNKNOWN"}
        payload = json.dumps(query_data).encode()

        await proto._handle_query(payload)

        mock_protocol.send.assert_called_once()
        # Should have sent error response


class TestDNSProtocolIntegration:
    """Integration-style tests for DNSProtocol."""

    @pytest.mark.asyncio
    async def test_full_query_flow(self):
        """Test full query flow."""
        proto = DNSProtocol(is_server=False)
        mock_protocol = Mock()
        mock_protocol.send = Mock()
        proto._protocol = mock_protocol

        # Simulate receiving response
        async def simulate_response():
            await asyncio.sleep(0.01)

            if proto._response_future and not proto._response_future.done():
                proto._response_future.set_result({
                    "query": "example.com",
                    "query_type": "A",
                    "answers": [
                        {"name": "example.com", "type": "A", "ttl": 300, "value": "93.184.216.34"},
                    ],
                    "authorities": [],
                    "additionals": [],
                    "error": "",
                })

        asyncio.create_task(simulate_response())

        result = await proto.query("example.com", "A")

        assert result["query"] == "example.com"
        assert len(result["answers"]) == 1
        assert result["answers"][0]["value"] == "93.184.216.34"

    @pytest.mark.asyncio
    async def test_query_with_error(self):
        """Test query returning error."""
        proto = DNSProtocol(is_server=False)
        mock_protocol = Mock()
        mock_protocol.send = Mock()
        proto._protocol = mock_protocol

        async def simulate_error():
            await asyncio.sleep(0.01)
            if proto._response_future and not proto._response_future.done():
                proto._response_future.set_result({
                    "query": "nonexistent.invalid",
                    "query_type": "A",
                    "answers": [],
                    "authorities": [],
                    "additionals": [],
                    "error": "NXDOMAIN",
                })

        asyncio.create_task(simulate_error())

        result = await proto.query("nonexistent.invalid", "A")

        assert result["error"] == "NXDOMAIN"
        assert len(result["answers"]) == 0
