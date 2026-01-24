"""
Smoke tests for wh CLI commands.

These tests verify that all CLI commands are functional at a basic level:
- Commands can be invoked with --help
- The main CLI can show version information
- CLI modules can be imported without errors
- Help text lists all expected subcommands
"""

import pytest
from click.testing import CliRunner
import importlib


# All CLI commands that should be available
ALL_COMMANDS = [
    'nc',
    'listen',
    'ssh',
    'scp',
    'sftp',
    'curl',
    'wget',
    'ping',
    'tunnel',
    'proxy',
    'rsync',
    'telnet',
    'ftp',
    'nmap',
    'traceroute',
    'dns',
    'mount',
    'vnc',
    'rdp',
    'identity',
    'alias',
    'namespace',
    'relay',
    'daemon',
    'serve',
]


class TestCLIVersion:
    """Test that the main CLI version command works."""

    def test_version(self):
        """Test that wh --version displays version information."""
        from wh.cli.main import cli
        import wh

        runner = CliRunner()
        result = runner.invoke(cli, ['--version'])

        # Should exit successfully
        assert result.exit_code == 0, f"Version command failed: {result.output}"

        # Should show the version number
        assert wh.__version__ in result.output, \
            f"Version {wh.__version__} not found in output: {result.output}"

        # Should mention 'wh' in the output
        assert 'wh' in result.output.lower(), \
            f"'wh' not found in version output: {result.output}"


class TestMainHelp:
    """Test that the main CLI help shows all subcommands."""

    def test_main_help(self):
        """Test that wh --help lists all subcommands."""
        from wh.cli.main import cli

        runner = CliRunner()
        result = runner.invoke(cli, ['--help'])

        # Should exit successfully
        assert result.exit_code == 0, f"Help command failed: {result.output}"

        # Should show all commands
        for cmd in ALL_COMMANDS:
            assert cmd in result.output, \
                f"Command '{cmd}' not found in help output"

    def test_main_help_shows_description(self):
        """Test that main help includes key descriptions."""
        from wh.cli.main import cli

        runner = CliRunner()
        result = runner.invoke(cli, ['--help'])

        assert result.exit_code == 0

        # Check for key description phrases
        assert 'Wormhole Tools' in result.output or 'wh - Wormhole Tools' in result.output
        assert 'Commands:' in result.output

    def test_main_help_shows_options(self):
        """Test that main help shows global options."""
        from wh.cli.main import cli

        runner = CliRunner()
        result = runner.invoke(cli, ['--help'])

        assert result.exit_code == 0

        # Check for key global options
        assert '--relay' in result.output or '-r' in result.output
        assert '--version' in result.output
        assert '--code-length' in result.output or '-c' in result.output
        assert '--verbose' in result.output or '-v' in result.output


class TestCommandHelp:
    """Test that all CLI commands respond to --help."""

    @pytest.mark.parametrize('command', ALL_COMMANDS)
    def test_all_commands_help(self, command):
        """Test that each command can be invoked with --help."""
        from wh.cli.main import cli

        runner = CliRunner()
        result = runner.invoke(cli, [command, '--help'])

        # Should exit successfully
        assert result.exit_code == 0, \
            f"Command '{command} --help' failed with exit code {result.exit_code}: {result.output}"

        # Should produce non-empty output
        assert len(result.output) > 0, \
            f"Command '{command} --help' produced no output"

        # Help output should mention the command name (in most cases)
        # Note: Some commands might have different help text, so we just check for substantive content
        assert len(result.output.split('\n')) > 3, \
            f"Command '{command} --help' output too short: {result.output}"

    @pytest.mark.parametrize('command', ALL_COMMANDS)
    def test_all_commands_help_shows_usage(self, command):
        """Test that each command's help shows usage information."""
        from wh.cli.main import cli

        runner = CliRunner()
        result = runner.invoke(cli, [command, '--help'])

        assert result.exit_code == 0

        # Check that it looks like Click help output (has "Usage:" or "Options:")
        output_lower = result.output.lower()
        assert 'usage:' in output_lower or 'options:' in output_lower, \
            f"Command '{command} --help' doesn't show standard help format: {result.output}"


class TestCLIImports:
    """Test that all CLI modules can be imported."""

    def test_main_cli_import(self):
        """Test that the main CLI module can be imported."""
        try:
            from wh.cli.main import cli
            assert cli is not None
            assert callable(cli)
        except ImportError as e:
            pytest.fail(f"Failed to import main CLI: {e}")

    def test_cli_commands_import(self):
        """Test that all CLI command modules can be imported."""
        command_modules = {
            'nc': 'wh.cli.nc',
            'listen': 'wh.cli.listen',
            'ssh': 'wh.cli.ssh',
            'scp': 'wh.cli.scp',
            'sftp': 'wh.cli.sftp',
            'curl': 'wh.cli.curl',
            'wget': 'wh.cli.wget',
            'ping': 'wh.cli.ping',
            'tunnel': 'wh.cli.tunnel',
            'proxy': 'wh.cli.proxy',
            'rsync': 'wh.cli.rsync',
            'telnet': 'wh.cli.telnet',
            'ftp': 'wh.cli.ftp',
            'nmap': 'wh.cli.nmap',
            'traceroute': 'wh.cli.traceroute',
            'dns': 'wh.cli.dns',
            'mount': 'wh.cli.mount',
            'vnc': 'wh.cli.vnc',
            'rdp': 'wh.cli.rdp',
            'relay': 'wh.cli.relay',
            'daemon': 'wh.cli.daemon',
            'serve': 'wh.cli.serve',
            'namespace': 'wh.cli.namespace',
        }

        for cmd_name, module_path in command_modules.items():
            try:
                module = importlib.import_module(module_path)
                assert module is not None, f"Module {module_path} imported as None"

                # Check that the module exports the command
                assert hasattr(module, cmd_name), \
                    f"Module {module_path} does not export '{cmd_name}' command"

                cmd = getattr(module, cmd_name)
                assert callable(cmd), \
                    f"Command '{cmd_name}' in {module_path} is not callable"

            except ImportError as e:
                pytest.fail(f"Failed to import {module_path} for command '{cmd_name}': {e}")

    def test_wns_cli_import(self):
        """Test that WNS CLI commands can be imported."""
        try:
            from wh.wns.cli import identity, alias
            assert identity is not None
            assert alias is not None
            assert callable(identity)
            assert callable(alias)
        except ImportError as e:
            pytest.fail(f"Failed to import WNS CLI commands: {e}")


class TestCLIRegistration:
    """Test that all commands are properly registered with the CLI."""

    def test_all_commands_registered(self):
        """Test that all expected commands are registered in the CLI group."""
        from wh.cli.main import cli

        registered_commands = set(cli.commands.keys())
        expected_commands = set(ALL_COMMANDS)

        # Check for missing commands
        missing = expected_commands - registered_commands
        assert not missing, f"Commands not registered: {missing}"

        # Check for unexpected commands
        extra = registered_commands - expected_commands
        assert not extra, f"Unexpected commands registered: {extra}"

        # Verify exact count
        assert len(registered_commands) == len(ALL_COMMANDS), \
            f"Expected {len(ALL_COMMANDS)} commands, got {len(registered_commands)}"

    def test_command_objects_are_click_commands(self):
        """Test that all registered commands are Click Command objects."""
        from wh.cli.main import cli
        import click

        for cmd_name, cmd_obj in cli.commands.items():
            assert isinstance(cmd_obj, (click.Command, click.Group)), \
                f"Command '{cmd_name}' is not a Click Command or Group: {type(cmd_obj)}"


class TestBasicCLIInvocation:
    """Test basic CLI invocation patterns."""

    def test_cli_with_no_args(self):
        """Test that CLI with no arguments shows help."""
        from wh.cli.main import cli

        runner = CliRunner()
        result = runner.invoke(cli, [])

        # Should exit successfully and show help
        assert result.exit_code == 0
        assert 'Usage:' in result.output or 'Commands:' in result.output

    def test_cli_invalid_command(self):
        """Test that CLI with invalid command shows error."""
        from wh.cli.main import cli

        runner = CliRunner()
        result = runner.invoke(cli, ['invalid-command-xyz'])

        # Should exit with error
        assert result.exit_code != 0

        # Should mention the invalid command or show an error
        output_lower = result.output.lower()
        assert 'error' in output_lower or 'invalid' in output_lower or 'no such' in output_lower, \
            f"Expected error message, got: {result.output}"


class TestGlobalOptions:
    """Test that global CLI options work."""

    def test_verbose_flag(self):
        """Test that -v/--verbose flag is accepted."""
        from wh.cli.main import cli

        runner = CliRunner()

        # Test with -v
        result = runner.invoke(cli, ['-v', '--help'])
        assert result.exit_code == 0

        # Test with -vv
        result = runner.invoke(cli, ['-vv', '--help'])
        assert result.exit_code == 0

    def test_code_length_option(self):
        """Test that -c/--code-length option is accepted."""
        from wh.cli.main import cli

        runner = CliRunner()

        # Test with -c
        result = runner.invoke(cli, ['-c', '3', '--help'])
        assert result.exit_code == 0

        # Test with --code-length
        result = runner.invoke(cli, ['--code-length', '4', '--help'])
        assert result.exit_code == 0

    def test_relay_option(self):
        """Test that -r/--relay option is accepted."""
        from wh.cli.main import cli

        runner = CliRunner()

        # Test with -r
        result = runner.invoke(cli, ['-r', 'test-relay', '--help'])
        assert result.exit_code == 0

        # Test with --relay
        result = runner.invoke(cli, ['--relay', 'ws://test:4000/v1', '--help'])
        assert result.exit_code == 0

    def test_namespace_option(self):
        """Test that -n/--namespace option is accepted."""
        from wh.cli.main import cli

        runner = CliRunner()

        # Test with -n
        result = runner.invoke(cli, ['-n', 'test-ns', '--help'])
        assert result.exit_code == 0

        # Test with --namespace
        result = runner.invoke(cli, ['--namespace', 'test-namespace', '--help'])
        assert result.exit_code == 0
