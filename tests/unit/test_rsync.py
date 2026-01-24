"""Unit tests for rsync module."""

import asyncio
import hashlib
import json
import struct
from pathlib import Path
from unittest.mock import Mock, MagicMock

import pytest


class TestFileChecksum:
    """Tests for file_checksum function."""

    def test_file_checksum(self, tmp_path):
        """Test correct MD5 hash returned for a file."""
        from wh.cli.rsync import file_checksum

        # Create a test file with known content
        test_file = tmp_path / "test.txt"
        test_content = b"Hello, world!\nThis is a test file.\n"
        test_file.write_bytes(test_content)

        # Calculate expected checksum
        expected = hashlib.md5(test_content).hexdigest()

        # Test the function
        result = file_checksum(test_file)

        assert result == expected

    def test_file_checksum_empty_file(self, tmp_path):
        """Test checksum of empty file."""
        from wh.cli.rsync import file_checksum

        empty_file = tmp_path / "empty.txt"
        empty_file.write_bytes(b"")

        result = file_checksum(empty_file)
        expected = hashlib.md5(b"").hexdigest()

        assert result == expected

    def test_file_checksum_large_file(self, tmp_path):
        """Test checksum works with files larger than block size."""
        from wh.cli.rsync import file_checksum

        large_file = tmp_path / "large.bin"
        # Create file larger than default block size (65536)
        large_content = b"x" * 100000
        large_file.write_bytes(large_content)

        result = file_checksum(large_file)
        expected = hashlib.md5(large_content).hexdigest()

        assert result == expected


class TestScanDirectory:
    """Tests for scan_directory function."""

    def test_scan_directory(self, tmp_path):
        """Test manifest generated with path, size, mtime, checksum."""
        from wh.cli.rsync import scan_directory

        # Create test file
        test_file = tmp_path / "test.txt"
        test_content = b"test content"
        test_file.write_bytes(test_content)

        # Scan directory
        manifest = scan_directory(tmp_path, tmp_path)

        # Verify manifest structure
        assert len(manifest) == 1
        assert manifest[0]["path"] == "test.txt"
        assert manifest[0]["size"] == len(test_content)
        assert "mtime" in manifest[0]
        assert manifest[0]["checksum"] == hashlib.md5(test_content).hexdigest()

    def test_scan_directory_recursive(self, tmp_path):
        """Test all nested files found."""
        from wh.cli.rsync import scan_directory

        # Create nested directory structure
        (tmp_path / "dir1").mkdir()
        (tmp_path / "dir1" / "dir2").mkdir()

        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "dir1" / "file2.txt"
        file3 = tmp_path / "dir1" / "dir2" / "file3.txt"

        file1.write_bytes(b"content1")
        file2.write_bytes(b"content2")
        file3.write_bytes(b"content3")

        # Scan directory
        manifest = scan_directory(tmp_path, tmp_path)

        # Verify all files found
        assert len(manifest) == 3

        paths = {item["path"] for item in manifest}
        assert "file1.txt" in paths
        assert str(Path("dir1") / "file2.txt") in paths
        assert str(Path("dir1") / "dir2" / "file3.txt") in paths

    def test_scan_directory_empty(self, tmp_path):
        """Test scanning empty directory."""
        from wh.cli.rsync import scan_directory

        manifest = scan_directory(tmp_path, tmp_path)

        assert manifest == []

    def test_scan_directory_ignores_directories(self, tmp_path):
        """Test that only files are included, not directories."""
        from wh.cli.rsync import scan_directory

        # Create directories and a file
        (tmp_path / "dir1").mkdir()
        (tmp_path / "dir2").mkdir()
        (tmp_path / "file.txt").write_bytes(b"content")

        manifest = scan_directory(tmp_path, tmp_path)

        # Only the file should be in manifest
        assert len(manifest) == 1
        assert manifest[0]["path"] == "file.txt"


class TestCompareManifests:
    """Tests for compare_manifests function."""

    def test_compare_manifests_new_file(self):
        """Test new file appears in to_send."""
        from wh.cli.rsync import compare_manifests

        local = [
            {"path": "file1.txt", "checksum": "abc123", "size": 100, "mtime": 1000},
            {"path": "file2.txt", "checksum": "def456", "size": 200, "mtime": 2000},
        ]
        remote = [
            {"path": "file1.txt", "checksum": "abc123", "size": 100, "mtime": 1000},
        ]

        to_send, to_delete = compare_manifests(local, remote)

        assert "file2.txt" in to_send
        assert "file1.txt" not in to_send
        assert to_delete == []

    def test_compare_manifests_changed(self):
        """Test changed checksum appears in to_send."""
        from wh.cli.rsync import compare_manifests

        local = [
            {"path": "file1.txt", "checksum": "new_checksum", "size": 100, "mtime": 1000},
        ]
        remote = [
            {"path": "file1.txt", "checksum": "old_checksum", "size": 100, "mtime": 1000},
        ]

        to_send, to_delete = compare_manifests(local, remote)

        assert "file1.txt" in to_send
        assert to_delete == []

    def test_compare_manifests_unchanged(self):
        """Test file with same checksum not in to_send."""
        from wh.cli.rsync import compare_manifests

        local = [
            {"path": "file1.txt", "checksum": "abc123", "size": 100, "mtime": 1000},
        ]
        remote = [
            {"path": "file1.txt", "checksum": "abc123", "size": 100, "mtime": 1000},
        ]

        to_send, to_delete = compare_manifests(local, remote)

        assert to_send == []
        assert to_delete == []

    def test_compare_manifests_delete(self):
        """Test extra remote files in to_delete when delete=True."""
        from wh.cli.rsync import compare_manifests

        local = [
            {"path": "file1.txt", "checksum": "abc123", "size": 100, "mtime": 1000},
        ]
        remote = [
            {"path": "file1.txt", "checksum": "abc123", "size": 100, "mtime": 1000},
            {"path": "file2.txt", "checksum": "def456", "size": 200, "mtime": 2000},
            {"path": "file3.txt", "checksum": "ghi789", "size": 300, "mtime": 3000},
        ]

        to_send, to_delete = compare_manifests(local, remote, delete=True)

        assert to_send == []
        assert "file2.txt" in to_delete
        assert "file3.txt" in to_delete
        assert "file1.txt" not in to_delete

    def test_compare_manifests_no_delete_flag(self):
        """Test extra remote files NOT in to_delete when delete=False."""
        from wh.cli.rsync import compare_manifests

        local = [
            {"path": "file1.txt", "checksum": "abc123", "size": 100, "mtime": 1000},
        ]
        remote = [
            {"path": "file1.txt", "checksum": "abc123", "size": 100, "mtime": 1000},
            {"path": "file2.txt", "checksum": "def456", "size": 200, "mtime": 2000},
        ]

        to_send, to_delete = compare_manifests(local, remote, delete=False)

        assert to_send == []
        assert to_delete == []

    def test_compare_manifests_complex_scenario(self):
        """Test complex scenario with new, changed, unchanged, and deleted files."""
        from wh.cli.rsync import compare_manifests

        local = [
            {"path": "unchanged.txt", "checksum": "aaa", "size": 100, "mtime": 1000},
            {"path": "changed.txt", "checksum": "new_bbb", "size": 200, "mtime": 2000},
            {"path": "new.txt", "checksum": "ccc", "size": 300, "mtime": 3000},
        ]
        remote = [
            {"path": "unchanged.txt", "checksum": "aaa", "size": 100, "mtime": 1000},
            {"path": "changed.txt", "checksum": "old_bbb", "size": 200, "mtime": 1500},
            {"path": "deleted.txt", "checksum": "ddd", "size": 400, "mtime": 4000},
        ]

        to_send, to_delete = compare_manifests(local, remote, delete=True)

        assert "changed.txt" in to_send
        assert "new.txt" in to_send
        assert "unchanged.txt" not in to_send
        assert "deleted.txt" in to_delete


class TestRsyncProtocol:
    """Tests for RsyncProtocol class."""

    def test_rsync_protocol_init(self):
        """Test RsyncProtocol state initialized."""
        from wh.cli.rsync import RsyncProtocol

        on_status = Mock()
        on_progress = Mock()

        protocol = RsyncProtocol(on_status=on_status, on_progress=on_progress)

        assert protocol.on_status is on_status
        assert protocol.on_progress is on_progress
        assert protocol._protocol is None
        assert protocol._buffer == b""
        assert not protocol._done.is_set()
        assert protocol._current_file is None
        assert protocol._current_file_handle is None
        assert protocol._current_file_size == 0
        assert protocol._current_file_received == 0
        assert protocol._files_transferred == 0
        assert protocol._bytes_transferred == 0
        assert protocol._manifest_future is None
        assert protocol._request_future is None

    @pytest.mark.asyncio
    async def test_rsync_send_manifest(self):
        """Test JSON serialized and sent."""
        from wh.cli.rsync import RsyncProtocol, MSG_MANIFEST

        protocol = RsyncProtocol()
        mock_stream_protocol = MagicMock()
        protocol._protocol = mock_stream_protocol

        manifest = [
            {"path": "file1.txt", "checksum": "abc123", "size": 100, "mtime": 1000},
            {"path": "file2.txt", "checksum": "def456", "size": 200, "mtime": 2000},
        ]

        await protocol.send_manifest(manifest)

        # Verify send was called
        mock_stream_protocol.send.assert_called_once()

        # Verify the message format
        sent_data = mock_stream_protocol.send.call_args[0][0]
        msg_type = struct.unpack(">B", sent_data[:1])[0]
        data_len = struct.unpack(">I", sent_data[1:5])[0]
        payload = sent_data[5:]

        assert msg_type == MSG_MANIFEST
        assert len(payload) == data_len
        assert json.loads(payload.decode()) == manifest

    @pytest.mark.asyncio
    async def test_rsync_receive_manifest(self):
        """Test receiving manifest via _handle_manifest."""
        from wh.cli.rsync import RsyncProtocol, MSG_MANIFEST

        protocol = RsyncProtocol()
        mock_stream_protocol = MagicMock()
        protocol._protocol = mock_stream_protocol

        manifest = [
            {"path": "file1.txt", "checksum": "abc123", "size": 100, "mtime": 1000},
        ]

        # Start receiving manifest
        receive_task = asyncio.create_task(protocol.receive_manifest())

        # Give the future time to be created
        await asyncio.sleep(0.01)

        # Simulate receiving manifest data
        payload = json.dumps(manifest).encode()
        header = struct.pack(">BI", MSG_MANIFEST, len(payload))
        protocol._on_data(header + payload)

        # Wait for result
        result = await receive_task

        assert result == manifest

    @pytest.mark.asyncio
    async def test_rsync_file_transfer(self, tmp_path):
        """Test file data written correctly."""
        from wh.cli.rsync import RsyncProtocol, MSG_FILE_START, MSG_FILE_DATA, MSG_FILE_END

        # Change to tmp_path for file operations
        import os
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            protocol = RsyncProtocol()
            mock_stream_protocol = MagicMock()
            protocol._protocol = mock_stream_protocol

            # Simulate receiving file
            file_path = "test_received.txt"
            file_content = b"This is the file content."

            # Send FILE_START message
            path_bytes = file_path.encode()
            file_size = len(file_content)
            start_payload = struct.pack(">H", len(path_bytes)) + path_bytes + struct.pack(">Q", file_size)
            start_header = struct.pack(">BI", MSG_FILE_START, len(start_payload))
            protocol._on_data(start_header + start_payload)

            # Send FILE_DATA message
            data_header = struct.pack(">BI", MSG_FILE_DATA, len(file_content))
            protocol._on_data(data_header + file_content)

            # Send FILE_END message
            end_header = struct.pack(">BI", MSG_FILE_END, 0)
            protocol._on_data(end_header)

            # Verify file was written
            received_file = tmp_path / file_path
            assert received_file.exists()
            assert received_file.read_bytes() == file_content

            # Verify statistics
            assert protocol._files_transferred == 1
            assert protocol._bytes_transferred == len(file_content)

        finally:
            os.chdir(original_cwd)

    def test_rsync_file_end(self):
        """Test file handle closed and counter incremented."""
        from wh.cli.rsync import RsyncProtocol

        protocol = RsyncProtocol()

        # Set up current file transfer state
        mock_handle = MagicMock()
        protocol._current_file_handle = mock_handle
        protocol._current_file = Path("test.txt")
        protocol._files_transferred = 5

        # Call _handle_file_end
        protocol._handle_file_end()

        # Verify handle was closed
        mock_handle.close.assert_called_once()

        # Verify state was reset
        assert protocol._current_file_handle is None
        assert protocol._current_file is None
        assert protocol._files_transferred == 6

    def test_rsync_file_end_no_handle(self):
        """Test _handle_file_end when no file handle exists."""
        from wh.cli.rsync import RsyncProtocol

        protocol = RsyncProtocol()
        protocol._current_file_handle = None
        protocol._files_transferred = 5

        # Should not raise
        protocol._handle_file_end()

        # Counter should not increment if no handle
        assert protocol._files_transferred == 5

    @pytest.mark.asyncio
    async def test_rsync_send_file(self, tmp_path):
        """Test sending a file via send_file."""
        from wh.cli.rsync import RsyncProtocol, MSG_FILE_START, MSG_FILE_END

        protocol = RsyncProtocol()
        mock_stream_protocol = MagicMock()
        protocol._protocol = mock_stream_protocol

        # Create a test file
        test_file = tmp_path / "send_test.txt"
        test_content = b"x" * 40000  # Larger than chunk size to test chunking
        test_file.write_bytes(test_content)

        await protocol.send_file(test_file, "send_test.txt")

        # Verify messages were sent
        assert mock_stream_protocol.send.call_count >= 3  # At least START, DATA, END

        calls = mock_stream_protocol.send.call_args_list

        # Verify first call is FILE_START
        first_msg = calls[0][0][0]
        msg_type = struct.unpack(">B", first_msg[:1])[0]
        assert msg_type == MSG_FILE_START

        # Verify last call is FILE_END
        last_msg = calls[-1][0][0]
        msg_type = struct.unpack(">B", last_msg[:1])[0]
        assert msg_type == MSG_FILE_END

        # Verify file was counted
        assert protocol._files_transferred == 1
        assert protocol._bytes_transferred == len(test_content)

    @pytest.mark.asyncio
    async def test_rsync_send_request(self):
        """Test sending file request."""
        from wh.cli.rsync import RsyncProtocol, MSG_REQUEST

        protocol = RsyncProtocol()
        mock_stream_protocol = MagicMock()
        protocol._protocol = mock_stream_protocol

        files = ["file1.txt", "file2.txt", "dir/file3.txt"]

        await protocol.send_request(files)

        # Verify send was called
        mock_stream_protocol.send.assert_called_once()

        # Verify the message format
        sent_data = mock_stream_protocol.send.call_args[0][0]
        msg_type = struct.unpack(">B", sent_data[:1])[0]
        data_len = struct.unpack(">I", sent_data[1:5])[0]
        payload = sent_data[5:]

        assert msg_type == MSG_REQUEST
        assert len(payload) == data_len
        assert json.loads(payload.decode()) == files

    @pytest.mark.asyncio
    async def test_rsync_send_delete(self):
        """Test sending delete request."""
        from wh.cli.rsync import RsyncProtocol, MSG_DELETE

        protocol = RsyncProtocol()
        mock_stream_protocol = MagicMock()
        protocol._protocol = mock_stream_protocol

        files = ["file1.txt", "file2.txt"]

        await protocol.send_delete(files)

        # Verify send was called
        mock_stream_protocol.send.assert_called_once()

        # Verify the message format
        sent_data = mock_stream_protocol.send.call_args[0][0]
        msg_type = struct.unpack(">B", sent_data[:1])[0]
        data_len = struct.unpack(">I", sent_data[1:5])[0]
        payload = sent_data[5:]

        assert msg_type == MSG_DELETE
        assert len(payload) == data_len
        assert json.loads(payload.decode()) == files

    @pytest.mark.asyncio
    async def test_rsync_send_done(self):
        """Test sending done signal."""
        from wh.cli.rsync import RsyncProtocol, MSG_DONE

        protocol = RsyncProtocol()
        mock_stream_protocol = MagicMock()
        protocol._protocol = mock_stream_protocol

        await protocol.send_done()

        # Verify send was called
        mock_stream_protocol.send.assert_called_once()

        # Verify the message format
        sent_data = mock_stream_protocol.send.call_args[0][0]
        msg_type = struct.unpack(">B", sent_data[:1])[0]

        assert msg_type == MSG_DONE

    def test_rsync_handle_delete(self, tmp_path):
        """Test handling delete request."""
        from wh.cli.rsync import RsyncProtocol
        import os

        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            protocol = RsyncProtocol()

            # Create test files
            file1 = tmp_path / "file1.txt"
            file2 = tmp_path / "file2.txt"
            file1.write_bytes(b"content1")
            file2.write_bytes(b"content2")

            assert file1.exists()
            assert file2.exists()

            # Send delete message
            files = ["file1.txt"]
            payload = json.dumps(files).encode()
            protocol._handle_delete(payload)

            # Verify file was deleted
            assert not file1.exists()
            assert file2.exists()

        finally:
            os.chdir(original_cwd)

    def test_rsync_handle_done(self):
        """Test handling done signal."""
        from wh.cli.rsync import RsyncProtocol

        protocol = RsyncProtocol()

        assert not protocol._done.is_set()

        protocol._handle_done()

        assert protocol._done.is_set()

    def test_rsync_on_connection_lost(self):
        """Test connection lost sets done event."""
        from wh.cli.rsync import RsyncProtocol

        protocol = RsyncProtocol()

        assert not protocol._done.is_set()

        protocol._on_connection_lost(None)

        assert protocol._done.is_set()

    def test_rsync_status_callback(self):
        """Test status callback is called."""
        from wh.cli.rsync import RsyncProtocol

        statuses = []
        protocol = RsyncProtocol(on_status=lambda m: statuses.append(m))

        protocol._status("Test message")

        assert "Test message" in statuses

    def test_rsync_progress_callback(self):
        """Test progress callback is called."""
        from wh.cli.rsync import RsyncProtocol

        progress_calls = []

        def on_progress(filename, current, total):
            progress_calls.append((filename, current, total))

        protocol = RsyncProtocol(on_progress=on_progress)

        protocol._progress("test.txt", 50, 100)

        assert len(progress_calls) == 1
        assert progress_calls[0] == ("test.txt", 50, 100)

    def test_rsync_file_data_updates_progress(self):
        """Test _handle_file_data updates bytes transferred and progress."""
        from wh.cli.rsync import RsyncProtocol

        progress_calls = []

        def on_progress(filename, current, total):
            progress_calls.append((filename, current, total))

        protocol = RsyncProtocol(on_progress=on_progress)

        # Set up file transfer state
        mock_handle = MagicMock()
        protocol._current_file_handle = mock_handle
        protocol._current_file = Path("test.txt")
        protocol._current_file_size = 1000
        protocol._current_file_received = 0
        protocol._bytes_transferred = 0

        # Simulate receiving data
        data_chunk = b"x" * 100
        protocol._handle_file_data(data_chunk)

        # Verify handle write was called
        mock_handle.write.assert_called_once_with(data_chunk)

        # Verify counters updated
        assert protocol._current_file_received == 100
        assert protocol._bytes_transferred == 100

        # Verify progress callback
        assert len(progress_calls) == 1
        assert progress_calls[0] == ("test.txt", 100, 1000)

    def test_rsync_buffer_processing_partial_message(self):
        """Test buffer processing handles partial messages."""
        from wh.cli.rsync import RsyncProtocol, MSG_DONE

        protocol = RsyncProtocol()

        # Create a message
        header = struct.pack(">BI", MSG_DONE, 0)

        # Send only part of the header
        protocol._on_data(header[:3])

        # Done should not be set yet
        assert not protocol._done.is_set()

        # Send the rest
        protocol._on_data(header[3:])

        # Now done should be set
        assert protocol._done.is_set()

    def test_rsync_multiple_messages_in_buffer(self):
        """Test processing multiple messages in one buffer."""
        from wh.cli.rsync import RsyncProtocol, MSG_DONE

        protocol = RsyncProtocol()

        # Create multiple DONE messages
        msg1 = struct.pack(">BI", MSG_DONE, 0)
        msg2 = struct.pack(">BI", MSG_DONE, 0)

        # Send both at once
        protocol._on_data(msg1 + msg2)

        # Done should be set (either message would set it)
        assert protocol._done.is_set()

    @pytest.mark.asyncio
    async def test_rsync_file_start_creates_directories(self, tmp_path):
        """Test _handle_file_start creates parent directories."""
        from wh.cli.rsync import RsyncProtocol, MSG_FILE_START
        import os

        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            protocol = RsyncProtocol()

            # Create file path with nested directories
            file_path = "dir1/dir2/dir3/test.txt"
            path_bytes = file_path.encode()
            file_size = 100

            # Create FILE_START payload
            payload = struct.pack(">H", len(path_bytes)) + path_bytes + struct.pack(">Q", file_size)
            header = struct.pack(">BI", MSG_FILE_START, len(payload))

            protocol._on_data(header + payload)

            # Verify directories were created
            assert (tmp_path / "dir1" / "dir2" / "dir3").exists()
            assert protocol._current_file == Path(file_path)
            assert protocol._current_file_size == file_size

            # Clean up open file handle
            if protocol._current_file_handle:
                protocol._current_file_handle.close()

        finally:
            os.chdir(original_cwd)
