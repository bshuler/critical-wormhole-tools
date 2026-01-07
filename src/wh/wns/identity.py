"""
WNS Identity Management - Ed25519 keypairs and self-certifying addresses.

An identity consists of an Ed25519 keypair. The address is derived from
the hash of the public key, making it self-certifying (like Tor .onion).
"""

import base64
import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from nacl.signing import SigningKey, VerifyKey
from nacl.encoding import RawEncoder


# Address length in bytes (128 bits = 16 bytes)
ADDRESS_BYTES = 16

# Base32 alphabet (lowercase, no padding)
BASE32_ALPHABET = "abcdefghijklmnopqrstuvwxyz234567"


def _base32_encode(data: bytes) -> str:
    """Encode bytes to lowercase base32 without padding."""
    encoded = base64.b32encode(data).decode("ascii").lower().rstrip("=")
    return encoded


def _base32_decode(s: str) -> bytes:
    """Decode lowercase base32 string to bytes."""
    # Add padding if needed
    padding = (8 - len(s) % 8) % 8
    s = s.upper() + "=" * padding
    return base64.b32decode(s)


@dataclass
class WNSIdentity:
    """
    A WNS identity consisting of an Ed25519 keypair.

    The address is derived from: base32(sha256(public_key)[:16])
    This gives us a 26-character address with 128 bits of collision resistance.

    Supports scoped names: name.address.wns (e.g., laptop.abc123def456.wns)
    The scoped name provides a human-readable prefix while maintaining
    cryptographic identity through the address suffix.
    """

    _signing_key: SigningKey
    _verify_key: VerifyKey
    _address: str
    name: Optional[str] = None  # Local/display name
    scoped_name: Optional[str] = None  # Published scoped name (e.g., "laptop")

    @classmethod
    def generate(cls, name: Optional[str] = None) -> "WNSIdentity":
        """Generate a new random identity."""
        signing_key = SigningKey.generate()
        verify_key = signing_key.verify_key
        address = cls._derive_address(verify_key)
        return cls(
            _signing_key=signing_key,
            _verify_key=verify_key,
            _address=address,
            name=name,
        )

    @classmethod
    def from_private_key(cls, private_key: bytes, name: Optional[str] = None) -> "WNSIdentity":
        """Create identity from existing private key."""
        signing_key = SigningKey(private_key)
        verify_key = signing_key.verify_key
        address = cls._derive_address(verify_key)
        return cls(
            _signing_key=signing_key,
            _verify_key=verify_key,
            _address=address,
            name=name,
        )

    @classmethod
    def from_public_key(cls, public_key: bytes) -> "WNSIdentity":
        """
        Create a public-only identity (for verification, not signing).

        This is used on the client side to verify server signatures.
        """
        verify_key = VerifyKey(public_key)
        address = cls._derive_address(verify_key)
        # Create with a placeholder signing key - will raise on sign attempts
        return cls(
            _signing_key=None,  # type: ignore
            _verify_key=verify_key,
            _address=address,
            name=None,
        )

    @staticmethod
    def _derive_address(verify_key: VerifyKey) -> str:
        """Derive WNS address from public key."""
        public_bytes = verify_key.encode(encoder=RawEncoder)
        digest = hashlib.sha256(public_bytes).digest()
        truncated = digest[:ADDRESS_BYTES]
        return _base32_encode(truncated)

    @property
    def address(self) -> str:
        """The WNS address (base32-encoded hash of public key)."""
        return self._address

    @property
    def full_address(self) -> str:
        """The full WNS URI: wh://address.wns"""
        return f"wh://{self._address}.wns"

    @property
    def full_scoped_address(self) -> Optional[str]:
        """
        The full scoped WNS URI: wh://name.address.wns

        Returns None if no scoped name is set.
        """
        if not self.scoped_name:
            return None
        return f"wh://{self.scoped_name}.{self._address}.wns"

    @property
    def public_key(self) -> bytes:
        """The raw Ed25519 public key bytes."""
        return self._verify_key.encode(encoder=RawEncoder)

    @property
    def private_key(self) -> bytes:
        """The raw Ed25519 private key bytes."""
        if self._signing_key is None:
            raise ValueError("This identity has no private key (public-only)")
        return self._signing_key.encode(encoder=RawEncoder)

    @property
    def can_sign(self) -> bool:
        """Whether this identity can sign messages (has private key)."""
        return self._signing_key is not None

    def sign(self, message: bytes) -> bytes:
        """Sign a message with the private key."""
        if self._signing_key is None:
            raise ValueError("Cannot sign: this identity has no private key")
        signed = self._signing_key.sign(message, encoder=RawEncoder)
        # Return just the signature (first 64 bytes), not signature + message
        return signed.signature

    def verify(self, message: bytes, signature: bytes) -> bool:
        """Verify a signature against a message."""
        try:
            # Reconstruct signed message (signature + message) for verification
            signed_message = signature + message
            self._verify_key.verify(signed_message, encoder=RawEncoder)
            return True
        except Exception:
            return False

    def to_dict(self) -> dict:
        """Serialize identity to dictionary (for JSON storage)."""
        result = {
            "address": self._address,
            "public_key": base64.b64encode(self.public_key).decode("ascii"),
        }
        if self.can_sign:
            result["private_key"] = base64.b64encode(self.private_key).decode("ascii")
        if self.name:
            result["name"] = self.name
        if self.scoped_name:
            result["scoped_name"] = self.scoped_name
        return result

    @classmethod
    def from_dict(cls, data: dict) -> "WNSIdentity":
        """Deserialize identity from dictionary."""
        if "private_key" in data:
            private_key = base64.b64decode(data["private_key"])
            identity = cls.from_private_key(private_key, name=data.get("name"))
        else:
            public_key = base64.b64decode(data["public_key"])
            identity = cls.from_public_key(public_key)
            identity.name = data.get("name")
        identity.scoped_name = data.get("scoped_name")
        return identity


class WNSIdentityStore:
    """
    Persistent storage for WNS identities.

    Storage layout:
        ~/.wh/
            identity/
                <address>/
                    identity.json    # Contains keys and metadata
            known_hosts/
                <address>.json       # Cached public keys of known servers
    """

    def __init__(self, base_path: Optional[Path] = None):
        """Initialize identity store."""
        if base_path is None:
            base_path = Path.home() / ".wh"
        self.base_path = Path(base_path)
        self.identity_path = self.base_path / "identity"
        self.known_hosts_path = self.base_path / "known_hosts"

    def _ensure_dirs(self) -> None:
        """Ensure storage directories exist."""
        self.identity_path.mkdir(parents=True, exist_ok=True)
        self.known_hosts_path.mkdir(parents=True, exist_ok=True)
        # Set restrictive permissions on identity directory
        os.chmod(self.identity_path, 0o700)

    def save_identity(self, identity: WNSIdentity) -> Path:
        """Save an identity to storage."""
        self._ensure_dirs()
        identity_dir = self.identity_path / identity.address
        identity_dir.mkdir(exist_ok=True)
        os.chmod(identity_dir, 0o700)

        identity_file = identity_dir / "identity.json"
        with open(identity_file, "w") as f:
            json.dump(identity.to_dict(), f, indent=2)
        os.chmod(identity_file, 0o600)

        return identity_file

    def load_identity(self, address: str) -> Optional[WNSIdentity]:
        """Load an identity by address."""
        identity_file = self.identity_path / address / "identity.json"
        if not identity_file.exists():
            return None

        with open(identity_file) as f:
            data = json.load(f)
        return WNSIdentity.from_dict(data)

    def list_identities(self) -> list[WNSIdentity]:
        """List all stored identities."""
        if not self.identity_path.exists():
            return []

        identities = []
        for identity_dir in self.identity_path.iterdir():
            if identity_dir.is_dir():
                identity = self.load_identity(identity_dir.name)
                if identity:
                    identities.append(identity)
        return identities

    def delete_identity(self, address: str) -> bool:
        """Delete an identity by address."""
        identity_dir = self.identity_path / address
        if not identity_dir.exists():
            return False

        # Securely delete private key file
        identity_file = identity_dir / "identity.json"
        if identity_file.exists():
            # Overwrite with zeros before deletion
            size = identity_file.stat().st_size
            with open(identity_file, "wb") as f:
                f.write(b"\x00" * size)
            identity_file.unlink()

        identity_dir.rmdir()
        return True

    def save_known_host(self, identity: WNSIdentity) -> Path:
        """Save a public-only identity as a known host."""
        self._ensure_dirs()

        # Only save public key for known hosts
        data = {
            "address": identity.address,
            "public_key": base64.b64encode(identity.public_key).decode("ascii"),
            "name": identity.name,
        }

        known_host_file = self.known_hosts_path / f"{identity.address}.json"
        with open(known_host_file, "w") as f:
            json.dump(data, f, indent=2)

        return known_host_file

    def load_known_host(self, address: str) -> Optional[WNSIdentity]:
        """Load a known host by address."""
        known_host_file = self.known_hosts_path / f"{address}.json"
        if not known_host_file.exists():
            return None

        with open(known_host_file) as f:
            data = json.load(f)

        public_key = base64.b64decode(data["public_key"])
        identity = WNSIdentity.from_public_key(public_key)
        identity.name = data.get("name")
        return identity

    def get_default_identity(self) -> Optional[WNSIdentity]:
        """Get the default identity (first one, or marked as default)."""
        identities = self.list_identities()
        if not identities:
            return None

        # TODO: Add support for marking an identity as default
        return identities[0]


def parse_wns_address(uri: str) -> Optional[str]:
    """
    Parse a WNS URI and return the base address.

    Accepts:
        wh://abc123def456ghij.wns           -> abc123def456ghij
        abc123def456ghij.wns                -> abc123def456ghij
        abc123def456ghij                    -> abc123def456ghij
        user@wh://abc123def456ghij.wns      -> abc123def456ghij
        wh://laptop.abc123def456ghij.wns    -> abc123def456ghij (scoped)

    Returns the bare address (abc123def456ghij) or None if invalid.
    """
    result = parse_scoped_wns_address(uri)
    if result:
        return result[1]  # Return just the address
    return None


def parse_scoped_wns_address(uri: str) -> Optional[tuple]:
    """
    Parse a WNS URI and return both scoped name and address.

    Accepts:
        wh://abc123def456ghij.wns           -> (None, abc123def456ghij)
        wh://laptop.abc123def456ghij.wns    -> ("laptop", abc123def456ghij)
        laptop.abc123def456ghij.wns         -> ("laptop", abc123def456ghij)
        user@wh://laptop.abc123.wns         -> ("laptop", abc123)

    Returns tuple of (scoped_name, address) or None if invalid.
    scoped_name may be None if no scoped name is present.
    """
    uri = uri.strip()

    # Remove user@ prefix if present
    if "@" in uri:
        # Split from right to handle user@wh://xxx.wns
        _, uri = uri.rsplit("@", 1)

    # Remove wh:// prefix if present
    if uri.startswith("wh://"):
        uri = uri[5:]

    # Remove .wns suffix if present
    if uri.endswith(".wns"):
        uri = uri[:-4]

    # Check for scoped name (name.address format)
    parts = uri.rsplit(".", 1)

    if len(parts) == 2:
        scoped_name, address = parts
        # Validate scoped name: alphanumeric + dash/underscore
        if scoped_name and scoped_name.replace("-", "").replace("_", "").isalnum():
            # Validate address: 26 base32 characters
            if len(address) == 26 and all(c in BASE32_ALPHABET for c in address):
                return (scoped_name, address)

    # No scoped name - just address
    address = uri
    if len(address) == 26 and all(c in BASE32_ALPHABET for c in address):
        return (None, address)

    # Invalid format
    return None


def is_wns_address(uri: str) -> bool:
    """
    Check if a string is a WNS address (vs ephemeral wormhole code).

    Detects:
        wh://xxx.wns
        wh://name.xxx.wns (scoped)
        user@wh://xxx.wns
        xxx.wns (if xxx is valid base32)
    """
    # Quick check for common WNS patterns
    if "wh://" in uri and ".wns" in uri:
        return True

    # Otherwise parse and validate
    return parse_wns_address(uri) is not None
