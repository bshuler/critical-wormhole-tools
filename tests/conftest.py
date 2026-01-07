"""
Pytest configuration and fixtures for wh tests.

Provides mock wormhole objects, in-memory transports, and
other test utilities.
"""

import pytest
import asyncio
from unittest.mock import Mock, MagicMock, AsyncMock
from typing import Tuple, Any


@pytest.fixture
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_wormhole():
    """
    Mock wormhole object for unit testing.

    Simulates the wormhole API without network.
    """
    wormhole = MagicMock()
    wormhole.allocate_code = Mock(return_value=MagicMock())
    wormhole.get_code = Mock(return_value=MagicMock())
    wormhole.set_code = Mock()
    wormhole.get_versions = Mock(return_value=MagicMock())
    wormhole.dilate = Mock(return_value=MagicMock())
    wormhole.close = Mock(return_value=MagicMock())
    wormhole.send_message = Mock(return_value=MagicMock())
    wormhole.get_message = Mock(return_value=MagicMock())

    # Make Deferreds return proper values
    code_deferred = MagicMock()
    code_deferred.addCallbacks = lambda cb, eb: cb("7-guitar-sunset")

    versions_deferred = MagicMock()
    versions_deferred.addCallbacks = lambda cb, eb: cb({"wh.tools/v1": {}})

    dilate_deferred = MagicMock()
    mock_endpoints = (Mock(), Mock(), Mock())
    dilate_deferred.addCallbacks = lambda cb, eb: cb(mock_endpoints)

    close_deferred = MagicMock()
    close_deferred.addCallbacks = lambda cb, eb: cb(None)

    wormhole.get_code.return_value = code_deferred
    wormhole.get_versions.return_value = versions_deferred
    wormhole.dilate.return_value = dilate_deferred
    wormhole.close.return_value = close_deferred

    return wormhole


@pytest.fixture
def mock_transport():
    """Mock Twisted transport for protocol testing."""
    transport = MagicMock()
    transport.write = Mock()
    transport.loseConnection = Mock()
    transport.loseWriteConnection = Mock()
    transport.abortConnection = Mock()
    return transport


@pytest.fixture
def in_memory_pipe() -> Tuple[Any, Any]:
    """
    Creates a pair of connected in-memory transports.

    Useful for testing protocols without network.
    """
    class InMemoryTransport:
        def __init__(self):
            self.peer = None
            self.received: list = []
            self.protocol = None
            self._closed = False

        def write(self, data: bytes) -> None:
            if self.peer and self.peer.protocol and not self._closed:
                self.peer.protocol.dataReceived(data)

        def loseConnection(self) -> None:
            self._closed = True
            if self.protocol:
                self.protocol.connectionLost(None)

        def loseWriteConnection(self) -> None:
            pass

        def connect(self, other: "InMemoryTransport") -> None:
            self.peer = other
            other.peer = self

        def get_extra_info(self, name: str, default=None):
            if name == 'peername':
                return ('memory', 0)
            return default

    t1 = InMemoryTransport()
    t2 = InMemoryTransport()
    t1.connect(t2)
    return t1, t2


@pytest.fixture
def mock_ssh_connection():
    """Mock AsyncSSH connection for SSH tests."""
    conn = MagicMock()
    conn.run = AsyncMock(return_value=MagicMock(
        stdout="test output",
        stderr="",
        returncode=0,
    ))
    conn.create_process = MagicMock()
    conn.start_sftp_client = AsyncMock()
    conn.close = Mock()
    conn.wait_closed = AsyncMock()
    return conn


@pytest.fixture
def mock_sftp_client():
    """Mock SFTP client for SFTP tests."""
    sftp = MagicMock()
    sftp.readdir = AsyncMock(return_value=[])
    sftp.stat = AsyncMock()
    sftp.getcwd = AsyncMock(return_value="/home/user")
    sftp.get = AsyncMock()
    sftp.put = AsyncMock()
    sftp.mkdir = AsyncMock()
    sftp.remove = AsyncMock()
    sftp.rmdir = AsyncMock()
    sftp.exit = Mock()
    return sftp


@pytest.fixture
def temp_files(tmp_path):
    """Create temporary test files."""
    # Create a small text file
    small_txt = tmp_path / "small.txt"
    small_txt.write_text("Hello, World!\n")

    # Create a binary file
    binary_bin = tmp_path / "binary.bin"
    binary_bin.write_bytes(bytes(range(256)))

    # Create a directory with files
    test_dir = tmp_path / "test_dir"
    test_dir.mkdir()
    (test_dir / "file1.txt").write_text("File 1")
    (test_dir / "file2.txt").write_text("File 2")

    return {
        "small_txt": str(small_txt),
        "binary_bin": str(binary_bin),
        "test_dir": str(test_dir),
        "tmp_path": str(tmp_path),
    }


@pytest.fixture
def mock_wormhole_manager():
    """
    Mock WormholeManager for testing commands.

    Provides a fully mocked manager that doesn't require network.
    """
    manager = MagicMock()
    manager.code = "7-guitar-sunset"
    manager.is_dilated = True

    # Mock DilatedWormhole object
    mock_dilated_wormhole = MagicMock()
    mock_dilated_wormhole.connector_for = MagicMock(return_value=MagicMock())
    mock_dilated_wormhole.listener_for = MagicMock(return_value=MagicMock())

    manager.dilated_wormhole = mock_dilated_wormhole
    manager.connector_for = MagicMock(return_value=MagicMock())
    manager.listener_for = MagicMock(return_value=MagicMock())

    # Async methods
    manager.create_and_allocate_code = AsyncMock(return_value="7-guitar-sunset")
    manager.create_and_set_code = AsyncMock()
    manager.dilate = AsyncMock(return_value=mock_dilated_wormhole)
    manager.verify_connection = AsyncMock(return_value={"wh.tools/v1": {}})
    manager.close = AsyncMock()

    return manager


# Mark for integration tests
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers",
        "integration: marks tests as integration tests (may require network)"
    )
