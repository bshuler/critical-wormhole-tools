"""Unit tests for enterprise policy module."""

import os
import tempfile

import pytest
import yaml

from wh.enterprise.policy import (
    RateLimitConfig,
    QuotaConfig,
    PolicyRule,
    PolicyConfig,
    Policy,
    load_policy,
    get_default_policy,
    load_default_policy,
)


class TestRateLimitConfig:
    """Tests for RateLimitConfig dataclass."""

    def test_defaults(self):
        """Test default values."""
        config = RateLimitConfig()

        assert config.connections_per_minute is None
        assert config.requests_per_second is None
        assert config.bandwidth_mbps is None
        assert config.burst_multiplier == 2.0

    def test_custom_values(self):
        """Test custom values."""
        config = RateLimitConfig(
            connections_per_minute=10,
            requests_per_second=100.0,
            bandwidth_mbps=50.0,
            burst_multiplier=3.0,
        )

        assert config.connections_per_minute == 10
        assert config.requests_per_second == 100.0
        assert config.bandwidth_mbps == 50.0
        assert config.burst_multiplier == 3.0

    def test_merge(self):
        """Test merging configs."""
        base = RateLimitConfig(
            connections_per_minute=10,
            requests_per_second=100.0,
        )

        override = RateLimitConfig(
            connections_per_minute=20,  # Override
            bandwidth_mbps=50.0,  # New value
        )

        merged = base.merge(override)

        assert merged.connections_per_minute == 20
        assert merged.requests_per_second == 100.0
        assert merged.bandwidth_mbps == 50.0

    def test_from_dict(self):
        """Test creating from dictionary."""
        data = {
            "connections_per_minute": 10,
            "requests_per_second": 100,
            "bandwidth_mbps": 50,
        }

        config = RateLimitConfig.from_dict(data)

        assert config.connections_per_minute == 10
        assert config.requests_per_second == 100
        assert config.bandwidth_mbps == 50


class TestQuotaConfig:
    """Tests for QuotaConfig dataclass."""

    def test_defaults(self):
        """Test default values."""
        config = QuotaConfig()

        assert config.max_concurrent_connections is None
        assert config.max_transfer_bytes_per_day is None

    def test_from_dict_with_sizes(self):
        """Test creating from dict with human-readable sizes."""
        data = {
            "max_concurrent_connections": 50,
            "max_transfer_gb_per_day": 100,  # Should be converted to bytes
            "max_file_size": "10MB",  # Human-readable
        }

        config = QuotaConfig.from_dict(data)

        assert config.max_concurrent_connections == 50
        # Note: max_transfer_gb_per_day maps to max_transfer_bytes_per_day
        assert config.max_file_size_bytes == 10 * 1024 * 1024

    def test_merge(self):
        """Test merging configs."""
        base = QuotaConfig(
            max_concurrent_connections=50,
            max_sessions_per_identity=5,
        )

        override = QuotaConfig(
            max_concurrent_connections=100,  # Override
        )

        merged = base.merge(override)

        assert merged.max_concurrent_connections == 100
        assert merged.max_sessions_per_identity == 5


class TestPolicyRule:
    """Tests for PolicyRule dataclass."""

    def test_match_identity_exact(self):
        """Test exact identity matching."""
        rule = PolicyRule(match={"identity": "admin"})

        assert rule.matches(identity="admin") is True
        assert rule.matches(identity="user") is False

    def test_match_identity_wildcard(self):
        """Test wildcard identity matching."""
        rule = PolicyRule(match={"identity": "admin@*"})

        assert rule.matches(identity="admin@example.com") is True
        assert rule.matches(identity="admin@test.org") is True
        assert rule.matches(identity="user@example.com") is False

    def test_match_identity_suffix_wildcard(self):
        """Test suffix wildcard matching."""
        rule = PolicyRule(match={"identity": "*@example.com"})

        assert rule.matches(identity="admin@example.com") is True
        assert rule.matches(identity="user@example.com") is True
        assert rule.matches(identity="admin@test.org") is False

    def test_match_any_identity(self):
        """Test matching any identity."""
        rule = PolicyRule(match={"identity": "*"})

        assert rule.matches(identity="anyone") is True
        assert rule.matches(identity=None) is True

    def test_match_ip_exact(self):
        """Test exact IP matching."""
        rule = PolicyRule(match={"source_ip": "192.168.1.100"})

        assert rule.matches(source_ip="192.168.1.100") is True
        assert rule.matches(source_ip="192.168.1.101") is False

    def test_match_ip_cidr(self):
        """Test CIDR IP matching."""
        rule = PolicyRule(match={"source_ip": "192.168.0.0/16"})

        assert rule.matches(source_ip="192.168.1.100") is True
        assert rule.matches(source_ip="192.168.255.255") is True
        assert rule.matches(source_ip="10.0.0.1") is False

    def test_match_namespace(self):
        """Test namespace matching."""
        rule = PolicyRule(match={"namespace": "engineering"})

        assert rule.matches(namespace="engineering") is True
        assert rule.matches(namespace="sales") is False

    def test_match_multiple_conditions(self):
        """Test matching multiple conditions."""
        rule = PolicyRule(match={
            "identity": "admin",
            "namespace": "engineering",
        })

        assert rule.matches(identity="admin", namespace="engineering") is True
        assert rule.matches(identity="admin", namespace="sales") is False
        assert rule.matches(identity="user", namespace="engineering") is False

    def test_from_dict(self):
        """Test creating from dictionary."""
        data = {
            "match": {"identity": "admin"},
            "rate_limits": {"connections_per_minute": 100},
            "allow": ["*"],
            "priority": 10,
        }

        rule = PolicyRule.from_dict(data)

        assert rule.match == {"identity": "admin"}
        assert rule.rate_limits.connections_per_minute == 100
        assert "*" in rule.allow
        assert rule.priority == 10


class TestPolicy:
    """Tests for Policy class."""

    def test_get_rate_limits_default(self):
        """Test getting default rate limits."""
        config = PolicyConfig(
            rate_limits=RateLimitConfig(connections_per_minute=10)
        )
        policy = Policy(config)

        limits = policy.get_rate_limits()

        assert limits.connections_per_minute == 10

    def test_get_rate_limits_with_rule(self):
        """Test getting rate limits from matching rule."""
        config = PolicyConfig(
            rate_limits=RateLimitConfig(connections_per_minute=10),
            rules=[
                PolicyRule(
                    match={"identity": "admin"},
                    rate_limits=RateLimitConfig(connections_per_minute=100),
                )
            ]
        )
        policy = Policy(config)

        # Default limits for regular user
        limits = policy.get_rate_limits(identity="user")
        assert limits.connections_per_minute == 10

        # Higher limits for admin
        limits = policy.get_rate_limits(identity="admin")
        assert limits.connections_per_minute == 100

    def test_get_quotas_default(self):
        """Test getting default quotas."""
        config = PolicyConfig(
            quotas=QuotaConfig(max_concurrent_connections=50)
        )
        policy = Policy(config)

        quotas = policy.get_quotas()

        assert quotas.max_concurrent_connections == 50

    def test_is_action_allowed(self):
        """Test checking if action is allowed."""
        config = PolicyConfig(
            rules=[
                PolicyRule(
                    match={"identity": "guest"},
                    deny=["ssh", "file_transfer"],
                    priority=10,
                ),
                PolicyRule(
                    match={"identity": "admin"},
                    allow=["*"],
                    priority=10,
                ),
            ]
        )
        policy = Policy(config)

        # Guest is denied ssh
        assert policy.is_action_allowed("ssh", identity="guest") is False
        assert policy.is_action_allowed("file_transfer", identity="guest") is False

        # Guest is allowed other actions (not in deny list)
        assert policy.is_action_allowed("read", identity="guest") is True

        # Admin is allowed everything
        assert policy.is_action_allowed("ssh", identity="admin") is True
        assert policy.is_action_allowed("file_transfer", identity="admin") is True

        # Unknown user allowed by default
        assert policy.is_action_allowed("ssh", identity="unknown") is True

    def test_rule_priority(self):
        """Test that higher priority rules are evaluated first."""
        config = PolicyConfig(
            rules=[
                PolicyRule(
                    match={"identity": "*"},
                    rate_limits=RateLimitConfig(connections_per_minute=10),
                    priority=0,  # Lower priority
                ),
                PolicyRule(
                    match={"identity": "admin"},
                    rate_limits=RateLimitConfig(connections_per_minute=100),
                    priority=10,  # Higher priority
                ),
            ]
        )
        policy = Policy(config)

        # Admin should get high limits (higher priority rule wins)
        limits = policy.get_rate_limits(identity="admin")
        assert limits.connections_per_minute == 100

    def test_get_default(self):
        """Test getting default values."""
        config = PolicyConfig(
            defaults={
                "auth_required": True,
                "namespace": "default",
            }
        )
        policy = Policy(config)

        assert policy.get_default("auth_required") is True
        assert policy.get_default("namespace") == "default"
        assert policy.get_default("unknown", "fallback") == "fallback"


class TestLoadPolicy:
    """Tests for policy loading functions."""

    @pytest.fixture
    def temp_policy_file(self):
        """Create a temporary policy file."""
        policy_data = {
            "rate_limits": {
                "connections_per_minute": 10,
                "bandwidth_mbps": 100,
            },
            "quotas": {
                "max_concurrent_connections": 50,
            },
            "rules": [
                {
                    "match": {"identity": "admin"},
                    "rate_limits": {"connections_per_minute": 100},
                    "allow": ["*"],
                }
            ],
            "defaults": {
                "auth_required": False,
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.safe_dump(policy_data, f)
            temp_path = f.name

        yield temp_path

        os.unlink(temp_path)

    def test_load_policy(self, temp_policy_file):
        """Test loading policy from file."""
        policy = load_policy(temp_policy_file)

        limits = policy.get_rate_limits()
        assert limits.connections_per_minute == 10
        assert limits.bandwidth_mbps == 100

        quotas = policy.get_quotas()
        assert quotas.max_concurrent_connections == 50

    def test_load_policy_with_rules(self, temp_policy_file):
        """Test loading policy with rules."""
        policy = load_policy(temp_policy_file)

        # Admin gets higher limits
        admin_limits = policy.get_rate_limits(identity="admin")
        assert admin_limits.connections_per_minute == 100

    def test_load_policy_missing_file(self):
        """Test loading from non-existent file."""
        policy = load_policy("/nonexistent/path/policy.yml")

        # Should return default policy
        limits = policy.get_rate_limits()
        assert limits.connections_per_minute is None

    def test_get_default_policy(self):
        """Test getting default policy."""
        policy = get_default_policy()

        assert policy is not None
        limits = policy.get_rate_limits()
        assert limits.connections_per_minute is None

    def test_load_default_policy_no_files(self, tmp_path, monkeypatch):
        """Test loading default policy when no files exist."""
        # Patch default paths to non-existent directories
        import wh.enterprise.policy as policy_module
        monkeypatch.setattr(
            policy_module,
            "DEFAULT_POLICY_PATHS",
            [tmp_path / "nonexistent.yml"]
        )

        policy = load_default_policy()
        assert policy is not None


class TestPolicyConfigFromDict:
    """Tests for PolicyConfig.from_dict."""

    def test_empty_dict(self):
        """Test creating from empty dictionary."""
        config = PolicyConfig.from_dict({})

        assert config.rate_limits is not None
        assert config.quotas is not None
        assert len(config.rules) == 0

    def test_full_dict(self):
        """Test creating from full dictionary."""
        data = {
            "rate_limits": {
                "connections_per_minute": 10,
            },
            "quotas": {
                "max_concurrent_connections": 50,
            },
            "rules": [
                {"match": {"identity": "admin"}},
            ],
            "defaults": {
                "key": "value",
            }
        }

        config = PolicyConfig.from_dict(data)

        assert config.rate_limits.connections_per_minute == 10
        assert config.quotas.max_concurrent_connections == 50
        assert len(config.rules) == 1
        assert config.defaults["key"] == "value"
