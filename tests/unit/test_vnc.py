"""Unit tests for wh vnc command."""

import pytest
import struct
from unittest.mock import Mock, MagicMock, AsyncMock, patch
import asyncio

from wh.cli.vnc import (
    VNCProtocol,
    MSG_CONNECT, MSG_CONNECT_OK, MSG_CONNECT_FAIL,
    MSG_DATA, MSG_CLOSE,
    DEFAULT_VNC_PORT,
)


class TestVNCProtocol:
    """Tests for VNCProtocol class."""

    def test_init_defaults(self):
        """Test protocol initialization with defaults."""
        proto = VNCProtocol()

        assert proto.on_status is None
        assert proto.is_server is False
        assert proto.vnc_host == "localhost"
        assert proto.vnc_port == DEFAULT_VNC_PORT
        assert proto.vnc_display == 0
        assert proto._protocol is None
        assert proto._buffer == b""
        assert not proto._done.is_set()
        assert not proto._connected.is_set()

    def test_init_with_options(self):
        """Test protocol initialization with options."""
        on_status = Mock()

        proto = VNCProtocol(
            on_status=on_status,
            is_server=True,
            vnc_host="192.168.1.100",
            vnc_port=5900,
            vnc_display=1,
        )

        assert proto.on_status is on_status
        assert proto.is_server is True
        assert proto.vnc_host == "192.168.1.100"
        assert proto.vnc_port == 5901  # 5900 + display 1
        assert proto.vnc_display == 1

    def test_status_callback(self):
        """Test status callback."""
        on_status = Mock()
        proto = VNCProtocol(on_status=on_status)

        proto._status("connecting...")

        on_status.assert_called_once_with("connecting...")

    def test_send_message(self):
        """Test message sending."""
        proto = VNCProtocol()
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
        proto = VNCProtocol()
        proto._protocol = None

        # Should not raise
        proto._send_message(MSG_DATA, b"test")

    def test_handle_connect_ok(self):
        """Test handling connect success."""
        proto = VNCProtocol(is_server=False)

        assert not proto._vnc_connected.is_set()
        proto._handle_connect_ok()

        assert proto._vnc_connected.is_set()

    def test_handle_connect_fail(self):
        """Test handling connect failure."""
        proto = VNCProtocol(is_server=False)
        on_status = Mock()
        proto.on_status = on_status

        proto._handle_connect_fail(b"Connection refused")

        assert proto._done.is_set()

    def test_handle_data_server_mode(self):
        """Test data handling in server mode."""
        proto = VNCProtocol(is_server=True)
        mock_writer = Mock()
        mock_writer.write = Mock()
        proto._vnc_writer = mock_writer

        with patch('asyncio.create_task'):
            proto._handle_data(b"vnc data")

        mock_writer.write.assert_called_once_with(b"vnc data")

    def test_handle_data_client_mode(self):
        """Test data handling in client mode."""
        proto = VNCProtocol(is_server=False)
        mock_writer = Mock()
        mock_writer.write = Mock()
        proto._vnc_writer = mock_writer

        with patch('asyncio.create_task'):
            proto._handle_data(b"vnc data")

        mock_writer.write.assert_called_once_with(b"vnc data")

    def test_handle_close(self):
        """Test handling close message."""
        proto = VNCProtocol()
        mock_writer = Mock()
        mock_writer.close = Mock()
        proto._vnc_writer = mock_writer

        proto._handle_close()

        assert proto._done.is_set()
        mock_writer.close.assert_called_once()

    def test_on_connection_lost(self):
        """Test connection lost handling."""
        proto = VNCProtocol()
        mock_writer = Mock()
        mock_writer.close = Mock()
        proto._vnc_writer = mock_writer

        proto._on_connection_lost(None)

        assert proto._done.is_set()
        mock_writer.close.assert_called_once()

    def test_on_data_buffering(self):
        """Test data buffering."""
        proto = VNCProtocol()

        proto._on_data(b"partial")
        assert proto._buffer == b"partial"

    def test_process_buffer_incomplete(self):
        """Test processing incomplete buffer."""
        proto = VNCProtocol()

        header = struct.pack(">BI", MSG_DATA, 100)
        proto._buffer = header

        proto._process_buffer()

        assert proto._buffer == header


class TestVNCProtocolMessages:
    """Tests for VNCProtocol message parsing."""

    def test_parse_connect_message(self):
        """Test parsing connect message."""
        proto = VNCProtocol(is_server=True)

        header = struct.pack(">BI", MSG_CONNECT, 0)
        proto._buffer = header

        with patch('asyncio.create_task') as mock_create_task:
            proto._process_buffer()
            mock_create_task.assert_called_once()

    def test_parse_connect_ok_message(self):
        """Test parsing connect OK message."""
        proto = VNCProtocol(is_server=False)

        header = struct.pack(">BI", MSG_CONNECT_OK, 0)
        proto._buffer = header

        proto._process_buffer()

        assert proto._vnc_connected.is_set()

    def test_parse_connect_fail_message(self):
        """Test parsing connect fail message."""
        proto = VNCProtocol(is_server=False)

        error = b"VNC server not available"
        header = struct.pack(">BI", MSG_CONNECT_FAIL, len(error))
        proto._buffer = header + error

        proto._process_buffer()

        assert proto._done.is_set()

    def test_parse_data_message(self):
        """Test parsing data message."""
        proto = VNCProtocol(is_server=False)
        mock_writer = Mock()
        mock_writer.write = Mock()
        proto._vnc_writer = mock_writer

        data = b"VNC protocol data"
        header = struct.pack(">BI", MSG_DATA, len(data))
        proto._buffer = header + data

        with patch('asyncio.create_task'):
            proto._process_buffer()

        mock_writer.write.assert_called_once_with(data)

    def test_parse_close_message(self):
        """Test parsing close message."""
        proto = VNCProtocol()

        header = struct.pack(">BI", MSG_CLOSE, 0)
        proto._buffer = header

        proto._process_buffer()

        assert proto._done.is_set()

    def test_parse_multiple_messages(self):
        """Test parsing multiple messages."""
        proto = VNCProtocol(is_server=False)
        mock_writer = Mock()
        mock_writer.write = Mock()
        proto._vnc_writer = mock_writer

        # Two data messages
        data1 = b"first"
        msg1 = struct.pack(">BI", MSG_DATA, len(data1)) + data1

        data2 = b"second"
        msg2 = struct.pack(">BI", MSG_DATA, len(data2)) + data2

        proto._buffer = msg1 + msg2

        with patch('asyncio.create_task'):
            proto._process_buffer()

        assert mock_writer.write.call_count == 2


class TestVNCProtocolServer:
    """Tests for VNCProtocol server-side functionality."""

    @pytest.mark.asyncio
    async def test_handle_connect_success(self):
        """Test handling connect with successful VNC connection."""
        proto = VNCProtocol(is_server=True, vnc_host="localhost", vnc_port=5900)
        mock_protocol = Mock()
        mock_protocol.send = Mock()
        proto._protocol = mock_protocol

        mock_reader = AsyncMock()
        mock_writer = Mock()
        mock_writer.close = Mock()

        async def mock_open_connection(*args, **kwargs):
            return (mock_reader, mock_writer)

        with patch('asyncio.open_connection', side_effect=mock_open_connection):
            with patch('asyncio.create_task'):  # Prevent background task from running
                await proto._handle_connect(b"")

        # Should have sent MSG_CONNECT_OK
        mock_protocol.send.assert_called()
        sent_data = mock_protocol.send.call_args[0][0]
        msg_type, _ = struct.unpack(">BI", sent_data[:5])
        assert msg_type == MSG_CONNECT_OK

    @pytest.mark.asyncio
    async def test_handle_connect_timeout(self):
        """Test handling connect with timeout."""
        proto = VNCProtocol(is_server=True, vnc_host="localhost", vnc_port=5900)
        mock_protocol = Mock()
        mock_protocol.send = Mock()
        proto._protocol = mock_protocol

        async def mock_timeout(*args, **kwargs):
            raise asyncio.TimeoutError()

        with patch('asyncio.open_connection', side_effect=mock_timeout):
            await proto._handle_connect(b"")

        # Should have sent MSG_CONNECT_FAIL
        mock_protocol.send.assert_called()
        sent_data = mock_protocol.send.call_args[0][0]
        msg_type, _ = struct.unpack(">BI", sent_data[:5])
        assert msg_type == MSG_CONNECT_FAIL

    @pytest.mark.asyncio
    async def test_handle_connect_refused(self):
        """Test handling connect with connection refused."""
        proto = VNCProtocol(is_server=True, vnc_host="localhost", vnc_port=5900)
        mock_protocol = Mock()
        mock_protocol.send = Mock()
        proto._protocol = mock_protocol

        async def mock_refused(*args, **kwargs):
            raise ConnectionRefusedError()

        with patch('asyncio.open_connection', side_effect=mock_refused):
            await proto._handle_connect(b"")

        # Should have sent MSG_CONNECT_FAIL
        mock_protocol.send.assert_called()


class TestVNCProtocolClient:
    """Tests for VNCProtocol client-side functionality."""

    def test_client_init(self):
        """Test client initialization."""
        proto = VNCProtocol(is_server=False)
        assert proto.is_server is False
        assert proto.vnc_port == DEFAULT_VNC_PORT

    def test_client_send_connect(self):
        """Test client sends connect message."""
        proto = VNCProtocol(is_server=False)
        mock_protocol = Mock()
        mock_protocol.send = Mock()
        proto._protocol = mock_protocol

        proto._send_message(MSG_CONNECT)

        mock_protocol.send.assert_called_once()
        sent_data = mock_protocol.send.call_args[0][0]
        msg_type, _ = struct.unpack(">BI", sent_data[:5])
        assert msg_type == MSG_CONNECT

    def test_client_handle_connect_ok(self):
        """Test client handles connect OK."""
        proto = VNCProtocol(is_server=False)

        proto._handle_connect_ok()

        assert proto._vnc_connected.is_set()


class TestDefaultVNCPort:
    """Tests for VNC port constants."""

    def test_default_port(self):
        """Test default VNC port."""
        assert DEFAULT_VNC_PORT == 5900

    def test_display_calculation(self):
        """Test display number calculation."""
        proto = VNCProtocol(vnc_port=5900, vnc_display=0)
        assert proto.vnc_port == 5900

        proto = VNCProtocol(vnc_port=5900, vnc_display=1)
        assert proto.vnc_port == 5901

        proto = VNCProtocol(vnc_port=5900, vnc_display=5)
        assert proto.vnc_port == 5905
