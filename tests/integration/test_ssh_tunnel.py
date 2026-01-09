"""Integration tests for SSH tunnel module."""

import asyncio
from unittest.mock import MagicMock, AsyncMock
import pytest


class TestWormholeTunnel:
    """Tests for WormholeTunnel class."""

    def test_init(self):
        """Test tunnel initialization."""
        from wh.ssh.tunnel import WormholeTunnel

        manager = MagicMock()
        tunnel = WormholeTunnel(manager)

        assert tunnel._manager is manager

    @pytest.mark.asyncio
    async def test_create_connection_not_dilated(self):
        """Test create_connection fails if not dilated."""
        from wh.ssh.tunnel import WormholeTunnel

        manager = MagicMock()
        manager.is_dilated = False

        tunnel = WormholeTunnel(manager)

        with pytest.raises(RuntimeError, match="must be dilated"):
            await tunnel.create_connection(lambda: MagicMock(), "host", 22)


class TestBridgeProtocol:
    """Tests for _BridgeProtocol class."""

    def test_init(self):
        """Test bridge protocol initialization."""
        from wh.ssh.tunnel import _BridgeProtocol

        target = MagicMock()
        bridge = _BridgeProtocol(target)

        assert bridge._target is target
        assert bridge._transport is None

    def test_connection_made(self):
        """Test connection_made forwards to target."""
        from wh.ssh.tunnel import _BridgeProtocol

        target = MagicMock()
        bridge = _BridgeProtocol(target)
        transport = MagicMock()

        bridge.connection_made(transport)

        assert bridge._transport is transport
        target.connection_made.assert_called_once_with(transport)

    def test_data_received(self):
        """Test data_received forwards to target."""
        from wh.ssh.tunnel import _BridgeProtocol

        target = MagicMock()
        bridge = _BridgeProtocol(target)

        bridge.data_received(b"test data")

        target.data_received.assert_called_once_with(b"test data")

    def test_eof_received_with_method(self):
        """Test eof_received with target having method."""
        from wh.ssh.tunnel import _BridgeProtocol

        target = MagicMock()
        target.eof_received.return_value = True
        bridge = _BridgeProtocol(target)

        result = bridge.eof_received()

        assert result is True
        target.eof_received.assert_called_once()

    def test_eof_received_without_method(self):
        """Test eof_received without target method."""
        from wh.ssh.tunnel import _BridgeProtocol

        target = MagicMock(spec=[])  # No eof_received method
        bridge = _BridgeProtocol(target)

        result = bridge.eof_received()

        assert result is False

    def test_connection_lost(self):
        """Test connection_lost forwards to target."""
        from wh.ssh.tunnel import _BridgeProtocol

        target = MagicMock()
        bridge = _BridgeProtocol(target)
        exc = Exception("test error")

        bridge.connection_lost(exc)

        target.connection_lost.assert_called_once_with(exc)

    def test_connection_lost_none(self):
        """Test connection_lost with None exception."""
        from wh.ssh.tunnel import _BridgeProtocol

        target = MagicMock()
        bridge = _BridgeProtocol(target)

        bridge.connection_lost(None)

        target.connection_lost.assert_called_once_with(None)
