"""Unit tests for wh telnet command."""

import pytest
import struct
from unittest.mock import Mock, patch
import asyncio

from wh.cli.telnet import (
    TelnetProtocol,
    MSG_CONNECT, MSG_DATA, MSG_CLOSE,
)


class TestTelnetProtocol:
    """Tests for TelnetProtocol class."""

    def test_init_defaults(self):
        """Test protocol initialization with defaults."""
        proto = TelnetProtocol()

        assert proto.on_status is None
        assert proto.on_data_callback is None
        assert proto.is_server is False
        assert proto._protocol is None
        assert proto._buffer == b""
        assert not proto._done.is_set()
        assert not proto._connected.is_set()

    def test_init_with_callbacks(self):
        """Test protocol initialization with callbacks."""
        on_status = Mock()
        on_data = Mock()

        proto = TelnetProtocol(
            on_status=on_status,
            on_data=on_data,
            is_server=True,
        )

        assert proto.on_status is on_status
        assert proto.on_data_callback is on_data
        assert proto.is_server is True

    def test_status_callback(self):
        """Test status callback is called."""
        on_status = Mock()
        proto = TelnetProtocol(on_status=on_status)

        proto._status("test message")

        on_status.assert_called_once_with("test message")

    def test_status_no_callback(self):
        """Test status when no callback is set."""
        proto = TelnetProtocol()

        # Should not raise
        proto._status("test message")

    def test_send_message(self):
        """Test message sending."""
        proto = TelnetProtocol()
        mock_protocol = Mock()
        mock_protocol.send = Mock()
        proto._protocol = mock_protocol

        proto._send_message(MSG_DATA, b"test data")

        mock_protocol.send.assert_called_once()
        sent_data = mock_protocol.send.call_args[0][0]

        # Parse header
        msg_type, data_len = struct.unpack(">BI", sent_data[:5])
        assert msg_type == MSG_DATA
        assert data_len == 9  # len("test data")
        assert sent_data[5:] == b"test data"

    def test_send_message_no_protocol(self):
        """Test send message when protocol is None."""
        proto = TelnetProtocol()
        proto._protocol = None

        # Should not raise
        proto._send_message(MSG_DATA, b"test")

    def test_on_data_buffering(self):
        """Test data is buffered correctly."""
        proto = TelnetProtocol()

        proto._on_data(b"partial")
        assert proto._buffer == b"partial"

        proto._on_data(b" data")
        assert proto._buffer == b"partial data"

    def test_process_buffer_incomplete_message(self):
        """Test processing incomplete message."""
        proto = TelnetProtocol()

        # Send only header, no payload
        header = struct.pack(">BI", MSG_DATA, 10)
        proto._buffer = header

        proto._process_buffer()

        # Buffer should remain unchanged (waiting for more data)
        assert proto._buffer == header

    def test_handle_connect_ok(self):
        """Test handling connect success."""
        proto = TelnetProtocol(is_server=False)

        assert not proto._connected.is_set()
        proto._handle_connect_ok()

        assert proto._connect_result is True
        assert proto._connected.is_set()

    def test_handle_connect_fail(self):
        """Test handling connect failure."""
        proto = TelnetProtocol(is_server=False)

        proto._handle_connect_fail(b"Connection refused")

        assert proto._connect_result is False
        assert proto._connect_error == "Connection refused"
        assert proto._connected.is_set()

    def test_handle_data_server_mode(self):
        """Test data handling in server mode."""
        proto = TelnetProtocol(is_server=True)
        mock_writer = Mock()
        mock_writer.write = Mock()
        proto._target_writer = mock_writer

        with patch('asyncio.create_task'):
            proto._handle_data(b"test data")

        mock_writer.write.assert_called_once_with(b"test data")

    def test_handle_data_client_mode(self):
        """Test data handling in client mode."""
        on_data = Mock()
        proto = TelnetProtocol(is_server=False, on_data=on_data)

        proto._handle_data(b"test data")

        on_data.assert_called_once_with(b"test data")

    def test_handle_close(self):
        """Test handling close message."""
        proto = TelnetProtocol()
        mock_writer = Mock()
        mock_writer.close = Mock()
        proto._target_writer = mock_writer

        proto._handle_close()

        assert proto._done.is_set()
        mock_writer.close.assert_called_once()

    def test_send_data(self):
        """Test sending data to remote."""
        proto = TelnetProtocol()
        mock_protocol = Mock()
        mock_protocol.send = Mock()
        proto._protocol = mock_protocol

        proto.send_data(b"hello")

        mock_protocol.send.assert_called_once()
        sent_data = mock_protocol.send.call_args[0][0]
        msg_type, _ = struct.unpack(">BI", sent_data[:5])
        assert msg_type == MSG_DATA

    def test_close(self):
        """Test close method."""
        proto = TelnetProtocol()
        mock_protocol = Mock()
        mock_protocol.send = Mock()
        proto._protocol = mock_protocol

        proto.close()

        assert proto._done.is_set()
        mock_protocol.send.assert_called_once()

    def test_on_connection_lost(self):
        """Test connection lost handling."""
        proto = TelnetProtocol()
        mock_writer = Mock()
        mock_writer.close = Mock()
        proto._target_writer = mock_writer

        proto._on_connection_lost(None)

        assert proto._done.is_set()
        mock_writer.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_success(self):
        """Test connect method success."""
        proto = TelnetProtocol()
        mock_protocol = Mock()
        mock_protocol.send = Mock()
        proto._protocol = mock_protocol

        # Simulate successful response
        async def set_connected():
            await asyncio.sleep(0.01)
            proto._connect_result = True
            proto._connected.set()

        asyncio.create_task(set_connected())

        result = await proto.connect("example.com", 80)

        assert result is True

    @pytest.mark.asyncio
    async def test_connect_failure(self):
        """Test connect method failure."""
        proto = TelnetProtocol()
        mock_protocol = Mock()
        mock_protocol.send = Mock()
        proto._protocol = mock_protocol

        # Simulate failed response
        async def set_connected():
            await asyncio.sleep(0.01)
            proto._connect_result = False
            proto._connect_error = "Connection refused"
            proto._connected.set()

        asyncio.create_task(set_connected())

        result = await proto.connect("example.com", 80)

        assert result is False
        assert proto._connect_error == "Connection refused"


class TestTelnetProtocolMessages:
    """Tests for TelnetProtocol message parsing."""

    def test_parse_connect_message(self):
        """Test parsing connect message."""
        proto = TelnetProtocol(is_server=True)

        # Build connect message: host_len + host + port
        host = b"example.com"
        port = 80
        payload = bytes([len(host)]) + host + struct.pack(">H", port)

        header = struct.pack(">BI", MSG_CONNECT, len(payload))
        proto._buffer = header + payload

        # Note: This will try to actually connect, so we mock asyncio.create_task
        with patch('asyncio.create_task') as mock_create_task:
            proto._process_buffer()

            # Check that create_task was called (which schedules _handle_connect)
            mock_create_task.assert_called_once()

    def test_parse_data_message(self):
        """Test parsing data message."""
        proto = TelnetProtocol(is_server=False)
        on_data = Mock()
        proto.on_data_callback = on_data

        payload = b"test payload data"
        header = struct.pack(">BI", MSG_DATA, len(payload))
        proto._buffer = header + payload

        proto._process_buffer()

        on_data.assert_called_once_with(b"test payload data")

    def test_parse_close_message(self):
        """Test parsing close message."""
        proto = TelnetProtocol()

        header = struct.pack(">BI", MSG_CLOSE, 0)
        proto._buffer = header

        proto._process_buffer()

        assert proto._done.is_set()

    def test_parse_multiple_messages(self):
        """Test parsing multiple messages in buffer."""
        proto = TelnetProtocol(is_server=False)
        on_data = Mock()
        proto.on_data_callback = on_data

        # Build two data messages
        payload1 = b"first"
        msg1 = struct.pack(">BI", MSG_DATA, len(payload1)) + payload1

        payload2 = b"second"
        msg2 = struct.pack(">BI", MSG_DATA, len(payload2)) + payload2

        proto._buffer = msg1 + msg2

        proto._process_buffer()

        assert on_data.call_count == 2
        on_data.assert_any_call(b"first")
        on_data.assert_any_call(b"second")
