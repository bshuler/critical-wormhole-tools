"""Functional tests for wh relay CLI commands."""

from unittest.mock import patch
from click.testing import CliRunner
import tempfile
from pathlib import Path
import json


class TestRelayListCommand:
    """Test wh relay list command."""

    def test_list_command_exists(self):
        """Test that the relay list command exists."""
        from wh.cli.relay import list_relays

        assert list_relays is not None
        assert list_relays.name == "list"

    def test_list_default_relays(self):
        """Test listing default relays."""
        from wh.cli.relay import relay
        from wh.relay.config import RelayConfigManager

        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)

            with patch("wh.relay.config.get_relay_manager") as mock_get:
                manager = RelayConfigManager(config_dir=config_dir)
                mock_get.return_value = manager

                result = runner.invoke(relay, ["list"])

                assert result.exit_code == 0
                assert "public" in result.output

    def test_list_as_json(self):
        """Test listing relays as JSON."""
        from wh.cli.relay import relay
        from wh.relay.config import RelayConfigManager

        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)

            with patch("wh.relay.config.get_relay_manager") as mock_get:
                manager = RelayConfigManager(config_dir=config_dir)
                mock_get.return_value = manager

                result = runner.invoke(relay, ["list", "--json"])

                assert result.exit_code == 0
                data = json.loads(result.output)
                assert "relays" in data
                assert "default" in data


class TestRelayAddCommand:
    """Test wh relay add command."""

    def test_add_command_exists(self):
        """Test that the relay add command exists."""
        from wh.cli.relay import add_relay

        assert add_relay is not None
        assert add_relay.name == "add"

    def test_add_relay(self):
        """Test adding a relay."""
        from wh.cli.relay import relay
        from wh.relay.config import RelayConfigManager

        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)

            with patch("wh.relay.config.get_relay_manager") as mock_get:
                manager = RelayConfigManager(config_dir=config_dir)
                mock_get.return_value = manager

                result = runner.invoke(
                    relay,
                    ["add", "test", "ws://test:4000/v1", "tcp:test:4001"]
                )

                assert result.exit_code == 0
                assert "Added relay 'test'" in result.output

                # Verify relay was added
                added = manager.get_relay("test")
                assert added is not None
                assert added.mailbox_url == "ws://test:4000/v1"


class TestRelayRemoveCommand:
    """Test wh relay remove command."""

    def test_remove_command_exists(self):
        """Test that the relay remove command exists."""
        from wh.cli.relay import remove_relay

        assert remove_relay is not None
        assert remove_relay.name == "remove"

    def test_cannot_remove_public(self):
        """Test that public relay cannot be removed."""
        from wh.cli.relay import relay
        from wh.relay.config import RelayConfigManager

        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)

            with patch("wh.relay.config.get_relay_manager") as mock_get:
                manager = RelayConfigManager(config_dir=config_dir)
                mock_get.return_value = manager

                result = runner.invoke(relay, ["remove", "public", "--force"])

                assert result.exit_code != 0
                assert "Cannot remove" in result.output


class TestRelaySetDefaultCommand:
    """Test wh relay set-default command."""

    def test_set_default_command_exists(self):
        """Test that the relay set-default command exists."""
        from wh.cli.relay import set_default

        assert set_default is not None
        assert set_default.name == "set-default"

    def test_set_default(self):
        """Test setting default relay."""
        from wh.cli.relay import relay
        from wh.relay.config import RelayConfigManager

        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)

            with patch("wh.relay.config.get_relay_manager") as mock_get:
                manager = RelayConfigManager(config_dir=config_dir)
                # Add a relay to set as default
                manager.add_relay(
                    name="test",
                    mailbox_url="ws://test:4000/v1",
                    transit_url="tcp:test:4001",
                )
                mock_get.return_value = manager

                result = runner.invoke(relay, ["set-default", "test"])

                assert result.exit_code == 0
                assert "Default relay set" in result.output


class TestRelayServeCommand:
    """Test wh relay serve command options."""

    def test_serve_command_exists(self):
        """Test that the relay serve command exists."""
        from wh.cli.relay import serve

        assert serve is not None
        assert serve.name == "serve"

    def test_serve_has_advertise_option(self):
        """Test that serve has --advertise option."""
        from wh.cli.relay import serve

        options = {p.name for p in serve.params}
        assert "advertise" in options

    def test_serve_has_name_option(self):
        """Test that serve has --name option."""
        from wh.cli.relay import serve

        options = {p.name for p in serve.params}
        assert "advertise_name" in options

    def test_serve_has_host_option(self):
        """Test that serve has --host option."""
        from wh.cli.relay import serve

        options = {p.name for p in serve.params}
        assert "host" in options

    def test_serve_has_port_options(self):
        """Test that serve has port options."""
        from wh.cli.relay import serve

        options = {p.name for p in serve.params}
        assert "mailbox_port" in options
        assert "transit_port" in options


class TestRelayDiscoverCommand:
    """Test wh relay discover command."""

    def test_discover_command_exists(self):
        """Test that the relay discover command exists."""
        from wh.cli.relay import discover_relays

        assert discover_relays is not None
        assert discover_relays.name == "discover"

    def test_discover_has_timeout_option(self):
        """Test that discover has --timeout option."""
        from wh.cli.relay import discover_relays

        options = {p.name for p in discover_relays.params}
        assert "timeout" in options

    def test_discover_has_add_option(self):
        """Test that discover has --add option."""
        from wh.cli.relay import discover_relays

        options = {p.name for p in discover_relays.params}
        assert "add_found" in options
