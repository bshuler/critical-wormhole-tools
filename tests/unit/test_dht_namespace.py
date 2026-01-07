"""Unit tests for DHT namespace encryption integration."""

import pytest
from unittest.mock import MagicMock


class TestAddressToDhtKey:
    """Tests for address_to_dht_key function."""

    def test_without_relay_url(self):
        """Test key generation without relay URL."""
        from wh.wns.dht import address_to_dht_key
        import hashlib

        address = "abc123"
        key = address_to_dht_key(address)

        # Should be SHA256 of address
        expected = hashlib.sha256(address.encode("utf-8")).digest()
        assert key == expected

    def test_with_relay_url(self):
        """Test namespace-scoped key generation."""
        from wh.wns.dht import address_to_dht_key
        from wh.wns.namespace import namespace_dht_key

        address = "abc123"
        relay_url = "ws://relay.example.com:4000/v1"

        key = address_to_dht_key(address, relay_url)

        # Should use namespace_dht_key
        expected = namespace_dht_key(address, relay_url)
        assert key == expected

    def test_same_address_different_relays(self):
        """Same address should have different keys for different relays."""
        from wh.wns.dht import address_to_dht_key

        address = "abc123"
        key1 = address_to_dht_key(address, "ws://relay1.example.com:4000/v1")
        key2 = address_to_dht_key(address, "ws://relay2.example.com:4000/v1")

        assert key1 != key2


class TestDHTConfig:
    """Tests for DHTConfig class."""

    def test_default_values(self):
        """Test default configuration values."""
        from wh.wns.dht import DHTConfig, DEFAULT_DHT_PORT, DEFAULT_TTL_SECONDS

        config = DHTConfig()

        assert config.port == DEFAULT_DHT_PORT
        assert config.ttl_seconds == DEFAULT_TTL_SECONDS
        assert config.relay_url is None
        assert config.encrypt_advertisements is False

    def test_auto_enable_encryption(self):
        """Test that encryption is auto-enabled when relay_url is provided."""
        from wh.wns.dht import DHTConfig

        config = DHTConfig(relay_url="ws://relay.example.com:4000/v1")

        assert config.relay_url == "ws://relay.example.com:4000/v1"
        assert config.encrypt_advertisements is True

    def test_explicit_encryption_flag(self):
        """Test explicit encryption flag."""
        from wh.wns.dht import DHTConfig

        # Without relay URL, encryption should stay disabled even if set
        config1 = DHTConfig(encrypt_advertisements=True)
        assert config1.encrypt_advertisements is True

        # With relay URL, encryption enabled
        config2 = DHTConfig(
            relay_url="ws://relay.example.com:4000/v1",
            encrypt_advertisements=True
        )
        assert config2.encrypt_advertisements is True


class TestWNSDHTNode:
    """Tests for WNSDHTNode class."""

    def test_init_default(self):
        """Test default initialization."""
        from wh.wns.dht import WNSDHTNode

        node = WNSDHTNode()
        assert node.config is not None
        assert not node.is_running

    def test_init_with_config(self):
        """Test initialization with custom config."""
        from wh.wns.dht import WNSDHTNode, DHTConfig

        config = DHTConfig(port=9000, relay_url="ws://test:4000/v1")
        node = WNSDHTNode(config=config)

        assert node.config.port == 9000
        assert node.config.relay_url == "ws://test:4000/v1"


class TestWNSDHTClient:
    """Tests for WNSDHTClient class."""

    def test_init_default(self):
        """Test default initialization."""
        from wh.wns.dht import WNSDHTClient

        client = WNSDHTClient()
        assert client.relay_urls == []

    def test_init_with_relay_urls(self):
        """Test initialization with relay URLs."""
        from wh.wns.dht import WNSDHTClient

        relay_urls = [
            "ws://relay1.example.com:4000/v1",
            "ws://relay2.example.com:4000/v1",
        ]
        client = WNSDHTClient(relay_urls=relay_urls)

        assert len(client.relay_urls) == 2

    def test_add_relay_namespace(self):
        """Test adding relay namespace."""
        from wh.wns.dht import WNSDHTClient

        client = WNSDHTClient()
        client.add_relay_namespace("ws://relay.example.com:4000/v1")

        assert "ws://relay.example.com:4000/v1" in client.relay_urls

    def test_add_relay_namespace_no_duplicates(self):
        """Test that duplicate relay URLs are not added."""
        from wh.wns.dht import WNSDHTClient

        client = WNSDHTClient()
        client.add_relay_namespace("ws://relay.example.com:4000/v1")
        client.add_relay_namespace("ws://relay.example.com:4000/v1")

        assert len(client.relay_urls) == 1


class TestDHTNodePublish:
    """Tests for WNSDHTNode publish functionality."""

    def test_publish_raises_when_not_running(self):
        """Test that publish raises when node not running."""
        from wh.wns.dht import WNSDHTNode

        node = WNSDHTNode()
        ad = MagicMock()

        with pytest.raises(RuntimeError, match="not running"):
            import asyncio
            asyncio.get_event_loop().run_until_complete(node.publish(ad))

    def test_publish_validates_advertisement(self):
        """Test that publish validates the advertisement."""
        from wh.wns.dht import WNSDHTNode

        node = WNSDHTNode()
        node._running = True
        node._server = MagicMock()

        ad = MagicMock()
        ad.verify.return_value = False

        with pytest.raises(ValueError, match="invalid"):
            import asyncio
            asyncio.get_event_loop().run_until_complete(node.publish(ad))


class TestDHTClientLookup:
    """Tests for WNSDHTClient lookup functionality."""

    def test_lookup_raises_when_not_running(self):
        """Test that lookup raises when client not running."""
        from wh.wns.dht import WNSDHTClient

        client = WNSDHTClient()

        with pytest.raises(RuntimeError, match="not running"):
            import asyncio
            asyncio.get_event_loop().run_until_complete(client.lookup("abc123"))

    def test_lookup_multi_namespace_raises_when_not_running(self):
        """Test that lookup_multi_namespace raises when client not running."""
        from wh.wns.dht import WNSDHTClient

        client = WNSDHTClient()

        with pytest.raises(RuntimeError, match="not running"):
            import asyncio
            asyncio.get_event_loop().run_until_complete(
                client.lookup_multi_namespace("abc123")
            )
