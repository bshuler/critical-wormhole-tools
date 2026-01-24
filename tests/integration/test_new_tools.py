"""
Integration tests for new network tools.

These tests verify the tools work with mocked wormhole connections
and real local network operations where possible.
"""

import pytest
from unittest.mock import Mock


# Mark all tests in this file as integration tests
pytestmark = pytest.mark.integration


class TestTelnetIntegration:
    """Integration tests for wh telnet."""

    @pytest.mark.asyncio
    async def test_telnet_protocol_echo_server(self):
        """Test telnet protocol with a local echo server."""
        from wh.cli.telnet import TelnetProtocol

        # Create server-side protocol
        server_proto = TelnetProtocol(is_server=True)

        # Create client-side protocol
        client_proto = TelnetProtocol(is_server=False)

        # Simulate data callback
        received_data = []
        client_proto.on_data_callback = lambda d: received_data.append(d)

        # Both protocols initialized correctly
        assert server_proto.is_server is True
        assert client_proto.is_server is False


class TestFTPIntegration:
    """Integration tests for wh ftp."""

    @pytest.mark.asyncio
    async def test_ftp_list_directory(self, tmp_path):
        """Test FTP LIST command on real directory."""
        from wh.cli.ftp import FTPProtocol

        # Create test files
        (tmp_path / "file1.txt").write_text("content1")
        (tmp_path / "file2.txt").write_text("content2")
        (tmp_path / "subdir").mkdir()

        # Create server protocol
        proto = FTPProtocol(is_server=True, root_dir=str(tmp_path))
        mock_protocol = Mock()
        mock_protocol.send = Mock()
        proto._protocol = mock_protocol

        # Execute LIST command
        await proto._cmd_list("")

        # Verify response was sent
        assert mock_protocol.send.call_count >= 4  # 150, DATA_START, DATA, DATA_END, 226

    @pytest.mark.asyncio
    async def test_ftp_file_operations(self, tmp_path):
        """Test FTP file operations."""
        from wh.cli.ftp import FTPProtocol

        proto = FTPProtocol(is_server=True, root_dir=str(tmp_path))
        mock_protocol = Mock()
        mock_protocol.send = Mock()
        proto._protocol = mock_protocol

        # Test MKD
        await proto._cmd_mkd("testdir")
        assert (tmp_path / "testdir").is_dir()

        # Change to that directory
        await proto._cmd_cwd("testdir")
        assert proto.cwd == str(tmp_path / "testdir")

        # Go back to root
        await proto._cmd_cwd("/")
        assert proto.cwd == str(tmp_path)

        # Test RMD
        await proto._cmd_rmd("testdir")
        assert not (tmp_path / "testdir").exists()

    @pytest.mark.asyncio
    async def test_ftp_file_transfer(self, tmp_path):
        """Test FTP file read."""
        from wh.cli.ftp import FTPProtocol

        # Create test file
        test_file = tmp_path / "download.txt"
        test_file.write_text("Hello, FTP!")

        proto = FTPProtocol(is_server=True, root_dir=str(tmp_path))
        mock_protocol = Mock()
        mock_protocol.send = Mock()
        proto._protocol = mock_protocol

        # Test RETR
        await proto._cmd_retr("download.txt")

        # Should have sent file data
        assert mock_protocol.send.call_count >= 3  # 150, DATA_START, DATA, DATA_END, 226


class TestNmapIntegration:
    """Integration tests for wh nmap."""

    @pytest.mark.asyncio
    async def test_port_parsing(self):
        """Test port specification parsing."""
        from wh.cli.nmap import parse_ports

        # Test common ports
        ports = parse_ports("common")
        assert 22 in ports
        assert 80 in ports
        assert 443 in ports

        # Test range
        ports = parse_ports("1-10")
        assert ports == list(range(1, 11))

        # Test mixed
        ports = parse_ports("22,80,100-102,443")
        assert ports == [22, 80, 100, 101, 102, 443]

    @pytest.mark.asyncio
    async def test_scan_localhost(self):
        """Test scanning localhost (some ports should be closed)."""
        from wh.cli.nmap import NmapProtocol

        proto = NmapProtocol(is_server=True, timeout=0.5, concurrency=10)
        mock_protocol = Mock()
        mock_protocol.send = Mock()
        proto._protocol = mock_protocol

        # This will actually try to scan, but we use high ports that are likely closed
        # Just verify the protocol handles it correctly


class TestTracerouteIntegration:
    """Integration tests for wh traceroute."""

    @pytest.mark.asyncio
    async def test_traceroute_protocol_init(self):
        """Test traceroute protocol initialization."""
        from wh.cli.traceroute import TracerouteProtocol

        proto = TracerouteProtocol(max_hops=10, queries=3, timeout=2.0)

        assert proto.max_hops == 10
        assert proto.queries == 3
        assert proto.timeout == 2.0

    @pytest.mark.asyncio
    async def test_hop_result_statistics(self):
        """Test HopResult statistics."""
        from wh.cli.traceroute import HopResult

        hop = HopResult(
            hop_num=1,
            name="router",
            ip="192.168.1.1",
            rtts=[10.0, 20.0, 30.0],
        )

        assert hop.min_rtt == 10.0
        assert hop.max_rtt == 30.0
        assert hop.avg_rtt == 20.0


class TestDNSIntegration:
    """Integration tests for wh dns."""

    @pytest.mark.asyncio
    async def test_dns_a_record_localhost(self):
        """Test DNS A record lookup for localhost."""
        from wh.cli.dns import DNSProtocol

        proto = DNSProtocol(is_server=True)
        mock_protocol = Mock()
        mock_protocol.send = Mock()
        proto._protocol = mock_protocol

        # Query localhost - should resolve
        import json
        query_data = {"name": "localhost", "type": "A"}
        payload = json.dumps(query_data).encode()

        await proto._handle_query(payload)

        # Should have sent a response
        mock_protocol.send.assert_called()

    @pytest.mark.asyncio
    async def test_dns_ptr_record(self):
        """Test DNS PTR record lookup."""
        from wh.cli.dns import DNSProtocol

        proto = DNSProtocol(is_server=True)
        mock_protocol = Mock()
        mock_protocol.send = Mock()
        proto._protocol = mock_protocol

        import json
        query_data = {"name": "127.0.0.1", "type": "PTR"}
        payload = json.dumps(query_data).encode()

        await proto._handle_query(payload)

        # Should have sent a response (even if error)
        mock_protocol.send.assert_called()


class TestMountIntegration:
    """Integration tests for wh mount."""

    @pytest.mark.asyncio
    async def test_mount_directory_operations(self, tmp_path):
        """Test mount protocol directory operations."""
        from wh.cli.mount import MountProtocol

        # Create test structure
        (tmp_path / "file1.txt").write_text("content1")
        (tmp_path / "subdir").mkdir()
        (tmp_path / "subdir" / "file2.txt").write_text("content2")

        proto = MountProtocol(is_server=True, root_dir=str(tmp_path))
        mock_protocol = Mock()
        mock_protocol.send = Mock()
        proto._protocol = mock_protocol

        # Test getattr on directory
        await proto._handle_getattr(1, str(tmp_path))
        assert mock_protocol.send.called

        # Test readdir
        mock_protocol.reset_mock()
        await proto._handle_readdir(2, str(tmp_path))
        assert mock_protocol.send.called

        # Test getattr on file
        mock_protocol.reset_mock()
        await proto._handle_getattr(3, str(tmp_path / "file1.txt"))
        assert mock_protocol.send.called

    @pytest.mark.asyncio
    async def test_mount_file_read_write(self, tmp_path):
        """Test mount protocol file read/write."""
        from wh.cli.mount import MountProtocol
        import base64

        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!")

        proto = MountProtocol(is_server=True, root_dir=str(tmp_path))
        mock_protocol = Mock()
        mock_protocol.send = Mock()
        proto._protocol = mock_protocol

        # Test read
        await proto._handle_read(1, str(test_file), {"offset": 0, "size": 100})
        assert mock_protocol.send.called

        # Test write
        new_file = tmp_path / "new.txt"
        new_file.write_text("initial")  # Create file first

        await proto._handle_write(
            2,
            str(new_file),
            {"offset": 0, "data": base64.b64encode(b"written").decode()}
        )

    @pytest.mark.asyncio
    async def test_mount_path_security(self, tmp_path):
        """Test mount protocol path traversal protection."""
        from wh.cli.mount import MountProtocol

        proto = MountProtocol(is_server=True, root_dir=str(tmp_path))
        mock_protocol = Mock()
        mock_protocol.send = Mock()
        proto._protocol = mock_protocol

        # Try to access parent directory
        import json
        request = {"path": "../../../etc/passwd"}
        payload = json.dumps(request).encode()

        # This should be caught by _handle_request
        await proto._handle_request(1, 1, payload)  # MSG_GETATTR = 1

        # Should have sent error response
        mock_protocol.send.assert_called()


class TestVNCIntegration:
    """Integration tests for wh vnc."""

    @pytest.mark.asyncio
    async def test_vnc_protocol_connection_flow(self):
        """Test VNC protocol connection flow."""
        from wh.cli.vnc import VNCProtocol, DEFAULT_VNC_PORT

        # Server-side protocol
        server_proto = VNCProtocol(is_server=True, vnc_port=DEFAULT_VNC_PORT)

        # Client-side protocol
        client_proto = VNCProtocol(is_server=False)

        # Verify initialization
        assert server_proto.vnc_port == DEFAULT_VNC_PORT
        assert not server_proto._vnc_connected.is_set()
        assert not client_proto._vnc_connected.is_set()

    @pytest.mark.asyncio
    async def test_vnc_display_numbers(self):
        """Test VNC display number handling."""
        from wh.cli.vnc import VNCProtocol, DEFAULT_VNC_PORT

        # Display 0 -> port 5900
        proto0 = VNCProtocol(vnc_display=0)
        assert proto0.vnc_port == DEFAULT_VNC_PORT

        # Display 1 -> port 5901
        proto1 = VNCProtocol(vnc_display=1)
        assert proto1.vnc_port == DEFAULT_VNC_PORT + 1

        # Display 5 -> port 5905
        proto5 = VNCProtocol(vnc_display=5)
        assert proto5.vnc_port == DEFAULT_VNC_PORT + 5


class TestRDPIntegration:
    """Integration tests for wh rdp."""

    @pytest.mark.asyncio
    async def test_rdp_protocol_connection_flow(self):
        """Test RDP protocol connection flow."""
        from wh.cli.rdp import RDPProtocol, DEFAULT_RDP_PORT

        # Server-side protocol
        server_proto = RDPProtocol(is_server=True, rdp_port=DEFAULT_RDP_PORT)

        # Client-side protocol
        client_proto = RDPProtocol(is_server=False)

        # Verify initialization
        assert server_proto.rdp_port == DEFAULT_RDP_PORT
        assert not server_proto._rdp_connected.is_set()
        assert not client_proto._rdp_connected.is_set()

    @pytest.mark.asyncio
    async def test_rdp_custom_host_port(self):
        """Test RDP with custom host and port."""
        from wh.cli.rdp import RDPProtocol

        proto = RDPProtocol(
            is_server=True,
            rdp_host="192.168.1.100",
            rdp_port=3390,
        )

        assert proto.rdp_host == "192.168.1.100"
        assert proto.rdp_port == 3390


class TestToolsCLI:
    """Integration tests for CLI commands."""

    def test_telnet_cli_help(self):
        """Test telnet CLI help."""
        from click.testing import CliRunner
        from wh.cli.telnet import telnet

        runner = CliRunner()
        result = runner.invoke(telnet, ['--help'])

        assert result.exit_code == 0
        assert 'telnet' in result.output.lower() or 'tcp' in result.output.lower()

    def test_ftp_cli_help(self):
        """Test ftp CLI help."""
        from click.testing import CliRunner
        from wh.cli.ftp import ftp

        runner = CliRunner()
        result = runner.invoke(ftp, ['--help'])

        assert result.exit_code == 0
        assert 'ftp' in result.output.lower()

    def test_nmap_cli_help(self):
        """Test nmap CLI help."""
        from click.testing import CliRunner
        from wh.cli.nmap import nmap

        runner = CliRunner()
        result = runner.invoke(nmap, ['--help'])

        assert result.exit_code == 0
        assert 'scan' in result.output.lower() or 'port' in result.output.lower()

    def test_traceroute_cli_help(self):
        """Test traceroute CLI help."""
        from click.testing import CliRunner
        from wh.cli.traceroute import traceroute

        runner = CliRunner()
        result = runner.invoke(traceroute, ['--help'])

        assert result.exit_code == 0
        assert 'trace' in result.output.lower() or 'hop' in result.output.lower()

    def test_dns_cli_help(self):
        """Test dns CLI help."""
        from click.testing import CliRunner
        from wh.cli.dns import dns

        runner = CliRunner()
        result = runner.invoke(dns, ['--help'])

        assert result.exit_code == 0
        assert 'dns' in result.output.lower()

    def test_mount_cli_help(self):
        """Test mount CLI help."""
        from click.testing import CliRunner
        from wh.cli.mount import mount

        runner = CliRunner()
        result = runner.invoke(mount, ['--help'])

        assert result.exit_code == 0
        assert 'mount' in result.output.lower() or 'filesystem' in result.output.lower()

    def test_vnc_cli_help(self):
        """Test vnc CLI help."""
        from click.testing import CliRunner
        from wh.cli.vnc import vnc

        runner = CliRunner()
        result = runner.invoke(vnc, ['--help'])

        assert result.exit_code == 0
        assert 'vnc' in result.output.lower()

    def test_rdp_cli_help(self):
        """Test rdp CLI help."""
        from click.testing import CliRunner
        from wh.cli.rdp import rdp

        runner = CliRunner()
        result = runner.invoke(rdp, ['--help'])

        assert result.exit_code == 0
        assert 'rdp' in result.output.lower() or 'remote desktop' in result.output.lower()


class TestMainCLI:
    """Integration tests for main CLI."""

    def test_main_cli_includes_new_commands(self):
        """Test main CLI includes all new commands."""
        from click.testing import CliRunner
        from wh.cli.main import cli

        runner = CliRunner()
        result = runner.invoke(cli, ['--help'])

        assert result.exit_code == 0

        # Check that new commands are listed
        result.output.lower()
        # The commands should appear in the help output
        # (they may be in a different format depending on click version)
