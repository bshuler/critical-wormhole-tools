"""
Enterprise Authentication Module.

Provides authentication methods for wormhole connections:
- None: No authentication (default)
- PubKey: SSH public key authentication
- Password: Simple password authentication
- LDAP: LDAP/Active Directory authentication

Usage:
    # Create authenticator
    auth = create_authenticator(AuthMethod.PUBKEY, authorized_keys="/etc/wh/authorized_keys")

    # Authenticate a connection
    result = await auth.authenticate(credentials)
    if result.success:
        print(f"Authenticated as {result.identity}")
"""

import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import nacl.signing
import nacl.encoding


logger = logging.getLogger(__name__)


class AuthMethod(Enum):
    """Supported authentication methods."""
    NONE = "none"
    PUBKEY = "pubkey"
    PASSWORD = "password"
    LDAP = "ldap"


@dataclass
class AuthConfig:
    """Configuration for authentication."""
    method: AuthMethod = AuthMethod.NONE
    # Pubkey auth options
    authorized_keys: Optional[str] = None  # Path to authorized_keys file
    # Password auth options
    password_file: Optional[str] = None  # Path to htpasswd-style file
    # LDAP auth options
    ldap_server: Optional[str] = None
    ldap_base_dn: Optional[str] = None
    ldap_bind_dn: Optional[str] = None  # Optional bind DN for searches
    ldap_bind_password: Optional[str] = None
    ldap_user_filter: str = "(uid={username})"
    ldap_group_filter: Optional[str] = None
    ldap_required_group: Optional[str] = None
    ldap_use_tls: bool = True
    ldap_timeout: float = 10.0


@dataclass
class AuthResult:
    """Result of an authentication attempt."""
    success: bool
    identity: Optional[str] = None  # Username or key identifier
    groups: List[str] = field(default_factory=list)
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class Authenticator(ABC):
    """Abstract base class for authenticators."""

    @abstractmethod
    async def authenticate(self, credentials: Dict[str, Any]) -> AuthResult:
        """
        Authenticate with provided credentials.

        Args:
            credentials: Dictionary containing authentication data

        Returns:
            AuthResult with success status and identity info
        """
        pass

    @abstractmethod
    def get_challenge(self) -> Optional[Dict[str, Any]]:
        """
        Get challenge for challenge-response authentication.

        Returns:
            Challenge data, or None if not applicable
        """
        pass


class NoAuthenticator(Authenticator):
    """No authentication - allows all connections."""

    async def authenticate(self, credentials: Dict[str, Any]) -> AuthResult:
        """Always succeeds."""
        return AuthResult(
            success=True,
            identity="anonymous",
            metadata={"method": "none"}
        )

    def get_challenge(self) -> Optional[Dict[str, Any]]:
        """No challenge needed."""
        return None


class PubkeyAuthenticator(Authenticator):
    """
    SSH public key authentication.

    Verifies Ed25519 signatures against an authorized_keys file.
    File format (one key per line):
        <base64-encoded-public-key> <key-id or comment>
    """

    def __init__(self, authorized_keys_path: str):
        self.authorized_keys_path = Path(authorized_keys_path)
        self._authorized_keys: Dict[str, str] = {}  # pubkey -> key_id
        self._challenge: bytes = os.urandom(32)
        self._load_keys()

    def _load_keys(self) -> None:
        """Load authorized keys from file."""
        self._authorized_keys.clear()

        if not self.authorized_keys_path.exists():
            logger.warning(f"Authorized keys file not found: {self.authorized_keys_path}")
            return

        try:
            with open(self.authorized_keys_path, "r") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue

                    parts = line.split(None, 1)
                    if len(parts) < 1:
                        continue

                    pubkey_b64 = parts[0]
                    key_id = parts[1] if len(parts) > 1 else f"key-{line_num}"

                    # Validate it's a valid base64 key
                    try:
                        key_bytes = nacl.encoding.Base64Encoder.decode(pubkey_b64.encode())
                        if len(key_bytes) == 32:  # Ed25519 public key
                            self._authorized_keys[pubkey_b64] = key_id
                        else:
                            logger.warning(f"Invalid key length on line {line_num}")
                    except Exception as e:
                        logger.warning(f"Invalid key format on line {line_num}: {e}")

            logger.info(f"Loaded {len(self._authorized_keys)} authorized keys")
        except Exception as e:
            logger.error(f"Failed to load authorized keys: {e}")

    def reload_keys(self) -> None:
        """Reload authorized keys from file."""
        self._load_keys()

    def get_challenge(self) -> Optional[Dict[str, Any]]:
        """Get a random challenge for signature verification."""
        self._challenge = os.urandom(32)
        return {
            "method": "pubkey",
            "challenge": nacl.encoding.Base64Encoder.encode(self._challenge).decode(),
        }

    async def authenticate(self, credentials: Dict[str, Any]) -> AuthResult:
        """
        Authenticate with public key signature.

        Credentials should contain:
            - public_key: Base64-encoded Ed25519 public key
            - signature: Base64-encoded signature of the challenge
        """
        pubkey_b64 = credentials.get("public_key")
        signature_b64 = credentials.get("signature")

        if not pubkey_b64 or not signature_b64:
            return AuthResult(
                success=False,
                error="Missing public_key or signature"
            )

        # Check if key is authorized
        if pubkey_b64 not in self._authorized_keys:
            return AuthResult(
                success=False,
                error="Public key not authorized"
            )

        # Verify signature
        try:
            pubkey_bytes = nacl.encoding.Base64Encoder.decode(pubkey_b64.encode())
            signature_bytes = nacl.encoding.Base64Encoder.decode(signature_b64.encode())

            verify_key = nacl.signing.VerifyKey(pubkey_bytes)
            verify_key.verify(self._challenge, signature_bytes)

            key_id = self._authorized_keys[pubkey_b64]

            return AuthResult(
                success=True,
                identity=key_id,
                metadata={
                    "method": "pubkey",
                    "public_key": pubkey_b64[:16] + "...",
                }
            )
        except Exception as e:
            logger.debug(f"Signature verification failed: {e}")
            return AuthResult(
                success=False,
                error="Signature verification failed"
            )


class PasswordAuthenticator(Authenticator):
    """
    Password authentication using htpasswd-style file.

    File format (one user per line):
        username:bcrypt_hash
    """

    def __init__(self, password_file: str):
        self.password_file = Path(password_file)
        self._users: Dict[str, str] = {}  # username -> password_hash
        self._load_users()

    def _load_users(self) -> None:
        """Load users from password file."""
        self._users.clear()

        if not self.password_file.exists():
            logger.warning(f"Password file not found: {self.password_file}")
            return

        try:
            with open(self.password_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue

                    if ":" not in line:
                        continue

                    username, password_hash = line.split(":", 1)
                    self._users[username] = password_hash

            logger.info(f"Loaded {len(self._users)} users")
        except Exception as e:
            logger.error(f"Failed to load password file: {e}")

    def get_challenge(self) -> Optional[Dict[str, Any]]:
        """Password auth uses direct credentials, no challenge."""
        return {"method": "password"}

    async def authenticate(self, credentials: Dict[str, Any]) -> AuthResult:
        """
        Authenticate with username and password.

        Credentials should contain:
            - username: The username
            - password: The password
        """
        username = credentials.get("username")
        password = credentials.get("password")

        if not username or not password:
            return AuthResult(
                success=False,
                error="Missing username or password"
            )

        stored_hash = self._users.get(username)
        if not stored_hash:
            return AuthResult(
                success=False,
                error="Invalid credentials"
            )

        # Verify password using bcrypt if it's a bcrypt hash, otherwise plaintext
        # Bcrypt hashes start with $2a$, $2b$, or $2y$
        if stored_hash.startswith(("$2a$", "$2b$", "$2y$")):
            try:
                import bcrypt
                if bcrypt.checkpw(password.encode(), stored_hash.encode()):
                    return AuthResult(
                        success=True,
                        identity=username,
                        metadata={"method": "password"}
                    )
                else:
                    return AuthResult(
                        success=False,
                        error="Invalid credentials"
                    )
            except ImportError:
                logger.warning("bcrypt not installed, cannot verify bcrypt hash")
                return AuthResult(
                    success=False,
                    error="bcrypt not installed"
                )
            except Exception as e:
                logger.error(f"Password verification error: {e}")
                return AuthResult(
                    success=False,
                    error="Authentication error"
                )
        else:
            # Fallback to plain text comparison (not recommended for production)
            if password == stored_hash:
                return AuthResult(
                    success=True,
                    identity=username,
                    metadata={"method": "password", "warning": "plaintext password"}
                )
            return AuthResult(
                success=False,
                error="Invalid credentials"
            )


class LDAPAuthenticator(Authenticator):
    """
    LDAP/Active Directory authentication.

    Supports:
    - Simple bind authentication
    - Group membership verification
    - TLS/SSL connections
    """

    def __init__(
        self,
        server: str,
        base_dn: str,
        bind_dn: Optional[str] = None,
        bind_password: Optional[str] = None,
        user_filter: str = "(uid={username})",
        group_filter: Optional[str] = None,
        required_group: Optional[str] = None,
        use_tls: bool = True,
        timeout: float = 10.0,
    ):
        self.server = server
        self.base_dn = base_dn
        self.bind_dn = bind_dn
        self.bind_password = bind_password
        self.user_filter = user_filter
        self.group_filter = group_filter
        self.required_group = required_group
        self.use_tls = use_tls
        self.timeout = timeout

    def get_challenge(self) -> Optional[Dict[str, Any]]:
        """LDAP uses direct credentials."""
        return {"method": "ldap"}

    async def authenticate(self, credentials: Dict[str, Any]) -> AuthResult:
        """
        Authenticate against LDAP server.

        Credentials should contain:
            - username: The username
            - password: The password
        """
        username = credentials.get("username")
        password = credentials.get("password")

        if not username or not password:
            return AuthResult(
                success=False,
                error="Missing username or password"
            )

        try:
            from ldap3 import Server, Connection, ALL, SUBTREE, Tls
            import ssl

            # Create server with optional TLS
            tls_config = None
            if self.use_tls:
                tls_config = Tls(validate=ssl.CERT_OPTIONAL)

            server = Server(
                self.server,
                get_info=ALL,
                tls=tls_config,
                connect_timeout=self.timeout,
            )

            # Build user filter
            search_filter = self.user_filter.format(username=username)

            # First, search for the user DN
            if self.bind_dn and self.bind_password:
                # Use service account to search
                conn = Connection(
                    server,
                    user=self.bind_dn,
                    password=self.bind_password,
                    auto_bind=True,
                    read_only=True,
                )
            else:
                # Anonymous bind for search
                conn = Connection(server, auto_bind=True, read_only=True)

            # Search for user
            conn.search(
                search_base=self.base_dn,
                search_filter=search_filter,
                search_scope=SUBTREE,
                attributes=["dn", "memberOf", "cn"],
            )

            if not conn.entries:
                conn.unbind()
                return AuthResult(
                    success=False,
                    error="User not found"
                )

            user_entry = conn.entries[0]
            user_dn = user_entry.entry_dn

            # Get groups if available
            groups = []
            if hasattr(user_entry, "memberOf"):
                groups = list(user_entry.memberOf)

            conn.unbind()

            # Now try to bind as the user
            user_conn = Connection(
                server,
                user=user_dn,
                password=password,
                auto_bind=True,
            )

            # Successful bind means authentication passed
            user_conn.unbind()

            # Check required group if specified
            if self.required_group:
                if not any(self.required_group in g for g in groups):
                    return AuthResult(
                        success=False,
                        error=f"User not in required group: {self.required_group}"
                    )

            return AuthResult(
                success=True,
                identity=username,
                groups=groups,
                metadata={
                    "method": "ldap",
                    "dn": user_dn,
                }
            )

        except ImportError:
            return AuthResult(
                success=False,
                error="ldap3 library not installed"
            )
        except Exception as e:
            logger.error(f"LDAP authentication error: {e}")
            return AuthResult(
                success=False,
                error=f"LDAP error: {str(e)}"
            )


def create_authenticator(
    method: AuthMethod,
    authorized_keys: Optional[str] = None,
    password_file: Optional[str] = None,
    ldap_server: Optional[str] = None,
    ldap_base_dn: Optional[str] = None,
    ldap_bind_dn: Optional[str] = None,
    ldap_bind_password: Optional[str] = None,
    ldap_user_filter: str = "(uid={username})",
    ldap_group_filter: Optional[str] = None,
    ldap_required_group: Optional[str] = None,
    ldap_use_tls: bool = True,
    ldap_timeout: float = 10.0,
) -> Authenticator:
    """
    Create an authenticator based on method.

    Args:
        method: Authentication method to use
        authorized_keys: Path to authorized_keys file (for pubkey)
        password_file: Path to htpasswd-style file (for password)
        ldap_*: LDAP configuration options

    Returns:
        Configured Authenticator instance
    """
    if method == AuthMethod.NONE:
        return NoAuthenticator()

    elif method == AuthMethod.PUBKEY:
        if not authorized_keys:
            raise ValueError("authorized_keys path required for pubkey auth")
        return PubkeyAuthenticator(authorized_keys)

    elif method == AuthMethod.PASSWORD:
        if not password_file:
            raise ValueError("password_file path required for password auth")
        return PasswordAuthenticator(password_file)

    elif method == AuthMethod.LDAP:
        if not ldap_server or not ldap_base_dn:
            raise ValueError("ldap_server and ldap_base_dn required for LDAP auth")
        return LDAPAuthenticator(
            server=ldap_server,
            base_dn=ldap_base_dn,
            bind_dn=ldap_bind_dn,
            bind_password=ldap_bind_password,
            user_filter=ldap_user_filter,
            group_filter=ldap_group_filter,
            required_group=ldap_required_group,
            use_tls=ldap_use_tls,
            timeout=ldap_timeout,
        )

    else:
        raise ValueError(f"Unknown authentication method: {method}")
