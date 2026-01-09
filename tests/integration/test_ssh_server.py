"""Integration tests for SSH server module."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch
import pytest
import asyncssh


class TestWormholeSSHServer:
    """Tests for WormholeSSHServer class."""

    def test_init_default(self):
        """Test default initialization."""
        from wh.ssh.server import WormholeSSHServer

        server = WormholeSSHServer()

        assert server.authorized_keys_path is None
        assert server._passwords == {}
        assert server._conn is None

    def test_init_with_authorized_keys(self):
        """Test initialization with authorized keys path."""
        from wh.ssh.server import WormholeSSHServer

        server = WormholeSSHServer(authorized_keys="/path/to/keys")

        assert server.authorized_keys_path == "/path/to/keys"

    def test_init_with_passwords(self):
        """Test initialization with passwords dict."""
        from wh.ssh.server import WormholeSSHServer

        passwords = {"user1": "pass1", "user2": "pass2"}
        server = WormholeSSHServer(passwords=passwords)

        assert server._passwords == passwords

    def test_begin_auth_returns_true(self):
        """Test begin_auth always returns True."""
        from wh.ssh.server import WormholeSSHServer

        server = WormholeSSHServer()

        assert server.begin_auth("anyuser") is True

    def test_password_auth_supported(self):
        """Test password auth is supported."""
        from wh.ssh.server import WormholeSSHServer

        server = WormholeSSHServer()

        assert server.password_auth_supported() is True

    def test_validate_password_with_known_user(self):
        """Test password validation for known user."""
        from wh.ssh.server import WormholeSSHServer

        passwords = {"testuser": "correctpass"}
        server = WormholeSSHServer(passwords=passwords)

        assert server.validate_password("testuser", "correctpass") is True
        assert server.validate_password("testuser", "wrongpass") is False

    def test_validate_password_unknown_user(self):
        """Test password validation for unknown user (accepts any)."""
        from wh.ssh.server import WormholeSSHServer

        passwords = {"knownuser": "pass"}
        server = WormholeSSHServer(passwords=passwords)

        # Unknown users accepted with any password (dev mode)
        assert server.validate_password("unknownuser", "anypass") is True

    def test_public_key_auth_supported(self):
        """Test public key auth supported only with authorized_keys."""
        from wh.ssh.server import WormholeSSHServer

        server_without = WormholeSSHServer()
        assert server_without.public_key_auth_supported() is False

        server_with = WormholeSSHServer(authorized_keys="/path/to/keys")
        assert server_with.public_key_auth_supported() is True

    def test_validate_public_key_no_keys_path(self):
        """Test public key validation fails without keys path."""
        from wh.ssh.server import WormholeSSHServer

        server = WormholeSSHServer()
        mock_key = MagicMock()

        assert server.validate_public_key("user", mock_key) is False

    def test_connection_made(self):
        """Test connection_made stores connection."""
        from wh.ssh.server import WormholeSSHServer

        server = WormholeSSHServer()
        mock_conn = MagicMock()

        server.connection_made(mock_conn)

        assert server._conn is mock_conn


class TestSSHServerHandler:
    """Tests for SSHServerHandler class."""

    def test_init_default(self):
        """Test default initialization."""
        from wh.ssh.server import SSHServerHandler

        manager = MagicMock()
        handler = SSHServerHandler(manager)

        assert handler.manager is manager
        assert handler.host_keys == []
        assert handler.authorized_keys is None
        assert handler.passwords is None
        assert handler._local_server is None
        assert handler._local_port is None

    def test_init_with_options(self):
        """Test initialization with options."""
        from wh.ssh.server import SSHServerHandler

        manager = MagicMock()
        host_keys = ["/path/to/key"]
        passwords = {"user": "pass"}

        handler = SSHServerHandler(
            manager,
            host_keys=host_keys,
            authorized_keys="/path/to/authorized_keys",
            passwords=passwords,
        )

        assert handler.host_keys == host_keys
        assert handler.authorized_keys == "/path/to/authorized_keys"
        assert handler.passwords == passwords

    def test_generate_host_keys(self):
        """Test automatic host key generation."""
        from wh.ssh.server import SSHServerHandler

        manager = MagicMock()
        handler = SSHServerHandler(manager)

        # Host key should be generated when no keys provided
        assert handler._server_key is not None

    def test_init_with_existing_keys_no_generation(self):
        """Test no key generation when keys provided."""
        from wh.ssh.server import SSHServerHandler

        manager = MagicMock()

        # Create a temporary key file
        with tempfile.TemporaryDirectory() as tmpdir:
            key_path = Path(tmpdir) / "host_key"

            # Generate a key
            key = asyncssh.generate_private_key("ssh-rsa", key_size=2048)
            key.write_private_key(str(key_path))

            handler = SSHServerHandler(
                manager,
                host_keys=[str(key_path)],
            )

            # Server key should not be generated
            assert handler._server_key is None


class TestSSHServerHandlerAsync:
    """Async tests for SSHServerHandler."""

    @pytest.mark.asyncio
    async def test_handler_stores_manager(self):
        """Test handler stores manager reference."""
        from wh.ssh.server import SSHServerHandler

        manager = MagicMock()
        manager.listener_for = MagicMock(return_value=MagicMock())

        handler = SSHServerHandler(manager)

        assert handler.manager is manager


class TestHasPty:
    """Tests for PTY availability detection."""

    def test_has_pty_defined(self):
        """Test HAS_PTY is defined."""
        from wh.ssh.server import HAS_PTY

        # Should be True on Unix, False on Windows
        assert isinstance(HAS_PTY, bool)
