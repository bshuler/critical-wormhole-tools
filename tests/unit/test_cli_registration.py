"""Unit tests for CLI command registration and main CLI group."""

from unittest.mock import patch, MagicMock
from click.testing import CliRunner
import tempfile
from pathlib import Path


# Expected list of all 25 commands
EXPECTED_COMMANDS = [
    'nc', 'listen', 'ssh', 'scp', 'sftp', 'curl', 'wget',
    'ping', 'tunnel', 'proxy', 'rsync', 'serve', 'daemon', 'relay',
    'telnet', 'ftp', 'nmap', 'traceroute', 'dns', 'mount', 'vnc', 'rdp',
    'identity', 'alias', 'namespace'
]


class TestCLIRegistration:
    """Test that all commands are properly registered."""

    def test_all_commands_registered(self):
        """Test that all 25 expected commands exist in cli.commands."""
        from wh.cli.main import cli

        registered_commands = list(cli.commands.keys())

        # Check that we have exactly 25 commands
        assert len(registered_commands) == 25, \
            f"Expected 25 commands, got {len(registered_commands)}: {registered_commands}"

        # Check that all expected commands are registered
        for expected_cmd in EXPECTED_COMMANDS:
            assert expected_cmd in registered_commands, \
                f"Command '{expected_cmd}' not registered"

        # Check that no unexpected commands exist
        for registered_cmd in registered_commands:
            assert registered_cmd in EXPECTED_COMMANDS, \
                f"Unexpected command '{registered_cmd}' registered"

    def test_cli_help_lists_commands(self):
        """Test that help output shows all command names."""
        from wh.cli.main import cli

        runner = CliRunner()
        result = runner.invoke(cli, ['--help'])

        assert result.exit_code == 0

        # Check that help mentions all commands (they appear in help text)
        for cmd in EXPECTED_COMMANDS:
            assert cmd in result.output, \
                f"Command '{cmd}' not found in help output"

    def test_cli_version(self):
        """Test that --version shows version number."""
        from wh.cli.main import cli
        import wh

        runner = CliRunner()
        result = runner.invoke(cli, ['--version'])

        assert result.exit_code == 0
        assert wh.__version__ in result.output
        assert 'wh' in result.output.lower()


class TestCLIOptions:
    """Test CLI option handling."""

    def test_cli_relay_option(self):
        """Test that --relay option is passed to context."""
        from wh.cli.main import cli
        import click

        runner = CliRunner()

        # Track context object
        captured_ctx = {}

        # Mock the nc command to capture context
        original_nc = cli.commands.get('nc')

        @click.command('nc')
        @click.pass_context
        def mock_nc(ctx):
            """Mock nc command."""
            captured_ctx.update(ctx.obj)

        with patch("wh.cli.main.resolve_relay") as mock_resolve:
            mock_resolve.return_value = ("ws://test:4000/v1", "tcp:test:4001")

            # Temporarily replace nc command
            cli.commands['nc'] = mock_nc

            try:
                runner.invoke(cli, ['--relay', 'myrelay', 'nc'])

                # Verify resolve_relay was called with the relay option
                mock_resolve.assert_called_once_with('myrelay')
                assert captured_ctx.get('relay') == "ws://test:4000/v1"
            finally:
                # Restore original command
                if original_nc:
                    cli.commands['nc'] = original_nc

    def test_cli_transit_option(self):
        """Test that --transit option overrides relay transit URL."""
        from wh.cli.main import cli
        import click

        runner = CliRunner()
        captured_ctx = {}

        original_nc = cli.commands.get('nc')

        @click.command('nc')
        @click.pass_context
        def mock_nc(ctx):
            """Mock nc command."""
            captured_ctx.update(ctx.obj)

        with patch("wh.cli.main.resolve_relay") as mock_resolve:
            mock_resolve.return_value = ("ws://test:4000/v1", "tcp:test:4001")

            cli.commands['nc'] = mock_nc

            try:
                runner.invoke(cli, ['--transit', 'tcp:custom:5001', 'nc'])

                # Transit should be overridden
                assert captured_ctx.get('transit') == "tcp:custom:5001"
            finally:
                if original_nc:
                    cli.commands['nc'] = original_nc

    def test_cli_code_length_option(self):
        """Test that -c/--code-length flag sets code length."""
        from wh.cli.main import cli
        import click

        runner = CliRunner()
        captured_ctx = {}

        original_nc = cli.commands.get('nc')

        @click.command('nc')
        @click.pass_context
        def mock_nc(ctx):
            """Mock nc command."""
            captured_ctx.update(ctx.obj)

        cli.commands['nc'] = mock_nc

        try:
            runner.invoke(cli, ['-c', '3', 'nc'])

            # Should accept the custom code length
            assert captured_ctx.get('code_length') == 3
        finally:
            if original_nc:
                cli.commands['nc'] = original_nc

    def test_cli_verbose_option(self):
        """Test that -v flag increases verbosity."""
        from wh.cli.main import cli
        import click

        runner = CliRunner()
        captured_ctx = {}

        original_nc = cli.commands.get('nc')

        @click.command('nc')
        @click.pass_context
        def mock_nc(ctx):
            """Mock nc command."""
            captured_ctx.update(ctx.obj)

        cli.commands['nc'] = mock_nc

        try:
            runner.invoke(cli, ['-vv', 'nc'])

            # Should count verbose flags
            assert captured_ctx.get('verbose') == 2
        finally:
            if original_nc:
                cli.commands['nc'] = original_nc

    def test_cli_namespace_option(self):
        """Test that -n/--namespace flag sets namespace."""
        from wh.cli.main import cli
        import click

        runner = CliRunner()
        captured_ctx = {}

        original_nc = cli.commands.get('nc')

        @click.command('nc')
        @click.pass_context
        def mock_nc(ctx):
            """Mock nc command."""
            captured_ctx.update(ctx.obj)

        with patch("wh.enterprise.namespace.get_namespace_manager") as mock_get_ns:
            mock_manager = MagicMock()
            mock_manager.exists.return_value = True
            mock_get_ns.return_value = mock_manager

            cli.commands['nc'] = mock_nc

            try:
                runner.invoke(cli, ['-n', 'test-namespace', 'nc'])

                # Should set namespace in context
                assert captured_ctx.get('namespace') == 'test-namespace'
            finally:
                if original_nc:
                    cli.commands['nc'] = original_nc


class TestResolveRelay:
    """Test resolve_relay function."""

    def test_resolve_relay_default(self):
        """Test that resolve_relay uses default relay from config when no option given."""
        from wh.cli.main import resolve_relay
        from wh.relay.config import RelayConfigManager

        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)

            with patch("wh.relay.config.get_relay_manager") as mock_get:
                manager = RelayConfigManager(config_dir=config_dir)
                manager.add_relay(
                    name="default_relay",
                    mailbox_url="ws://default:4000/v1",
                    transit_url="tcp:default:4001",
                    set_default=True
                )
                mock_get.return_value = manager

                mailbox_url, transit_url = resolve_relay(None)

                assert mailbox_url == "ws://default:4000/v1"
                assert transit_url == "tcp:default:4001"

    def test_resolve_relay_by_name(self):
        """Test that resolve_relay looks up relay by name."""
        from wh.cli.main import resolve_relay
        from wh.relay.config import RelayConfigManager

        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)

            with patch("wh.relay.config.get_relay_manager") as mock_get:
                manager = RelayConfigManager(config_dir=config_dir)
                manager.add_relay(
                    name="named_relay",
                    mailbox_url="ws://named:4000/v1",
                    transit_url="tcp:named:4001",
                    set_default=False
                )
                mock_get.return_value = manager

                mailbox_url, transit_url = resolve_relay("named_relay")

                assert mailbox_url == "ws://named:4000/v1"
                assert transit_url == "tcp:named:4001"

    def test_resolve_relay_by_url(self):
        """Test that resolve_relay uses URL directly when provided."""
        from wh.cli.main import resolve_relay

        # URL with :// should be used as-is
        mailbox_url, transit_url = resolve_relay("ws://custom:4000/v1")

        assert mailbox_url == "ws://custom:4000/v1"
        assert transit_url is None
