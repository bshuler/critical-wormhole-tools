"""Unit tests for wh ftp command."""

import pytest
import struct
import os
from unittest.mock import Mock, patch
import asyncio

from wh.cli.ftp import (
    FTPProtocol, FileInfo,
    MSG_COMMAND, MSG_RESPONSE, MSG_DATA_START, MSG_DATA, MSG_DATA_END,
)


class TestFileInfo:
    """Tests for FileInfo dataclass."""

    def test_create_file_info(self):
        """Test creating FileInfo."""
        info = FileInfo(
            name="test.txt",
            size=1024,
            is_dir=False,
            modified="2024-01-15T10:30:00",
            permissions="644",
        )

        assert info.name == "test.txt"
        assert info.size == 1024
        assert info.is_dir is False
        assert info.modified == "2024-01-15T10:30:00"
        assert info.permissions == "644"


class TestFTPProtocol:
    """Tests for FTPProtocol class."""

    def test_init_defaults(self):
        """Test protocol initialization with defaults."""
        proto = FTPProtocol()

        assert proto.on_status is None
        assert proto.is_server is False
        assert proto.root_dir == os.path.expanduser("~")
        assert proto.cwd == proto.root_dir
        assert proto._protocol is None
        assert proto._buffer == b""
        assert not proto._done.is_set()

    def test_init_with_options(self):
        """Test protocol initialization with options."""
        on_status = Mock()
        root = "/tmp/test"

        proto = FTPProtocol(
            on_status=on_status,
            is_server=True,
            root_dir=root,
        )

        assert proto.on_status is on_status
        assert proto.is_server is True
        assert proto.root_dir == root
        assert proto.cwd == root

    def test_status_callback(self):
        """Test status callback is called."""
        on_status = Mock()
        proto = FTPProtocol(on_status=on_status)

        proto._status("test message")

        on_status.assert_called_once_with("test message")

    def test_send_message(self):
        """Test message sending."""
        proto = FTPProtocol()
        mock_protocol = Mock()
        mock_protocol.send = Mock()
        proto._protocol = mock_protocol

        proto._send_message(MSG_DATA, b"test data")

        mock_protocol.send.assert_called_once()
        sent_data = mock_protocol.send.call_args[0][0]

        # Parse header
        msg_type, data_len = struct.unpack(">BI", sent_data[:5])
        assert msg_type == MSG_DATA
        assert data_len == 9

    def test_resolve_path_absolute(self, tmp_path):
        """Test resolving absolute path."""
        root = str(tmp_path)
        proto = FTPProtocol(root_dir=root)

        resolved = proto._resolve_path(str(tmp_path / "subdir"))
        assert resolved == str(tmp_path / "subdir")

    def test_resolve_path_relative(self, tmp_path):
        """Test resolving relative path."""
        root = str(tmp_path)
        proto = FTPProtocol(root_dir=root)
        proto.cwd = root

        resolved = proto._resolve_path("subdir")
        assert resolved == str(tmp_path / "subdir")

    def test_resolve_path_security(self, tmp_path):
        """Test path resolution blocks path traversal."""
        root = str(tmp_path)
        proto = FTPProtocol(root_dir=root)

        with pytest.raises(PermissionError):
            proto._resolve_path("../../../etc/passwd")

    def test_send_response(self):
        """Test sending FTP response."""
        proto = FTPProtocol()
        mock_protocol = Mock()
        mock_protocol.send = Mock()
        proto._protocol = mock_protocol

        proto._send_response(220, "Welcome")

        mock_protocol.send.assert_called_once()
        sent_data = mock_protocol.send.call_args[0][0]

        msg_type, data_len = struct.unpack(">BI", sent_data[:5])
        assert msg_type == MSG_RESPONSE

        payload = sent_data[5:]
        code = struct.unpack(">H", payload[:2])[0]
        message = payload[2:].decode()

        assert code == 220
        assert message == "Welcome"

    def test_handle_response(self):
        """Test handling FTP response."""
        proto = FTPProtocol(is_server=False)
        proto._response_future = asyncio.get_event_loop().create_future()

        payload = struct.pack(">H", 250) + b"OK"
        proto._handle_response(payload)

        assert proto._response_future.done()
        code, message = proto._response_future.result()
        assert code == 250
        assert message == "OK"

    def test_on_data_buffering(self):
        """Test data buffering."""
        proto = FTPProtocol()

        proto._on_data(b"partial")
        assert proto._buffer == b"partial"

    def test_process_buffer_incomplete(self):
        """Test processing incomplete buffer."""
        proto = FTPProtocol()

        # Header only, no full payload
        header = struct.pack(">BI", MSG_DATA, 100)
        proto._buffer = header

        proto._process_buffer()

        assert proto._buffer == header

    def test_on_connection_lost(self):
        """Test connection lost handling."""
        proto = FTPProtocol()
        proto._response_future = asyncio.get_event_loop().create_future()

        proto._on_connection_lost(None)

        assert proto._done.is_set()
        assert proto._response_future.done()

    @pytest.mark.asyncio
    async def test_cmd_pwd(self, tmp_path):
        """Test PWD command."""
        root = str(tmp_path)
        proto = FTPProtocol(is_server=True, root_dir=root)
        mock_protocol = Mock()
        mock_protocol.send = Mock()
        proto._protocol = mock_protocol

        await proto._cmd_pwd()

        mock_protocol.send.assert_called_once()
        sent_data = mock_protocol.send.call_args[0][0]
        payload = sent_data[5:]
        code = struct.unpack(">H", payload[:2])[0]

        assert code == 257

    @pytest.mark.asyncio
    async def test_cmd_cwd(self, tmp_path):
        """Test CWD command."""
        root = str(tmp_path)
        subdir = tmp_path / "subdir"
        subdir.mkdir()

        proto = FTPProtocol(is_server=True, root_dir=root)
        mock_protocol = Mock()
        mock_protocol.send = Mock()
        proto._protocol = mock_protocol

        await proto._cmd_cwd("subdir")

        assert proto.cwd == str(subdir)

    @pytest.mark.asyncio
    async def test_cmd_list(self, tmp_path):
        """Test LIST command."""
        root = str(tmp_path)
        (tmp_path / "file1.txt").write_text("content")
        (tmp_path / "file2.txt").write_text("content2")

        proto = FTPProtocol(is_server=True, root_dir=root)
        mock_protocol = Mock()
        mock_protocol.send = Mock()
        proto._protocol = mock_protocol

        await proto._cmd_list("")

        # Should have sent multiple messages (150, DATA_START, DATA, DATA_END, 226)
        assert mock_protocol.send.call_count >= 4

    @pytest.mark.asyncio
    async def test_cmd_size(self, tmp_path):
        """Test SIZE command."""
        root = str(tmp_path)
        test_file = tmp_path / "test.txt"
        test_file.write_text("hello world")

        proto = FTPProtocol(is_server=True, root_dir=root)
        mock_protocol = Mock()
        mock_protocol.send = Mock()
        proto._protocol = mock_protocol

        await proto._cmd_size("test.txt")

        mock_protocol.send.assert_called_once()
        sent_data = mock_protocol.send.call_args[0][0]
        payload = sent_data[5:]
        code = struct.unpack(">H", payload[:2])[0]

        assert code == 213

    @pytest.mark.asyncio
    async def test_cmd_mkd(self, tmp_path):
        """Test MKD command."""
        root = str(tmp_path)
        proto = FTPProtocol(is_server=True, root_dir=root)
        mock_protocol = Mock()
        mock_protocol.send = Mock()
        proto._protocol = mock_protocol

        await proto._cmd_mkd("newdir")

        assert (tmp_path / "newdir").is_dir()

    @pytest.mark.asyncio
    async def test_cmd_dele(self, tmp_path):
        """Test DELE command."""
        root = str(tmp_path)
        test_file = tmp_path / "delete_me.txt"
        test_file.write_text("delete me")

        proto = FTPProtocol(is_server=True, root_dir=root)
        mock_protocol = Mock()
        mock_protocol.send = Mock()
        proto._protocol = mock_protocol

        await proto._cmd_dele("delete_me.txt")

        assert not test_file.exists()

    @pytest.mark.asyncio
    async def test_cmd_rmd(self, tmp_path):
        """Test RMD command."""
        root = str(tmp_path)
        test_dir = tmp_path / "remove_me"
        test_dir.mkdir()

        proto = FTPProtocol(is_server=True, root_dir=root)
        mock_protocol = Mock()
        mock_protocol.send = Mock()
        proto._protocol = mock_protocol

        await proto._cmd_rmd("remove_me")

        assert not test_dir.exists()

    @pytest.mark.asyncio
    async def test_send_command(self):
        """Test sending command."""
        proto = FTPProtocol(is_server=False)
        mock_protocol = Mock()
        mock_protocol.send = Mock()
        proto._protocol = mock_protocol

        # Simulate response
        async def set_response():
            await asyncio.sleep(0.01)
            if proto._response_future and not proto._response_future.done():
                proto._response_future.set_result((250, "OK"))

        asyncio.create_task(set_response())

        code, msg = await proto.send_command("PWD")

        assert code == 250
        assert msg == "OK"


class TestFTPProtocolMessages:
    """Tests for FTPProtocol message parsing."""

    def test_parse_command_message(self):
        """Test parsing command message."""
        proto = FTPProtocol(is_server=True)

        cmd = b"PWD"
        payload = bytes([len(cmd)]) + cmd
        header = struct.pack(">BI", MSG_COMMAND, len(payload))
        proto._buffer = header + payload

        with patch('asyncio.create_task') as mock_create_task:
            proto._process_buffer()
            mock_create_task.assert_called_once()

    def test_parse_response_message(self):
        """Test parsing response message."""
        proto = FTPProtocol(is_server=False)
        proto._response_future = asyncio.get_event_loop().create_future()

        payload = struct.pack(">H", 200) + b"OK"
        header = struct.pack(">BI", MSG_RESPONSE, len(payload))
        proto._buffer = header + payload

        proto._process_buffer()

        assert proto._response_future.done()

    def test_parse_data_start_message(self):
        """Test parsing data start message."""
        proto = FTPProtocol(is_server=False)

        header = struct.pack(">BI", MSG_DATA_START, 0)
        proto._buffer = header

        proto._process_buffer()

        assert proto._receiving_data is True
        assert proto._data_buffer == b""

    def test_parse_data_message(self):
        """Test parsing data message."""
        proto = FTPProtocol(is_server=False)
        proto._receiving_data = True
        proto._data_buffer = b""

        payload = b"file contents"
        header = struct.pack(">BI", MSG_DATA, len(payload))
        proto._buffer = header + payload

        proto._process_buffer()

        assert proto._data_buffer == b"file contents"

    def test_parse_data_end_message(self):
        """Test parsing data end message."""
        proto = FTPProtocol(is_server=False)
        proto._receiving_data = True
        proto._data_buffer = b"accumulated data"

        header = struct.pack(">BI", MSG_DATA_END, 0)
        proto._buffer = header

        proto._process_buffer()

        assert proto._receiving_data is False
