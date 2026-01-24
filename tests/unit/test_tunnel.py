"""
Unit tests for wh.cli.tunnel module.

Tests for TunnelProtocol and LocalForwarder classes.
"""

import asyncio
import pytest
import struct
from unittest.mock import MagicMock, AsyncMock, patch

from wh.cli.tunnel import (
    parse_forward_spec,
    TunnelProtocol,
    LocalForwarder,
    MSG_OPEN,
    MSG_OPEN_OK,
    MSG_OPEN_FAIL,
    MSG_DATA,
    MSG_CLOSE,
    HEADER_SIZE,
)


class TestParseForwardSpec:
    """Tests for parse_forward_spec function."""

    def test_parse_forward_spec_simple(self):
        """Test parsing simple port:port format defaults to localhost."""
        local_port, remote_host, remote_port = parse_forward_spec("8080:80")

        assert local_port == 8080
        assert remote_host == "localhost"
        assert remote_port == 80

    def test_parse_forward_spec_full(self):
        """Test parsing full port:host:port format."""
        local_port, remote_host, remote_port = parse_forward_spec("8080:example.com:80")

        assert local_port == 8080
        assert remote_host == "example.com"
        assert remote_port == 80

    def test_parse_forward_spec_invalid(self):
        """Test that invalid format raises ValueError."""
        with pytest.raises(ValueError, match="Invalid forward spec"):
            parse_forward_spec("8080")

        with pytest.raises(ValueError, match="Invalid forward spec"):
            parse_forward_spec("8080:example.com:80:extra")


class TestTunnelProtocol:
    """Tests for TunnelProtocol class."""

    def test_tunnel_protocol_init(self):
        """Test TunnelProtocol initialization with all fields."""
        status_callback = MagicMock()
        tunnel = TunnelProtocol(on_status=status_callback)

        assert tunnel.on_status == status_callback
        assert tunnel._protocol is None
        assert tunnel._channels == {}
        assert tunnel._next_channel_id == 1
        assert tunnel._buffer == b""
        assert isinstance(tunnel._done, asyncio.Event)
        assert tunnel._pending_opens == {}

    def test_tunnel_send_message(self):
        """Test _send_message creates correct header format (type + channel_id + data_len)."""
        tunnel = TunnelProtocol()
        mock_protocol = MagicMock()
        tunnel._protocol = mock_protocol

        # Test MSG_DATA with data length
        tunnel._send_message(MSG_DATA, 42, b"test data")

        expected_header = struct.pack(">BH", MSG_DATA, 42)  # type + channel_id
        expected_header += struct.pack(">I", 9)  # data length for "test data"
        expected_message = expected_header + b"test data"

        mock_protocol.send.assert_called_once_with(expected_message)

        # Test MSG_CLOSE without data length
        mock_protocol.reset_mock()
        tunnel._send_message(MSG_CLOSE, 42)

        expected_header = struct.pack(">BH", MSG_CLOSE, 42)
        mock_protocol.send.assert_called_once_with(expected_header)

    def test_tunnel_send_message_no_protocol(self):
        """Test _send_message does nothing when protocol is None."""
        tunnel = TunnelProtocol()
        tunnel._protocol = None

        # Should not raise exception
        tunnel._send_message(MSG_DATA, 1, b"test")

    @pytest.mark.asyncio
    async def test_tunnel_open_channel(self):
        """Test open_channel sends MSG_OPEN message."""
        tunnel = TunnelProtocol()
        mock_protocol = MagicMock()
        tunnel._protocol = mock_protocol

        # Create a task to simulate the response
        async def simulate_response():
            await asyncio.sleep(0.01)
            if 1 in tunnel._pending_opens:
                tunnel._pending_opens[1].set_result(True)

        response_task = asyncio.create_task(simulate_response())

        # Open channel
        channel_id = await tunnel.open_channel("example.com", 80)

        # Wait for response task
        await response_task

        assert channel_id == 1
        assert tunnel._next_channel_id == 2

        # Verify MSG_OPEN was sent
        assert mock_protocol.send.called
        sent_data = mock_protocol.send.call_args[0][0]

        # Parse the header
        msg_type, channel_id_sent = struct.unpack(">BH", sent_data[:HEADER_SIZE])
        assert msg_type == MSG_OPEN
        assert channel_id_sent == 1

    @pytest.mark.asyncio
    async def test_tunnel_handle_data(self):
        """Test _handle_data writes data to channel writer."""
        tunnel = TunnelProtocol()

        # Create mock writer
        mock_writer = MagicMock()
        mock_writer.drain = AsyncMock()

        # Register channel
        tunnel._channels[5] = {"writer": mock_writer}

        # Handle data
        test_data = b"test payload"
        tunnel._handle_data(5, test_data)

        # Give asyncio.create_task a chance to run
        await asyncio.sleep(0.01)

        mock_writer.write.assert_called_once_with(test_data)

    def test_tunnel_handle_data_missing_channel(self):
        """Test _handle_data ignores data for non-existent channel."""
        tunnel = TunnelProtocol()

        # Should not raise exception
        tunnel._handle_data(999, b"test")

    def test_tunnel_handle_close(self):
        """Test _handle_close closes writer and removes channel."""
        tunnel = TunnelProtocol()

        # Create mock writer
        mock_writer = MagicMock()

        # Register channel
        tunnel._channels[3] = {"writer": mock_writer}

        # Handle close
        tunnel._handle_close(3)

        mock_writer.close.assert_called_once()
        assert 3 not in tunnel._channels

    def test_tunnel_handle_close_no_writer(self):
        """Test _handle_close handles channel without writer gracefully."""
        tunnel = TunnelProtocol()

        # Register channel without writer
        tunnel._channels[3] = {"reader": MagicMock()}

        # Should not raise exception
        tunnel._handle_close(3)
        assert 3 not in tunnel._channels

    @pytest.mark.asyncio
    async def test_tunnel_handle_open(self):
        """Test _handle_open establishes connection and sends MSG_OPEN_OK."""
        tunnel = TunnelProtocol()
        mock_protocol = MagicMock()
        tunnel._protocol = mock_protocol

        # Mock asyncio.open_connection
        mock_reader = MagicMock()
        mock_writer = MagicMock()

        with patch('wh.cli.tunnel.asyncio.open_connection',
                   new_callable=AsyncMock,
                   return_value=(mock_reader, mock_writer)):
            # Handle open
            await tunnel._handle_open(7, "example.com", 80)

            # Verify channel was registered
            assert 7 in tunnel._channels
            assert tunnel._channels[7]["reader"] == mock_reader
            assert tunnel._channels[7]["writer"] == mock_writer

            # Verify MSG_OPEN_OK was sent
            assert mock_protocol.send.called
            sent_data = mock_protocol.send.call_args[0][0]
            msg_type, channel_id = struct.unpack(">BH", sent_data[:HEADER_SIZE])
            assert msg_type == MSG_OPEN_OK
            assert channel_id == 7

    @pytest.mark.asyncio
    async def test_tunnel_handle_open_failure(self):
        """Test _handle_open sends MSG_OPEN_FAIL on connection error."""
        tunnel = TunnelProtocol()
        mock_protocol = MagicMock()
        tunnel._protocol = mock_protocol

        # Mock asyncio.open_connection to raise exception
        with patch('wh.cli.tunnel.asyncio.open_connection',
                   new_callable=AsyncMock,
                   side_effect=ConnectionRefusedError("Connection refused")):
            # Handle open
            await tunnel._handle_open(7, "example.com", 80)

            # Verify channel was NOT registered
            assert 7 not in tunnel._channels

            # Verify MSG_OPEN_FAIL was sent
            assert mock_protocol.send.called
            sent_data = mock_protocol.send.call_args[0][0]
            msg_type, channel_id = struct.unpack(">BH", sent_data[:HEADER_SIZE])
            assert msg_type == MSG_OPEN_FAIL
            assert channel_id == 7


class TestLocalForwarder:
    """Tests for LocalForwarder class."""

    def test_local_forwarder_init(self):
        """Test LocalForwarder initialization with all parameters stored."""
        mock_tunnel = MagicMock()
        status_callback = MagicMock()

        forwarder = LocalForwarder(
            tunnel=mock_tunnel,
            local_port=8080,
            remote_host="example.com",
            remote_port=80,
            local_host="0.0.0.0",
            on_status=status_callback,
        )

        assert forwarder.tunnel == mock_tunnel
        assert forwarder.local_port == 8080
        assert forwarder.remote_host == "example.com"
        assert forwarder.remote_port == 80
        assert forwarder.local_host == "0.0.0.0"
        assert forwarder.on_status == status_callback
        assert forwarder._server is None

    @pytest.mark.asyncio
    async def test_local_forwarder_start(self):
        """Test LocalForwarder.start() creates server listening on port."""
        mock_tunnel = MagicMock()
        mock_server = MagicMock()

        forwarder = LocalForwarder(
            tunnel=mock_tunnel,
            local_port=8080,
            remote_host="example.com",
            remote_port=80,
        )

        # Mock asyncio.start_server
        with patch('wh.cli.tunnel.asyncio.start_server',
                   new_callable=AsyncMock,
                   return_value=mock_server) as mock_start_server:
            await forwarder.start()

            # Verify server was created with correct parameters
            mock_start_server.assert_called_once()
            call_args = mock_start_server.call_args
            assert call_args[0][1] == "127.0.0.1"  # local_host (default)
            assert call_args[0][2] == 8080  # local_port

            # Verify server was stored
            assert forwarder._server == mock_server

    @pytest.mark.asyncio
    async def test_local_forwarder_start_with_custom_host(self):
        """Test LocalForwarder.start() with custom local_host."""
        mock_tunnel = MagicMock()
        mock_server = MagicMock()

        forwarder = LocalForwarder(
            tunnel=mock_tunnel,
            local_port=3000,
            remote_host="api.example.com",
            remote_port=443,
            local_host="0.0.0.0",
        )

        # Mock asyncio.start_server
        with patch('wh.cli.tunnel.asyncio.start_server',
                   new_callable=AsyncMock,
                   return_value=mock_server) as mock_start_server:
            await forwarder.start()

            # Verify server was created with custom host
            call_args = mock_start_server.call_args
            assert call_args[0][1] == "0.0.0.0"
            assert call_args[0][2] == 3000

    @pytest.mark.asyncio
    async def test_local_forwarder_stop(self):
        """Test LocalForwarder.stop() closes and waits for server."""
        mock_tunnel = MagicMock()
        forwarder = LocalForwarder(
            tunnel=mock_tunnel,
            local_port=8080,
            remote_host="example.com",
            remote_port=80,
        )

        # Create mock server
        mock_server = MagicMock()
        mock_server.wait_closed = AsyncMock()
        forwarder._server = mock_server

        # Stop the forwarder
        await forwarder.stop()

        # Verify server was closed
        mock_server.close.assert_called_once()
        mock_server.wait_closed.assert_called_once()

    @pytest.mark.asyncio
    async def test_local_forwarder_handle_connection(self):
        """Test _handle_connection opens channel and forwards data."""
        mock_tunnel = MagicMock()
        mock_tunnel.open_channel = AsyncMock(return_value=42)
        mock_tunnel._channels = {}
        mock_tunnel._forward_to_wormhole = AsyncMock()

        forwarder = LocalForwarder(
            tunnel=mock_tunnel,
            local_port=8080,
            remote_host="example.com",
            remote_port=80,
        )

        # Create mock reader/writer
        mock_reader = MagicMock()
        mock_writer = MagicMock()

        # Handle connection
        await forwarder._handle_connection(mock_reader, mock_writer)

        # Verify channel was opened
        mock_tunnel.open_channel.assert_called_once_with("example.com", 80)

        # Verify channel was registered
        assert 42 in mock_tunnel._channels
        assert mock_tunnel._channels[42]["reader"] == mock_reader
        assert mock_tunnel._channels[42]["writer"] == mock_writer

        # Verify forwarding started
        mock_tunnel._forward_to_wormhole.assert_called_once_with(42, mock_reader)

    @pytest.mark.asyncio
    async def test_local_forwarder_handle_connection_failure(self):
        """Test _handle_connection closes writer when channel open fails."""
        mock_tunnel = MagicMock()
        mock_tunnel.open_channel = AsyncMock(return_value=None)

        forwarder = LocalForwarder(
            tunnel=mock_tunnel,
            local_port=8080,
            remote_host="example.com",
            remote_port=80,
        )

        # Create mock reader/writer
        mock_reader = MagicMock()
        mock_writer = MagicMock()

        # Handle connection
        await forwarder._handle_connection(mock_reader, mock_writer)

        # Verify channel was attempted
        mock_tunnel.open_channel.assert_called_once_with("example.com", 80)

        # Verify writer was closed
        mock_writer.close.assert_called_once()

    def test_local_forwarder_status_callback(self):
        """Test that status messages are sent to callback."""
        mock_tunnel = MagicMock()
        status_callback = MagicMock()

        forwarder = LocalForwarder(
            tunnel=mock_tunnel,
            local_port=8080,
            remote_host="example.com",
            remote_port=80,
            on_status=status_callback,
        )

        # Trigger status message
        forwarder._status("test message")

        status_callback.assert_called_once_with("test message")

    def test_tunnel_protocol_status_callback(self):
        """Test that TunnelProtocol status messages are sent to callback."""
        status_callback = MagicMock()
        tunnel = TunnelProtocol(on_status=status_callback)

        # Trigger status message
        tunnel._status("test message")

        status_callback.assert_called_once_with("test message")

    def test_tunnel_on_connection_lost(self):
        """Test _on_connection_lost closes all channels and sets done event."""
        tunnel = TunnelProtocol()

        # Create mock writers for multiple channels
        mock_writer1 = MagicMock()
        mock_writer2 = MagicMock()

        tunnel._channels[1] = {"writer": mock_writer1}
        tunnel._channels[2] = {"writer": mock_writer2}
        tunnel._channels[3] = {"reader": MagicMock()}  # No writer

        # Handle connection lost
        tunnel._on_connection_lost(None)

        # Verify all writers were closed
        mock_writer1.close.assert_called_once()
        mock_writer2.close.assert_called_once()

        # Verify channels were cleared
        assert len(tunnel._channels) == 0

        # Verify done event was set
        assert tunnel._done.is_set()
