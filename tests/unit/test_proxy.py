"""Unit tests for proxy module."""

import pytest
import struct
import socket
import asyncio
from unittest.mock import Mock, MagicMock, AsyncMock, patch
from wh.cli.proxy import (
    ProxyProtocol,
    Socks5Server,
    SOCKS_VERSION,
    AUTH_NONE,
    AUTH_NO_ACCEPTABLE,
    CMD_CONNECT,
    CMD_BIND,
    CMD_UDP,
    ATYP_IPV4,
    ATYP_DOMAIN,
    ATYP_IPV6,
    REP_SUCCESS,
    REP_CMD_NOT_SUPPORTED,
    REP_HOST_UNREACHABLE,
    MSG_CONNECT,
    MSG_CONNECT_OK,
    MSG_CONNECT_FAIL,
    MSG_DATA,
    MSG_CLOSE,
)


class TestProxyProtocol:
    """Tests for ProxyProtocol class."""

    def test_proxy_protocol_init(self):
        """Test ProxyProtocol initialization - all fields initialized."""
        on_status = Mock()
        protocol = ProxyProtocol(on_status=on_status)

        assert protocol.on_status is on_status
        assert protocol._protocol is None
        assert protocol._channels == {}
        assert protocol._next_channel_id == 1
        assert protocol._buffer == b""
        assert isinstance(protocol._done, asyncio.Event)
        assert not protocol._done.is_set()

    def test_proxy_send_message(self):
        """Test _send_message - header format: type (1) + channel_id (2) + data_len (4) + data."""
        protocol = ProxyProtocol()
        mock_streaming_protocol = MagicMock()
        protocol._protocol = mock_streaming_protocol

        # Test with data
        protocol._send_message(MSG_DATA, 42, b"hello")

        # Verify header format: type=1, channel_id=2, data_len=4, data=variable
        expected_header = struct.pack(">BHI", MSG_DATA, 42, 5)
        expected_message = expected_header + b"hello"
        mock_streaming_protocol.send.assert_called_once_with(expected_message)

        # Test with empty data
        mock_streaming_protocol.reset_mock()
        protocol._send_message(MSG_CONNECT_OK, 1, b"")

        expected_header = struct.pack(">BHI", MSG_CONNECT_OK, 1, 0)
        mock_streaming_protocol.send.assert_called_once_with(expected_header)

    def test_proxy_send_message_no_protocol(self):
        """Test _send_message when protocol is not set."""
        protocol = ProxyProtocol()
        # Should not raise when protocol is None
        protocol._send_message(MSG_DATA, 1, b"test")

    def test_proxy_connect_request(self):
        """Test connect() - MSG_CONNECT message sent with host/port."""
        protocol = ProxyProtocol()
        mock_streaming_protocol = MagicMock()
        protocol._protocol = mock_streaming_protocol

        # Create a pending future that will be set
        loop = asyncio.new_event_loop()

        async def test_connect():
            # Start connect
            connect_task = asyncio.create_task(protocol.connect("example.com", 443))

            # Allow the connect to setup
            await asyncio.sleep(0.01)

            # Verify message was sent
            assert mock_streaming_protocol.send.called
            call_args = mock_streaming_protocol.send.call_args[0][0]

            # Parse header
            msg_type, channel_id, data_len = struct.unpack(">BHI", call_args[:7])
            assert msg_type == MSG_CONNECT
            assert channel_id == 1

            # Parse payload
            payload = call_args[7:]
            host_len = payload[0]
            assert host_len == len(b"example.com")
            host = payload[1:1 + host_len].decode()
            assert host == "example.com"
            port = struct.unpack(">H", payload[1 + host_len:3 + host_len])[0]
            assert port == 443

            # Simulate success response
            protocol._handle_connect_ok(channel_id)

            # Wait for connect to complete
            result = await connect_task
            assert result == channel_id

        loop.run_until_complete(test_connect())
        loop.close()

    @pytest.mark.asyncio
    async def test_proxy_handle_data(self):
        """Test _handle_data - data written to channel writer."""
        protocol = ProxyProtocol()

        # Create mock writer
        mock_writer = MagicMock()
        mock_writer.write = Mock()
        mock_writer.drain = AsyncMock()

        # Set up channel
        channel_id = 1
        protocol._channels[channel_id] = {"writer": mock_writer}

        # Handle data
        test_data = b"test data payload"
        protocol._handle_data(channel_id, test_data)

        # Verify data was written
        mock_writer.write.assert_called_once_with(test_data)

        # Wait for drain task to be created
        await asyncio.sleep(0.01)

    def test_proxy_handle_data_no_channel(self):
        """Test _handle_data when channel doesn't exist."""
        protocol = ProxyProtocol()

        # Should not raise
        protocol._handle_data(999, b"test")

    def test_proxy_handle_data_no_writer(self):
        """Test _handle_data when channel has no writer."""
        protocol = ProxyProtocol()
        protocol._channels[1] = {}

        # Should not raise
        protocol._handle_data(1, b"test")

    @pytest.mark.asyncio
    async def test_proxy_handle_connect_ok(self):
        """Test _handle_connect_ok sets pending future."""
        protocol = ProxyProtocol()

        # Create pending future
        pending = asyncio.get_event_loop().create_future()
        protocol._channels[1] = {"pending": pending}

        # Handle connect ok
        protocol._handle_connect_ok(1)

        # Verify future was set
        assert pending.done()
        assert pending.result() is True

    @pytest.mark.asyncio
    async def test_proxy_handle_connect_fail(self):
        """Test _handle_connect_fail sets pending future."""
        protocol = ProxyProtocol()

        # Create pending future
        pending = asyncio.get_event_loop().create_future()
        protocol._channels[1] = {"pending": pending}

        # Handle connect fail
        protocol._handle_connect_fail(1)

        # Verify future was set
        assert pending.done()
        assert pending.result() is False

    @pytest.mark.asyncio
    async def test_proxy_handle_connect_success(self):
        """Test _handle_connect with successful connection."""
        protocol = ProxyProtocol()
        mock_streaming_protocol = MagicMock()
        protocol._protocol = mock_streaming_protocol

        # Create payload for example.com:443
        host = "example.com"
        port = 443
        payload = bytes([len(host)]) + host.encode() + struct.pack(">H", port)

        # Mock asyncio.open_connection
        mock_reader = MagicMock()
        mock_writer = MagicMock()

        with patch('asyncio.open_connection', AsyncMock(return_value=(mock_reader, mock_writer))):
            await protocol._handle_connect(1, payload)

        # Verify channel was created
        assert 1 in protocol._channels
        assert protocol._channels[1]["reader"] is mock_reader
        assert protocol._channels[1]["writer"] is mock_writer

        # Verify success message was sent
        calls = mock_streaming_protocol.send.call_args_list
        assert len(calls) == 1
        msg = calls[0][0][0]
        msg_type, channel_id, _ = struct.unpack(">BHI", msg[:7])
        assert msg_type == MSG_CONNECT_OK
        assert channel_id == 1

    @pytest.mark.asyncio
    async def test_proxy_handle_connect_failure(self):
        """Test _handle_connect with connection failure."""
        protocol = ProxyProtocol()
        mock_streaming_protocol = MagicMock()
        protocol._protocol = mock_streaming_protocol

        # Create payload
        host = "unreachable.invalid"
        port = 443
        payload = bytes([len(host)]) + host.encode() + struct.pack(">H", port)

        # Mock connection failure
        with patch('asyncio.open_connection', AsyncMock(side_effect=OSError("Connection refused"))):
            await protocol._handle_connect(1, payload)

        # Verify failure message was sent
        calls = mock_streaming_protocol.send.call_args_list
        assert len(calls) == 1
        msg = calls[0][0][0]
        msg_type, channel_id, _ = struct.unpack(">BHI", msg[:7])
        assert msg_type == MSG_CONNECT_FAIL
        assert channel_id == 1

    def test_proxy_handle_close(self):
        """Test _handle_close removes channel and closes writer."""
        protocol = ProxyProtocol()

        mock_writer = MagicMock()
        mock_writer.close = Mock()
        protocol._channels[1] = {"writer": mock_writer}

        protocol._handle_close(1)

        assert 1 not in protocol._channels
        mock_writer.close.assert_called_once()

    def test_proxy_on_connection_lost(self):
        """Test _on_connection_lost sets done event."""
        protocol = ProxyProtocol()

        assert not protocol._done.is_set()
        protocol._on_connection_lost(None)
        assert protocol._done.is_set()


class TestSocks5Server:
    """Tests for Socks5Server class."""

    def test_socks5_server_init(self):
        """Test Socks5Server initialization - port and host set."""
        mock_proxy = MagicMock()
        on_status = Mock()

        server = Socks5Server(
            mock_proxy,
            host="0.0.0.0",
            port=8080,
            on_status=on_status,
        )

        assert server.proxy_proto is mock_proxy
        assert server.host == "0.0.0.0"
        assert server.port == 8080
        assert server.on_status is on_status
        assert server._server is None

    @pytest.mark.asyncio
    async def test_socks5_greeting(self):
        """Test SOCKS5 greeting - no auth selected (AUTH_NONE response)."""
        mock_proxy = MagicMock()
        server = Socks5Server(mock_proxy)

        # Create mock reader/writer
        mock_reader = MagicMock()
        mock_writer = MagicMock()
        mock_writer.write = Mock()
        mock_writer.drain = AsyncMock()
        mock_writer.close = Mock()

        # Simulate SOCKS5 greeting: version=5, nmethods=1, methods=[AUTH_NONE]
        # Then short read on request (will close connection)
        mock_reader.read = AsyncMock(side_effect=[
            bytes([SOCKS_VERSION, 1]),  # Greeting
            bytes([AUTH_NONE]),  # Methods
            b"",  # Short read on request (EOF)
        ])

        # Run handler (will close after greeting due to short read)
        await server._handle_client(mock_reader, mock_writer)

        # Verify AUTH_NONE response was sent
        calls = mock_writer.write.call_args_list
        assert len(calls) >= 1
        assert calls[0][0][0] == bytes([SOCKS_VERSION, AUTH_NONE])
        mock_writer.close.assert_called()

    @pytest.mark.asyncio
    async def test_socks5_greeting_no_acceptable_auth(self):
        """Test SOCKS5 greeting with no acceptable auth."""
        mock_proxy = MagicMock()
        server = Socks5Server(mock_proxy)

        mock_reader = MagicMock()
        mock_writer = MagicMock()
        mock_writer.write = Mock()
        mock_writer.drain = AsyncMock()
        mock_writer.close = Mock()

        # Simulate greeting with auth method we don't support
        mock_reader.read = AsyncMock(side_effect=[
            bytes([SOCKS_VERSION, 1]),  # Greeting
            bytes([0x02]),  # Username/password auth (not supported)
        ])

        await server._handle_client(mock_reader, mock_writer)

        # Verify AUTH_NO_ACCEPTABLE response
        calls = mock_writer.write.call_args_list
        assert calls[0][0][0] == bytes([SOCKS_VERSION, AUTH_NO_ACCEPTABLE])
        mock_writer.close.assert_called()

    @pytest.mark.asyncio
    async def test_socks5_connect_ipv4(self):
        """Test SOCKS5 CONNECT with IPv4 - address parsed correctly."""
        mock_proxy = MagicMock()
        mock_proxy.connect = AsyncMock(return_value=1)
        mock_proxy._send_message = Mock()
        mock_proxy._channels = {}

        server = Socks5Server(mock_proxy)

        mock_reader = MagicMock()
        mock_writer = MagicMock()
        mock_writer.write = Mock()
        mock_writer.drain = AsyncMock()
        mock_writer.close = Mock()

        # Prepare IPv4 address 93.184.216.34 (example.com)
        ipv4_addr = socket.inet_aton("93.184.216.34")
        port_bytes = struct.pack(">H", 80)

        mock_reader.read = AsyncMock(side_effect=[
            bytes([SOCKS_VERSION, 1]),  # Greeting
            bytes([AUTH_NONE]),  # Methods
            bytes([SOCKS_VERSION, CMD_CONNECT, 0x00, ATYP_IPV4]),  # Request
            ipv4_addr,  # IPv4 address
            port_bytes,  # Port
            b"",  # EOF for client data read
        ])

        await server._handle_client(mock_reader, mock_writer)

        # Verify connect was called with correct host/port
        mock_proxy.connect.assert_called_once()
        call_args = mock_proxy.connect.call_args[0]
        assert call_args[0] == "93.184.216.34"
        assert call_args[1] == 80

        # Verify success response was sent
        write_calls = mock_writer.write.call_args_list
        # Last write should be success response
        success_response = write_calls[-2][0][0]  # -2 because -1 might be drain
        assert success_response[0] == SOCKS_VERSION
        assert success_response[1] == REP_SUCCESS

    @pytest.mark.asyncio
    async def test_socks5_connect_domain(self):
        """Test SOCKS5 CONNECT with domain name - parsed correctly."""
        mock_proxy = MagicMock()
        mock_proxy.connect = AsyncMock(return_value=1)
        mock_proxy._send_message = Mock()
        mock_proxy._channels = {}

        server = Socks5Server(mock_proxy)

        mock_reader = MagicMock()
        mock_writer = MagicMock()
        mock_writer.write = Mock()
        mock_writer.drain = AsyncMock()
        mock_writer.close = Mock()

        domain = b"example.com"
        port_bytes = struct.pack(">H", 443)

        mock_reader.read = AsyncMock(side_effect=[
            bytes([SOCKS_VERSION, 1]),  # Greeting
            bytes([AUTH_NONE]),  # Methods
            bytes([SOCKS_VERSION, CMD_CONNECT, 0x00, ATYP_DOMAIN]),  # Request
            bytes([len(domain)]),  # Domain length
            domain,  # Domain name
            port_bytes,  # Port
            b"",  # EOF
        ])

        await server._handle_client(mock_reader, mock_writer)

        # Verify connect was called with correct host/port
        mock_proxy.connect.assert_called_once()
        call_args = mock_proxy.connect.call_args[0]
        assert call_args[0] == "example.com"
        assert call_args[1] == 443

    @pytest.mark.asyncio
    async def test_socks5_connect_ipv6(self):
        """Test SOCKS5 CONNECT with IPv6 - address parsed correctly."""
        mock_proxy = MagicMock()
        mock_proxy.connect = AsyncMock(return_value=1)
        mock_proxy._send_message = Mock()
        mock_proxy._channels = {}

        server = Socks5Server(mock_proxy)

        mock_reader = MagicMock()
        mock_writer = MagicMock()
        mock_writer.write = Mock()
        mock_writer.drain = AsyncMock()
        mock_writer.close = Mock()

        # IPv6 address 2606:2800:220:1:248:1893:25c8:1946 (example.com)
        ipv6_addr = socket.inet_pton(socket.AF_INET6, "2606:2800:220:1:248:1893:25c8:1946")
        port_bytes = struct.pack(">H", 80)

        mock_reader.read = AsyncMock(side_effect=[
            bytes([SOCKS_VERSION, 1]),  # Greeting
            bytes([AUTH_NONE]),  # Methods
            bytes([SOCKS_VERSION, CMD_CONNECT, 0x00, ATYP_IPV6]),  # Request
            ipv6_addr,  # IPv6 address
            port_bytes,  # Port
            b"",  # EOF
        ])

        await server._handle_client(mock_reader, mock_writer)

        # Verify connect was called with correct host/port
        mock_proxy.connect.assert_called_once()
        call_args = mock_proxy.connect.call_args[0]
        assert call_args[0] == "2606:2800:220:1:248:1893:25c8:1946"
        assert call_args[1] == 80

    @pytest.mark.asyncio
    async def test_socks5_unsupported_cmd(self):
        """Test SOCKS5 BIND/UDP return CMD_NOT_SUPPORTED."""
        mock_proxy = MagicMock()
        server = Socks5Server(mock_proxy)

        # Test BIND command
        for cmd in [CMD_BIND, CMD_UDP]:
            mock_reader = MagicMock()
            mock_writer = MagicMock()
            mock_writer.write = Mock()
            mock_writer.drain = AsyncMock()
            mock_writer.close = Mock()

            mock_reader.read = AsyncMock(side_effect=[
                bytes([SOCKS_VERSION, 1]),  # Greeting
                bytes([AUTH_NONE]),  # Methods
                bytes([SOCKS_VERSION, cmd, 0x00, ATYP_IPV4]),  # Request with unsupported cmd
            ])

            await server._handle_client(mock_reader, mock_writer)

            # Verify CMD_NOT_SUPPORTED response
            write_calls = mock_writer.write.call_args_list
            # Last write before close should be error response
            error_response = write_calls[-1][0][0]
            assert error_response[0] == SOCKS_VERSION
            assert error_response[1] == REP_CMD_NOT_SUPPORTED
            mock_writer.close.assert_called()

    @pytest.mark.asyncio
    async def test_socks5_connection_failure(self):
        """Test SOCKS5 connection failure - returns HOST_UNREACHABLE."""
        mock_proxy = MagicMock()
        mock_proxy.connect = AsyncMock(return_value=None)  # Connection failed

        server = Socks5Server(mock_proxy)

        mock_reader = MagicMock()
        mock_writer = MagicMock()
        mock_writer.write = Mock()
        mock_writer.drain = AsyncMock()
        mock_writer.close = Mock()

        ipv4_addr = socket.inet_aton("192.0.2.1")  # TEST-NET-1 (unreachable)
        port_bytes = struct.pack(">H", 80)

        mock_reader.read = AsyncMock(side_effect=[
            bytes([SOCKS_VERSION, 1]),  # Greeting
            bytes([AUTH_NONE]),  # Methods
            bytes([SOCKS_VERSION, CMD_CONNECT, 0x00, ATYP_IPV4]),  # Request
            ipv4_addr,  # IPv4 address
            port_bytes,  # Port
        ])

        await server._handle_client(mock_reader, mock_writer)

        # Verify HOST_UNREACHABLE response
        write_calls = mock_writer.write.call_args_list
        # Last write should be error response
        error_response = write_calls[-1][0][0]
        assert error_response[0] == SOCKS_VERSION
        assert error_response[1] == REP_HOST_UNREACHABLE
        mock_writer.close.assert_called()

    @pytest.mark.asyncio
    async def test_socks5_start_server(self):
        """Test starting SOCKS5 server."""
        mock_proxy = MagicMock()
        server = Socks5Server(mock_proxy, host="127.0.0.1", port=1080)

        with patch('asyncio.start_server', AsyncMock(return_value=MagicMock())) as mock_start:
            await server.start()

            mock_start.assert_called_once_with(
                server._handle_client,
                "127.0.0.1",
                1080,
            )
            assert server._server is not None

    @pytest.mark.asyncio
    async def test_socks5_stop_server(self):
        """Test stopping SOCKS5 server."""
        mock_proxy = MagicMock()
        server = Socks5Server(mock_proxy)

        mock_server = MagicMock()
        mock_server.close = Mock()
        mock_server.wait_closed = AsyncMock()
        server._server = mock_server

        await server.stop()

        mock_server.close.assert_called_once()
        mock_server.wait_closed.assert_called_once()

    @pytest.mark.asyncio
    async def test_socks5_invalid_version(self):
        """Test SOCKS5 with invalid version."""
        mock_proxy = MagicMock()
        server = Socks5Server(mock_proxy)

        mock_reader = MagicMock()
        mock_writer = MagicMock()
        mock_writer.write = Mock()
        mock_writer.close = Mock()

        # Wrong version (SOCKS4)
        mock_reader.read = AsyncMock(return_value=bytes([0x04, 1]))

        await server._handle_client(mock_reader, mock_writer)

        # Should close without response
        mock_writer.close.assert_called()

    def test_socks5_status_callback(self):
        """Test status callback is called."""
        mock_proxy = MagicMock()
        statuses = []
        server = Socks5Server(mock_proxy, on_status=lambda m: statuses.append(m))

        server._status("test message")

        assert "test message" in statuses

    def test_socks5_status_no_callback(self):
        """Test status when no callback set."""
        mock_proxy = MagicMock()
        server = Socks5Server(mock_proxy)

        # Should not raise
        server._status("test message")


class TestProxyProtocolMessageProcessing:
    """Test message processing in ProxyProtocol."""

    def test_process_buffer_connect_message(self):
        """Test processing MSG_CONNECT from buffer."""
        protocol = ProxyProtocol()
        mock_streaming_protocol = MagicMock()
        protocol._protocol = mock_streaming_protocol

        # Create MSG_CONNECT message
        host = b"example.com"
        port = 443
        payload = bytes([len(host)]) + host + struct.pack(">H", port)
        header = struct.pack(">BHI", MSG_CONNECT, 1, len(payload))

        # Add to buffer
        protocol._buffer = header + payload

        # Process should create task for handling
        with patch('asyncio.create_task') as mock_create_task:
            protocol._process_buffer()
            mock_create_task.assert_called_once()

    def test_process_buffer_incomplete_header(self):
        """Test processing with incomplete header."""
        protocol = ProxyProtocol()

        # Only 6 bytes (need 7 for header)
        protocol._buffer = b"123456"

        protocol._process_buffer()

        # Buffer should remain unchanged
        assert protocol._buffer == b"123456"

    def test_process_buffer_incomplete_payload(self):
        """Test processing with incomplete payload."""
        protocol = ProxyProtocol()

        # Header says 10 bytes payload, but only 5 present
        header = struct.pack(">BHI", MSG_DATA, 1, 10)
        protocol._buffer = header + b"12345"

        protocol._process_buffer()

        # Buffer should remain unchanged
        assert protocol._buffer == header + b"12345"

    @pytest.mark.asyncio
    async def test_process_buffer_multiple_messages(self):
        """Test processing multiple messages in buffer."""
        protocol = ProxyProtocol()
        mock_writer = MagicMock()
        mock_writer.write = Mock()
        mock_writer.drain = AsyncMock()
        protocol._channels[1] = {"writer": mock_writer}

        # Create two MSG_DATA messages
        data1 = b"hello"
        data2 = b"world"
        msg1 = struct.pack(">BHI", MSG_DATA, 1, len(data1)) + data1
        msg2 = struct.pack(">BHI", MSG_DATA, 1, len(data2)) + data2

        protocol._buffer = msg1 + msg2
        protocol._process_buffer()

        # Wait for drain tasks
        await asyncio.sleep(0.01)

        # Both messages should be processed
        assert len(mock_writer.write.call_args_list) == 2
        assert protocol._buffer == b""

    @pytest.mark.asyncio
    async def test_forward_from_target(self):
        """Test forwarding data from target to wormhole."""
        protocol = ProxyProtocol()
        mock_streaming_protocol = MagicMock()
        protocol._protocol = mock_streaming_protocol

        # Create mock reader
        mock_reader = AsyncMock()
        mock_reader.read = AsyncMock(side_effect=[
            b"chunk1",
            b"chunk2",
            b"",  # EOF
        ])

        mock_writer = MagicMock()
        protocol._channels[1] = {"writer": mock_writer}

        await protocol._forward_from_target(1, mock_reader)

        # Verify data was sent
        send_calls = mock_streaming_protocol.send.call_args_list

        # Should have 2 data messages and 1 close message
        assert len(send_calls) == 3

        # Verify MSG_CLOSE was sent
        last_msg = send_calls[-1][0][0]
        msg_type, _, _ = struct.unpack(">BHI", last_msg[:7])
        assert msg_type == MSG_CLOSE

    @pytest.mark.asyncio
    async def test_connect_timeout(self):
        """Test connect request timeout."""
        protocol = ProxyProtocol()
        mock_streaming_protocol = MagicMock()
        protocol._protocol = mock_streaming_protocol

        # Don't respond to the connect request
        result = await protocol.connect("example.com", 443)

        # Should return None on timeout
        assert result is None
        assert 2 not in protocol._channels  # Channel should be cleaned up
