"""Unit tests for wh rdp command."""

import pytest
import struct
from unittest.mock import Mock, MagicMock, AsyncMock, patch
import asyncio

from wh.cli.rdp import (
    RDPProtocol,
    MSG_CONNECT, MSG_CONNECT_OK, MSG_CONNECT_FAIL,
    MSG_DATA, MSG_CLOSE,
    DEFAULT_RDP_PORT,
)


class TestRDPProtocol:
    """Tests for RDPProtocol class."""

    def test_init_defaults(self):
        """Test protocol initialization with defaults."""
        proto = RDPProtocol()

        assert proto.on_status is None
        assert proto.is_server is False
        assert proto.rdp_host == "localhost"
        assert proto.rdp_port == DEFAULT_RDP_PORT
        assert proto._protocol is None
        assert proto._buffer == b""
        assert not proto._done.is_set()
        assert not proto._connected.is_set()

    def test_init_with_options(self):
        """Test protocol initialization with options."""
        on_status = Mock()

        proto = RDPProtocol(
            on_status=on_status,
            is_server=True,
            rdp_host="192.168.1.100",
            rdp_port=3389,
        )

        assert proto.on_status is on_status
        assert proto.is_server is True
        assert proto.rdp_host == "192.168.1.100"
        assert proto.rdp_port == 3389

    def test_status_callback(self):
        """Test status callback."""
        on_status = Mock()
        proto = RDPProtocol(on_status=on_status)

        proto._status("connecting...")

        on_status.assert_called_once_with("connecting...")

    def test_send_message(self):
        """Test message sending."""
        proto = RDPProtocol()
        mock_protocol = Mock()
        mock_protocol.send = Mock()
        proto._protocol = mock_protocol

        proto._send_message(MSG_CONNECT, b"")

        mock_protocol.send.assert_called_once()
        sent_data = mock_protocol.send.call_args[0][0]
        msg_type, data_len = struct.unpack(">BI", sent_data[:5])
        assert msg_type == MSG_CONNECT
        assert data_len == 0

    def test_send_message_no_protocol(self):
        """Test send message when protocol is None."""
        proto = RDPProtocol()
        proto._protocol = None

        # Should not raise
        proto._send_message(MSG_DATA, b"test")

    def test_handle_connect_ok(self):
        """Test handling connect success."""
        proto = RDPProtocol(is_server=False)

        assert not proto._rdp_connected.is_set()
        proto._handle_connect_ok()

        assert proto._rdp_connected.is_set()

    def test_handle_connect_fail(self):
        """Test handling connect failure."""
        proto = RDPProtocol(is_server=False)
        on_status = Mock()
        proto.on_status = on_status

        proto._handle_connect_fail(b"Connection refused")

        assert proto._done.is_set()

    def test_handle_data_server_mode(self):
        """Test data handling in server mode."""
        proto = RDPProtocol(is_server=True)
        mock_writer = Mock()
        mock_writer.write = Mock()
        proto._rdp_writer = mock_writer

        with patch('asyncio.create_task'):
            proto._handle_data(b"rdp data")

        mock_writer.write.assert_called_once_with(b"rdp data")

    def test_handle_data_client_mode(self):
        """Test data handling in client mode."""
        proto = RDPProtocol(is_server=False)
        mock_writer = Mock()
        mock_writer.write = Mock()
        proto._rdp_writer = mock_writer

        with patch('asyncio.create_task'):
            proto._handle_data(b"rdp data")

        mock_writer.write.assert_called_once_with(b"rdp data")

    def test_handle_close(self):
        """Test handling close message."""
        proto = RDPProtocol()
        mock_writer = Mock()
        mock_writer.close = Mock()
        proto._rdp_writer = mock_writer

        proto._handle_close()

        assert proto._done.is_set()
        mock_writer.close.assert_called_once()

    def test_on_connection_lost(self):
        """Test connection lost handling."""
        proto = RDPProtocol()
        mock_writer = Mock()
        mock_writer.close = Mock()
        proto._rdp_writer = mock_writer

        proto._on_connection_lost(None)

        assert proto._done.is_set()
        mock_writer.close.assert_called_once()

    def test_on_data_buffering(self):
        """Test data buffering."""
        proto = RDPProtocol()

        proto._on_data(b"partial")
        assert proto._buffer == b"partial"

    def test_process_buffer_incomplete(self):
        """Test processing incomplete buffer."""
        proto = RDPProtocol()

        header = struct.pack(">BI", MSG_DATA, 100)
        proto._buffer = header

        proto._process_buffer()

        assert proto._buffer == header


class TestRDPProtocolMessages:
    """Tests for RDPProtocol message parsing."""

    def test_parse_connect_message(self):
        """Test parsing connect message."""
        proto = RDPProtocol(is_server=True)

        header = struct.pack(">BI", MSG_CONNECT, 0)
        proto._buffer = header

        with patch('asyncio.create_task') as mock_create_task:
            proto._process_buffer()
            mock_create_task.assert_called_once()

    def test_parse_connect_ok_message(self):
        """Test parsing connect OK message."""
        proto = RDPProtocol(is_server=False)

        header = struct.pack(">BI", MSG_CONNECT_OK, 0)
        proto._buffer = header

        proto._process_buffer()

        assert proto._rdp_connected.is_set()

    def test_parse_connect_fail_message(self):
        """Test parsing connect fail message."""
        proto = RDPProtocol(is_server=False)

        error = b"RDP server not available"
        header = struct.pack(">BI", MSG_CONNECT_FAIL, len(error))
        proto._buffer = header + error

        proto._process_buffer()

        assert proto._done.is_set()

    def test_parse_data_message(self):
        """Test parsing data message."""
        proto = RDPProtocol(is_server=False)
        mock_writer = Mock()
        mock_writer.write = Mock()
        proto._rdp_writer = mock_writer

        data = b"RDP protocol data"
        header = struct.pack(">BI", MSG_DATA, len(data))
        proto._buffer = header + data

        with patch('asyncio.create_task'):
            proto._process_buffer()

        mock_writer.write.assert_called_once_with(data)

    def test_parse_close_message(self):
        """Test parsing close message."""
        proto = RDPProtocol()

        header = struct.pack(">BI", MSG_CLOSE, 0)
        proto._buffer = header

        proto._process_buffer()

        assert proto._done.is_set()

    def test_parse_multiple_messages(self):
        """Test parsing multiple messages."""
        proto = RDPProtocol(is_server=False)
        mock_writer = Mock()
        mock_writer.write = Mock()
        proto._rdp_writer = mock_writer

        # Two data messages
        data1 = b"first"
        msg1 = struct.pack(">BI", MSG_DATA, len(data1)) + data1

        data2 = b"second"
        msg2 = struct.pack(">BI", MSG_DATA, len(data2)) + data2

        proto._buffer = msg1 + msg2

        with patch('asyncio.create_task'):
            proto._process_buffer()

        assert mock_writer.write.call_count == 2


class TestRDPProtocolServer:
    """Tests for RDPProtocol server-side functionality."""

    @pytest.mark.asyncio
    async def test_handle_connect_success(self):
        """Test handling connect with successful RDP connection."""
        proto = RDPProtocol(is_server=True, rdp_host="localhost", rdp_port=3389)
        mock_protocol = Mock()
        mock_protocol.send = Mock()
        proto._protocol = mock_protocol

        mock_reader = AsyncMock()
        mock_writer = Mock()
        mock_writer.close = Mock()

        with patch('asyncio.open_connection', return_value=(mock_reader, mock_writer)):
            await proto._handle_connect(b"")

        # Should have sent MSG_CONNECT_OK
        mock_protocol.send.assert_called()
        sent_data = mock_protocol.send.call_args[0][0]
        msg_type, _ = struct.unpack(">BI", sent_data[:5])
        assert msg_type == MSG_CONNECT_OK

    @pytest.mark.asyncio
    async def test_handle_connect_timeout(self):
        """Test handling connect with timeout."""
        proto = RDPProtocol(is_server=True, rdp_host="localhost", rdp_port=3389)
        mock_protocol = Mock()
        mock_protocol.send = Mock()
        proto._protocol = mock_protocol

        with patch('asyncio.open_connection', side_effect=asyncio.TimeoutError()):
            await proto._handle_connect(b"")

        # Should have sent MSG_CONNECT_FAIL
        mock_protocol.send.assert_called()
        sent_data = mock_protocol.send.call_args[0][0]
        msg_type, _ = struct.unpack(">BI", sent_data[:5])
        assert msg_type == MSG_CONNECT_FAIL

    @pytest.mark.asyncio
    async def test_handle_connect_refused(self):
        """Test handling connect with connection refused."""
        proto = RDPProtocol(is_server=True, rdp_host="localhost", rdp_port=3389)
        mock_protocol = Mock()
        mock_protocol.send = Mock()
        proto._protocol = mock_protocol

        with patch('asyncio.open_connection', side_effect=ConnectionRefusedError()):
            await proto._handle_connect(b"")

        # Should have sent MSG_CONNECT_FAIL
        mock_protocol.send.assert_called()


class TestRDPProtocolClient:
    """Tests for RDPProtocol client-side functionality."""

    @pytest.mark.asyncio
    async def test_run_client(self):
        """Test client mode setup."""
        proto = RDPProtocol(is_server=False)

        mock_manager = MagicMock()
        mock_endpoint = MagicMock()

        # Create a mock deferred
        class MockDeferred:
            def addCallbacks(self, callback, errback):
                mock_protocol = Mock()
                proto._protocol = mock_protocol
                callback(mock_protocol)

        mock_endpoint.connect.return_value = MockDeferred()
        mock_manager.connector_for.return_value = mock_endpoint

        # Mock the server start
        with patch('asyncio.start_server') as mock_server:
            mock_server.return_value = AsyncMock()

            local_port = await proto.run_client(mock_manager, 13389)

        assert local_port == 13389


class TestDefaultRDPPort:
    """Tests for RDP port constants."""

    def test_default_port(self):
        """Test default RDP port."""
        assert DEFAULT_RDP_PORT == 3389

    def test_custom_port(self):
        """Test custom RDP port."""
        proto = RDPProtocol(rdp_port=3390)
        assert proto.rdp_port == 3390


class TestRDPProtocolIntegration:
    """Integration-style tests for RDPProtocol."""

    @pytest.mark.asyncio
    async def test_forward_from_rdp(self):
        """Test forwarding data from RDP server."""
        proto = RDPProtocol(is_server=True)
        mock_protocol = Mock()
        mock_protocol.send = Mock()
        proto._protocol = mock_protocol

        # Create mock reader that returns data then EOF
        mock_reader = AsyncMock()
        mock_reader.read = AsyncMock(side_effect=[b"rdp data", b""])
        proto._rdp_reader = mock_reader

        await proto._forward_from_rdp()

        # Should have sent data and close
        assert mock_protocol.send.call_count >= 1

    @pytest.mark.asyncio
    async def test_drain_rdp_success(self):
        """Test draining RDP writer."""
        proto = RDPProtocol()
        mock_writer = AsyncMock()
        mock_writer.drain = AsyncMock()
        proto._rdp_writer = mock_writer

        await proto._drain_rdp()

        mock_writer.drain.assert_called_once()

    @pytest.mark.asyncio
    async def test_drain_rdp_error(self):
        """Test draining RDP writer with error."""
        proto = RDPProtocol()
        mock_writer = AsyncMock()
        mock_writer.drain = AsyncMock(side_effect=Exception("Drain failed"))
        proto._rdp_writer = mock_writer

        # Should not raise
        await proto._drain_rdp()
