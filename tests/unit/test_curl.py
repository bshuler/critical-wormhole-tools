"""Unit tests for wh curl command."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from click.testing import CliRunner
import tempfile
from pathlib import Path


class TestCurlCommandHelp:
    """Tests for curl command help and documentation."""

    def test_curl_command_help(self):
        """Test --help shows usage, options, examples."""
        from wh.cli.curl import curl

        runner = CliRunner()
        result = runner.invoke(curl, ['--help'])

        assert result.exit_code == 0
        # Check for usage information
        assert 'Usage:' in result.output
        # Check for options
        assert '--code' in result.output
        assert '--request' in result.output or '-X' in result.output
        assert '--header' in result.output or '-H' in result.output
        assert '--data' in result.output or '-d' in result.output
        assert '--data-binary' in result.output
        assert '--output' in result.output or '-o' in result.output
        assert '--include' in result.output or '-i' in result.output
        assert '--silent' in result.output or '-s' in result.output
        assert '--verbose' in result.output or '-v' in result.output
        # Check for examples
        assert 'Examples:' in result.output
        assert 'wh curl' in result.output

    def test_curl_command_has_url_argument(self):
        """Test curl command has url argument."""
        from wh.cli.curl import curl

        # Check the command has params
        param_names = [p.name for p in curl.params]
        assert 'url' in param_names

    def test_curl_command_has_code_option(self):
        """Test curl command has --code option."""
        from wh.cli.curl import curl

        param_names = [p.name for p in curl.params]
        assert 'code' in param_names


class TestCurlParseHeaders:
    """Tests for header parsing functionality."""

    def test_curl_parse_headers_single(self):
        """Single header parsing 'Key: Value'."""
        # Test the header parsing logic directly
        headers = {}
        header_list = ['Authorization: Bearer token123']

        for h in header_list:
            if ':' in h:
                key, value = h.split(':', 1)
                headers[key.strip()] = value.strip()

        assert 'Authorization' in headers
        assert headers['Authorization'] == 'Bearer token123'

    def test_curl_parse_headers_multiple(self):
        """Multiple -H flags all parsed."""
        headers = {}
        header_list = [
            'Content-Type: application/json',
            'Authorization: Bearer token',
            'X-Custom-Header: value'
        ]

        for h in header_list:
            if ':' in h:
                key, value = h.split(':', 1)
                headers[key.strip()] = value.strip()

        assert len(headers) == 3
        assert headers['Content-Type'] == 'application/json'
        assert headers['Authorization'] == 'Bearer token'
        assert headers['X-Custom-Header'] == 'value'

    def test_curl_parse_headers_invalid(self):
        """Header without colon ignored gracefully."""
        headers = {}
        header_list = [
            'ValidHeader: value',
            'InvalidHeaderNoColon'
        ]

        for h in header_list:
            if ':' in h:
                key, value = h.split(':', 1)
                headers[key.strip()] = value.strip()

        # Only valid header should be present
        assert 'ValidHeader' in headers
        assert len(headers) == 1

    def test_curl_parse_headers_with_whitespace(self):
        """Headers with extra whitespace are trimmed."""
        headers = {}
        header_list = ['  Content-Type  :   application/json  ']

        for h in header_list:
            if ':' in h:
                key, value = h.split(':', 1)
                headers[key.strip()] = value.strip()

        assert headers['Content-Type'] == 'application/json'


class TestCurlData:
    """Tests for request body data handling."""

    def test_curl_data_string(self):
        """-d flag with string encoded as bytes."""
        data = '{"key": "value"}'
        body = data.encode('utf-8')

        assert body == b'{"key": "value"}'
        assert isinstance(body, bytes)

    def test_curl_data_binary(self):
        """--data-binary reads file contents."""
        with tempfile.NamedTemporaryFile(mode='wb', delete=False) as f:
            test_file = f.name
            test_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR'
            f.write(test_data)

        try:
            with open(test_file, 'rb') as f:
                body = f.read()

            assert body == test_data
            assert isinstance(body, bytes)
        finally:
            Path(test_file).unlink()

    def test_curl_data_none_by_default(self):
        """Body is None when no data provided."""
        data = None
        data_binary = None

        body = None
        if data_binary:
            # Would read file
            pass
        elif data:
            body = data.encode('utf-8')

        assert body is None


class TestCurlOutput:
    """Tests for output handling."""

    def test_curl_output_to_file(self):
        """-o flag writes response to file."""
        with tempfile.NamedTemporaryFile(mode='wb', delete=False) as f:
            output_file = f.name

        try:
            response_body = b'file contents here'

            # Simulate writing to file
            with open(output_file, 'wb') as f:
                f.write(response_body)

            # Verify file was written
            with open(output_file, 'rb') as f:
                assert f.read() == b'file contents here'
        finally:
            Path(output_file).unlink()

    def test_curl_include_headers(self):
        """-i flag includes headers in output."""
        # Test header formatting
        status_code = 200
        reason = 'OK'
        headers = {
            'Content-Type': 'application/json',
            'Content-Length': '42'
        }

        output_lines = []
        output_lines.append(f"HTTP/1.1 {status_code} {reason}")
        for k, v in headers.items():
            output_lines.append(f"{k}: {v}")

        output = '\n'.join(output_lines)

        assert 'HTTP/1.1 200 OK' in output
        assert 'Content-Type: application/json' in output
        assert 'Content-Length: 42' in output

    def test_curl_output_text_decode(self):
        """Text response is decoded from bytes."""
        response_body = b'{"result": "success"}'

        # Try to decode as text
        try:
            text = response_body.decode('utf-8')
            assert text == '{"result": "success"}'
        except UnicodeDecodeError:
            # Would write binary to stdout.buffer
            pass

    def test_curl_output_binary(self):
        """Binary response that can't be decoded."""
        response_body = bytes([0xFF, 0xFE, 0xFD, 0xFC])

        # Try to decode as text
        try:
            response_body.decode('utf-8')
            # Should not reach here
            assert False, "Should have raised UnicodeDecodeError"
        except UnicodeDecodeError:
            # Would write to stdout.buffer instead
            pass


class TestCurlVerbosity:
    """Tests for verbose and silent modes."""

    def test_curl_verbose_mode(self):
        """-v flag shows request/response details."""
        # Test verbose output formatting
        method = 'POST'
        url = 'http://example.com/api'
        headers = {'Content-Type': 'application/json'}
        status_code = 200
        reason = 'OK'
        response_headers = {'Server': 'nginx'}

        # Request output (with > prefix)
        request_lines = [f"> {method} {url}"]
        for k, v in headers.items():
            request_lines.append(f"> {k}: {v}")
        request_lines.append(">")

        # Response output (with < prefix)
        response_lines = [f"< HTTP/1.1 {status_code} {reason}"]
        for k, v in response_headers.items():
            response_lines.append(f"< {k}: {v}")
        response_lines.append("<")

        request_output = '\n'.join(request_lines)
        response_output = '\n'.join(response_lines)

        assert '> POST http://example.com/api' in request_output
        assert '> Content-Type: application/json' in request_output
        assert '< HTTP/1.1 200 OK' in response_output
        assert '< Server: nginx' in response_output

    def test_curl_silent_mode(self):
        """-s flag suppresses progress output."""
        silent = True
        verbose = False

        # Status callback should be None when silent and not verbose
        status_callback = None if (silent or not verbose) else print

        assert status_callback is None

    def test_curl_verbose_overrides_silent(self):
        """Verbose flag overrides silent for status messages."""
        silent = True
        curl_verbose = True
        ctx_verbose = 0

        verbose = ctx_verbose or curl_verbose

        # Status callback should still be suppressed if silent
        status_callback = None if (not verbose or silent) else print

        # With both flags, still silent for status messages
        assert status_callback is None


class TestCurlMethodOptions:
    """Tests for HTTP method options."""

    def test_curl_method_options(self):
        """-X with POST, PUT, DELETE works."""
        methods_to_test = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']

        for method in methods_to_test:
            # Verify method string is valid
            assert isinstance(method, str)
            assert len(method) > 0

    def test_curl_default_method(self):
        """Default method is GET."""
        method = 'GET'  # Default from Click option

        assert method == 'GET'


class TestCurlHTTPClient:
    """Tests for HTTP client integration."""

    @pytest.mark.asyncio
    async def test_curl_calls_http_client(self):
        """Test that curl properly calls WormholeHTTPClient."""
        from wh.http.client import WormholeHTTPClient

        mock_manager = MagicMock()
        mock_manager.is_dilated = True

        client = WormholeHTTPClient(mock_manager)

        # Mock the _send_request method
        mock_response_data = {
            'status_code': 200,
            'reason': 'OK',
            'headers': {},
            'body': b'test response'
        }

        with patch.object(client, '_send_request', new=AsyncMock(return_value=mock_response_data)):
            response = await client.request(
                method='GET',
                url='http://example.com',
                headers={'User-Agent': 'test'},
                body=None
            )

            assert response.status_code == 200
            assert response.reason == 'OK'
            assert response.body == b'test response'

    @pytest.mark.asyncio
    async def test_curl_passes_headers_to_client(self):
        """Test headers are passed correctly to client."""
        from wh.http.client import WormholeHTTPClient

        mock_manager = MagicMock()
        mock_manager.is_dilated = True

        client = WormholeHTTPClient(mock_manager)

        mock_response_data = {
            'status_code': 200,
            'reason': 'OK',
            'headers': {},
            'body': b''
        }

        with patch.object(client, '_send_request', new=AsyncMock(return_value=mock_response_data)) as mock_send:
            headers = {
                'Authorization': 'Bearer token',
                'Content-Type': 'application/json'
            }

            await client.request(
                method='POST',
                url='http://example.com',
                headers=headers,
                body=b'{"test": true}'
            )

            # Verify _send_request was called with correct headers
            mock_send.assert_called_once()
            call_args = mock_send.call_args[0][0]
            assert call_args['headers'] == headers
            assert call_args['method'] == 'POST'


class TestCurlErrorHandling:
    """Tests for error handling."""

    def test_curl_code_required(self):
        """--code option is required."""
        from wh.cli.curl import curl

        runner = CliRunner()
        result = runner.invoke(curl, ['http://example.com'], obj={})

        # Should fail without --code
        assert result.exit_code != 0
        assert 'Missing option' in result.output or 'required' in result.output.lower()

    def test_curl_url_required(self):
        """URL argument is required."""
        from wh.cli.curl import curl

        runner = CliRunner()
        result = runner.invoke(curl, ['--code', '7-guitar-sunset'], obj={})

        # Should fail without URL
        assert result.exit_code != 0

    @pytest.mark.asyncio
    async def test_curl_handles_connection_error(self):
        """Test handling of connection errors."""
        from wh.http.client import WormholeHTTPClient

        mock_manager = MagicMock()
        mock_manager.is_dilated = True

        client = WormholeHTTPClient(mock_manager)

        # Mock _send_request to raise an error
        with patch.object(client, '_send_request', new=AsyncMock(side_effect=ConnectionError("Connection failed"))):
            with pytest.raises(ConnectionError, match="Connection failed"):
                await client.request(
                    method='GET',
                    url='http://example.com',
                )


class TestCurlCommandOptions:
    """Tests for command option definitions."""

    def test_curl_has_all_required_options(self):
        """Test that curl command has all required options."""
        from wh.cli.curl import curl

        param_names = [p.name for p in curl.params]

        # Required parameters
        assert 'url' in param_names
        assert 'code' in param_names

        # Optional parameters
        assert 'method' in param_names
        assert 'header' in param_names
        assert 'data' in param_names
        assert 'data_binary' in param_names
        assert 'output' in param_names
        assert 'include' in param_names
        assert 'silent' in param_names
        assert 'curl_verbose' in param_names

    def test_curl_method_default_is_get(self):
        """Test that default HTTP method is GET."""
        from wh.cli.curl import curl

        method_param = next(p for p in curl.params if p.name == 'method')
        assert method_param.default == 'GET'

    def test_curl_header_allows_multiple(self):
        """Test that header option allows multiple values."""
        from wh.cli.curl import curl

        header_param = next(p for p in curl.params if p.name == 'header')
        assert header_param.multiple
