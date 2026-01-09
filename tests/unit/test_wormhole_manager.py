"""Unit tests for WormholeManager."""

import pytest
from unittest.mock import patch, AsyncMock
import asyncio
import tempfile
from pathlib import Path


class TestWormholeManager:
    """Tests for WormholeManager class."""

    def test_init_defaults(self):
        """Test default initialization values."""
        from wh.core.wormhole_manager import WormholeManager

        manager = WormholeManager()

        assert manager.appid == "wh.tools/v1"
        assert manager.relay_url == "wss://relay.magic-wormhole.io/v1"
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


class TestMultiRelayFallback:
    """Tests for multi-relay fallback functionality."""

    def test_init_with_fallback_relays(self):
        """Test initialization with fallback relays."""
        from wh.core.wormhole_manager import WormholeManager

        fallbacks = [
            ("ws://fallback1:4000/v1", "tcp:fallback1:4001"),
            ("ws://fallback2:4000/v1", "tcp:fallback2:4001"),
        ]

        manager = WormholeManager(
            relay_url="ws://primary:4000/v1",
            transit_relay="tcp:primary:4001",
            fallback_relays=fallbacks,
        )

        assert len(manager._relay_list) == 3
        assert manager._relay_list[0] == ("ws://primary:4000/v1", "tcp:primary:4001")
        assert manager._relay_list[1] == ("ws://fallback1:4000/v1", "tcp:fallback1:4001")
        assert manager._relay_list[2] == ("ws://fallback2:4000/v1", "tcp:fallback2:4001")

    def test_has_fallback_relays(self):
        """Test has_fallback_relays property."""
        from wh.core.wormhole_manager import WormholeManager

        # Without fallbacks
        manager1 = WormholeManager()
        assert not manager1.has_fallback_relays

        # With fallbacks
        manager2 = WormholeManager(
            fallback_relays=[("ws://fallback:4000/v1", "tcp:fallback:4001")]
        )
        assert manager2.has_fallback_relays

    def test_get_current_relay(self):
        """Test getting current relay configuration."""
        from wh.core.wormhole_manager import WormholeManager

        manager = WormholeManager(
            relay_url="ws://primary:4000/v1",
            transit_relay="tcp:primary:4001",
        )

        mailbox, transit = manager._get_current_relay()
        assert mailbox == "ws://primary:4000/v1"
        assert transit == "tcp:primary:4001"

    def test_try_next_relay(self):
        """Test switching to next relay."""
        from wh.core.wormhole_manager import WormholeManager

        manager = WormholeManager(
            relay_url="ws://primary:4000/v1",
            transit_relay="tcp:primary:4001",
            fallback_relays=[
                ("ws://fallback1:4000/v1", "tcp:fallback1:4001"),
            ],
        )

        assert manager._current_relay_index == 0

        # Try next relay
        has_more = manager._try_next_relay()
        assert has_more
        assert manager._current_relay_index == 1
        assert manager.relay_url == "ws://fallback1:4000/v1"

        # No more relays
        has_more = manager._try_next_relay()
        assert not has_more

    def test_from_relay_config(self):
        """Test creating manager from relay config file."""
        from wh.core.wormhole_manager import WormholeManager
        from wh.relay.config import RelayConfigManager

        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)

            # Set up test config
            config_manager = RelayConfigManager(config_dir=config_dir)
            config_manager.add_relay(
                name="relay1",
                mailbox_url="ws://relay1:4000/v1",
                transit_url="tcp:relay1:4001",
                set_default=True,
            )
            config_manager.add_relay(
                name="relay2",
                mailbox_url="ws://relay2:4000/v1",
                transit_url="tcp:relay2:4001",
            )

            # Mock get_relay_manager to use our temp config
            with patch("wh.relay.config.get_relay_manager") as mock_get:
                mock_get.return_value = config_manager

                manager = WormholeManager.from_relay_config()

                assert manager.relay_url == "ws://relay1:4000/v1"
                assert len(manager._relay_list) >= 2

    def test_current_relay_index_property(self):
        """Test current_relay_index property."""
        from wh.core.wormhole_manager import WormholeManager

        manager = WormholeManager(
            fallback_relays=[("ws://fallback:4000/v1", "tcp:fallback:4001")]
        )

        assert manager.current_relay_index == 0
        manager._try_next_relay()
        assert manager.current_relay_index == 1


class TestMessageMethods:
    """Tests for send_json and receive_json methods."""

    @pytest.mark.asyncio
    async def test_send_json_not_created(self):
        """Test send_json raises when wormhole not created."""
        from wh.core.wormhole_manager import WormholeManager

        manager = WormholeManager()

        with pytest.raises(RuntimeError, match="not created"):
            await manager.send_json({"test": "data"})

    @pytest.mark.asyncio
    async def test_receive_json_not_created(self):
        """Test receive_json raises when wormhole not created."""
        from wh.core.wormhole_manager import WormholeManager

        manager = WormholeManager()

        with pytest.raises(RuntimeError, match="not created"):
            await manager.receive_json()

    @pytest.mark.asyncio
    async def test_establish_with_timeout(self):
        """Test establish method with timeout parameter."""
        from wh.core.wormhole_manager import WormholeManager

        manager = WormholeManager()
        manager.verify_connection = AsyncMock(return_value={"test": "versions"})

        result = await manager.establish(timeout=5.0)
        assert result == {"test": "versions"}
