"""Unit tests for transport module."""

from unittest.mock import MagicMock


class TestAsyncioTransportAdapter:
    """Tests for AsyncioTransportAdapter class."""

    def test_init(self):
        """Test adapter initialization."""
        from wh.core.transport import AsyncioTransportAdapter

        twisted_transport = MagicMock()
        adapter = AsyncioTransportAdapter(twisted_transport)

        assert adapter._transport is twisted_transport
        assert not adapter._closing

    def test_get_extra_info_peername(self):
        """Test get_extra_info returns peername."""
        from wh.core.transport import AsyncioTransportAdapter

        adapter = AsyncioTransportAdapter(MagicMock())

        assert adapter.get_extra_info('peername') == ('wormhole', 0)

    def test_get_extra_info_sockname(self):
        """Test get_extra_info returns sockname."""
        from wh.core.transport import AsyncioTransportAdapter

        adapter = AsyncioTransportAdapter(MagicMock())

        assert adapter.get_extra_info('sockname') == ('wormhole', 0)

    def test_get_extra_info_unknown(self):
        """Test get_extra_info returns default for unknown keys."""
        from wh.core.transport import AsyncioTransportAdapter

        adapter = AsyncioTransportAdapter(MagicMock())

        assert adapter.get_extra_info('unknown') is None
        assert adapter.get_extra_info('unknown', 'default') == 'default'

    def test_write(self):
        """Test write passes through to twisted transport."""
        from wh.core.transport import AsyncioTransportAdapter

        twisted_transport = MagicMock()
        adapter = AsyncioTransportAdapter(twisted_transport)

        adapter.write(b"test data")

        twisted_transport.write.assert_called_once_with(b"test data")

    def test_write_when_closing(self):
        """Test write does nothing when closing."""
        from wh.core.transport import AsyncioTransportAdapter

        twisted_transport = MagicMock()
        adapter = AsyncioTransportAdapter(twisted_transport)
        adapter._closing = True

        adapter.write(b"test data")

        twisted_transport.write.assert_not_called()

    def test_writelines(self):
        """Test writelines writes multiple chunks."""
        from wh.core.transport import AsyncioTransportAdapter

        twisted_transport = MagicMock()
        adapter = AsyncioTransportAdapter(twisted_transport)

        adapter.writelines([b"chunk1", b"chunk2"])

        assert twisted_transport.write.call_count == 2

    def test_close(self):
        """Test close sets flag and loses connection."""
        from wh.core.transport import AsyncioTransportAdapter

        twisted_transport = MagicMock()
        adapter = AsyncioTransportAdapter(twisted_transport)

        adapter.close()

        assert adapter._closing
        twisted_transport.loseConnection.assert_called_once()

    def test_close_idempotent(self):
        """Test close is idempotent."""
        from wh.core.transport import AsyncioTransportAdapter

        twisted_transport = MagicMock()
        adapter = AsyncioTransportAdapter(twisted_transport)

        adapter.close()
        adapter.close()

        # Should only lose connection once
        twisted_transport.loseConnection.assert_called_once()

    def test_is_closing(self):
        """Test is_closing returns correct state."""
        from wh.core.transport import AsyncioTransportAdapter

        adapter = AsyncioTransportAdapter(MagicMock())

        assert not adapter.is_closing()
        adapter.close()
        assert adapter.is_closing()

    def test_abort(self):
        """Test abort calls abortConnection."""
        from wh.core.transport import AsyncioTransportAdapter

        twisted_transport = MagicMock()
        adapter = AsyncioTransportAdapter(twisted_transport)

        adapter.abort()

        assert adapter._closing
        twisted_transport.abortConnection.assert_called_once()

    def test_can_write_eof(self):
        """Test can_write_eof returns True."""
        from wh.core.transport import AsyncioTransportAdapter

        adapter = AsyncioTransportAdapter(MagicMock())

        assert adapter.can_write_eof()

    def test_get_write_buffer_size(self):
        """Test get_write_buffer_size returns 0."""
        from wh.core.transport import AsyncioTransportAdapter

        adapter = AsyncioTransportAdapter(MagicMock())

        assert adapter.get_write_buffer_size() == 0

    def test_get_write_buffer_limits(self):
        """Test get_write_buffer_limits returns (0, 0)."""
        from wh.core.transport import AsyncioTransportAdapter

        adapter = AsyncioTransportAdapter(MagicMock())

        assert adapter.get_write_buffer_limits() == (0, 0)

    def test_protocol_accessors(self):
        """Test protocol get/set."""
        from wh.core.transport import AsyncioTransportAdapter

        adapter = AsyncioTransportAdapter(MagicMock())
        protocol = MagicMock()

        assert adapter.get_protocol() is None
        adapter.set_protocol(protocol)
        assert adapter.get_protocol() is protocol


class TestDuplexPipe:
    """Tests for DuplexPipe class."""

    def test_get_endpoints(self):
        """Test get_endpoints returns two connected endpoints."""
        from wh.core.transport import DuplexPipe

        pipe = DuplexPipe()
        a, b = pipe.get_endpoints()

        assert a is not b
        assert a._read_queue is b._write_queue
        assert b._read_queue is a._write_queue


class TestPipeEndpoint:
    """Tests for PipeEndpoint class."""

    def test_write_and_read(self):
        """Test data written to one endpoint can be read from other."""
        from wh.core.transport import DuplexPipe
        import asyncio

        async def test():
            pipe = DuplexPipe()
            a, b = pipe.get_endpoints()

            a.write(b"hello")
            data = await asyncio.wait_for(b.read(), timeout=1.0)
            assert data == b"hello"

        asyncio.get_event_loop().run_until_complete(test())

    def test_close(self):
        """Test close marks endpoint as closing."""
        from wh.core.transport import DuplexPipe

        pipe = DuplexPipe()
        a, _ = pipe.get_endpoints()

        assert not a.is_closing()
        a.close()
        assert a.is_closing()

    def test_get_extra_info(self):
        """Test get_extra_info returns pipe info."""
        from wh.core.transport import DuplexPipe

        pipe = DuplexPipe()
        a, _ = pipe.get_endpoints()

        assert a.get_extra_info('peername') == ('pipe', 0)
        assert a.get_extra_info('sockname') == ('pipe', 0)
        assert a.get_extra_info('unknown') is None
