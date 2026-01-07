"""Unit tests for protocol module."""

import pytest
from unittest.mock import Mock, MagicMock
from io import BytesIO


class TestStreamingProtocol:
    """Tests for StreamingProtocol class."""

    def test_init(self):
        """Test protocol initialization."""
        from wh.core.protocol import StreamingProtocol

        protocol = StreamingProtocol()

        assert protocol.transport is None
        assert not protocol.is_connected

    def test_init_with_callbacks(self):
        """Test protocol initialization with callbacks."""
        from wh.core.protocol import StreamingProtocol

        on_data = Mock()
        on_made = Mock()
        on_lost = Mock()

        protocol = StreamingProtocol(
            on_data=on_data,
            on_connection_made=on_made,
            on_connection_lost=on_lost,
        )

        assert protocol.on_data_callback is on_data
        assert protocol.on_connection_made_callback is on_made
        assert protocol.on_connection_lost_callback is on_lost

    def test_connection_made(self):
        """Test connectionMade callback."""
        from wh.core.protocol import StreamingProtocol

        on_made = Mock()
        protocol = StreamingProtocol(on_connection_made=on_made)

        protocol.connectionMade()

        assert protocol.is_connected
        on_made.assert_called_once()

    def test_data_received(self):
        """Test dataReceived callback."""
        from wh.core.protocol import StreamingProtocol

        on_data = Mock()
        protocol = StreamingProtocol(on_data=on_data)

        protocol.dataReceived(b"test data")

        on_data.assert_called_once_with(b"test data")

    def test_connection_lost(self):
        """Test connectionLost callback."""
        from wh.core.protocol import StreamingProtocol

        on_lost = Mock()
        protocol = StreamingProtocol(on_connection_lost=on_lost)
        protocol._connected = True

        reason = MagicMock()
        reason.value = ValueError("connection lost")
        protocol.connectionLost(reason)

        assert not protocol.is_connected
        on_lost.assert_called_once()

    def test_send(self, mock_transport):
        """Test send method."""
        from wh.core.protocol import StreamingProtocol

        protocol = StreamingProtocol()
        protocol.transport = mock_transport
        protocol._connected = True

        protocol.send(b"test data")

        mock_transport.write.assert_called_once_with(b"test data")

    def test_send_not_connected(self, mock_transport):
        """Test send when not connected does nothing."""
        from wh.core.protocol import StreamingProtocol

        protocol = StreamingProtocol()
        protocol.transport = mock_transport
        protocol._connected = False

        protocol.send(b"test data")

        mock_transport.write.assert_not_called()

    def test_close(self, mock_transport):
        """Test close method."""
        from wh.core.protocol import StreamingProtocol

        protocol = StreamingProtocol()
        protocol.transport = mock_transport

        protocol.close()

        mock_transport.loseConnection.assert_called_once()


class TestStreamingProtocolFactory:
    """Tests for StreamingProtocolFactory class."""

    def test_build_protocol(self):
        """Test factory builds protocol with callbacks."""
        from wh.core.protocol import StreamingProtocolFactory

        on_data = Mock()
        on_made = Mock()
        on_lost = Mock()

        factory = StreamingProtocolFactory(
            on_data=on_data,
            on_connection_made=on_made,
            on_connection_lost=on_lost,
        )

        protocol = factory.buildProtocol(None)

        assert protocol.on_data_callback is on_data
        assert protocol.on_connection_made_callback is on_made
        assert protocol.on_connection_lost_callback is on_lost
        assert protocol.factory is factory


class TestBidirectionalPipe:
    """Tests for BidirectionalPipe class."""

    def test_init(self):
        """Test pipe initialization."""
        from wh.core.protocol import BidirectionalPipe

        stdin = BytesIO()
        stdout = BytesIO()

        pipe = BidirectionalPipe(stdin=stdin, stdout=stdout)

        assert pipe.stdin is stdin
        assert pipe.stdout is stdout

    def test_on_data_writes_to_stdout(self):
        """Test received data is written to stdout."""
        from wh.core.protocol import BidirectionalPipe

        stdout = BytesIO()
        pipe = BidirectionalPipe(stdout=stdout)

        pipe._on_data(b"hello world")

        stdout.seek(0)
        assert stdout.read() == b"hello world"

    def test_status_callback(self):
        """Test status callback is called."""
        from wh.core.protocol import BidirectionalPipe

        statuses = []
        pipe = BidirectionalPipe(on_status=lambda m: statuses.append(m))

        pipe._status("test message")

        assert "test message" in statuses

    def test_on_connection_lost_sets_done(self):
        """Test connection lost sets done event."""
        from wh.core.protocol import BidirectionalPipe

        pipe = BidirectionalPipe()

        assert not pipe._done.is_set()
        pipe._on_connection_lost(None)
        assert pipe._done.is_set()
