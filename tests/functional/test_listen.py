"""Functional tests for wh listen command.

These tests validate command structure, options, and imports without
invoking the full async command flow (which uses Twisted reactor).
"""

import pytest
from click.testing import CliRunner


class TestListenCommand:
    """Test wh listen CLI command functionality.

    Tests validate the command structure using --help and verify that
    required modules can be imported correctly.
    """

    @pytest.fixture
    def runner(self):
        """Click CLI runner for testing."""
        return CliRunner()

    def test_listen_generates_code(self, runner):
        """Test that listen command exists and can import WormholeManager."""
        from wh.cli.listen import listen
        from wh.core.wormhole_manager import WormholeManager

        # Verify command has help
        result = runner.invoke(listen, ['--help'])
        assert result.exit_code == 0
        assert "Listen daemon" in result.output
        assert "accept connections on a wormhole code" in result.output

        # Verify WormholeManager is importable (used by listen command)
        assert WormholeManager is not None
        assert callable(WormholeManager)

        # Verify the command structure
        assert "Press Ctrl+C to stop" in result.output or "Ctrl+C" in listen.__doc__

    def test_listen_port_forward_setup(self, runner):
        """Test that -p option exists and help shows port forwarding."""
        from wh.cli.listen import listen

        # Verify -p/--port option exists
        result = runner.invoke(listen, ['--help'])
        assert result.exit_code == 0
        assert "-p" in result.output or "--port" in result.output
        assert "local port" in result.output

        # Verify PortForwarder is importable
        from wh.core.forwarder import PortForwarder
        assert PortForwarder is not None

        # Verify help mentions port forwarding
        assert "BASIC MODE" in result.output or "forward" in result.output.lower()

    def test_listen_ssh_server_setup(self, runner):
        """Test that --ssh option exists in help."""
        from wh.cli.listen import listen

        # Verify --ssh option exists
        result = runner.invoke(listen, ['--help'])
        assert result.exit_code == 0
        assert "--ssh" in result.output
        assert "SSH server" in result.output or "ssh" in result.output.lower()

        # Verify SSHServerHandler is importable
        from wh.ssh.server import SSHServerHandler
        assert SSHServerHandler is not None

        # Verify help mentions SSH mode
        assert "SSH SERVER MODE" in result.output or "SSH" in result.output

    def test_listen_http_proxy_setup(self, runner):
        """Test that --http option exists in help."""
        from wh.cli.listen import listen

        # Verify --http option exists
        result = runner.invoke(listen, ['--help'])
        assert result.exit_code == 0
        assert "--http" in result.output
        assert "HTTP proxy" in result.output or "http" in result.output.lower()

        # Verify HTTPProxyHandler is importable
        from wh.http.client import HTTPProxyHandler
        assert HTTPProxyHandler is not None

        # Verify help mentions HTTP mode
        assert "HTTP PROXY MODE" in result.output or "proxy" in result.output.lower()

    def test_listen_file_server_setup(self, runner):
        """Test that --serve option exists in help."""
        from wh.cli.listen import listen

        # Verify --serve option exists
        result = runner.invoke(listen, ['--help'])
        assert result.exit_code == 0
        assert "--serve" in result.output
        assert "files from directory" in result.output or "serve" in result.output.lower()

        # Verify HTTPFileServer is importable
        from wh.http.server import HTTPFileServer
        assert HTTPFileServer is not None

        # Verify help mentions file serving
        assert "browser extension compatible" in result.output or "directory" in result.output
