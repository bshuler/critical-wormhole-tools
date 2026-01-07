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
