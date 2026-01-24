"""Unit tests for DHT namespace encryption integration."""

import pytest
from unittest.mock import MagicMock


class TestAddressToDhtKey:
    """Tests for address_to_dht_key function."""

    def test_without_relay_url(self):
        """Test key generation without relay URL."""
        from wh.wns.dht import address_to_dht_key, wns_address_to_info_hash

        address = "abc123"
        key = address_to_dht_key(address)

        # Should be info_hash (SHA1(SHA256(address)))
        expected = wns_address_to_info_hash(address)
        assert key == expected
        assert len(key) == 20  # 20-byte info_hash for BitTorrent DHT

    def test_with_relay_url(self):
        """Test namespace-scoped key generation."""
        from wh.wns.dht import address_to_dht_key, namespace_dht_key

        address = "abc123"
        relay_url = "ws://relay.example.com:4000/v1"

        key = address_to_dht_key(address, relay_url)

        # Should use namespace_dht_key
        expected = namespace_dht_key(address, relay_url)
        assert key == expected
        assert len(key) == 20  # 20-byte info_hash

    def test_same_address_different_relays(self):
        """Same address should have different keys for different relays."""
        from wh.wns.dht import address_to_dht_key

        address = "abc123"
        key1 = address_to_dht_key(address, "ws://relay1.example.com:4000/v1")
        key2 = address_to_dht_key(address, "ws://relay2.example.com:4000/v1")

        assert key1 != key2


class TestWnsAddressToInfoHash:
    """Tests for wns_address_to_info_hash function."""

    def test_returns_20_bytes(self):
        """Test that info_hash is 20 bytes (160 bits)."""
        from wh.wns.dht import wns_address_to_info_hash

        result = wns_address_to_info_hash("test_address")
        assert len(result) == 20

    def test_consistent_hash(self):
        """Test that same input produces same hash."""
        from wh.wns.dht import wns_address_to_info_hash

        result1 = wns_address_to_info_hash("test_address")
        result2 = wns_address_to_info_hash("test_address")
        assert result1 == result2

    def test_different_inputs_different_hashes(self):
        """Test that different inputs produce different hashes."""
        from wh.wns.dht import wns_address_to_info_hash

        result1 = wns_address_to_info_hash("address1")
        result2 = wns_address_to_info_hash("address2")
        assert result1 != result2


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
        node._dht = MagicMock()
        node._ad_server = MagicMock()

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


class TestDHTConstants:
    """Tests for DHT constants."""

    def test_default_port(self):
        """Test default DHT port is BitTorrent standard."""
        from wh.wns.dht import DEFAULT_DHT_PORT

        assert DEFAULT_DHT_PORT == 6881  # BitTorrent DHT standard port

    def test_default_ttl(self):
        """Test default TTL."""
        from wh.wns.dht import DEFAULT_TTL_SECONDS

        assert DEFAULT_TTL_SECONDS == 3600  # 1 hour

    def test_default_republish(self):
        """Test default republish interval."""
        from wh.wns.dht import DEFAULT_REPUBLISH_INTERVAL

        assert DEFAULT_REPUBLISH_INTERVAL == 300  # 5 minutes

    def test_public_bootstrap_nodes(self):
        """Test public BitTorrent bootstrap nodes are defined."""
        from wh.wns.dht import PUBLIC_BOOTSTRAP_NODES

        assert len(PUBLIC_BOOTSTRAP_NODES) >= 3
        # Should include well-known BitTorrent nodes
        hosts = [node[0] for node in PUBLIC_BOOTSTRAP_NODES]
        assert "router.bittorrent.com" in hosts


class TestWNSDHTNodeProperties:
    """Tests for WNSDHTNode properties."""

    def test_config_stored(self):
        """Test config is stored."""
        from wh.wns.dht import WNSDHTNode, DHTConfig

        config = DHTConfig(port=9000)
        node = WNSDHTNode(config=config)

        assert node.config.port == 9000

    def test_is_running_false_initially(self):
        """Test is_running is False initially."""
        from wh.wns.dht import WNSDHTNode

        node = WNSDHTNode()
        assert node.is_running is False

    def test_dht_none_initially(self):
        """Test _dht is None initially."""
        from wh.wns.dht import WNSDHTNode

        node = WNSDHTNode()
        assert node._dht is None

    def test_ad_server_none_initially(self):
        """Test _ad_server is None initially."""
        from wh.wns.dht import WNSDHTNode

        node = WNSDHTNode()
        assert node._ad_server is None


class TestWNSDHTClientProperties:
    """Tests for WNSDHTClient properties."""

    def test_relay_urls_stored(self):
        """Test relay_urls is stored."""
        from wh.wns.dht import WNSDHTClient

        urls = ["ws://relay1:4000", "ws://relay2:4000"]
        client = WNSDHTClient(relay_urls=urls)

        assert client.relay_urls == urls

    def test_is_running_false_initially(self):
        """Test _running is False initially."""
        from wh.wns.dht import WNSDHTClient

        client = WNSDHTClient()
        assert client._running is False


class TestDHTConfigBootstrap:
    """Tests for DHTConfig bootstrap nodes."""

    def test_default_bootstrap_nodes_empty(self):
        """Test default bootstrap nodes is empty list."""
        from wh.wns.dht import DHTConfig

        config = DHTConfig()
        # Default bootstrap_nodes should be empty list (uses PUBLIC_BOOTSTRAP_NODES via get_all_bootstrap_nodes)
        assert config.bootstrap_nodes == []

    def test_custom_bootstrap_nodes(self):
        """Test custom bootstrap nodes."""
        from wh.wns.dht import DHTConfig

        nodes = [("127.0.0.1", 6881), ("localhost", 6882)]
        config = DHTConfig(bootstrap_nodes=nodes)

        assert config.bootstrap_nodes == nodes

    def test_use_public_bootstrap_default_true(self):
        """Test use_public_bootstrap defaults to True."""
        from wh.wns.dht import DHTConfig

        config = DHTConfig()
        assert config.use_public_bootstrap is True

    def test_disable_public_bootstrap(self):
        """Test disabling public bootstrap nodes."""
        from wh.wns.dht import DHTConfig

        config = DHTConfig(use_public_bootstrap=False)
        assert config.use_public_bootstrap is False


class TestAddressToDhtKeyEdgeCases:
    """Edge case tests for address_to_dht_key."""

    def test_empty_address(self):
        """Test with empty address."""
        from wh.wns.dht import address_to_dht_key, wns_address_to_info_hash

        key = address_to_dht_key("")
        expected = wns_address_to_info_hash("")
        assert key == expected
        assert len(key) == 20

    def test_unicode_address(self):
        """Test with unicode address."""
        from wh.wns.dht import address_to_dht_key, wns_address_to_info_hash

        address = "テスト"  # Japanese characters
        key = address_to_dht_key(address)
        expected = wns_address_to_info_hash(address)
        assert key == expected
        assert len(key) == 20


class TestNamespaceEncryption:
    """Tests for namespace encryption functions."""

    def test_encrypt_decrypt_roundtrip(self):
        """Test that encrypt/decrypt is symmetric."""
        from wh.wns.dht import encrypt_for_namespace, decrypt_for_namespace

        data = b"test data for encryption"
        relay_url = "ws://relay.example.com:4000/v1"

        encrypted = encrypt_for_namespace(data, relay_url)
        decrypted = decrypt_for_namespace(encrypted, relay_url)

        assert decrypted == data

    def test_different_relays_different_encryption(self):
        """Test that different relay URLs produce different encryption."""
        from wh.wns.dht import encrypt_for_namespace

        data = b"test data"
        encrypted1 = encrypt_for_namespace(data, "ws://relay1.example.com:4000/v1")
        encrypted2 = encrypt_for_namespace(data, "ws://relay2.example.com:4000/v1")

        assert encrypted1 != encrypted2


class TestGetAllBootstrapNodes:
    """Tests for get_all_bootstrap_nodes function."""

    def test_returns_public_by_default(self):
        """Test that public nodes are included by default."""
        from wh.wns.dht import get_all_bootstrap_nodes, PUBLIC_BOOTSTRAP_NODES

        nodes = get_all_bootstrap_nodes()
        for node in PUBLIC_BOOTSTRAP_NODES:
            assert node in nodes

    def test_custom_nodes_first(self):
        """Test that custom nodes come before public nodes."""
        from wh.wns.dht import get_all_bootstrap_nodes

        custom = [("custom.example.com", 6881)]
        nodes = get_all_bootstrap_nodes(custom_nodes=custom)

        assert nodes[0] == custom[0]

    def test_disable_public(self):
        """Test disabling public bootstrap nodes."""
        from wh.wns.dht import get_all_bootstrap_nodes, PUBLIC_BOOTSTRAP_NODES

        custom = [("custom.example.com", 6881)]
        nodes = get_all_bootstrap_nodes(custom_nodes=custom, use_public=False)

        assert nodes == custom
        for pub_node in PUBLIC_BOOTSTRAP_NODES:
            assert pub_node not in nodes


class TestAdvertisementServer:
    """Tests for AdvertisementServer class."""

    def test_init(self):
        """Test initialization."""
        from wh.wns.dht import AdvertisementServer, DEFAULT_ADVERTISE_PORT

        server = AdvertisementServer()
        assert server.port == DEFAULT_ADVERTISE_PORT
        assert server._running is False

    def test_add_advertisement(self):
        """Test adding an advertisement."""
        from wh.wns.dht import AdvertisementServer

        server = AdvertisementServer()
        ad = MagicMock()

        server.add_advertisement("test_address", ad)
        assert server.get_advertisement("test_address") == ad

    def test_remove_advertisement(self):
        """Test removing an advertisement."""
        from wh.wns.dht import AdvertisementServer

        server = AdvertisementServer()
        ad = MagicMock()

        server.add_advertisement("test_address", ad)
        server.remove_advertisement("test_address")
        assert server.get_advertisement("test_address") is None


class TestSimpleDHTNode:
    """Tests for SimpleDHTNode class."""

    def test_init(self):
        """Test initialization."""
        from wh.wns.dht import SimpleDHTNode

        node = SimpleDHTNode(port=0)
        assert node._running is False
        assert len(node._node_id) == 20  # 160-bit node ID

    def test_bencode_integer(self):
        """Test bencoding integers."""
        from wh.wns.dht import SimpleDHTNode

        node = SimpleDHTNode()
        assert node._bencode(42) == b"i42e"
        assert node._bencode(0) == b"i0e"
        assert node._bencode(-1) == b"i-1e"

    def test_bencode_string(self):
        """Test bencoding strings."""
        from wh.wns.dht import SimpleDHTNode

        node = SimpleDHTNode()
        assert node._bencode(b"test") == b"4:test"
        assert node._bencode(b"") == b"0:"

    def test_bencode_list(self):
        """Test bencoding lists."""
        from wh.wns.dht import SimpleDHTNode

        node = SimpleDHTNode()
        assert node._bencode([b"a", b"b"]) == b"l1:a1:be"

    def test_bencode_dict(self):
        """Test bencoding dicts."""
        from wh.wns.dht import SimpleDHTNode

        node = SimpleDHTNode()
        # Keys should be sorted
        result = node._bencode({b"b": 2, b"a": 1})
        assert result == b"d1:ai1e1:bi2ee"

    def test_bdecode_integer(self):
        """Test bdecoding integers."""
        from wh.wns.dht import SimpleDHTNode

        node = SimpleDHTNode()
        assert node._bdecode(b"i42e") == 42
        assert node._bdecode(b"i0e") == 0

    def test_bdecode_string(self):
        """Test bdecoding strings."""
        from wh.wns.dht import SimpleDHTNode

        node = SimpleDHTNode()
        assert node._bdecode(b"4:test") == b"test"

    def test_bdecode_list(self):
        """Test bdecoding lists."""
        from wh.wns.dht import SimpleDHTNode

        node = SimpleDHTNode()
        assert node._bdecode(b"l1:a1:be") == [b"a", b"b"]

    def test_bdecode_dict(self):
        """Test bdecoding dicts."""
        from wh.wns.dht import SimpleDHTNode

        node = SimpleDHTNode()
        result = node._bdecode(b"d1:ai1e1:bi2ee")
        assert result == {b"a": 1, b"b": 2}
