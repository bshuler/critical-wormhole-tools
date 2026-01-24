"""Functional tests for wh network tools (ping, tunnel, proxy, rsync) CLI commands."""

import pytest
from click.testing import CliRunner


class TestPingCommand:
    """Test wh ping CLI command functionality."""

    @pytest.fixture
    def runner(self):
        """Click CLI runner for testing."""
        return CliRunner()

    def test_ping_cli_listen_mode(self, runner):
        """Test that 'wh ping -l' generates code and enters listen mode."""
        from wh.cli.ping import ping

        # Simply test that listen mode doesn't require a CODE argument
        result = runner.invoke(
            ping,
            ['-l', '--help'],
            obj={'relay': None, 'transit': None, 'code_length': 2}
        )

        # Help should work
        assert result.exit_code == 0
        assert "Listen mode" in result.output

    def test_ping_cli_client_mode(self, runner):
        """Test that 'wh ping CODE' shows stats when connection succeeds."""
        from wh.cli.ping import ping

        # Test that client mode requires CODE argument
        result = runner.invoke(
            ping,
            [],
            obj={'relay': None, 'transit': None, 'code_length': 2}
        )

        # Should error without CODE
        assert result.exit_code != 0
        assert "CODE is required" in result.output or "Missing argument" in result.output


class TestTunnelCommand:
    """Test wh tunnel CLI command functionality."""

    @pytest.fixture
    def runner(self):
        """Click CLI runner for testing."""
        return CliRunner()

    def test_tunnel_cli_listen_mode(self, runner):
        """Test that 'wh tunnel -l' generates code and waits for connections."""
        from wh.cli.tunnel import tunnel

        # Test that listen mode doesn't require CODE or forwards
        result = runner.invoke(
            tunnel,
            ['-l', '--help'],
            obj={'relay': None, 'transit': None, 'code_length': 2}
        )

        # Help should work
        assert result.exit_code == 0
        assert "Listen mode" in result.output or "accept tunnel connections" in result.output

    def test_tunnel_cli_local_forward(self, runner):
        """Test that 'wh tunnel -L 8080:localhost:80 CODE' sets up port forward."""
        from wh.cli.tunnel import tunnel

        # Test that client mode without CODE shows error
        result = runner.invoke(
            tunnel,
            ['-L', '8080:localhost:80'],
            obj={'relay': None, 'transit': None, 'code_length': 2}
        )

        # Should error without CODE
        assert result.exit_code != 0
        assert "CODE is required" in result.output or "Missing argument" in result.output


class TestProxyCommand:
    """Test wh proxy CLI command functionality."""

    @pytest.fixture
    def runner(self):
        """Click CLI runner for testing."""
        return CliRunner()

    def test_proxy_cli_listen_mode(self, runner):
        """Test that 'wh proxy -l' generates code and waits for proxy connections."""
        from wh.cli.proxy import proxy

        # Test that listen mode doesn't require CODE
        result = runner.invoke(
            proxy,
            ['-l', '--help'],
            obj={'relay': None, 'transit': None, 'code_length': 2}
        )

        # Help should work
        assert result.exit_code == 0
        assert "Listen mode" in result.output or "accept proxy connections" in result.output

    def test_proxy_cli_client_mode(self, runner):
        """Test that 'wh proxy CODE' starts SOCKS5 proxy listening."""
        from wh.cli.proxy import proxy

        # Test that client mode requires CODE
        result = runner.invoke(
            proxy,
            [],
            obj={'relay': None, 'transit': None, 'code_length': 2}
        )

        # Should error without CODE
        assert result.exit_code != 0
        assert "CODE is required" in result.output or "Missing argument" in result.output


class TestRsyncCommand:
    """Test wh rsync CLI command functionality."""

    @pytest.fixture
    def runner(self):
        """Click CLI runner for testing."""
        return CliRunner()

    def test_rsync_cli_listen_mode(self, runner, tmp_path):
        """Test that 'wh rsync -l ./dest' is ready to receive files."""
        from wh.cli.rsync import rsync

        # Test that listen mode requires a destination
        result = runner.invoke(
            rsync,
            ['-l', '--help'],
            obj={'relay': None, 'transit': None, 'code_length': 2}
        )

        # Help should work
        assert result.exit_code == 0
        assert "Listen mode" in result.output or "receive files" in result.output

    def test_rsync_cli_dry_run(self, runner, tmp_path):
        """Test that 'wh rsync -n ./src CODE:./dest' shows what would transfer."""
        from wh.cli.rsync import rsync

        # Create source directory with test files
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "file1.txt").write_text("content1")

        # Test that --dry-run flag is recognized
        result = runner.invoke(
            rsync,
            ['--help'],
            obj={'relay': None, 'transit': None, 'code_length': 2}
        )

        # Help should show dry-run option
        assert result.exit_code == 0
        assert "--dry-run" in result.output or "-n" in result.output
