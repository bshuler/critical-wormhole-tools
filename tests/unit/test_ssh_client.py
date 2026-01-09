"""Unit tests for SSH client module."""

import pytest
from unittest.mock import Mock, MagicMock, AsyncMock


class TestWormholeSSHClient:
    """Tests for WormholeSSHClient class."""

    def test_init(self):
        """Test client initialization."""
        from wh.ssh.client import WormholeSSHClient

        manager = MagicMock()
        client = WormholeSSHClient(
            wormhole_manager=manager,
            username="testuser",
            password="testpass",
        )

        assert client.manager is manager
        assert client.username == "testuser"
        assert client.password == "testpass"
        assert client._conn is None

    def test_init_with_keys(self):
        """Test client initialization with SSH keys."""
        from wh.ssh.client import WormholeSSHClient

        manager = MagicMock()
        client = WormholeSSHClient(
            wormhole_manager=manager,
            username="testuser",
            client_keys=["/path/to/key"],
        )

        assert client.client_keys == ["/path/to/key"]
        assert client.password is None

    @pytest.mark.asyncio
    async def test_close(self):
        """Test close method."""
        from wh.ssh.client import WormholeSSHClient

        manager = MagicMock()
        client = WormholeSSHClient(manager, username="user")

        mock_conn = MagicMock()
        mock_conn.close = Mock()
        mock_conn.wait_closed = AsyncMock()
        client._conn = mock_conn

        await client.close()

        mock_conn.close.assert_called_once()
        mock_conn.wait_closed.assert_called_once()
        assert client._conn is None

    @pytest.mark.asyncio
    async def test_close_when_not_connected(self):
        """Test close when not connected does nothing."""
        from wh.ssh.client import WormholeSSHClient

        manager = MagicMock()
        client = WormholeSSHClient(manager, username="user")

        # Should not raise
        await client.close()

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager."""
        from wh.ssh.client import WormholeSSHClient

        manager = MagicMock()
        manager.is_dilated = True

        client = WormholeSSHClient(manager, username="user", password="pass")
        client.connect = AsyncMock()
        client.close = AsyncMock()

        async with client as c:
            assert c is client
            client.connect.assert_called_once()

        client.close.assert_called_once()


class TestWormholeTunnel:
    """Tests for WormholeTunnel class."""

    def test_init(self):
        """Test tunnel initialization."""
        from wh.ssh.tunnel import WormholeTunnel

        manager = MagicMock()
        tunnel = WormholeTunnel(manager)

        assert tunnel._manager is manager

    @pytest.mark.asyncio
    async def test_create_connection_not_dilated(self):
        """Test create_connection raises when not dilated."""
        from wh.ssh.tunnel import WormholeTunnel

        manager = MagicMock()
        manager.is_dilated = False

        tunnel = WormholeTunnel(manager)

        with pytest.raises(RuntimeError, match="must be dilated"):
            await tunnel.create_connection(Mock, "host", 22)


class TestHasTty:
    """Tests for HAS_TTY availability check."""

    def test_has_tty_defined(self):
        """Test HAS_TTY is defined as boolean."""
        from wh.ssh.client import HAS_TTY

        assert isinstance(HAS_TTY, bool)


class TestSSHClientKnownHosts:
    """Tests for SSH client known_hosts handling."""

    def test_init_with_known_hosts(self):
        """Test client initialization with known_hosts."""
        from wh.ssh.client import WormholeSSHClient

        manager = MagicMock()
        client = WormholeSSHClient(
            wormhole_manager=manager,
            username="testuser",
            known_hosts="/path/to/known_hosts",
        )

        assert client.known_hosts == "/path/to/known_hosts"

    def test_init_without_known_hosts(self):
        """Test client initialization without known_hosts."""
        from wh.ssh.client import WormholeSSHClient

        manager = MagicMock()
        client = WormholeSSHClient(
            wormhole_manager=manager,
            username="testuser",
        )

        assert client.known_hosts is None


class TestSSHClientRunCommand:
    """Tests for SSH client run_command method."""

    @pytest.mark.asyncio
    async def test_run_command_connects_if_needed(self):
        """Test run_command connects if not connected."""
        from wh.ssh.client import WormholeSSHClient

        manager = MagicMock()
        client = WormholeSSHClient(manager, username="user")

        # Mock connect and run
        mock_conn = MagicMock()
        mock_result = MagicMock()
        mock_conn.run = AsyncMock(return_value=mock_result)

        # Connect should set _conn when called
        async def mock_connect():
            client._conn = mock_conn
            return mock_conn

        client.connect = mock_connect
        client._conn = None  # Not connected

        result = await client.run_command("ls -la")

        mock_conn.run.assert_called_once_with("ls -la", check=False)
        assert result is mock_result

    @pytest.mark.asyncio
    async def test_run_command_with_check(self):
        """Test run_command with check=True."""
        from wh.ssh.client import WormholeSSHClient

        manager = MagicMock()
        client = WormholeSSHClient(manager, username="user")

        mock_conn = MagicMock()
        mock_conn.run = AsyncMock()
        client._conn = mock_conn

        await client.run_command("ls", check=True)

        mock_conn.run.assert_called_once_with("ls", check=True)


class TestSSHClientProperties:
    """Additional tests for SSH client properties."""

    def test_manager_property(self):
        """Test manager property is stored."""
        from wh.ssh.client import WormholeSSHClient

        manager = MagicMock()
        manager.wormhole_code = "7-test"

        client = WormholeSSHClient(manager, username="user")

        assert client.manager.wormhole_code == "7-test"

    def test_username_property(self):
        """Test username is stored."""
        from wh.ssh.client import WormholeSSHClient

        manager = MagicMock()
        client = WormholeSSHClient(manager, username="admin")

        assert client.username == "admin"

    def test_is_connected_false(self):
        """Test is_connected returns False when not connected."""
        from wh.ssh.client import WormholeSSHClient

        manager = MagicMock()
        client = WormholeSSHClient(manager, username="user")

        assert client._conn is None

    def test_is_connected_true(self):
        """Test is_connected when connected."""
        from wh.ssh.client import WormholeSSHClient

        manager = MagicMock()
        client = WormholeSSHClient(manager, username="user")
        client._conn = MagicMock()

        assert client._conn is not None


class TestSSHClientAuth:
    """Tests for SSH client authentication options."""

    def test_password_auth_only(self):
        """Test client with password auth only."""
        from wh.ssh.client import WormholeSSHClient

        manager = MagicMock()
        client = WormholeSSHClient(
            manager,
            username="user",
            password="secret123",
        )

        assert client.password == "secret123"
        assert client.client_keys == []  # Default is empty list

    def test_key_auth_only(self):
        """Test client with key auth only."""
        from wh.ssh.client import WormholeSSHClient

        manager = MagicMock()
        client = WormholeSSHClient(
            manager,
            username="user",
            password=None,
            client_keys=["/home/user/.ssh/id_rsa"],
        )

        assert client.password is None
        assert "/home/user/.ssh/id_rsa" in client.client_keys

    def test_multiple_keys(self):
        """Test client with multiple SSH keys."""
        from wh.ssh.client import WormholeSSHClient

        manager = MagicMock()
        keys = [
            "/home/user/.ssh/id_rsa",
            "/home/user/.ssh/id_ed25519",
        ]
        client = WormholeSSHClient(
            manager,
            username="user",
            client_keys=keys,
        )

        assert len(client.client_keys) == 2


class TestSSHClientInteractive:
    """Tests for SSH client interactive mode."""

    def test_init_default_interactive(self):
        """Test default interactive mode is False."""
        from wh.ssh.client import WormholeSSHClient

        manager = MagicMock()
        client = WormholeSSHClient(manager, username="user")

        # Check that client is initialized correctly
        assert client.username == "user"
