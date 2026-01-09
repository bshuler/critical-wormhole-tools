"""Unit tests for transfer modules (SCP and SFTP)."""

import pytest
from unittest.mock import Mock, MagicMock, AsyncMock


class TestWormholeSCP:
    """Tests for WormholeSCP class."""

    def test_init(self):
        """Test SCP client initialization."""
        from wh.transfer.scp import WormholeSCP

        manager = MagicMock()
        scp = WormholeSCP(
            wormhole_manager=manager,
            username="testuser",
            password="testpass",
        )

        assert scp.manager is manager
        assert scp.username == "testuser"
        assert scp.password == "testpass"
        assert scp._ssh_client is None

    @pytest.mark.asyncio
    async def test_close(self):
        """Test close method."""
        from wh.transfer.scp import WormholeSCP

        manager = MagicMock()
        scp = WormholeSCP(manager, username="user")

        mock_client = MagicMock()
        mock_client.close = AsyncMock()
        scp._ssh_client = mock_client

        await scp.close()

        mock_client.close.assert_called_once()
        assert scp._ssh_client is None

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager."""
        from wh.transfer.scp import WormholeSCP

        manager = MagicMock()
        scp = WormholeSCP(manager, username="user", password="pass")
        scp._ensure_connected = AsyncMock()
        scp.close = AsyncMock()

        async with scp as s:
            assert s is scp
            scp._ensure_connected.assert_called_once()

        scp.close.assert_called_once()


class TestWormholeSCPInit:
    """Additional tests for WormholeSCP initialization."""

    def test_init_with_client_keys(self):
        """Test SCP client initialization with keys."""
        from wh.transfer.scp import WormholeSCP

        manager = MagicMock()
        scp = WormholeSCP(
            wormhole_manager=manager,
            username="testuser",
            client_keys=["/path/to/key"],
        )

        assert scp.client_keys == ["/path/to/key"]
        assert scp.password is None

    def test_init_with_progress_callback(self):
        """Test SCP client initialization with progress callback."""
        from wh.transfer.scp import WormholeSCP

        manager = MagicMock()
        progress_cb = MagicMock()

        scp = WormholeSCP(
            wormhole_manager=manager,
            username="testuser",
            on_progress=progress_cb,
        )

        assert scp.on_progress is progress_cb

    @pytest.mark.asyncio
    async def test_close_when_not_connected(self):
        """Test close when not connected."""
        from wh.transfer.scp import WormholeSCP

        manager = MagicMock()
        scp = WormholeSCP(manager, username="user")

        # Should not raise
        await scp.close()
        assert scp._ssh_client is None


class TestWormholeSFTP:
    """Tests for WormholeSFTP class."""

    def test_init(self):
        """Test SFTP client initialization."""
        from wh.transfer.sftp import WormholeSFTP

        manager = MagicMock()
        sftp = WormholeSFTP(
            wormhole_manager=manager,
            username="testuser",
            password="testpass",
        )

        assert sftp.manager is manager
        assert sftp.username == "testuser"
        assert sftp.password == "testpass"
        assert sftp._cwd == "/"

    @pytest.mark.asyncio
    async def test_pwd(self):
        """Test pwd returns current directory."""
        from wh.transfer.sftp import WormholeSFTP

        manager = MagicMock()
        sftp = WormholeSFTP(manager, username="user")
        sftp._cwd = "/home/user"

        result = await sftp.pwd()

        assert result == "/home/user"

    @pytest.mark.asyncio
    async def test_lpwd(self):
        """Test lpwd returns local directory."""
        from wh.transfer.sftp import WormholeSFTP
        import os

        manager = MagicMock()
        sftp = WormholeSFTP(manager, username="user")

        result = await sftp.lpwd()

        assert result == os.getcwd()

    @pytest.mark.asyncio
    async def test_lcd(self, tmp_path):
        """Test lcd changes local directory."""
        from wh.transfer.sftp import WormholeSFTP

        manager = MagicMock()
        sftp = WormholeSFTP(manager, username="user")

        result = await sftp.lcd(str(tmp_path))

        assert result == str(tmp_path)
        assert sftp._local_cwd == str(tmp_path)

    @pytest.mark.asyncio
    async def test_lcd_invalid_dir(self):
        """Test lcd raises for invalid directory."""
        from wh.transfer.sftp import WormholeSFTP

        manager = MagicMock()
        sftp = WormholeSFTP(manager, username="user")

        with pytest.raises(ValueError, match="Not a directory"):
            await sftp.lcd("/nonexistent/path")

    @pytest.mark.asyncio
    async def test_ls_not_connected(self):
        """Test ls raises when not connected."""
        from wh.transfer.sftp import WormholeSFTP

        manager = MagicMock()
        sftp = WormholeSFTP(manager, username="user")

        with pytest.raises(RuntimeError, match="Not connected"):
            await sftp.ls()

    @pytest.mark.asyncio
    async def test_execute_command_quit(self):
        """Test execute_command returns False for quit."""
        from wh.transfer.sftp import WormholeSFTP

        manager = MagicMock()
        sftp = WormholeSFTP(manager, username="user")

        assert await sftp.execute_command("quit") is False
        assert await sftp.execute_command("exit") is False
        assert await sftp.execute_command("bye") is False

    @pytest.mark.asyncio
    async def test_execute_command_help(self, capsys):
        """Test execute_command prints help."""
        from wh.transfer.sftp import WormholeSFTP

        manager = MagicMock()
        sftp = WormholeSFTP(manager, username="user")

        result = await sftp.execute_command("help")

        assert result is True
        captured = capsys.readouterr()
        assert "Available commands:" in captured.out

    @pytest.mark.asyncio
    async def test_execute_command_unknown(self, capsys):
        """Test execute_command handles unknown commands."""
        from wh.transfer.sftp import WormholeSFTP

        manager = MagicMock()
        sftp = WormholeSFTP(manager, username="user")

        result = await sftp.execute_command("unknowncommand")

        assert result is True
        captured = capsys.readouterr()
        assert "Unknown command" in captured.out

    @pytest.mark.asyncio
    async def test_close(self):
        """Test close method."""
        from wh.transfer.sftp import WormholeSFTP

        manager = MagicMock()
        sftp = WormholeSFTP(manager, username="user")

        mock_sftp = MagicMock()
        mock_sftp.exit = Mock()
        sftp._sftp = mock_sftp

        mock_client = MagicMock()
        mock_client.close = AsyncMock()
        sftp._ssh_client = mock_client

        await sftp.close()

        mock_sftp.exit.assert_called_once()
        mock_client.close.assert_called_once()
        assert sftp._sftp is None
        assert sftp._ssh_client is None


class TestWormholeSFTPAdditional:
    """Additional tests for WormholeSFTP."""

    @pytest.mark.asyncio
    async def test_close_when_not_connected(self):
        """Test close when not connected."""
        from wh.transfer.sftp import WormholeSFTP

        manager = MagicMock()
        sftp = WormholeSFTP(manager, username="user")

        # Should not raise
        await sftp.close()
        assert sftp._sftp is None
        assert sftp._ssh_client is None

    def test_init_with_client_keys(self):
        """Test SFTP client initialization with keys."""
        from wh.transfer.sftp import WormholeSFTP

        manager = MagicMock()
        sftp = WormholeSFTP(
            wormhole_manager=manager,
            username="testuser",
            client_keys=["/path/to/key"],
        )

        assert sftp.client_keys == ["/path/to/key"]

    def test_default_cwd(self):
        """Test default working directory is root."""
        from wh.transfer.sftp import WormholeSFTP

        manager = MagicMock()
        sftp = WormholeSFTP(manager, username="user")

        assert sftp._cwd == "/"

    @pytest.mark.asyncio
    async def test_execute_command_pwd(self):
        """Test execute_command for pwd."""
        from wh.transfer.sftp import WormholeSFTP

        manager = MagicMock()
        sftp = WormholeSFTP(manager, username="user")
        sftp._cwd = "/home/test"

        result = await sftp.execute_command("pwd")

        assert result is True

    @pytest.mark.asyncio
    async def test_execute_command_lpwd(self):
        """Test execute_command for lpwd."""
        from wh.transfer.sftp import WormholeSFTP

        manager = MagicMock()
        sftp = WormholeSFTP(manager, username="user")

        result = await sftp.execute_command("lpwd")

        assert result is True

    @pytest.mark.asyncio
    async def test_execute_command_lcd(self, tmp_path):
        """Test execute_command for lcd."""
        from wh.transfer.sftp import WormholeSFTP

        manager = MagicMock()
        sftp = WormholeSFTP(manager, username="user")

        result = await sftp.execute_command(f"lcd {tmp_path}")

        assert result is True

    @pytest.mark.asyncio
    async def test_execute_command_empty(self):
        """Test execute_command with empty string."""
        from wh.transfer.sftp import WormholeSFTP

        manager = MagicMock()
        sftp = WormholeSFTP(manager, username="user")

        result = await sftp.execute_command("")

        assert result is True  # Empty command should be okay

    @pytest.mark.asyncio
    async def test_cd_not_connected(self):
        """Test cd raises when not connected."""
        from wh.transfer.sftp import WormholeSFTP

        manager = MagicMock()
        sftp = WormholeSFTP(manager, username="user")

        with pytest.raises(RuntimeError, match="Not connected"):
            await sftp.cd("/home")


class TestWormholeSCPProperties:
    """Tests for WormholeSCP properties."""

    def test_manager_stored(self):
        """Test manager is stored."""
        from wh.transfer.scp import WormholeSCP

        manager = MagicMock()
        manager.wormhole_code = "7-test"

        scp = WormholeSCP(manager, username="user")

        assert scp.manager.wormhole_code == "7-test"

    def test_username_stored(self):
        """Test username is stored."""
        from wh.transfer.scp import WormholeSCP

        manager = MagicMock()
        scp = WormholeSCP(manager, username="admin")

        assert scp.username == "admin"

    def test_password_stored(self):
        """Test password is stored."""
        from wh.transfer.scp import WormholeSCP

        manager = MagicMock()
        scp = WormholeSCP(manager, username="user", password="secret")

        assert scp.password == "secret"

    def test_client_keys_stored(self):
        """Test client_keys is stored."""
        from wh.transfer.scp import WormholeSCP

        manager = MagicMock()
        scp = WormholeSCP(
            manager,
            username="user",
            client_keys=["/key1", "/key2"],
        )

        assert len(scp.client_keys) == 2
