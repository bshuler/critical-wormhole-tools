"""Unit tests for enterprise authentication module."""

import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import nacl.signing
import nacl.encoding

from wh.enterprise.auth import (
    AuthMethod,
    AuthConfig,
    AuthResult,
    Authenticator,
    NoAuthenticator,
    PubkeyAuthenticator,
    PasswordAuthenticator,
    LDAPAuthenticator,
    create_authenticator,
)


class TestAuthMethod:
    """Tests for AuthMethod enum."""

    def test_values(self):
        """Test enum values."""
        assert AuthMethod.NONE.value == "none"
        assert AuthMethod.PUBKEY.value == "pubkey"
        assert AuthMethod.PASSWORD.value == "password"
        assert AuthMethod.LDAP.value == "ldap"

    def test_from_string(self):
        """Test creating from string."""
        assert AuthMethod("none") == AuthMethod.NONE
        assert AuthMethod("pubkey") == AuthMethod.PUBKEY
        assert AuthMethod("password") == AuthMethod.PASSWORD
        assert AuthMethod("ldap") == AuthMethod.LDAP


class TestAuthResult:
    """Tests for AuthResult dataclass."""

    def test_success_result(self):
        """Test successful result."""
        result = AuthResult(success=True, identity="jdoe")
        assert result.success is True
        assert result.identity == "jdoe"
        assert result.error is None

    def test_failure_result(self):
        """Test failed result."""
        result = AuthResult(success=False, error="Invalid credentials")
        assert result.success is False
        assert result.identity is None
        assert result.error == "Invalid credentials"

    def test_with_groups(self):
        """Test result with groups."""
        result = AuthResult(
            success=True,
            identity="jdoe",
            groups=["cn=admins,dc=example,dc=com"]
        )
        assert len(result.groups) == 1

    def test_with_metadata(self):
        """Test result with metadata."""
        result = AuthResult(
            success=True,
            identity="jdoe",
            metadata={"method": "ldap", "dn": "uid=jdoe,dc=example,dc=com"}
        )
        assert result.metadata["method"] == "ldap"


class TestNoAuthenticator:
    """Tests for NoAuthenticator."""

    @pytest.mark.asyncio
    async def test_always_succeeds(self):
        """Test that authentication always succeeds."""
        auth = NoAuthenticator()
        result = await auth.authenticate({})
        assert result.success is True
        assert result.identity == "anonymous"

    def test_no_challenge(self):
        """Test that no challenge is needed."""
        auth = NoAuthenticator()
        assert auth.get_challenge() is None

    @pytest.mark.asyncio
    async def test_with_any_credentials(self):
        """Test that any credentials are accepted."""
        auth = NoAuthenticator()
        result = await auth.authenticate({
            "username": "anything",
            "password": "whatever"
        })
        assert result.success is True


class TestPubkeyAuthenticator:
    """Tests for PubkeyAuthenticator."""

    @pytest.fixture
    def temp_keys_file(self):
        """Create a temporary authorized keys file."""
        # Generate a test keypair
        signing_key = nacl.signing.SigningKey.generate()
        pubkey = signing_key.verify_key
        pubkey_b64 = nacl.encoding.Base64Encoder.encode(bytes(pubkey)).decode()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".keys", delete=False) as f:
            f.write(f"{pubkey_b64} test-key\n")
            f.write("# This is a comment\n")
            f.write("\n")  # Empty line
            temp_path = f.name

        yield temp_path, signing_key, pubkey_b64

        os.unlink(temp_path)

    def test_load_keys(self, temp_keys_file):
        """Test loading authorized keys from file."""
        path, _, _ = temp_keys_file
        auth = PubkeyAuthenticator(path)
        assert len(auth._authorized_keys) == 1

    def test_get_challenge(self, temp_keys_file):
        """Test getting challenge."""
        path, _, _ = temp_keys_file
        auth = PubkeyAuthenticator(path)
        challenge = auth.get_challenge()

        assert challenge is not None
        assert challenge["method"] == "pubkey"
        assert "challenge" in challenge

    @pytest.mark.asyncio
    async def test_authenticate_success(self, temp_keys_file):
        """Test successful authentication."""
        path, signing_key, pubkey_b64 = temp_keys_file
        auth = PubkeyAuthenticator(path)

        # Get challenge
        challenge = auth.get_challenge()
        challenge_bytes = nacl.encoding.Base64Encoder.decode(
            challenge["challenge"].encode()
        )

        # Sign challenge
        signature = signing_key.sign(challenge_bytes).signature
        signature_b64 = nacl.encoding.Base64Encoder.encode(signature).decode()

        result = await auth.authenticate({
            "public_key": pubkey_b64,
            "signature": signature_b64,
        })

        assert result.success is True
        assert result.identity == "test-key"

    @pytest.mark.asyncio
    async def test_authenticate_unknown_key(self, temp_keys_file):
        """Test authentication with unknown key."""
        path, _, _ = temp_keys_file
        auth = PubkeyAuthenticator(path)

        # Generate a different keypair
        other_key = nacl.signing.SigningKey.generate()
        other_pubkey_b64 = nacl.encoding.Base64Encoder.encode(
            bytes(other_key.verify_key)
        ).decode()

        result = await auth.authenticate({
            "public_key": other_pubkey_b64,
            "signature": "dummy",
        })

        assert result.success is False
        assert "not authorized" in result.error.lower()

    @pytest.mark.asyncio
    async def test_authenticate_invalid_signature(self, temp_keys_file):
        """Test authentication with invalid signature."""
        path, _, pubkey_b64 = temp_keys_file
        auth = PubkeyAuthenticator(path)
        auth.get_challenge()  # Generate challenge

        result = await auth.authenticate({
            "public_key": pubkey_b64,
            "signature": "aW52YWxpZA==",  # "invalid" in base64
        })

        assert result.success is False
        assert "verification failed" in result.error.lower()

    @pytest.mark.asyncio
    async def test_authenticate_missing_credentials(self, temp_keys_file):
        """Test authentication with missing credentials."""
        path, _, _ = temp_keys_file
        auth = PubkeyAuthenticator(path)

        result = await auth.authenticate({})
        assert result.success is False
        assert "missing" in result.error.lower()

    def test_reload_keys(self, temp_keys_file):
        """Test reloading keys."""
        path, _, _ = temp_keys_file
        auth = PubkeyAuthenticator(path)
        initial_count = len(auth._authorized_keys)

        auth.reload_keys()
        assert len(auth._authorized_keys) == initial_count

    def test_missing_file(self):
        """Test with non-existent file."""
        auth = PubkeyAuthenticator("/nonexistent/path")
        assert len(auth._authorized_keys) == 0


class TestPasswordAuthenticator:
    """Tests for PasswordAuthenticator."""

    @pytest.fixture
    def temp_password_file(self):
        """Create a temporary password file with plaintext passwords for fallback testing."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".passwd", delete=False) as f:
            # Use plaintext passwords (fallback when bcrypt not available, or for testing)
            # In production, use bcrypt hashes
            f.write("admin:secret123\n")
            f.write("jdoe:password456\n")
            f.write("# Comment line\n")
            temp_path = f.name

        yield temp_path

        os.unlink(temp_path)

    def test_load_users(self, temp_password_file):
        """Test loading users from file."""
        auth = PasswordAuthenticator(temp_password_file)
        assert len(auth._users) == 2
        assert "admin" in auth._users
        assert "jdoe" in auth._users

    def test_get_challenge(self, temp_password_file):
        """Test getting challenge."""
        auth = PasswordAuthenticator(temp_password_file)
        challenge = auth.get_challenge()

        assert challenge is not None
        assert challenge["method"] == "password"

    @pytest.mark.asyncio
    async def test_authenticate_success(self, temp_password_file):
        """Test successful authentication."""
        auth = PasswordAuthenticator(temp_password_file)

        result = await auth.authenticate({
            "username": "admin",
            "password": "secret123",
        })

        assert result.success is True
        assert result.identity == "admin"

    @pytest.mark.asyncio
    async def test_authenticate_wrong_password(self, temp_password_file):
        """Test authentication with wrong password."""
        auth = PasswordAuthenticator(temp_password_file)

        result = await auth.authenticate({
            "username": "admin",
            "password": "wrongpassword",
        })

        assert result.success is False
        assert "invalid" in result.error.lower()

    @pytest.mark.asyncio
    async def test_authenticate_unknown_user(self, temp_password_file):
        """Test authentication with unknown user."""
        auth = PasswordAuthenticator(temp_password_file)

        result = await auth.authenticate({
            "username": "unknown",
            "password": "password",
        })

        assert result.success is False
        assert "invalid" in result.error.lower()

    @pytest.mark.asyncio
    async def test_authenticate_missing_credentials(self, temp_password_file):
        """Test authentication with missing credentials."""
        auth = PasswordAuthenticator(temp_password_file)

        result = await auth.authenticate({})
        assert result.success is False
        assert "missing" in result.error.lower()

    def test_missing_file(self):
        """Test with non-existent file."""
        auth = PasswordAuthenticator("/nonexistent/path")
        assert len(auth._users) == 0


class TestLDAPAuthenticator:
    """Tests for LDAPAuthenticator."""

    def test_init(self):
        """Test initialization."""
        auth = LDAPAuthenticator(
            server="ldap://ldap.example.com:389",
            base_dn="dc=example,dc=com",
            use_tls=False,
        )

        assert auth.server == "ldap://ldap.example.com:389"
        assert auth.base_dn == "dc=example,dc=com"
        assert auth.use_tls is False

    def test_get_challenge(self):
        """Test getting challenge."""
        auth = LDAPAuthenticator(
            server="ldap://localhost",
            base_dn="dc=test",
        )
        challenge = auth.get_challenge()

        assert challenge is not None
        assert challenge["method"] == "ldap"

    @pytest.mark.asyncio
    async def test_authenticate_missing_credentials(self):
        """Test authentication with missing credentials."""
        auth = LDAPAuthenticator(
            server="ldap://localhost",
            base_dn="dc=test",
        )

        result = await auth.authenticate({})
        assert result.success is False
        assert "missing" in result.error.lower()

    @pytest.mark.asyncio
    async def test_authenticate_without_ldap3(self):
        """Test authentication when ldap3 is not installed."""
        auth = LDAPAuthenticator(
            server="ldap://localhost",
            base_dn="dc=test",
        )

        with patch.dict("sys.modules", {"ldap3": None}):
            result = await auth.authenticate({
                "username": "test",
                "password": "password"
            })
            # Should fail gracefully when ldap3 is not available
            assert result.success is False


class TestCreateAuthenticator:
    """Tests for create_authenticator factory function."""

    def test_create_none_auth(self):
        """Test creating no-auth authenticator."""
        auth = create_authenticator(AuthMethod.NONE)
        assert isinstance(auth, NoAuthenticator)

    def test_create_pubkey_auth(self, tmp_path):
        """Test creating pubkey authenticator."""
        keys_file = tmp_path / "authorized_keys"
        keys_file.write_text("")

        auth = create_authenticator(
            AuthMethod.PUBKEY,
            authorized_keys=str(keys_file)
        )
        assert isinstance(auth, PubkeyAuthenticator)

    def test_create_pubkey_auth_missing_path(self):
        """Test creating pubkey auth without path."""
        with pytest.raises(ValueError, match="authorized_keys"):
            create_authenticator(AuthMethod.PUBKEY)

    def test_create_password_auth(self, tmp_path):
        """Test creating password authenticator."""
        passwd_file = tmp_path / "passwd"
        passwd_file.write_text("")

        auth = create_authenticator(
            AuthMethod.PASSWORD,
            password_file=str(passwd_file)
        )
        assert isinstance(auth, PasswordAuthenticator)

    def test_create_password_auth_missing_path(self):
        """Test creating password auth without path."""
        with pytest.raises(ValueError, match="password_file"):
            create_authenticator(AuthMethod.PASSWORD)

    def test_create_ldap_auth(self):
        """Test creating LDAP authenticator."""
        auth = create_authenticator(
            AuthMethod.LDAP,
            ldap_server="ldap://ldap.example.com",
            ldap_base_dn="dc=example,dc=com",
        )
        assert isinstance(auth, LDAPAuthenticator)

    def test_create_ldap_auth_missing_server(self):
        """Test creating LDAP auth without server."""
        with pytest.raises(ValueError, match="ldap_server"):
            create_authenticator(AuthMethod.LDAP)

    def test_create_ldap_auth_missing_base_dn(self):
        """Test creating LDAP auth without base_dn."""
        with pytest.raises(ValueError, match="ldap_base_dn"):
            create_authenticator(
                AuthMethod.LDAP,
                ldap_server="ldap://localhost"
            )


class TestAuthConfig:
    """Tests for AuthConfig dataclass."""

    def test_defaults(self):
        """Test default values."""
        config = AuthConfig()
        assert config.method == AuthMethod.NONE
        assert config.authorized_keys is None
        assert config.ldap_user_filter == "(uid={username})"
        assert config.ldap_use_tls is True

    def test_full_config(self):
        """Test with all values."""
        config = AuthConfig(
            method=AuthMethod.LDAP,
            ldap_server="ldap://ldap.example.com",
            ldap_base_dn="dc=example,dc=com",
            ldap_bind_dn="cn=admin,dc=example,dc=com",
            ldap_bind_password="secret",
            ldap_required_group="cn=admins,dc=example,dc=com",
        )

        assert config.method == AuthMethod.LDAP
        assert config.ldap_server == "ldap://ldap.example.com"
        assert config.ldap_required_group == "cn=admins,dc=example,dc=com"
