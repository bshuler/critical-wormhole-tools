"""Unit tests for wormhole daemon."""

import pytest
from unittest.mock import patch, MagicMock
import tempfile
from pathlib import Path


class TestWormholeDaemon:
    """Tests for WormholeDaemon class."""

    def test_init_defaults(self):
        """Test default initialization values."""
        from wh.cli.daemon import WormholeDaemon

        daemon = WormholeDaemon()
        assert daemon.port == 9475
        assert daemon.verbose is False
        assert daemon.connections == {}

    def test_init_custom_values(self):
        """Test initialization with custom values."""
        from wh.cli.daemon import WormholeDaemon

        daemon = WormholeDaemon(port=8080, verbose=True)
        assert daemon.port == 8080
        assert daemon.verbose is True


class TestDaemonRelayEndpoint:
    """Tests for the daemon relay config endpoint."""

    @pytest.mark.asyncio
    async def test_handle_get_relays(self):
        """Test that handle_get_relays returns relay config."""
        from wh.cli.daemon import WormholeDaemon
        from wh.relay.config import RelayConfigManager

        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)

            # Set up test config
            config_manager = RelayConfigManager(config_dir=config_dir)
            config_manager.add_relay(
                name="test_relay",
                mailbox_url="ws://test:4000/v1",
                transit_url="tcp:test:4001",
                description="Test relay",
                set_default=True,
            )

            daemon = WormholeDaemon()

            # Mock request object
            request = MagicMock()

            # Mock get_relay_manager to return our test manager
            with patch("wh.relay.config.get_relay_manager") as mock_get:
                mock_get.return_value = config_manager

                response = await daemon.handle_get_relays(request)

                # Response should be a web.json_response
                assert response.status == 200

    @pytest.mark.asyncio
    async def test_handle_get_relays_format(self):
        """Test the format of relay config response."""
        from wh.cli.daemon import WormholeDaemon
        from wh.relay.config import RelayConfigManager
        import json

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

            daemon = WormholeDaemon()
            request = MagicMock()

            with patch("wh.relay.config.get_relay_manager") as mock_get:
                mock_get.return_value = config_manager

                response = await daemon.handle_get_relays(request)

                # Parse response body
                body = json.loads(response.body.decode("utf-8"))

                assert "relays" in body
                assert "default" in body
                assert len(body["relays"]) >= 2  # At least our 2 relays

                # Check relay format
                relay_names = [r["name"] for r in body["relays"]]
                assert "relay1" in relay_names
                assert "relay2" in relay_names

                # Find relay1 and check fields
                relay1 = next(r for r in body["relays"] if r["name"] == "relay1")
                assert relay1["mailboxUrl"] == "ws://relay1:4000/v1"
                assert relay1["transitUrl"] == "tcp:relay1:4001"
                assert relay1["isDefault"] is True

    @pytest.mark.asyncio
    async def test_handle_get_relays_error(self):
        """Test error handling in relay config endpoint."""
        from wh.cli.daemon import WormholeDaemon

        daemon = WormholeDaemon()
        request = MagicMock()

        with patch("wh.relay.config.get_relay_manager") as mock_get:
            mock_get.side_effect = Exception("Config error")

            response = await daemon.handle_get_relays(request)

            assert response.status == 500
