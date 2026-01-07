"""Unit tests for relay-scoped WNS namespace encryption."""

import pytest
import json

from wh.wns.namespace import (
    derive_namespace_key,
    derive_namespace_id,
    namespace_dht_key,
    encrypt_for_namespace,
    decrypt_for_namespace,
    NamespaceConfig,
    MultiNamespaceResolver,
    encrypt_advertisement,
    decrypt_advertisement,
    KEY_SIZE,
)


class TestDeriveNamespaceKey:
    """Tests for derive_namespace_key function."""

    def test_produces_32_byte_key(self):
        """Key should be 32 bytes."""
        key = derive_namespace_key("ws://relay.example.com:4000/v1")
        assert len(key) == KEY_SIZE

    def test_deterministic(self):
        """Same URL should produce same key."""
        url = "ws://relay.example.com:4000/v1"
        key1 = derive_namespace_key(url)
        key2 = derive_namespace_key(url)
        assert key1 == key2

    def test_different_urls_different_keys(self):
        """Different URLs should produce different keys."""
        key1 = derive_namespace_key("ws://relay1.example.com:4000/v1")
        key2 = derive_namespace_key("ws://relay2.example.com:4000/v1")
        assert key1 != key2

    def test_case_insensitive(self):
        """URL should be normalized to lowercase."""
        key1 = derive_namespace_key("ws://RELAY.EXAMPLE.COM:4000/v1")
        key2 = derive_namespace_key("ws://relay.example.com:4000/v1")
        assert key1 == key2

    def test_trailing_slash_normalized(self):
        """Trailing slashes should be stripped."""
        key1 = derive_namespace_key("ws://relay.example.com:4000/v1/")
        key2 = derive_namespace_key("ws://relay.example.com:4000/v1")
        assert key1 == key2


class TestDeriveNamespaceId:
    """Tests for derive_namespace_id function."""

    def test_produces_8_char_id(self):
        """ID should be 8 hex characters."""
        ns_id = derive_namespace_id("ws://relay.example.com:4000/v1")
        assert len(ns_id) == 8
        assert all(c in "0123456789abcdef" for c in ns_id)

    def test_deterministic(self):
        """Same URL should produce same ID."""
        url = "ws://relay.example.com:4000/v1"
        id1 = derive_namespace_id(url)
        id2 = derive_namespace_id(url)
        assert id1 == id2

    def test_different_urls_different_ids(self):
        """Different URLs should produce different IDs."""
        id1 = derive_namespace_id("ws://relay1.example.com:4000/v1")
        id2 = derive_namespace_id("ws://relay2.example.com:4000/v1")
        assert id1 != id2


class TestNamespaceDhtKey:
    """Tests for namespace_dht_key function."""

    def test_produces_32_byte_key(self):
        """DHT key should be 32 bytes."""
        key = namespace_dht_key("abc123", "ws://relay.example.com:4000/v1")
        assert len(key) == 32

    def test_deterministic(self):
        """Same inputs should produce same key."""
        address = "abc123"
        url = "ws://relay.example.com:4000/v1"
        key1 = namespace_dht_key(address, url)
        key2 = namespace_dht_key(address, url)
        assert key1 == key2

    def test_different_addresses_different_keys(self):
        """Different addresses should produce different keys."""
        url = "ws://relay.example.com:4000/v1"
        key1 = namespace_dht_key("abc123", url)
        key2 = namespace_dht_key("def456", url)
        assert key1 != key2

    def test_different_namespaces_different_keys(self):
        """Same address in different namespaces should have different keys."""
        address = "abc123"
        key1 = namespace_dht_key(address, "ws://relay1.example.com:4000/v1")
        key2 = namespace_dht_key(address, "ws://relay2.example.com:4000/v1")
        assert key1 != key2


class TestEncryptDecrypt:
    """Tests for encrypt/decrypt functions."""

    def test_roundtrip(self):
        """Encrypt then decrypt should return original data."""
        url = "ws://relay.example.com:4000/v1"
        data = b"Hello, World!"

        encrypted = encrypt_for_namespace(data, url)
        decrypted = decrypt_for_namespace(encrypted, url)

        assert decrypted == data

    def test_encrypted_differs_from_plaintext(self):
        """Encrypted data should differ from plaintext."""
        url = "ws://relay.example.com:4000/v1"
        data = b"Hello, World!"

        encrypted = encrypt_for_namespace(data, url)
        assert encrypted != data
        assert data not in encrypted

    def test_different_nonces(self):
        """Each encryption should use different nonce."""
        url = "ws://relay.example.com:4000/v1"
        data = b"Hello, World!"

        encrypted1 = encrypt_for_namespace(data, url)
        encrypted2 = encrypt_for_namespace(data, url)

        assert encrypted1 != encrypted2

    def test_wrong_key_fails(self):
        """Decryption with wrong key should fail."""
        data = b"Hello, World!"

        encrypted = encrypt_for_namespace(data, "ws://relay1.example.com:4000/v1")
        decrypted = decrypt_for_namespace(encrypted, "ws://relay2.example.com:4000/v1")

        assert decrypted is None

    def test_corrupted_data_fails(self):
        """Corrupted data should fail decryption."""
        url = "ws://relay.example.com:4000/v1"
        data = b"Hello, World!"

        encrypted = encrypt_for_namespace(data, url)
        corrupted = encrypted[:10] + b"X" + encrypted[11:]
        decrypted = decrypt_for_namespace(corrupted, url)

        assert decrypted is None

    def test_truncated_data_fails(self):
        """Truncated data should fail decryption."""
        url = "ws://relay.example.com:4000/v1"
        data = b"Hello, World!"

        encrypted = encrypt_for_namespace(data, url)
        truncated = encrypted[:10]
        decrypted = decrypt_for_namespace(truncated, url)

        assert decrypted is None

    def test_empty_data(self):
        """Empty data should encrypt/decrypt correctly."""
        url = "ws://relay.example.com:4000/v1"
        data = b""

        encrypted = encrypt_for_namespace(data, url)
        decrypted = decrypt_for_namespace(encrypted, url)

        assert decrypted == data


class TestNamespaceConfig:
    """Tests for NamespaceConfig class."""

    def test_from_relay_url(self):
        """Create config from relay URL."""
        config = NamespaceConfig.from_relay_url(
            "ws://relay.example.com:4000/v1",
            "tcp:relay.example.com:4001"
        )

        assert config.relay_url == "ws://relay.example.com:4000/v1"
        assert config.transit_url == "tcp:relay.example.com:4001"
        assert len(config.namespace_key) == 32
        assert len(config.namespace_id) == 8

    def test_dht_key(self):
        """DHT key method should work."""
        config = NamespaceConfig.from_relay_url("ws://relay.example.com:4000/v1")
        key = config.dht_key("abc123")
        assert len(key) == 32

    def test_encrypt_decrypt(self):
        """Config encrypt/decrypt methods should work."""
        config = NamespaceConfig.from_relay_url("ws://relay.example.com:4000/v1")
        data = b"test data"

        encrypted = config.encrypt(data)
        decrypted = config.decrypt(encrypted)

        assert decrypted == data

    def test_key_base64(self):
        """Base64 key property should work."""
        config = NamespaceConfig.from_relay_url("ws://relay.example.com:4000/v1")
        key_b64 = config.key_base64

        import base64
        decoded = base64.b64decode(key_b64)
        assert decoded == config.namespace_key


class TestMultiNamespaceResolver:
    """Tests for MultiNamespaceResolver class."""

    def test_add_namespace(self):
        """Adding namespace should work."""
        resolver = MultiNamespaceResolver()
        resolver.add_namespace("ws://relay.example.com:4000/v1")

        assert len(resolver.namespaces) == 1

    def test_get_dht_keys(self):
        """Should return DHT keys for all namespaces."""
        resolver = MultiNamespaceResolver()
        resolver.add_namespace("ws://relay1.example.com:4000/v1")
        resolver.add_namespace("ws://relay2.example.com:4000/v1")

        keys = resolver.get_dht_keys("abc123")

        assert len(keys) == 2
        assert keys[0][0] != keys[1][0]  # Different DHT keys

    def test_encrypt_for_all(self):
        """Should encrypt for all namespaces."""
        resolver = MultiNamespaceResolver()
        resolver.add_namespace("ws://relay1.example.com:4000/v1")
        resolver.add_namespace("ws://relay2.example.com:4000/v1")

        encrypted = resolver.encrypt_for_all(b"test data")

        assert len(encrypted) == 2
        assert encrypted[0][0] != encrypted[1][0]  # Different ciphertexts

    def test_try_decrypt_success(self):
        """Should successfully decrypt with correct namespace."""
        resolver = MultiNamespaceResolver()
        resolver.add_namespace("ws://relay1.example.com:4000/v1")
        resolver.add_namespace("ws://relay2.example.com:4000/v1")

        # Encrypt with second namespace
        config = NamespaceConfig.from_relay_url("ws://relay2.example.com:4000/v1")
        encrypted = config.encrypt(b"test data")

        result = resolver.try_decrypt(encrypted)

        assert result is not None
        decrypted, ns = result
        assert decrypted == b"test data"
        assert ns.relay_url == "ws://relay2.example.com:4000/v1"

    def test_try_decrypt_unknown_namespace(self):
        """Should return None for unknown namespace."""
        resolver = MultiNamespaceResolver()
        resolver.add_namespace("ws://relay1.example.com:4000/v1")

        # Encrypt with different namespace
        config = NamespaceConfig.from_relay_url("ws://unknown.example.com:4000/v1")
        encrypted = config.encrypt(b"test data")

        result = resolver.try_decrypt(encrypted)
        assert result is None


class TestAdvertisementEncryption:
    """Tests for advertisement encryption helpers."""

    def test_encrypt_decrypt_advertisement(self):
        """Should encrypt/decrypt JSON advertisement."""
        ad_json = json.dumps({
            "address": "abc123",
            "code": "7-guitar-sunset",
            "timestamp": "2024-01-01T00:00:00Z",
            "expires": "2024-01-01T00:05:00Z",
        })
        url = "ws://relay.example.com:4000/v1"

        encrypted = encrypt_advertisement(ad_json, url)
        decrypted = decrypt_advertisement(encrypted, url)

        assert decrypted == ad_json
        assert json.loads(decrypted)["code"] == "7-guitar-sunset"

    def test_wrong_relay_fails(self):
        """Decryption with wrong relay should fail."""
        ad_json = json.dumps({"code": "7-guitar-sunset"})

        encrypted = encrypt_advertisement(ad_json, "ws://relay1.example.com:4000/v1")
        decrypted = decrypt_advertisement(encrypted, "ws://relay2.example.com:4000/v1")

        assert decrypted is None
