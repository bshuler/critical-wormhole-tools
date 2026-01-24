"""Unit tests for wh mount command."""

import pytest
import struct
import json
import os
import errno
from unittest.mock import Mock, patch
import asyncio

from wh.cli.mount import (
    MountProtocol, FileAttr, check_fuse_available,
    MSG_GETATTR, MSG_RESPONSE, MSG_ERROR,
)


class TestFileAttr:
    """Tests for FileAttr dataclass."""

    def test_create_file_attr(self):
        """Test creating FileAttr."""
        attr = FileAttr(
            mode=0o644,
            size=1024,
            atime=1705334400.0,
            mtime=1705334400.0,
            ctime=1705334400.0,
            uid=1000,
            gid=1000,
            nlink=1,
        )

        assert attr.mode == 0o644
        assert attr.size == 1024
        assert attr.uid == 1000
        assert attr.nlink == 1


class TestCheckFuseAvailable:
    """Tests for check_fuse_available function."""

    def test_fuse_not_available(self):
        """Test when FUSE is not available."""
        with patch.dict('sys.modules', {'fuse': None}):
            # Force import to fail
            import sys
            if 'fuse' in sys.modules:
                del sys.modules['fuse']

            result = check_fuse_available()
            # Should return False when import fails
            assert isinstance(result, bool)


class TestMountProtocol:
    """Tests for MountProtocol class."""

    def test_init_defaults(self):
        """Test protocol initialization with defaults."""
        proto = MountProtocol()

        assert proto.on_status is None
        assert proto.is_server is False
        assert proto.root_dir == os.path.expanduser("~")
        assert proto._protocol is None
        assert proto._buffer == b""
        assert not proto._done.is_set()

    def test_init_with_options(self):
        """Test protocol initialization with options."""
        on_status = Mock()
        root = "/tmp/test"

        proto = MountProtocol(
            on_status=on_status,
            is_server=True,
            root_dir=root,
        )

        assert proto.on_status is on_status
        assert proto.is_server is True
        assert proto.root_dir == root

    def test_status_callback(self):
        """Test status callback."""
        on_status = Mock()
        proto = MountProtocol(on_status=on_status)

        proto._status("mounting...")

        on_status.assert_called_once_with("mounting...")

    def test_send_message(self):
        """Test message sending."""
        proto = MountProtocol()
        mock_protocol = Mock()
        mock_protocol.send = Mock()
        proto._protocol = mock_protocol

        proto._send_message(MSG_GETATTR, 1, b'{"path": "/"}')

        mock_protocol.send.assert_called_once()
        sent_data = mock_protocol.send.call_args[0][0]
        msg_type, request_id, data_len = struct.unpack(">BII", sent_data[:9])
        assert msg_type == MSG_GETATTR
        assert request_id == 1

    def test_resolve_path_absolute(self, tmp_path):
        """Test resolving path with leading slash (treated as relative to root)."""
        root = str(tmp_path)
        proto = MountProtocol(root_dir=root)

        # Leading slash is stripped, so /subdir is treated as subdir
        resolved = proto._resolve_path("/subdir")
        assert resolved == str(tmp_path / "subdir")

    def test_resolve_path_relative(self, tmp_path):
        """Test resolving relative path within root."""
        root = str(tmp_path)
        proto = MountProtocol(root_dir=root)

        resolved = proto._resolve_path("subdir")
        assert resolved == str(tmp_path / "subdir")

    def test_resolve_path_root(self, tmp_path):
        """Test resolving root path."""
        root = str(tmp_path)
        proto = MountProtocol(root_dir=root)

        resolved = proto._resolve_path("/")
        assert resolved == root

    def test_resolve_path_security(self, tmp_path):
        """Test path traversal is blocked."""
        root = str(tmp_path)
        proto = MountProtocol(root_dir=root)

        with pytest.raises(PermissionError):
            proto._resolve_path("../../../etc/passwd")

    def test_send_response(self):
        """Test sending response."""
        proto = MountProtocol()
        mock_protocol = Mock()
        mock_protocol.send = Mock()
        proto._protocol = mock_protocol

        proto._send_response(1, {"success": True})

        mock_protocol.send.assert_called_once()
        sent_data = mock_protocol.send.call_args[0][0]
        msg_type, _, _ = struct.unpack(">BII", sent_data[:9])
        assert msg_type == MSG_RESPONSE

    def test_send_error(self):
        """Test sending error."""
        proto = MountProtocol()
        mock_protocol = Mock()
        mock_protocol.send = Mock()
        proto._protocol = mock_protocol

        proto._send_error(1, errno.ENOENT, "File not found")

        mock_protocol.send.assert_called_once()
        sent_data = mock_protocol.send.call_args[0][0]
        msg_type, _, _ = struct.unpack(">BII", sent_data[:9])
        assert msg_type == MSG_ERROR

    def test_handle_response_success(self):
        """Test handling success response."""
        proto = MountProtocol(is_server=False)
        future = asyncio.get_event_loop().create_future()
        proto._pending_requests[1] = future

        payload = json.dumps({"success": True}).encode()
        proto._handle_response(MSG_RESPONSE, 1, payload)

        assert future.done()
        assert future.result()["success"] is True

    def test_handle_response_error(self):
        """Test handling error response."""
        proto = MountProtocol(is_server=False)
        future = asyncio.get_event_loop().create_future()
        proto._pending_requests[1] = future

        payload = json.dumps({"error": errno.ENOENT, "message": "Not found"}).encode()
        proto._handle_response(MSG_ERROR, 1, payload)

        assert future.done()
        with pytest.raises(OSError):
            future.result()

    def test_on_connection_lost(self):
        """Test connection lost handling."""
        proto = MountProtocol()
        future = asyncio.get_event_loop().create_future()
        proto._pending_requests[1] = future

        proto._on_connection_lost(None)

        assert proto._done.is_set()
        assert future.done()


class TestMountProtocolOperations:
    """Tests for MountProtocol filesystem operations."""

    @pytest.mark.asyncio
    async def test_handle_getattr(self, tmp_path):
        """Test getattr operation."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("hello")

        proto = MountProtocol(is_server=True, root_dir=str(tmp_path))
        mock_protocol = Mock()
        mock_protocol.send = Mock()
        proto._protocol = mock_protocol

        await proto._handle_getattr(1, str(test_file))

        mock_protocol.send.assert_called_once()
        sent_data = mock_protocol.send.call_args[0][0]
        msg_type, _, _ = struct.unpack(">BII", sent_data[:9])
        assert msg_type == MSG_RESPONSE

    @pytest.mark.asyncio
    async def test_handle_readdir(self, tmp_path):
        """Test readdir operation."""
        (tmp_path / "file1.txt").write_text("1")
        (tmp_path / "file2.txt").write_text("2")

        proto = MountProtocol(is_server=True, root_dir=str(tmp_path))
        mock_protocol = Mock()
        mock_protocol.send = Mock()
        proto._protocol = mock_protocol

        await proto._handle_readdir(1, str(tmp_path))

        mock_protocol.send.assert_called_once()
        sent_data = mock_protocol.send.call_args[0][0]
        payload = sent_data[9:]
        response = json.loads(payload.decode())

        assert "entries" in response
        assert "." in response["entries"]
        assert ".." in response["entries"]
        assert "file1.txt" in response["entries"]

    @pytest.mark.asyncio
    async def test_handle_read(self, tmp_path):
        """Test read operation."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("hello world")

        proto = MountProtocol(is_server=True, root_dir=str(tmp_path))
        mock_protocol = Mock()
        mock_protocol.send = Mock()
        proto._protocol = mock_protocol

        await proto._handle_read(1, str(test_file), {"offset": 0, "size": 5})

        mock_protocol.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_mkdir(self, tmp_path):
        """Test mkdir operation."""
        proto = MountProtocol(is_server=True, root_dir=str(tmp_path))
        mock_protocol = Mock()
        mock_protocol.send = Mock()
        proto._protocol = mock_protocol

        await proto._handle_mkdir(1, str(tmp_path / "newdir"), {"mode": 0o755})

        assert (tmp_path / "newdir").is_dir()

    @pytest.mark.asyncio
    async def test_handle_unlink(self, tmp_path):
        """Test unlink operation."""
        test_file = tmp_path / "delete_me.txt"
        test_file.write_text("delete")

        proto = MountProtocol(is_server=True, root_dir=str(tmp_path))
        mock_protocol = Mock()
        mock_protocol.send = Mock()
        proto._protocol = mock_protocol

        await proto._handle_unlink(1, str(test_file))

        assert not test_file.exists()

    @pytest.mark.asyncio
    async def test_handle_rmdir(self, tmp_path):
        """Test rmdir operation."""
        test_dir = tmp_path / "remove_me"
        test_dir.mkdir()

        proto = MountProtocol(is_server=True, root_dir=str(tmp_path))
        mock_protocol = Mock()
        mock_protocol.send = Mock()
        proto._protocol = mock_protocol

        await proto._handle_rmdir(1, str(test_dir))

        assert not test_dir.exists()

    @pytest.mark.asyncio
    async def test_handle_truncate(self, tmp_path):
        """Test truncate operation."""
        test_file = tmp_path / "truncate.txt"
        test_file.write_text("hello world long content")

        proto = MountProtocol(is_server=True, root_dir=str(tmp_path))
        mock_protocol = Mock()
        mock_protocol.send = Mock()
        proto._protocol = mock_protocol

        await proto._handle_truncate(1, str(test_file), {"length": 5})

        assert test_file.read_text() == "hello"


class TestMountProtocolClient:
    """Tests for MountProtocol client-side operations."""

    @pytest.mark.asyncio
    async def test_getattr_client(self):
        """Test client getattr."""
        proto = MountProtocol(is_server=False)
        mock_protocol = Mock()
        mock_protocol.send = Mock()
        proto._protocol = mock_protocol

        # Simulate response
        async def simulate_response():
            await asyncio.sleep(0.01)
            if 1 in proto._pending_requests:
                proto._pending_requests[1].set_result({
                    "mode": 0o644,
                    "size": 100,
                    "atime": 1705334400.0,
                    "mtime": 1705334400.0,
                    "ctime": 1705334400.0,
                })

        asyncio.create_task(simulate_response())

        attr = await proto.getattr("/test.txt")

        assert attr.mode == 0o644
        assert attr.size == 100

    @pytest.mark.asyncio
    async def test_readdir_client(self):
        """Test client readdir."""
        proto = MountProtocol(is_server=False)
        mock_protocol = Mock()
        mock_protocol.send = Mock()
        proto._protocol = mock_protocol

        async def simulate_response():
            await asyncio.sleep(0.01)
            if 1 in proto._pending_requests:
                proto._pending_requests[1].set_result({
                    "entries": [".", "..", "file1.txt", "file2.txt"]
                })

        asyncio.create_task(simulate_response())

        entries = await proto.readdir("/")

        assert "file1.txt" in entries
        assert "file2.txt" in entries

    @pytest.mark.asyncio
    async def test_mkdir_client(self):
        """Test client mkdir."""
        proto = MountProtocol(is_server=False)
        mock_protocol = Mock()
        mock_protocol.send = Mock()
        proto._protocol = mock_protocol

        async def simulate_response():
            await asyncio.sleep(0.01)
            if 1 in proto._pending_requests:
                proto._pending_requests[1].set_result({"success": True})

        asyncio.create_task(simulate_response())

        await proto.mkdir("/newdir", 0o755)

        mock_protocol.send.assert_called_once()
