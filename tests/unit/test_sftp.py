"""Unit tests for SFTP transfer module."""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock
import pytest


class TestWormholeSFTPInit:
    """Tests for WormholeSFTP initialization."""

    def test_init_with_required_args(self):
        """Test WormholeSFTP initialization with required args."""
        from wh.transfer.sftp import WormholeSFTP

        manager = MagicMock()
        sftp = WormholeSFTP(manager, username="testuser")

        assert sftp.manager is manager
        assert sftp.username == "testuser"
        assert sftp.password is None
        assert sftp._sftp is None
        assert sftp._cwd == "/"

    def test_init_with_password(self):
        """Test WormholeSFTP with username and password."""
        from wh.transfer.sftp import WormholeSFTP

        manager = MagicMock()
        sftp = WormholeSFTP(
            manager,
            username="testuser",
            password="testpass",
        )

        assert sftp.username == "testuser"
        assert sftp.password == "testpass"

    def test_init_with_client_keys(self):
        """Test WormholeSFTP with client keys."""
        from wh.transfer.sftp import WormholeSFTP

        manager = MagicMock()
        sftp = WormholeSFTP(
            manager,
            username="testuser",
            client_keys=["/path/to/key"],
        )

        assert sftp.client_keys == ["/path/to/key"]


class TestWormholeSFTPLocalDir:
    """Tests for local directory operations."""

    @pytest.mark.asyncio
    async def test_lpwd(self):
        """Test lpwd returns local working directory."""
        from wh.transfer.sftp import WormholeSFTP

        manager = MagicMock()
        sftp = WormholeSFTP(manager, username="user")

        cwd = await sftp.lpwd()
        assert cwd == os.getcwd()

    @pytest.mark.asyncio
    async def test_lcd_valid_dir(self):
        """Test lcd changes local directory."""
        from wh.transfer.sftp import WormholeSFTP

        manager = MagicMock()
        sftp = WormholeSFTP(manager, username="user")

        with tempfile.TemporaryDirectory() as tmpdir:
            result = await sftp.lcd(tmpdir)
            assert result == tmpdir
            assert sftp._local_cwd == tmpdir

    @pytest.mark.asyncio
    async def test_lcd_invalid_dir(self):
        """Test lcd with invalid directory raises."""
        from wh.transfer.sftp import WormholeSFTP

        manager = MagicMock()
        sftp = WormholeSFTP(manager, username="user")

        # lcd raises ValueError for invalid path
        with pytest.raises((FileNotFoundError, ValueError)):
            await sftp.lcd("/nonexistent/path/that/does/not/exist")


class TestWormholeSFTPRemoteDir:
    """Tests for remote directory operations."""

    @pytest.mark.asyncio
    async def test_pwd(self):
        """Test pwd returns remote working directory."""
        from wh.transfer.sftp import WormholeSFTP

        manager = MagicMock()
        sftp = WormholeSFTP(manager, username="user")

        cwd = await sftp.pwd()
        assert cwd == "/"


class TestWormholeSFTPCommands:
    """Tests for SFTP command parsing."""

    @pytest.mark.asyncio
    async def test_execute_quit(self):
        """Test execute_command with quit."""
        from wh.transfer.sftp import WormholeSFTP

        manager = MagicMock()
        sftp = WormholeSFTP(manager, username="user")

        result = await sftp.execute_command("quit")
        assert result is False  # Should signal exit

    @pytest.mark.asyncio
    async def test_execute_exit(self):
        """Test execute_command with exit."""
        from wh.transfer.sftp import WormholeSFTP

        manager = MagicMock()
        sftp = WormholeSFTP(manager, username="user")

        result = await sftp.execute_command("exit")
        assert result is False

    @pytest.mark.asyncio
    async def test_execute_bye(self):
        """Test execute_command with bye."""
        from wh.transfer.sftp import WormholeSFTP

        manager = MagicMock()
        sftp = WormholeSFTP(manager, username="user")

        result = await sftp.execute_command("bye")
        assert result is False

    @pytest.mark.asyncio
    async def test_execute_help(self):
        """Test execute_command with help."""
        from wh.transfer.sftp import WormholeSFTP

        manager = MagicMock()
        sftp = WormholeSFTP(manager, username="user")

        result = await sftp.execute_command("help")
        assert result is True  # Should continue

    @pytest.mark.asyncio
    async def test_execute_lpwd(self):
        """Test execute_command with lpwd."""
        from wh.transfer.sftp import WormholeSFTP

        manager = MagicMock()
        sftp = WormholeSFTP(manager, username="user")

        result = await sftp.execute_command("lpwd")
        assert result is True

    @pytest.mark.asyncio
    async def test_execute_pwd(self):
        """Test execute_command with pwd."""
        from wh.transfer.sftp import WormholeSFTP

        manager = MagicMock()
        sftp = WormholeSFTP(manager, username="user")

        result = await sftp.execute_command("pwd")
        assert result is True

    @pytest.mark.asyncio
    async def test_execute_lcd(self):
        """Test execute_command with lcd."""
        from wh.transfer.sftp import WormholeSFTP

        manager = MagicMock()
        sftp = WormholeSFTP(manager, username="user")

        with tempfile.TemporaryDirectory() as tmpdir:
            result = await sftp.execute_command(f"lcd {tmpdir}")
            assert result is True
            assert sftp._local_cwd == tmpdir

    @pytest.mark.asyncio
    async def test_execute_empty(self):
        """Test execute_command with empty string."""
        from wh.transfer.sftp import WormholeSFTP

        manager = MagicMock()
        sftp = WormholeSFTP(manager, username="user")

        result = await sftp.execute_command("")
        assert result is True

    @pytest.mark.asyncio
    async def test_execute_whitespace(self):
        """Test execute_command with whitespace only."""
        from wh.transfer.sftp import WormholeSFTP

        manager = MagicMock()
        sftp = WormholeSFTP(manager, username="user")

        result = await sftp.execute_command("   ")
        assert result is True

    @pytest.mark.asyncio
    async def test_execute_unknown_command(self):
        """Test execute_command with unknown command."""
        from wh.transfer.sftp import WormholeSFTP

        manager = MagicMock()
        sftp = WormholeSFTP(manager, username="user")

        result = await sftp.execute_command("unknowncommand")
        assert result is True  # Should continue but print error


class TestWormholeSFTPClose:
    """Tests for SFTP close functionality."""

    @pytest.mark.asyncio
    async def test_close_when_not_connected(self):
        """Test close when not connected."""
        from wh.transfer.sftp import WormholeSFTP

        manager = MagicMock()
        sftp = WormholeSFTP(manager, username="user")

        await sftp.close()  # Should not raise
        assert sftp._sftp is None

    @pytest.mark.asyncio
    async def test_close_with_connection(self):
        """Test close with mock connection."""
        from wh.transfer.sftp import WormholeSFTP

        manager = MagicMock()
        sftp = WormholeSFTP(manager, username="user")

        # Mock the SFTP client
        mock_sftp = MagicMock()
        mock_sftp.exit = MagicMock()
        sftp._sftp = mock_sftp

        # Mock the SSH client
        mock_ssh = MagicMock()
        mock_ssh.close = AsyncMock()
        sftp._ssh_client = mock_ssh

        await sftp.close()

        # Verify exit was called before _sftp was set to None
        mock_sftp.exit.assert_called_once()
        mock_ssh.close.assert_called_once()


class TestWormholeSFTPAttributes:
    """Tests for SFTP attributes."""

    def test_default_local_cwd(self):
        """Test default local working directory is os.getcwd()."""
        import os
        from wh.transfer.sftp import WormholeSFTP

        manager = MagicMock()
        sftp = WormholeSFTP(manager, username="user")

        assert sftp._local_cwd == os.getcwd()
