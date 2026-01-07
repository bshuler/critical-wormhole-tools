"""Unit tests for WormholeManager."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio


class TestWormholeManager:
    """Tests for WormholeManager class."""

    def test_init_defaults(self):
        """Test default initialization values."""
        from wh.core.wormhole_manager import WormholeManager

        manager = WormholeManager()

        assert manager.appid == "wh.tools/v1"
        assert manager.relay_url == "ws://relay.magic-wormhole.io:4000/v1"
        assert manager.code_length == 2
        assert manager.code is None
        assert not manager.is_dilated

    def test_init_custom_values(self):
        """Test initialization with custom values."""
        from wh.core.wormhole_manager import WormholeManager

        manager = WormholeManager(
            appid="custom.app",
            relay_url="ws://custom.relay:4000",
            transit_relay="tcp:custom.transit:4001",
            code_length=3,
        )

        assert manager.appid == "custom.app"
        assert manager.relay_url == "ws://custom.relay:4000"
        assert manager.transit_relay == "tcp:custom.transit:4001"
        assert manager.code_length == 3

    def test_status_callback(self):
        """Test status callback is called."""
        from wh.core.wormhole_manager import WormholeManager

        statuses = []
        manager = WormholeManager(on_status=lambda m: statuses.append(m))

        manager._status("test message")

        assert "test message" in statuses

    def test_properties_before_creation(self):
        """Test properties raise errors before wormhole is created."""
        from wh.core.wormhole_manager import WormholeManager

        manager = WormholeManager()

        assert manager.code is None
        assert not manager.is_dilated
        assert manager.dilated_wormhole is None

    def test_properties_raise_when_not_dilated(self):
        """Test connector_for/listener_for raise when not dilated."""
        from wh.core.wormhole_manager import WormholeManager

        manager = WormholeManager()

        with pytest.raises(RuntimeError, match="not dilated"):
            _ = manager.connector_for("test")

        with pytest.raises(RuntimeError, match="not dilated"):
            _ = manager.listener_for("test")


class TestWormholeManagerAsync:
    """Async tests for WormholeManager."""

    @pytest.mark.asyncio
    async def test_deferred_to_future_success(self):
        """Test Deferred to Future conversion on success."""
        from wh.core.wormhole_manager import WormholeManager
        from twisted.internet import defer

        manager = WormholeManager()

        # Create a deferred that succeeds
        d = defer.Deferred()

        async def run():
            # Schedule callback
            asyncio.get_event_loop().call_soon(
                lambda: d.callback("success")
            )
            return await manager._deferred_to_future(d)

        result = await run()
        assert result == "success"

    @pytest.mark.asyncio
    async def test_deferred_to_future_failure(self):
        """Test Deferred to Future conversion on failure."""
        from wh.core.wormhole_manager import WormholeManager
        from twisted.internet import defer

        manager = WormholeManager()

        # Create a deferred that fails
        d = defer.Deferred()

        async def run():
            asyncio.get_event_loop().call_soon(
                lambda: d.errback(ValueError("test error"))
            )
            return await manager._deferred_to_future(d)

        with pytest.raises(ValueError, match="test error"):
            await run()

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager."""
        from wh.core.wormhole_manager import WormholeManager

        manager = WormholeManager()
        manager.close = AsyncMock()

        async with manager as m:
            assert m is manager

        manager.close.assert_called_once()
