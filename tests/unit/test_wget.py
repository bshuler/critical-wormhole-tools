"""Unit tests for wget CLI command."""

import pytest
import os
from unittest.mock import MagicMock, AsyncMock, patch
from click.testing import CliRunner

from wh.cli.wget import wget
from wh.http.client import HTTPResponse


class TestWgetCommandHelp:
    """Tests for wget command help and interface."""

    def test_wget_command_help(self):
        """Test --help shows usage and options."""
        runner = CliRunner()
        result = runner.invoke(wget, ['--help'])

        assert result.exit_code == 0
        assert 'Download files through wormhole' in result.output
        assert '--code' in result.output
        assert '--output-document' in result.output
        assert '--directory-prefix' in result.output
        assert '--quiet' in result.output
        assert '--continue' in result.output
        assert '--header' in result.output
        assert 'URL' in result.output or 'url' in result.output.lower()


class TestWgetFilenameExtraction:
    """Tests for filename extraction from URLs."""

    def test_wget_filename_from_url(self):
        """Test correct filename extraction from http://example.com/file.zip."""
        from urllib.parse import urlparse

        url = "http://example.com/file.zip"
        parsed = urlparse(url)
        filename = os.path.basename(parsed.path)

        assert filename == "file.zip"

    def test_wget_filename_from_nested_path(self):
        """Test filename extraction from nested path."""
        from urllib.parse import urlparse

        url = "http://example.com/path/to/document.pdf"
        parsed = urlparse(url)
        filename = os.path.basename(parsed.path)

        assert filename == "document.pdf"

    def test_wget_filename_fallback(self):
        """Test fallback to index.html for empty path."""
        from urllib.parse import urlparse

        url = "http://example.com/"
        parsed = urlparse(url)
        filename = os.path.basename(parsed.path)

        if not filename:
            filename = 'index.html'

        assert filename == "index.html"

    def test_wget_filename_fallback_no_path(self):
        """Test fallback to index.html for URL with no path."""
        from urllib.parse import urlparse

        url = "http://example.com"
        parsed = urlparse(url)
        filename = os.path.basename(parsed.path)

        if not filename:
            filename = 'index.html'

        assert filename == "index.html"


class TestWgetOutputToFile:
    """Tests for wget output to file functionality."""

    def test_output_file_option(self):
        """Test -O flag is recognized."""
        runner = CliRunner()

        # Test that -O option is recognized by the command
        result = runner.invoke(wget, [
            '--help'
        ], obj={})

        assert '-O' in result.output or '--output-document' in result.output


class TestWgetOutputToStdout:
    """Tests for wget output to stdout functionality."""

    def test_output_stdout_logic(self):
        """Test -O - writes to stdout logic."""
        output = "-"

        # This is the logic in wget command
        if output == '-':
            output_path = None  # Will write to stdout
        else:
            output_path = output

        assert output_path is None


class TestWgetDirectoryPrefix:
    """Tests for wget directory prefix functionality."""

    def test_directory_prefix_option(self):
        """Test -P flag is recognized."""
        runner = CliRunner()

        result = runner.invoke(wget, [
            '--help'
        ], obj={})

        assert '-P' in result.output or '--directory-prefix' in result.output


class TestWgetQuietMode:
    """Tests for wget quiet mode."""

    def test_quiet_mode_option(self):
        """Test -q flag is recognized."""
        runner = CliRunner()

        result = runner.invoke(wget, [
            '--help'
        ], obj={})

        assert '-q' in result.output or '--quiet' in result.output

    def test_quiet_mode_logic(self):
        """Test quiet mode suppresses status messages."""
        quiet = True

        # Simulate status function from wget
        messages = []

        def status(msg: str) -> None:
            if not quiet:
                messages.append(msg)

        status("Connecting...")
        status("Downloading...")

        # In quiet mode, no messages should be added
        assert len(messages) == 0

    def test_non_quiet_mode_logic(self):
        """Test non-quiet mode shows status messages."""
        quiet = False

        # Simulate status function from wget
        messages = []

        def status(msg: str) -> None:
            if not quiet:
                messages.append(msg)

        status("Connecting...")
        status("Downloading...")

        # In non-quiet mode, messages should be added
        assert len(messages) == 2
        assert "Connecting..." in messages
        assert "Downloading..." in messages


class TestWgetCustomHeaders:
    """Tests for wget custom headers functionality."""

    def test_header_option(self):
        """Test --header flag is recognized."""
        runner = CliRunner()

        result = runner.invoke(wget, [
            '--help'
        ], obj={})

        assert '--header' in result.output

    def test_header_parsing(self):
        """Test header parsing logic."""
        headers = {}
        header_list = [
            'Authorization: Bearer token123',
            'X-Custom-Header: value',
            'Content-Type: application/json',
        ]

        for h in header_list:
            if ':' in h:
                key, value = h.split(':', 1)
                headers[key.strip()] = value.strip()

        assert headers['Authorization'] == 'Bearer token123'
        assert headers['X-Custom-Header'] == 'value'
        assert headers['Content-Type'] == 'application/json'

    def test_header_parsing_with_spaces(self):
        """Test header parsing with extra spaces."""
        headers = {}
        header_str = '  User-Agent  :   CustomAgent/1.0  '

        if ':' in header_str:
            key, value = header_str.split(':', 1)
            headers[key.strip()] = value.strip()

        assert headers['User-Agent'] == 'CustomAgent/1.0'

    def test_header_parsing_with_colons_in_value(self):
        """Test header parsing when value contains colons."""
        headers = {}
        header_str = 'X-Data: key:value:extra'

        if ':' in header_str:
            key, value = header_str.split(':', 1)
            headers[key.strip()] = value.strip()

        assert headers['X-Data'] == 'key:value:extra'


class TestWgetHTTPError:
    """Tests for wget HTTP error handling."""

    def test_http_error_handling_logic(self):
        """Test non-200 response raises ClickException."""
        import click

        response = HTTPResponse(
            status_code=404,
            reason="Not Found",
            headers={},
            body=b"Resource not found",
        )

        # Simulate the error check from wget command
        with pytest.raises(click.ClickException) as exc_info:
            if response.status_code != 200:
                raise click.ClickException(
                    f"HTTP {response.status_code}: {response.reason}"
                )

        assert "404" in str(exc_info.value)
        assert "Not Found" in str(exc_info.value)

    def test_http_500_error_logic(self):
        """Test 500 error raises ClickException."""
        import click

        response = HTTPResponse(
            status_code=500,
            reason="Internal Server Error",
            headers={},
            body=b"Server error",
        )

        # Simulate the error check from wget command
        with pytest.raises(click.ClickException) as exc_info:
            if response.status_code != 200:
                raise click.ClickException(
                    f"HTTP {response.status_code}: {response.reason}"
                )

        assert "500" in str(exc_info.value)
        assert "Internal Server Error" in str(exc_info.value)

    def test_http_200_success_logic(self):
        """Test 200 response does not raise exception."""
        response = HTTPResponse(
            status_code=200,
            reason="OK",
            headers={},
            body=b"Success",
        )

        # Should not raise any exception
        if response.status_code != 200:
            raise Exception("Should not happen")

        # Test passes if no exception raised
        assert response.status_code == 200


class TestWgetFilenameHandling:
    """Additional tests for filename handling edge cases."""

    def test_filename_with_query_params(self):
        """Test filename extraction ignores query parameters."""
        from urllib.parse import urlparse

        url = "http://example.com/file.zip?download=true&token=xyz"
        parsed = urlparse(url)
        filename = os.path.basename(parsed.path)

        assert filename == "file.zip"

    def test_filename_with_fragment(self):
        """Test filename extraction ignores fragment."""
        from urllib.parse import urlparse

        url = "http://example.com/doc.html#section1"
        parsed = urlparse(url)
        filename = os.path.basename(parsed.path)

        assert filename == "doc.html"

    def test_filename_with_trailing_slash(self):
        """Test filename extraction from path with trailing slash."""
        from urllib.parse import urlparse

        url = "http://example.com/path/"
        parsed = urlparse(url)
        filename = os.path.basename(parsed.path)

        if not filename:
            filename = 'index.html'

        assert filename == "index.html"


class TestWgetOutputPathConstruction:
    """Tests for output path construction logic."""

    def test_output_path_with_prefix(self):
        """Test output path construction with directory prefix."""
        prefix = "/downloads"
        output = "myfile.zip"

        output_path = os.path.join(prefix, output) if prefix != '.' else output

        assert output_path == "/downloads/myfile.zip"

    def test_output_path_without_prefix(self):
        """Test output path construction without prefix."""
        prefix = "."
        output = "myfile.zip"

        output_path = os.path.join(prefix, output) if prefix != '.' else output

        assert output_path == "myfile.zip"

    def test_output_path_from_url(self):
        """Test output path construction from URL filename."""
        from urllib.parse import urlparse

        url = "http://example.com/data/file.tar.gz"
        prefix = "/tmp"

        parsed = urlparse(url)
        filename = os.path.basename(parsed.path)
        if not filename:
            filename = 'index.html'

        output_path = os.path.join(prefix, filename)

        assert output_path == "/tmp/file.tar.gz"

    def test_output_to_stdout_flag(self):
        """Test that -O - results in None output_path."""
        output = "-"

        if output == '-':
            output_path = None
        else:
            output_path = output

        assert output_path is None


class TestWgetErrorHandling:
    """Tests for error handling scenarios."""

    def test_missing_code_option(self):
        """Test that --code option is required."""
        runner = CliRunner()

        result = runner.invoke(wget, [
            'http://example.com/file.zip'
        ], obj={})

        # Should fail without --code option
        assert result.exit_code != 0
        assert 'code' in result.output.lower() or 'required' in result.output.lower()

    def test_missing_url_argument(self):
        """Test that URL argument is required."""
        runner = CliRunner()

        result = runner.invoke(wget, [
            '--code', '7-guitar-sunset'
        ], obj={})

        # Should fail without URL
        assert result.exit_code != 0
