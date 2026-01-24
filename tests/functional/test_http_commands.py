"""Functional tests for wh curl and wget CLI commands.

Tests command structure, options, and module imports without invoking
the full async command flow (which uses Twisted reactor that can only run once).
"""

from click.testing import CliRunner


class TestCurlCLI:
    """Test wh curl command CLI validation."""

    def test_curl_cli_requires_code(self):
        """Test that curl without --code shows error."""
        from wh.cli.curl import curl

        runner = CliRunner()
        result = runner.invoke(curl, ["http://example.com"])

        assert result.exit_code != 0
        assert "Missing option" in result.output or "required" in result.output.lower()

    def test_curl_cli_requires_url(self):
        """Test that curl without URL shows error."""
        from wh.cli.curl import curl

        runner = CliRunner()
        result = runner.invoke(curl, ["--code", "7-guitar-sunset"])

        assert result.exit_code != 0
        assert "Missing argument" in result.output or "url" in result.output.lower()

    def test_curl_command_structure(self):
        """Test curl command has correct options and can import dependencies."""
        from wh.cli.curl import curl
        from wh.core.wormhole_manager import WormholeManager
        from wh.http.client import WormholeHTTPClient, HTTPResponse

        runner = CliRunner()
        result = runner.invoke(curl, ["--help"])

        # Verify command structure
        assert result.exit_code == 0
        assert "--code" in result.output
        assert "-X" in result.output or "--request" in result.output
        assert "-H" in result.output or "--header" in result.output
        assert "-d" in result.output or "--data" in result.output
        assert "-o" in result.output or "--output" in result.output

        # Verify dependencies are importable
        assert WormholeManager is not None
        assert WormholeHTTPClient is not None
        assert HTTPResponse is not None


class TestWgetCLI:
    """Test wh wget command CLI validation."""

    def test_wget_cli_requires_code(self):
        """Test that wget without --code shows error."""
        from wh.cli.wget import wget

        runner = CliRunner()
        result = runner.invoke(wget, ["http://example.com/file.txt"])

        assert result.exit_code != 0
        assert "Missing option" in result.output or "required" in result.output.lower()

    def test_wget_cli_requires_url(self):
        """Test that wget without URL shows error."""
        from wh.cli.wget import wget

        runner = CliRunner()
        result = runner.invoke(wget, ["--code", "7-guitar-sunset"])

        assert result.exit_code != 0
        assert "Missing argument" in result.output or "url" in result.output.lower()

    def test_wget_command_structure(self):
        """Test wget command has correct options and can import dependencies."""
        from wh.cli.wget import wget
        from wh.core.wormhole_manager import WormholeManager
        from wh.http.client import WormholeHTTPClient, HTTPResponse

        runner = CliRunner()
        result = runner.invoke(wget, ["--help"])

        # Verify command structure
        assert result.exit_code == 0
        assert "--code" in result.output
        assert "-O" in result.output or "--output-document" in result.output
        assert "-P" in result.output or "--directory-prefix" in result.output
        assert "-q" in result.output or "--quiet" in result.output
        assert "--header" in result.output

        # Verify dependencies are importable
        assert WormholeManager is not None
        assert WormholeHTTPClient is not None
        assert HTTPResponse is not None
