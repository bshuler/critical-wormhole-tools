"""
Tests for WNS (Wormhole Name Service) functionality.
"""

import pytest

from wh.wns.identity import (
    WNSIdentity,
    WNSIdentityStore,
    is_wns_address,
    parse_wns_address,
    parse_scoped_wns_address,
)
from wh.wns.advertisement import CodeAdvertisement
from wh.wns.aliases import AliasStore
from wh.wns.names import (
    NameClaim,
    NameClaimStore,
    is_valid_global_name,
    is_global_name_address,
    parse_global_name,
)


class TestWNSIdentity:
    """Tests for WNSIdentity class."""

    def test_generate(self):
        """Test identity generation."""
        identity = WNSIdentity.generate()
        assert identity.address is not None
        assert len(identity.address) == 26  # Base32 encoded 16 bytes
        assert identity.can_sign is True

    def test_generate_with_name(self):
        """Test identity generation with name."""
        identity = WNSIdentity.generate(name="test-server")
        assert identity.name == "test-server"

    def test_address_deterministic(self):
        """Test that address is deterministic from public key."""
        identity = WNSIdentity.generate()
        pk = identity.public_key

        # Create new identity from same public key
        identity2 = WNSIdentity.from_public_key(pk)
        assert identity2.address == identity.address

    def test_full_address(self):
        """Test full_address property."""
        identity = WNSIdentity.generate()
        assert identity.full_address == f"wh://{identity.address}.wns"

    def test_sign_and_verify(self):
        """Test signing and verification."""
        identity = WNSIdentity.generate()
        message = b"test message"

        signature = identity.sign(message)
        assert identity.verify(message, signature) is True

    def test_verify_wrong_message(self):
        """Test verification fails with wrong message."""
        identity = WNSIdentity.generate()
        message = b"test message"
        wrong_message = b"wrong message"

        signature = identity.sign(message)
        assert identity.verify(wrong_message, signature) is False

    def test_from_private_key(self):
        """Test creating identity from private key."""
        identity1 = WNSIdentity.generate()
        pk = identity1.private_key

        identity2 = WNSIdentity.from_private_key(pk)
        assert identity2.address == identity1.address
        assert identity2.public_key == identity1.public_key

    def test_from_public_key_cannot_sign(self):
        """Test that public-only identity cannot sign."""
        identity = WNSIdentity.generate()
        pk = identity.public_key

        public_identity = WNSIdentity.from_public_key(pk)
        assert public_identity.can_sign is False

        with pytest.raises(ValueError):
            public_identity.sign(b"test")


class TestWNSAddressParsing:
    """Tests for WNS address parsing functions."""

    def test_is_wns_address_full(self):
        """Test is_wns_address with full URI."""
        # Valid 26-char base32
        assert is_wns_address("wh://abcdefghijklmnopqrstuvwxyz.wns") is True

    def test_is_wns_address_with_user(self):
        """Test is_wns_address with user@."""
        assert is_wns_address("user@wh://abcdefghijklmnopqrstuvwxyz.wns") is True

    def test_is_wns_address_regular_code(self):
        """Test is_wns_address with regular wormhole code."""
        assert is_wns_address("7-guitar-sunset") is False
        assert is_wns_address("user@7-guitar-sunset") is False

    def test_is_wns_address_http_url(self):
        """Test is_wns_address with HTTP URL."""
        assert is_wns_address("http://example.com") is False

    def test_parse_wns_address_full(self):
        """Test parse_wns_address with full URI."""
        result = parse_wns_address("wh://abcdefghijklmnopqrstuvwxyz.wns")
        assert result == "abcdefghijklmnopqrstuvwxyz"

    def test_parse_wns_address_bare(self):
        """Test parse_wns_address with bare address."""
        result = parse_wns_address("abcdefghijklmnopqrstuvwxyz")
        assert result == "abcdefghijklmnopqrstuvwxyz"

    def test_parse_wns_address_with_suffix(self):
        """Test parse_wns_address with .wns suffix only."""
        result = parse_wns_address("abcdefghijklmnopqrstuvwxyz.wns")
        assert result == "abcdefghijklmnopqrstuvwxyz"

    def test_parse_wns_address_with_user(self):
        """Test parse_wns_address with user@."""
        result = parse_wns_address("user@wh://abcdefghijklmnopqrstuvwxyz.wns")
        assert result == "abcdefghijklmnopqrstuvwxyz"

    def test_parse_wns_address_invalid(self):
        """Test parse_wns_address with invalid address."""
        assert parse_wns_address("7-guitar-sunset") is None
        assert parse_wns_address("too-short") is None


class TestCodeAdvertisement:
    """Tests for CodeAdvertisement class."""

    def test_create_and_verify(self):
        """Test creating and verifying an advertisement."""
        identity = WNSIdentity.generate()
        code = "7-guitar-sunset"

        ad = CodeAdvertisement.create(identity, code)

        assert ad.address == identity.address
        assert ad.code == code
        assert ad.public_key == identity.public_key
        assert ad.verify() is True

    def test_verify_with_expected_address(self):
        """Test verification with expected address."""
        identity = WNSIdentity.generate()
        ad = CodeAdvertisement.create(identity, "7-guitar-sunset")

        assert ad.verify(expected_address=identity.address) is True
        assert ad.verify(expected_address="wrong") is False

    def test_expiry(self):
        """Test advertisement expiry."""
        identity = WNSIdentity.generate()

        # Create ad with 0 TTL (already expired)
        ad = CodeAdvertisement.create(identity, "7-guitar-sunset", ttl_seconds=0)
        assert ad.is_expired() is True

        # Create ad with long TTL
        ad = CodeAdvertisement.create(identity, "7-guitar-sunset", ttl_seconds=3600)
        assert ad.is_expired() is False

    def test_json_serialization(self):
        """Test JSON serialization roundtrip."""
        identity = WNSIdentity.generate()
        ad = CodeAdvertisement.create(identity, "7-guitar-sunset")

        json_str = ad.to_json()
        ad2 = CodeAdvertisement.from_json(json_str)

        assert ad2.address == ad.address
        assert ad2.code == ad.code
        assert ad2.signature == ad.signature
        assert ad2.verify() is True


class TestWNSIdentityStore:
    """Tests for WNSIdentityStore class."""

    def test_save_and_load_identity(self, tmp_path):
        """Test saving and loading an identity."""
        store = WNSIdentityStore(base_path=tmp_path)
        identity = WNSIdentity.generate(name="test")

        store.save_identity(identity)
        loaded = store.load_identity(identity.address)

        assert loaded is not None
        assert loaded.address == identity.address
        assert loaded.name == "test"
        assert loaded.public_key == identity.public_key

    def test_list_identities(self, tmp_path):
        """Test listing identities."""
        store = WNSIdentityStore(base_path=tmp_path)

        identity1 = WNSIdentity.generate(name="server1")
        identity2 = WNSIdentity.generate(name="server2")

        store.save_identity(identity1)
        store.save_identity(identity2)

        identities = store.list_identities()
        assert len(identities) == 2
        addresses = [i.address for i in identities]
        assert identity1.address in addresses
        assert identity2.address in addresses

    def test_delete_identity(self, tmp_path):
        """Test deleting an identity."""
        store = WNSIdentityStore(base_path=tmp_path)
        identity = WNSIdentity.generate()

        store.save_identity(identity)
        assert store.load_identity(identity.address) is not None

        store.delete_identity(identity.address)
        assert store.load_identity(identity.address) is None

    def test_known_hosts(self, tmp_path):
        """Test known hosts functionality."""
        store = WNSIdentityStore(base_path=tmp_path)
        identity = WNSIdentity.generate()

        # Create public-only identity for known hosts
        public_identity = WNSIdentity.from_public_key(identity.public_key)

        store.save_known_host(public_identity)
        loaded = store.load_known_host(identity.address)

        assert loaded is not None
        assert loaded.address == identity.address
        assert loaded.public_key == identity.public_key


class TestScopedNames:
    """Tests for scoped name functionality."""

    def test_parse_scoped_address(self):
        """Test parsing scoped addresses."""
        # Full scoped address
        result = parse_scoped_wns_address("wh://laptop.abcdefghijklmnopqrstuvwxyz.wns")
        assert result == ("laptop", "abcdefghijklmnopqrstuvwxyz")

        # Without prefix
        result = parse_scoped_wns_address("my-server.abcdefghijklmnopqrstuvwxyz.wns")
        assert result == ("my-server", "abcdefghijklmnopqrstuvwxyz")

        # Plain address (no scoped name)
        result = parse_scoped_wns_address("wh://abcdefghijklmnopqrstuvwxyz.wns")
        assert result == (None, "abcdefghijklmnopqrstuvwxyz")

    def test_identity_scoped_name(self):
        """Test scoped name on identity."""
        identity = WNSIdentity.generate()
        assert identity.scoped_name is None
        assert identity.full_scoped_address is None

        identity.scoped_name = "laptop"
        assert identity.scoped_name == "laptop"
        assert identity.full_scoped_address == f"wh://laptop.{identity.address}.wns"

    def test_scoped_name_in_advertisement(self):
        """Test scoped name included in advertisement."""
        identity = WNSIdentity.generate()
        identity.scoped_name = "my-server"

        ad = CodeAdvertisement.create(identity, "7-guitar-sunset")
        assert ad.scoped_name == "my-server"
        assert ad.full_scoped_address == f"wh://my-server.{identity.address}.wns"

        # Test serialization
        json_str = ad.to_json()
        ad2 = CodeAdvertisement.from_json(json_str)
        assert ad2.scoped_name == "my-server"


class TestAliases:
    """Tests for local alias functionality."""

    def test_add_and_resolve_alias(self, tmp_path):
        """Test adding and resolving aliases."""
        store = AliasStore(base_path=tmp_path)

        store.add("laptop", "wh://abcdefghijklmnopqrstuvwxyz.wns")
        address = store.resolve("laptop")
        assert address == "wh://abcdefghijklmnopqrstuvwxyz.wns"

    def test_resolve_wns_address_passthrough(self, tmp_path):
        """Test that WNS addresses pass through resolve."""
        store = AliasStore(base_path=tmp_path)

        address = store.resolve("wh://abcdefghijklmnopqrstuvwxyz.wns")
        assert address == "wh://abcdefghijklmnopqrstuvwxyz.wns"

    def test_resolve_unknown(self, tmp_path):
        """Test resolving unknown alias."""
        store = AliasStore(base_path=tmp_path)
        assert store.resolve("unknown") is None

    def test_alias_with_username(self, tmp_path):
        """Test alias with default username."""
        store = AliasStore(base_path=tmp_path)

        store.add(
            "server",
            "wh://abcdefghijklmnopqrstuvwxyz.wns",
            username="admin"
        )

        addr, user = store.resolve_with_username("server")
        assert addr == "wh://abcdefghijklmnopqrstuvwxyz.wns"
        assert user == "admin"

    def test_remove_alias(self, tmp_path):
        """Test removing an alias."""
        store = AliasStore(base_path=tmp_path)

        store.add("laptop", "wh://abcdefghijklmnopqrstuvwxyz.wns")
        assert store.resolve("laptop") is not None

        assert store.remove("laptop") is True
        assert store.resolve("laptop") is None

    def test_list_aliases(self, tmp_path):
        """Test listing aliases."""
        store = AliasStore(base_path=tmp_path)

        store.add("laptop", "wh://abcdefghijklmnopqrstuvwxyz.wns")
        store.add("server", "wh://zyxwvutsrqponmlkjihgfedcba.wns")

        aliases = store.list()
        assert len(aliases) == 2
        names = [a.name for a in aliases]
        assert "laptop" in names
        assert "server" in names


class TestGlobalNames:
    """Tests for global name functionality."""

    def test_is_valid_global_name(self):
        """Test global name validation."""
        # Valid names
        assert is_valid_global_name("laptop") is True
        assert is_valid_global_name("my-server") is True
        assert is_valid_global_name("test_123") is True

        # Invalid names
        assert is_valid_global_name("") is False
        assert is_valid_global_name("a" * 33) is False  # Too long
        assert is_valid_global_name("wns") is False  # Reserved
        assert is_valid_global_name("admin") is False  # Reserved
        # 26-char base32 string (looks like an address)
        assert is_valid_global_name("abcdefghijklmnopqrstuvwxyz") is False

    def test_is_global_name_address(self):
        """Test detecting global name addresses."""
        # Global names
        assert is_global_name_address("wh://laptop.wns") is True
        assert is_global_name_address("wh://my-server.wns") is True

        # NOT global names (scoped or full address)
        assert is_global_name_address("wh://laptop.abcdefghijklmnopqrstuvwxyz.wns") is False
        assert is_global_name_address("wh://abcdefghijklmnopqrstuvwxyz.wns") is False

    def test_parse_global_name(self):
        """Test parsing global name URIs."""
        assert parse_global_name("wh://laptop.wns") == "laptop"
        assert parse_global_name("wh://my-server.wns") == "my-server"

        # Not global names
        assert parse_global_name("wh://laptop.abc123.wns") is None
        assert parse_global_name("7-guitar-sunset") is None

    def test_name_claim_create_and_verify(self):
        """Test creating and verifying a name claim."""
        identity = WNSIdentity.generate()
        claim = NameClaim.create(identity, "my-laptop")

        assert claim.name == "my-laptop"
        assert claim.address == identity.address
        assert claim.verify() is True
        assert claim.verify(expected_name="my-laptop") is True
        assert claim.verify(expected_name="wrong") is False

    def test_name_claim_expiry(self):
        """Test name claim expiry."""
        identity = WNSIdentity.generate()

        # Create with 0 TTL (expired)
        claim = NameClaim.create(identity, "mytest", ttl_seconds=0)
        assert claim.is_expired() is True

        # Create with long TTL
        claim = NameClaim.create(identity, "mytest", ttl_seconds=3600)
        assert claim.is_expired() is False

    def test_name_claim_json_serialization(self):
        """Test name claim JSON serialization."""
        identity = WNSIdentity.generate()
        claim = NameClaim.create(identity, "my-laptop")

        json_str = claim.to_json()
        claim2 = NameClaim.from_json(json_str)

        assert claim2.name == claim.name
        assert claim2.address == claim.address
        assert claim2.verify() is True

    def test_name_claim_store(self, tmp_path):
        """Test NameClaimStore functionality."""
        store = NameClaimStore(base_path=tmp_path)
        identity = WNSIdentity.generate()

        claim = NameClaim.create(identity, "my-laptop")
        store.save_claim(claim)

        loaded = store.load_claim("my-laptop")
        assert loaded is not None
        assert loaded.name == "my-laptop"
        assert loaded.address == identity.address

    def test_name_claim_store_list_and_delete(self, tmp_path):
        """Test listing and deleting claims."""
        store = NameClaimStore(base_path=tmp_path)
        identity = WNSIdentity.generate()

        claim1 = NameClaim.create(identity, "laptop")
        claim2 = NameClaim.create(identity, "server")
        store.save_claim(claim1)
        store.save_claim(claim2)

        claims = store.list_claims()
        assert len(claims) == 2

        assert store.delete_claim("laptop") is True
        claims = store.list_claims()
        assert len(claims) == 1


class TestWNSIdentityAdditional:
    """Additional tests for WNSIdentity."""

    def test_to_dict(self):
        """Test identity to_dict method."""
        identity = WNSIdentity.generate(name="test")
        d = identity.to_dict()

        assert "address" in d
        assert "public_key" in d
        assert d["address"] == identity.address

    def test_from_dict(self):
        """Test identity from_dict method."""
        identity = WNSIdentity.generate(name="test")
        d = identity.to_dict()

        restored = WNSIdentity.from_dict(d)
        assert restored.address == identity.address

    def test_private_key_property(self):
        """Test private_key property."""
        identity = WNSIdentity.generate()
        pk = identity.private_key

        assert pk is not None
        assert len(pk) > 0


class TestWNSIdentityStoreAdditional:
    """Additional tests for WNSIdentityStore."""

    def test_load_nonexistent(self, tmp_path):
        """Test loading nonexistent identity."""
        store = WNSIdentityStore(base_path=tmp_path)
        result = store.load_identity("nonexistent")
        assert result is None

    def test_delete_nonexistent(self, tmp_path):
        """Test deleting nonexistent identity."""
        store = WNSIdentityStore(base_path=tmp_path)
        result = store.delete_identity("nonexistent")
        assert result is False

    def test_empty_list(self, tmp_path):
        """Test listing identities from empty store."""
        store = WNSIdentityStore(base_path=tmp_path)
        identities = store.list_identities()
        assert identities == []


class TestNameClaimAdditional:
    """Additional tests for NameClaim."""

    def test_to_dict(self):
        """Test claim to_dict method."""
        identity = WNSIdentity.generate()
        claim = NameClaim.create(identity, "myname")
        d = claim.to_dict()

        assert "name" in d
        assert "address" in d
        assert d["name"] == "myname"

    def test_from_dict(self):
        """Test claim from_dict method."""
        identity = WNSIdentity.generate()
        claim = NameClaim.create(identity, "myname")
        d = claim.to_dict()

        restored = NameClaim.from_dict(d)
        assert restored.name == "myname"
        assert restored.address == identity.address

    def test_time_remaining(self):
        """Test time_remaining method."""
        identity = WNSIdentity.generate()
        claim = NameClaim.create(identity, "myname", ttl_seconds=3600)

        remaining = claim.time_remaining()
        assert remaining > 3599  # Should be close to 3600


class TestGlobalNamesAdditional:
    """Additional tests for global names."""

    def test_name_with_numbers(self):
        """Test global name with numbers."""
        assert is_valid_global_name("test123") is True
        assert is_valid_global_name("123test") is True

    def test_name_with_underscore(self):
        """Test global name with underscore."""
        assert is_valid_global_name("my_server") is True

    def test_name_single_char(self):
        """Test single character name."""
        assert is_valid_global_name("a") is True

    def test_reserved_names(self):
        """Test reserved names are rejected."""
        reserved = ["wns", "admin", "system", "root", "localhost"]
        for name in reserved:
            assert is_valid_global_name(name) is False

    def test_name_claim_store_overwrite(self, tmp_path):
        """Test overwriting a claim."""
        store = NameClaimStore(base_path=tmp_path)
        identity1 = WNSIdentity.generate()
        identity2 = WNSIdentity.generate()

        claim1 = NameClaim.create(identity1, "myname")
        claim2 = NameClaim.create(identity2, "myname")

        store.save_claim(claim1)
        store.save_claim(claim2)

        loaded = store.load_claim("myname")
        assert loaded.address == identity2.address
