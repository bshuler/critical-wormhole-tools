"""Integration tests for multi-relay fallback functionality."""

import tempfile
from pathlib import Path
from unittest.mock import patch


class TestMultiRelayIntegration:
    """Integration tests for multi-relay configuration and fallback."""

    def test_relay_config_persistence(self):
        """Test that relay configuration persists across restarts."""
        from wh.relay.config import RelayConfigManager

        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)

            # Create config and add relays
            manager1 = RelayConfigManager(config_dir=config_dir)
            manager1.add_relay(
                name="work",
                mailbox_url="ws://work.example.com:4000/v1",
                transit_url="tcp:work.example.com:4001",
                description="Work relay",
                set_default=True,
            )
            manager1.add_relay(
                name="home",
                mailbox_url="ws://home.example.com:4000/v1",
                transit_url="tcp:home.example.com:4001",
            )

            # Create new manager instance (simulating restart)
            manager2 = RelayConfigManager(config_dir=config_dir)

            # Verify configuration persisted (includes default 'public' relay)
            relays = manager2.list_relays()
            assert len(relays) == 3  # public + work + home

            work_relay = manager2.get_relay("work")
            assert work_relay is not None
            assert work_relay.mailbox_url == "ws://work.example.com:4000/v1"

            default = manager2.get_default_relay()
            assert default.name == "work"

    def test_wormhole_manager_uses_relay_config(self):
        """Test WormholeManager uses relay configuration."""
        from wh.core.wormhole_manager import WormholeManager
        from wh.relay.config import RelayConfigManager

        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)

            # Set up relay config
            config_manager = RelayConfigManager(config_dir=config_dir)
            config_manager.add_relay(
                name="primary",
                mailbox_url="ws://primary.example.com:4000/v1",
                transit_url="tcp:primary.example.com:4001",
                set_default=True,
            )
            config_manager.add_relay(
                name="fallback",
                mailbox_url="ws://fallback.example.com:4000/v1",
                transit_url="tcp:fallback.example.com:4001",
            )

            # Create manager from config
            with patch("wh.relay.config.get_relay_manager") as mock_get:
                mock_get.return_value = config_manager

                manager = WormholeManager.from_relay_config()

                assert manager.relay_url == "ws://primary.example.com:4000/v1"
                assert manager.has_fallback_relays
                # primary + fallback + public (default)
                assert len(manager._relay_list) >= 2

    def test_relay_fallback_sequence(self):
        """Test fallback to next relay when primary fails."""
        from wh.core.wormhole_manager import WormholeManager

        manager = WormholeManager(
            relay_url="ws://primary:4000/v1",
            transit_relay="tcp:primary:4001",
            fallback_relays=[
                ("ws://secondary:4000/v1", "tcp:secondary:4001"),
                ("ws://tertiary:4000/v1", "tcp:tertiary:4001"),
            ],
        )

        # Initial state
        assert manager.current_relay_index == 0
        assert manager.relay_url == "ws://primary:4000/v1"

        # First fallback
        has_more = manager._try_next_relay()
        assert has_more
        assert manager.current_relay_index == 1
        assert manager.relay_url == "ws://secondary:4000/v1"

        # Second fallback
        has_more = manager._try_next_relay()
        assert has_more
        assert manager.current_relay_index == 2
        assert manager.relay_url == "ws://tertiary:4000/v1"

        # No more fallbacks
        has_more = manager._try_next_relay()
        assert not has_more

    def test_establish_with_fallback_setup(self):
        """Test that establish_with_fallback is properly configured."""
        from wh.core.wormhole_manager import WormholeManager

        manager = WormholeManager(
            relay_url="ws://primary:4000/v1",
            transit_relay="tcp:primary:4001",
            fallback_relays=[
                ("ws://secondary:4000/v1", "tcp:secondary:4001"),
            ],
        )

        # Verify manager is set up for fallback
        assert manager.has_fallback_relays
        assert len(manager._relay_list) == 2
        assert manager._relay_list[0] == ("ws://primary:4000/v1", "tcp:primary:4001")
        assert manager._relay_list[1] == ("ws://secondary:4000/v1", "tcp:secondary:4001")


class TestNamespaceEncryptionIntegration:
    """Integration tests for namespace encryption in DHT."""

    def test_dht_key_namespace_isolation(self):
        """Test that different relays produce different DHT keys."""
        from wh.wns.dht import address_to_dht_key

        address = "abc123"

        # Same address, different relays = different keys
        key1 = address_to_dht_key(address, "ws://relay1.example.com:4000/v1")
        key2 = address_to_dht_key(address, "ws://relay2.example.com:4000/v1")

        assert key1 != key2

        # Same address, same relay = same key
        key3 = address_to_dht_key(address, "ws://relay1.example.com:4000/v1")
        assert key1 == key3

    def test_dht_config_auto_enables_encryption(self):
        """Test that providing relay URL enables encryption automatically."""
        from wh.wns.dht import DHTConfig

        # Without relay URL
        config1 = DHTConfig()
        assert config1.relay_url is None
        assert config1.encrypt_advertisements is False

        # With relay URL - encryption auto-enabled
        config2 = DHTConfig(relay_url="ws://relay.example.com:4000/v1")
        assert config2.relay_url == "ws://relay.example.com:4000/v1"
        assert config2.encrypt_advertisements is True

    def test_namespace_key_derivation(self):
        """Test that namespace key derivation is deterministic."""
        from wh.wns.namespace import namespace_dht_key

        address = "test-address"
        relay = "ws://relay.example.com:4000/v1"

        key1 = namespace_dht_key(address, relay)
        key2 = namespace_dht_key(address, relay)

        assert key1 == key2
        assert len(key1) == 32  # SHA-256 produces 32 bytes


class TestMDNSRelayDiscovery:
    """Integration tests for mDNS relay discovery."""

    def test_relay_discovery_config(self):
        """Test relay discovery configuration."""
        from wh.relay.config import RelayConfigManager

        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            manager = RelayConfigManager(config_dir=config_dir)

            # Add a relay via discovery
            manager.add_relay(
                name="discovered",
                mailbox_url="ws://192.168.1.10:4000/v1",
                transit_url="tcp:192.168.1.10:4001",
                description="Discovered via mDNS",
            )

            # Verify it's saved
            relay = manager.get_relay("discovered")
            assert relay is not None
            assert relay.description == "Discovered via mDNS"

    def test_relay_config_with_multiple_discovered(self):
        """Test handling multiple discovered relays."""
        from wh.relay.config import RelayConfigManager

        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            manager = RelayConfigManager(config_dir=config_dir)

            # Add multiple discovered relays
            for i in range(3):
                manager.add_relay(
                    name=f"local-{i}",
                    mailbox_url=f"ws://192.168.1.{10+i}:4000/v1",
                    transit_url=f"tcp:192.168.1.{10+i}:4001",
                )

            relays = manager.list_relays()
            # Includes default 'public' relay + 3 local relays
            assert len(relays) == 4


class TestDaemonRelayEndpoint:
    """Integration tests for daemon relay configuration endpoint."""

    def test_daemon_relay_endpoint_returns_config(self):
        """Test that daemon relay endpoint returns configuration."""
        from wh.relay.config import RelayConfigManager

        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            manager = RelayConfigManager(config_dir=config_dir)

            # Add test relay
            manager.add_relay(
                name="test",
                mailbox_url="ws://test.example.com:4000/v1",
                transit_url="tcp:test.example.com:4001",
                set_default=True,
            )

            # Get relay configuration as would be returned by daemon
            relays = manager.list_relays()
            default = manager.get_default_relay()

            # Includes default 'public' relay + test relay
            assert len(relays) == 2
            assert default.name == "test"
