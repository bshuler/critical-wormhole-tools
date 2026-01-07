"""
Relay-scoped WNS Namespace Encryption.

Provides privacy-preserving namespaces where:
- DHT entries are encrypted with a key derived from the relay URL
- Only users who know the relay URL can discover addresses
- Multi-relay support allows falling back through relay list

Architecture:
    ┌─────────────────────────────────────────────────────────────────────┐
    │  Relay URL (e.g., ws://relay.company.com:4000/v1)                   │
    │       │                                                             │
    │       ▼                                                             │
    │  HKDF(relay_url, "wns-namespace-v1") → namespace_key (32 bytes)     │
    │       │                                                             │
    │       ▼                                                             │
    │  ┌─────────────────────────────────────────────────────────────┐   │
    │  │  DHT Entry = Encrypt(advertisement, namespace_key)          │   │
    │  │  DHT Key = HASH(address || namespace_id)                    │   │
    │  └─────────────────────────────────────────────────────────────┘   │
    └─────────────────────────────────────────────────────────────────────┘

This ensures:
- Relay URL acts as a shared secret for the namespace
- DHT entries are opaque to anyone without the relay URL
- Organizations can run private relays with private namespaces
"""

import base64
import hashlib
import os
from dataclasses import dataclass
from typing import Optional

from nacl.secret import SecretBox
from nacl.utils import random as nacl_random


# Constants
NAMESPACE_VERSION = 1
NAMESPACE_SALT = b"wns-namespace-v1"
DHT_KEY_SALT = b"wns-dht-key-v1"
NONCE_SIZE = 24
KEY_SIZE = 32


def derive_namespace_key(relay_url: str) -> bytes:
    """
    Derive a namespace encryption key from a relay URL.

    Uses HKDF-like derivation:
        key = SHA256(SHA256(relay_url) || NAMESPACE_SALT)[:32]

    Args:
        relay_url: The relay WebSocket URL

    Returns:
        32-byte encryption key
    """
    # Normalize the URL (lowercase, strip trailing slashes)
    normalized = relay_url.lower().rstrip("/")

    # Two-stage hash for key derivation
    url_hash = hashlib.sha256(normalized.encode("utf-8")).digest()
    key_material = hashlib.sha256(url_hash + NAMESPACE_SALT).digest()

    return key_material[:KEY_SIZE]


def derive_namespace_id(relay_url: str) -> str:
    """
    Derive a short namespace identifier for display.

    Args:
        relay_url: The relay WebSocket URL

    Returns:
        8-character hex identifier
    """
    key = derive_namespace_key(relay_url)
    return hashlib.sha256(key).hexdigest()[:8]


def namespace_dht_key(address: str, relay_url: str) -> bytes:
    """
    Derive a DHT key that's scoped to a namespace.

    The DHT key is: SHA256(address || namespace_key || DHT_KEY_SALT)

    This ensures:
    - Same address on different relays has different DHT keys
    - Cannot correlate entries across namespaces without the relay URL

    Args:
        address: The WNS address
        relay_url: The relay URL defining the namespace

    Returns:
        32-byte DHT key
    """
    namespace_key = derive_namespace_key(relay_url)
    combined = address.encode("utf-8") + namespace_key + DHT_KEY_SALT
    return hashlib.sha256(combined).digest()


def encrypt_for_namespace(data: bytes, relay_url: str) -> bytes:
    """
    Encrypt data for a relay-scoped namespace.

    Format: version (1 byte) || nonce (24 bytes) || ciphertext

    Args:
        data: Plaintext data to encrypt
        relay_url: The relay URL defining the namespace

    Returns:
        Encrypted data with prepended nonce
    """
    key = derive_namespace_key(relay_url)
    box = SecretBox(key)
    nonce = nacl_random(NONCE_SIZE)

    ciphertext = box.encrypt(data, nonce)

    # Prepend version byte
    return bytes([NAMESPACE_VERSION]) + ciphertext


def decrypt_for_namespace(encrypted_data: bytes, relay_url: str) -> Optional[bytes]:
    """
    Decrypt data from a relay-scoped namespace.

    Args:
        encrypted_data: Data encrypted with encrypt_for_namespace
        relay_url: The relay URL defining the namespace

    Returns:
        Decrypted data, or None if decryption fails
    """
    if len(encrypted_data) < 1 + NONCE_SIZE + 16:  # version + nonce + auth tag
        return None

    version = encrypted_data[0]
    if version != NAMESPACE_VERSION:
        return None

    ciphertext = encrypted_data[1:]

    key = derive_namespace_key(relay_url)
    box = SecretBox(key)

    try:
        return box.decrypt(ciphertext)
    except Exception:
        return None


@dataclass
class NamespaceConfig:
    """Configuration for a relay-scoped namespace."""

    relay_url: str
    transit_url: str
    namespace_key: bytes
    namespace_id: str

    @classmethod
    def from_relay_url(cls, relay_url: str, transit_url: str = "") -> "NamespaceConfig":
        """Create namespace config from relay URL."""
        return cls(
            relay_url=relay_url,
            transit_url=transit_url,
            namespace_key=derive_namespace_key(relay_url),
            namespace_id=derive_namespace_id(relay_url),
        )

    def dht_key(self, address: str) -> bytes:
        """Get the DHT key for an address in this namespace."""
        return namespace_dht_key(address, self.relay_url)

    def encrypt(self, data: bytes) -> bytes:
        """Encrypt data for this namespace."""
        return encrypt_for_namespace(data, self.relay_url)

    def decrypt(self, encrypted_data: bytes) -> Optional[bytes]:
        """Decrypt data from this namespace."""
        return decrypt_for_namespace(encrypted_data, self.relay_url)

    @property
    def key_base64(self) -> str:
        """Get the namespace key as base64 (for config storage)."""
        return base64.b64encode(self.namespace_key).decode("ascii")


class MultiNamespaceResolver:
    """
    Resolves WNS addresses across multiple namespaces.

    Tries each configured relay's namespace in order until
    a valid advertisement is found.
    """

    def __init__(self, namespaces: Optional[list] = None):
        """
        Initialize with a list of NamespaceConfig objects.

        Args:
            namespaces: List of namespace configs to try (in order)
        """
        self.namespaces = namespaces or []

    @classmethod
    def from_relay_config(cls) -> "MultiNamespaceResolver":
        """Create resolver from ~/.wh/relays.yaml config."""
        from wh.relay.config import get_relay_manager

        manager = get_relay_manager()
        relays = manager.list_relays()

        namespaces = [
            NamespaceConfig.from_relay_url(r.mailbox_url, r.transit_url)
            for r in relays
        ]

        return cls(namespaces)

    def add_namespace(self, relay_url: str, transit_url: str = "") -> None:
        """Add a namespace to try."""
        config = NamespaceConfig.from_relay_url(relay_url, transit_url)
        self.namespaces.append(config)

    def get_dht_keys(self, address: str) -> list:
        """
        Get all DHT keys to try for an address.

        Returns list of (dht_key, namespace_config) tuples.
        """
        return [(ns.dht_key(address), ns) for ns in self.namespaces]

    def encrypt_for_all(self, data: bytes) -> list:
        """
        Encrypt data for all namespaces.

        Returns list of (encrypted_data, namespace_config) tuples.
        """
        return [(ns.encrypt(data), ns) for ns in self.namespaces]

    def try_decrypt(self, encrypted_data: bytes) -> Optional[tuple]:
        """
        Try to decrypt data with each namespace key.

        Returns (decrypted_data, namespace_config) if successful, None otherwise.
        """
        for ns in self.namespaces:
            decrypted = ns.decrypt(encrypted_data)
            if decrypted is not None:
                return (decrypted, ns)
        return None


# Convenience functions

def get_default_namespace() -> NamespaceConfig:
    """Get the namespace for the default relay."""
    from wh.relay.config import get_relay_manager

    manager = get_relay_manager()
    relay = manager.get_default_relay()
    return NamespaceConfig.from_relay_url(relay.mailbox_url, relay.transit_url)


def encrypt_advertisement(ad_json: str, relay_url: str) -> bytes:
    """
    Encrypt a code advertisement for a namespace.

    Args:
        ad_json: JSON string of the advertisement
        relay_url: Relay URL defining the namespace

    Returns:
        Encrypted advertisement bytes
    """
    return encrypt_for_namespace(ad_json.encode("utf-8"), relay_url)


def decrypt_advertisement(encrypted: bytes, relay_url: str) -> Optional[str]:
    """
    Decrypt a code advertisement from a namespace.

    Args:
        encrypted: Encrypted advertisement bytes
        relay_url: Relay URL defining the namespace

    Returns:
        JSON string of advertisement, or None if decryption fails
    """
    decrypted = decrypt_for_namespace(encrypted, relay_url)
    if decrypted is None:
        return None
    return decrypted.decode("utf-8")
