"""Integration tests for WNS advertisement module."""

import json
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock
import pytest


class TestCodeAdvertisement:
    """Tests for CodeAdvertisement class."""

    @pytest.fixture
    def mock_identity(self):
        """Create a mock identity that can sign."""
        identity = MagicMock()
        identity.can_sign = True
        identity.address = "abcdefghijklmnopqrstuvwxyz"
        identity.public_key = b"mock_public_key_bytes_here"
        identity.sign = MagicMock(return_value=b"mock_signature")
        identity.scoped_name = None
        return identity

    def test_create_advertisement(self, mock_identity):
        """Test creating an advertisement."""
        from wh.wns.advertisement import CodeAdvertisement

        ad = CodeAdvertisement.create(
            identity=mock_identity,
            code="7-guitar-sunset",
            ttl_seconds=300,
        )

        assert ad.address == "abcdefghijklmnopqrstuvwxyz"
        assert ad.code == "7-guitar-sunset"
        assert ad.public_key == b"mock_public_key_bytes_here"
        assert ad.signature == b"mock_signature"
        mock_identity.sign.assert_called_once()

    def test_create_requires_signing_capability(self):
        """Test create fails without signing capability."""
        from wh.wns.advertisement import CodeAdvertisement

        identity = MagicMock()
        identity.can_sign = False

        with pytest.raises(ValueError, match="must have private key"):
            CodeAdvertisement.create(identity, "7-test")

    def test_is_expired(self, mock_identity):
        """Test is_expired method."""
        from wh.wns.advertisement import CodeAdvertisement

        # Create with very short TTL
        ad = CodeAdvertisement.create(
            identity=mock_identity,
            code="7-test",
            ttl_seconds=0,  # Expires immediately
        )

        # Should be expired immediately
        assert ad.is_expired() is True

    def test_not_expired(self, mock_identity):
        """Test advertisement is not expired."""
        from wh.wns.advertisement import CodeAdvertisement

        ad = CodeAdvertisement.create(
            identity=mock_identity,
            code="7-test",
            ttl_seconds=3600,  # 1 hour
        )

        assert ad.is_expired() is False

    def test_time_remaining(self, mock_identity):
        """Test time_remaining method."""
        from wh.wns.advertisement import CodeAdvertisement

        ad = CodeAdvertisement.create(
            identity=mock_identity,
            code="7-test",
            ttl_seconds=300,
        )

        remaining = ad.time_remaining()
        assert remaining > 299  # Should be close to 300

    def test_to_json(self, mock_identity):
        """Test JSON serialization."""
        from wh.wns.advertisement import CodeAdvertisement

        ad = CodeAdvertisement.create(
            identity=mock_identity,
            code="7-test",
        )

        json_str = ad.to_json()
        data = json.loads(json_str)

        assert data["address"] == "abcdefghijklmnopqrstuvwxyz"
        assert data["code"] == "7-test"
        assert "timestamp" in data
        assert "expires" in data
        assert "public_key" in data
        assert "signature" in data

    def test_to_dict(self, mock_identity):
        """Test dictionary serialization."""
        from wh.wns.advertisement import CodeAdvertisement

        ad = CodeAdvertisement.create(
            identity=mock_identity,
            code="7-test",
        )

        data = ad.to_dict()

        assert data["version"] == 1
        assert data["address"] == "abcdefghijklmnopqrstuvwxyz"
        assert data["code"] == "7-test"

    def test_to_dict_with_scoped_name(self, mock_identity):
        """Test dictionary serialization with scoped name."""
        from wh.wns.advertisement import CodeAdvertisement

        mock_identity.scoped_name = "laptop"

        ad = CodeAdvertisement.create(
            identity=mock_identity,
            code="7-test",
        )

        data = ad.to_dict()

        assert data["scoped_name"] == "laptop"

    def test_from_dict(self, mock_identity):
        """Test deserialization from dictionary."""
        from wh.wns.advertisement import CodeAdvertisement

        ad = CodeAdvertisement.create(
            identity=mock_identity,
            code="7-test",
        )

        data = ad.to_dict()
        restored = CodeAdvertisement.from_dict(data)

        assert restored.address == ad.address
        assert restored.code == ad.code
        assert restored.public_key == ad.public_key

    def test_from_json(self, mock_identity):
        """Test deserialization from JSON."""
        from wh.wns.advertisement import CodeAdvertisement

        ad = CodeAdvertisement.create(
            identity=mock_identity,
            code="7-test",
        )

        json_str = ad.to_json()
        restored = CodeAdvertisement.from_json(json_str)

        assert restored.address == ad.address
        assert restored.code == ad.code

    def test_full_address_property(self, mock_identity):
        """Test full_address property."""
        from wh.wns.advertisement import CodeAdvertisement

        ad = CodeAdvertisement.create(
            identity=mock_identity,
            code="7-test",
        )

        assert ad.full_address == "wh://abcdefghijklmnopqrstuvwxyz.wns"

    def test_full_scoped_address_property(self, mock_identity):
        """Test full_scoped_address property."""
        from wh.wns.advertisement import CodeAdvertisement

        mock_identity.scoped_name = "laptop"

        ad = CodeAdvertisement.create(
            identity=mock_identity,
            code="7-test",
        )

        assert ad.full_scoped_address == "wh://laptop.abcdefghijklmnopqrstuvwxyz.wns"

    def test_full_scoped_address_none_without_name(self, mock_identity):
        """Test full_scoped_address is None without scoped name."""
        from wh.wns.advertisement import CodeAdvertisement

        ad = CodeAdvertisement.create(
            identity=mock_identity,
            code="7-test",
        )

        assert ad.full_scoped_address is None

    def test_str_representation(self, mock_identity):
        """Test string representation."""
        from wh.wns.advertisement import CodeAdvertisement

        ad = CodeAdvertisement.create(
            identity=mock_identity,
            code="7-test",
            ttl_seconds=300,
        )

        str_repr = str(ad)
        assert "CodeAdvertisement" in str_repr
        assert "7-test" in str_repr
        assert "remaining" in str_repr

    def test_str_representation_expired(self, mock_identity):
        """Test string representation when expired."""
        from wh.wns.advertisement import CodeAdvertisement

        ad = CodeAdvertisement.create(
            identity=mock_identity,
            code="7-test",
            ttl_seconds=0,  # Expires immediately
        )

        str_repr = str(ad)
        assert "EXPIRED" in str_repr


class TestCodeAdvertisementVerification:
    """Tests for advertisement verification."""

    def test_verify_expired_fails(self):
        """Test verification fails for expired advertisement."""
        from wh.wns.advertisement import CodeAdvertisement

        # Create an expired advertisement manually
        now = datetime.now(timezone.utc)
        past = now - timedelta(hours=1)

        ad = CodeAdvertisement(
            address="abcdefghijklmnopqrstuvwxyz",
            code="7-test",
            timestamp=past - timedelta(hours=1),
            expires=past,  # Already expired
            public_key=b"key",
            signature=b"sig",
        )

        assert ad.verify() is False

    def test_create_sign_message(self):
        """Test _create_sign_message static method."""
        from wh.wns.advertisement import CodeAdvertisement

        now = datetime.now(timezone.utc)
        later = datetime.fromtimestamp(now.timestamp() + 300, tz=timezone.utc)

        message = CodeAdvertisement._create_sign_message(
            address="testaddr",
            code="7-test",
            timestamp=now,
            expires=later,
        )

        assert b"WNS-ADV-v1" in message
        assert b"testaddr" in message
        assert b"7-test" in message
