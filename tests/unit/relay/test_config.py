"""Unit tests for relay configuration management."""

import pytest
import tempfile
from pathlib import Path

from wh.relay.config import (
    RelayConfig,
    RelayConfigFile,
    RelayConfigManager,
    get_relay_manager,
    DEFAULT_MAILBOX_URL,
    DEFAULT_TRANSIT_URL,
)


class TestRelayConfig:
    """Tests for RelayConfig dataclass."""

    def test_basic_creation(self):
        """Test creating a basic relay config."""
        config = RelayConfig(
            name="test",
            mailbox_url="ws://example.com:4000/v1",
            transit_url="tcp:example.com:4001",
        )
        assert config.name == "test"
        assert config.mailbox_url == "ws://example.com:4000/v1"
        assert config.transit_url == "tcp:example.com:4001"
        assert config.namespace_key is None
        assert config.description is None

    def test_with_all_fields(self):
        """Test creating a relay config with all fields."""
        config = RelayConfig(
            name="full",
            mailbox_url="ws://server:5000/v1",
            transit_url="tcp:server:5001",
            namespace_key="base64key==",
            description="Full test relay",
        )
        assert config.namespace_key == "base64key=="
        assert config.description == "Full test relay"

    def test_to_dict_basic(self):
        """Test conversion to dict with basic fields."""
        config = RelayConfig(
            name="test",
            mailbox_url="ws://server:4000/v1",
            transit_url="tcp:server:4001",
        )
        d = config.to_dict()
        assert d["name"] == "test"
        assert d["mailbox_url"] == "ws://server:4000/v1"
        assert d["transit_url"] == "tcp:server:4001"
        assert "namespace_key" not in d  # None values omitted
        assert "description" not in d

    def test_to_dict_full(self):
        """Test conversion to dict with all fields."""
        config = RelayConfig(
            name="full",
            mailbox_url="ws://server:4000/v1",
            transit_url="tcp:server:4001",
            namespace_key="key123",
            description="Test",
        )
        d = config.to_dict()
        assert d["namespace_key"] == "key123"
        assert d["description"] == "Test"

    def test_from_dict(self):
        """Test creation from dict."""
        data = {
            "name": "fromdict",
            "mailbox_url": "ws://localhost:4000/v1",
            "transit_url": "tcp:localhost:4001",
            "description": "From dict",
        }
        config = RelayConfig.from_dict(data)
        assert config.name == "fromdict"
        assert config.description == "From dict"


class TestRelayConfigFile:
    """Tests for RelayConfigFile dataclass."""

    def test_default_public_relay(self):
        """Test that default config includes public relay."""
        config = RelayConfigFile()
        assert "public" in config.relays
        assert config.default == "public"

        public = config.relays["public"]
        assert public.mailbox_url == DEFAULT_MAILBOX_URL
        assert public.transit_url == DEFAULT_TRANSIT_URL

    def test_to_dict(self):
        """Test conversion to dict."""
        config = RelayConfigFile()
        d = config.to_dict()
        assert d["default"] == "public"
        assert "relays" in d
        assert "public" in d["relays"]

    def test_from_dict(self):
        """Test creation from dict."""
        data = {
            "default": "custom",
            "relays": {
                "custom": {
                    "mailbox_url": "ws://custom:4000/v1",
                    "transit_url": "tcp:custom:4001",
                }
            }
        }
        config = RelayConfigFile.from_dict(data)
        assert config.default == "custom"
        assert "custom" in config.relays
        assert config.relays["custom"].mailbox_url == "ws://custom:4000/v1"


class TestRelayConfigManager:
    """Tests for RelayConfigManager."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def manager(self, temp_dir):
        """Create a manager with temp directory."""
        return RelayConfigManager(config_dir=temp_dir)

    def test_load_creates_default(self, manager, temp_dir):
        """Test that loading creates default config if file doesn't exist."""
        config = manager.load()
        assert config is not None
        assert "public" in config.relays
        assert config.default == "public"

    def test_save_creates_file(self, manager, temp_dir):
        """Test that saving creates the config file."""
        manager.load()
        manager.save()
        assert (temp_dir / "relays.yaml").exists()

    def test_add_relay(self, manager):
        """Test adding a new relay."""
        relay = manager.add_relay(
            name="test",
            mailbox_url="ws://test:4000/v1",
            transit_url="tcp:test:4001",
        )
        assert relay.name == "test"

        # Verify it's retrievable
        retrieved = manager.get_relay("test")
        assert retrieved.mailbox_url == "ws://test:4000/v1"

    def test_add_relay_with_default(self, manager):
        """Test adding a relay and setting it as default."""
        manager.add_relay(
            name="newdefault",
            mailbox_url="ws://new:4000/v1",
            transit_url="tcp:new:4001",
            set_default=True,
        )
        config = manager.load()
        assert config.default == "newdefault"

    def test_remove_relay(self, manager):
        """Test removing a relay."""
        manager.add_relay(
            name="toremove",
            mailbox_url="ws://remove:4000/v1",
            transit_url="tcp:remove:4001",
        )

        result = manager.remove_relay("toremove")
        assert result is True
        assert manager.get_relay("toremove") is None

    def test_remove_nonexistent_relay(self, manager):
        """Test removing a relay that doesn't exist."""
        result = manager.remove_relay("nonexistent")
        assert result is False

    def test_cannot_remove_public_relay(self, manager):
        """Test that the public relay cannot be removed."""
        with pytest.raises(ValueError, match="Cannot remove"):
            manager.remove_relay("public")

    def test_get_default_relay(self, manager):
        """Test getting the default relay."""
        relay = manager.get_default_relay()
        assert relay.name == "public"

    def test_get_relay_by_name(self, manager):
        """Test getting a specific relay by name."""
        manager.add_relay(
            name="specific",
            mailbox_url="ws://specific:4000/v1",
            transit_url="tcp:specific:4001",
        )
        relay = manager.get_relay("specific")
        assert relay.name == "specific"

    def test_get_relay_none_returns_default(self, manager):
        """Test that get_relay with None returns the default."""
        relay = manager.get_relay(None)
        assert relay.name == "public"

    def test_set_default(self, manager):
        """Test setting the default relay."""
        manager.add_relay(
            name="newdefault",
            mailbox_url="ws://new:4000/v1",
            transit_url="tcp:new:4001",
        )
        manager.set_default("newdefault")
        config = manager.load()
        assert config.default == "newdefault"

    def test_set_default_nonexistent(self, manager):
        """Test setting default to nonexistent relay raises error."""
        with pytest.raises(ValueError, match="not found"):
            manager.set_default("nonexistent")

    def test_list_relays(self, manager):
        """Test listing all relays."""
        manager.add_relay(
            name="relay1",
            mailbox_url="ws://r1:4000/v1",
            transit_url="tcp:r1:4001",
        )
        manager.add_relay(
            name="relay2",
            mailbox_url="ws://r2:4000/v1",
            transit_url="tcp:r2:4001",
        )

        relays = manager.list_relays()
        names = [r.name for r in relays]
        assert "public" in names
        assert "relay1" in names
        assert "relay2" in names

    def test_export_relay(self, manager):
        """Test exporting a relay configuration."""
        manager.add_relay(
            name="export",
            mailbox_url="ws://export:4000/v1",
            transit_url="tcp:export:4001",
            description="For export",
        )

        data = manager.export_relay("export")
        assert data["version"] == 1
        assert data["relay"]["name"] == "export"
        assert data["relay"]["mailbox_url"] == "ws://export:4000/v1"

    def test_export_nonexistent_relay(self, manager):
        """Test exporting a nonexistent relay raises error."""
        with pytest.raises(ValueError, match="not found"):
            manager.export_relay("nonexistent")

    def test_import_relay(self, manager):
        """Test importing a relay configuration."""
        data = {
            "version": 1,
            "relay": {
                "name": "imported",
                "mailbox_url": "ws://import:4000/v1",
                "transit_url": "tcp:import:4001",
            }
        }

        relay = manager.import_relay(data)
        assert relay.name == "imported"

        # Verify it's stored
        retrieved = manager.get_relay("imported")
        assert retrieved.mailbox_url == "ws://import:4000/v1"

    def test_import_relay_with_name_override(self, manager):
        """Test importing a relay with name override."""
        data = {
            "version": 1,
            "relay": {
                "name": "original",
                "mailbox_url": "ws://import:4000/v1",
                "transit_url": "tcp:import:4001",
            }
        }

        relay = manager.import_relay(data, name_override="renamed")
        assert relay.name == "renamed"
        assert manager.get_relay("renamed") is not None

    def test_import_relay_with_invalid_version(self, manager):
        """Test importing with invalid version raises error."""
        data = {
            "version": 999,
            "relay": {}
        }
        with pytest.raises(ValueError, match="Unsupported"):
            manager.import_relay(data)

    def test_persistence(self, temp_dir):
        """Test that config persists across manager instances."""
        # First manager - add relay
        manager1 = RelayConfigManager(config_dir=temp_dir)
        manager1.add_relay(
            name="persistent",
            mailbox_url="ws://persist:4000/v1",
            transit_url="tcp:persist:4001",
        )

        # Second manager - should see the relay
        manager2 = RelayConfigManager(config_dir=temp_dir)
        relay = manager2.get_relay("persistent")
        assert relay is not None
        assert relay.mailbox_url == "ws://persist:4000/v1"

    def test_reset_default_on_remove(self, manager):
        """Test that removing the default relay resets default to public."""
        manager.add_relay(
            name="default_test",
            mailbox_url="ws://test:4000/v1",
            transit_url="tcp:test:4001",
            set_default=True,
        )
        assert manager.load().default == "default_test"

        manager.remove_relay("default_test")
        assert manager.load().default == "public"


class TestGetRelayManager:
    """Tests for the get_relay_manager function."""

    def test_returns_manager(self):
        """Test that get_relay_manager returns a manager."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = get_relay_manager(Path(tmpdir))
            assert isinstance(manager, RelayConfigManager)

    def test_singleton_without_path(self):
        """Test singleton behavior when no path is provided."""
        # This test just verifies no crash - actual behavior depends on module state
        manager = get_relay_manager()
        assert manager is not None
