"""
Enterprise Policy Module.

Defines and loads policy configurations for rate limiting, quotas,
and access control. Policies are defined in YAML format.

Policy file format (/etc/wh/policy.yml):
    rate_limits:
      connections_per_minute: 10
      requests_per_second: 100
      bandwidth_mbps: 100

    quotas:
      max_concurrent_connections: 50
      max_transfer_gb_per_day: 100
      max_sessions_per_identity: 5

    rules:
      - match:
          identity: "admin@*"
        allow:
          - "*"
      - match:
          source_ip: "192.168.0.0/16"
        rate_limits:
          connections_per_minute: 50

    defaults:
      auth_required: false
      namespace: "default"

Usage:
    policy = load_policy("/etc/wh/policy.yml")
    limits = policy.get_rate_limits(identity="jdoe", source_ip="192.168.1.100")
"""

import logging
import os
from dataclasses import dataclass, field
from ipaddress import ip_address, ip_network
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml


logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Rate limit configuration."""
    connections_per_minute: Optional[int] = None
    connections_per_hour: Optional[int] = None
    requests_per_second: Optional[float] = None
    requests_per_minute: Optional[int] = None
    bandwidth_mbps: Optional[float] = None
    burst_multiplier: float = 2.0  # Allow bursts up to N * limit

    def merge(self, other: "RateLimitConfig") -> "RateLimitConfig":
        """Merge with another config, taking non-None values from other."""
        return RateLimitConfig(
            connections_per_minute=other.connections_per_minute or self.connections_per_minute,
            connections_per_hour=other.connections_per_hour or self.connections_per_hour,
            requests_per_second=other.requests_per_second or self.requests_per_second,
            requests_per_minute=other.requests_per_minute or self.requests_per_minute,
            bandwidth_mbps=other.bandwidth_mbps or self.bandwidth_mbps,
            burst_multiplier=other.burst_multiplier if other.burst_multiplier != 2.0 else self.burst_multiplier,
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RateLimitConfig":
        """Create from dictionary."""
        return cls(
            connections_per_minute=data.get("connections_per_minute"),
            connections_per_hour=data.get("connections_per_hour"),
            requests_per_second=data.get("requests_per_second"),
            requests_per_minute=data.get("requests_per_minute"),
            bandwidth_mbps=data.get("bandwidth_mbps"),
            burst_multiplier=data.get("burst_multiplier", 2.0),
        )


@dataclass
class QuotaConfig:
    """Quota configuration."""
    max_concurrent_connections: Optional[int] = None
    max_connections_per_day: Optional[int] = None
    max_transfer_bytes_per_day: Optional[int] = None
    max_transfer_bytes_per_month: Optional[int] = None
    max_sessions_per_identity: Optional[int] = None
    max_file_size_bytes: Optional[int] = None

    def merge(self, other: "QuotaConfig") -> "QuotaConfig":
        """Merge with another config, taking non-None values from other."""
        return QuotaConfig(
            max_concurrent_connections=other.max_concurrent_connections or self.max_concurrent_connections,
            max_connections_per_day=other.max_connections_per_day or self.max_connections_per_day,
            max_transfer_bytes_per_day=other.max_transfer_bytes_per_day or self.max_transfer_bytes_per_day,
            max_transfer_bytes_per_month=other.max_transfer_bytes_per_month or self.max_transfer_bytes_per_month,
            max_sessions_per_identity=other.max_sessions_per_identity or self.max_sessions_per_identity,
            max_file_size_bytes=other.max_file_size_bytes or self.max_file_size_bytes,
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QuotaConfig":
        """Create from dictionary."""
        # Handle human-readable sizes
        def parse_size(value: Any) -> Optional[int]:
            if value is None:
                return None
            if isinstance(value, int):
                return value
            if isinstance(value, str):
                value = value.strip().upper()
                # Sort multipliers by suffix length (longest first) to match correctly
                multipliers = [
                    ("TB", 1024**4),
                    ("GB", 1024**3),
                    ("MB", 1024**2),
                    ("KB", 1024),
                    ("B", 1),
                ]
                for suffix, mult in multipliers:
                    if value.endswith(suffix):
                        num_str = value[:-len(suffix)].strip()
                        return int(float(num_str) * mult)
                return int(value)
            return None

        return cls(
            max_concurrent_connections=data.get("max_concurrent_connections"),
            max_connections_per_day=data.get("max_connections_per_day"),
            max_transfer_bytes_per_day=parse_size(data.get("max_transfer_gb_per_day", data.get("max_transfer_bytes_per_day"))),
            max_transfer_bytes_per_month=parse_size(data.get("max_transfer_bytes_per_month")),
            max_sessions_per_identity=data.get("max_sessions_per_identity"),
            max_file_size_bytes=parse_size(data.get("max_file_size_bytes", data.get("max_file_size"))),
        )


@dataclass
class PolicyRule:
    """A single policy rule."""
    match: Dict[str, str]  # Conditions to match
    rate_limits: Optional[RateLimitConfig] = None
    quotas: Optional[QuotaConfig] = None
    allow: List[str] = field(default_factory=list)  # Allowed actions
    deny: List[str] = field(default_factory=list)   # Denied actions
    priority: int = 0  # Higher = evaluated first

    def matches(
        self,
        identity: Optional[str] = None,
        source_ip: Optional[str] = None,
        namespace: Optional[str] = None,
    ) -> bool:
        """Check if this rule matches the given context."""
        for key, pattern in self.match.items():
            if key == "identity":
                if not self._match_pattern(identity, pattern):
                    return False
            elif key == "source_ip":
                if not self._match_ip(source_ip, pattern):
                    return False
            elif key == "namespace":
                if not self._match_pattern(namespace, pattern):
                    return False
        return True

    def _match_pattern(self, value: Optional[str], pattern: str) -> bool:
        """Match a value against a pattern with wildcards."""
        if value is None:
            return pattern == "*"

        if pattern == "*":
            return True

        if pattern.startswith("*"):
            return value.endswith(pattern[1:])
        if pattern.endswith("*"):
            return value.startswith(pattern[:-1])

        return value == pattern

    def _match_ip(self, ip: Optional[str], pattern: str) -> bool:
        """Match an IP address against a pattern (CIDR or exact)."""
        if ip is None:
            return pattern == "*"

        if pattern == "*":
            return True

        try:
            addr = ip_address(ip)
            if "/" in pattern:
                return addr in ip_network(pattern, strict=False)
            return str(addr) == pattern
        except ValueError:
            return False

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PolicyRule":
        """Create from dictionary."""
        rate_limits = None
        quotas = None

        if "rate_limits" in data:
            rate_limits = RateLimitConfig.from_dict(data["rate_limits"])
        if "quotas" in data:
            quotas = QuotaConfig.from_dict(data["quotas"])

        return cls(
            match=data.get("match", {}),
            rate_limits=rate_limits,
            quotas=quotas,
            allow=data.get("allow", []),
            deny=data.get("deny", []),
            priority=data.get("priority", 0),
        )


@dataclass
class PolicyConfig:
    """Complete policy configuration."""
    rate_limits: RateLimitConfig = field(default_factory=RateLimitConfig)
    quotas: QuotaConfig = field(default_factory=QuotaConfig)
    rules: List[PolicyRule] = field(default_factory=list)
    defaults: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PolicyConfig":
        """Create from dictionary."""
        rate_limits = RateLimitConfig()
        quotas = QuotaConfig()
        rules = []

        if "rate_limits" in data:
            rate_limits = RateLimitConfig.from_dict(data["rate_limits"])
        if "quotas" in data:
            quotas = QuotaConfig.from_dict(data["quotas"])
        if "rules" in data:
            rules = [PolicyRule.from_dict(r) for r in data["rules"]]

        return cls(
            rate_limits=rate_limits,
            quotas=quotas,
            rules=rules,
            defaults=data.get("defaults", {}),
        )


class Policy:
    """
    Policy manager that evaluates rules and returns effective limits.

    Rules are evaluated in priority order (highest first), and the first
    matching rule's limits are merged with defaults.
    """

    def __init__(self, config: PolicyConfig):
        self.config = config
        # Sort rules by priority (highest first)
        self._sorted_rules = sorted(config.rules, key=lambda r: r.priority, reverse=True)

    def get_rate_limits(
        self,
        identity: Optional[str] = None,
        source_ip: Optional[str] = None,
        namespace: Optional[str] = None,
    ) -> RateLimitConfig:
        """
        Get effective rate limits for the given context.

        Args:
            identity: User identity
            source_ip: Source IP address
            namespace: Namespace

        Returns:
            Merged RateLimitConfig
        """
        limits = self.config.rate_limits

        for rule in self._sorted_rules:
            if rule.matches(identity, source_ip, namespace):
                if rule.rate_limits:
                    limits = limits.merge(rule.rate_limits)
                break  # First match wins

        return limits

    def get_quotas(
        self,
        identity: Optional[str] = None,
        source_ip: Optional[str] = None,
        namespace: Optional[str] = None,
    ) -> QuotaConfig:
        """
        Get effective quotas for the given context.

        Args:
            identity: User identity
            source_ip: Source IP address
            namespace: Namespace

        Returns:
            Merged QuotaConfig
        """
        quotas = self.config.quotas

        for rule in self._sorted_rules:
            if rule.matches(identity, source_ip, namespace):
                if rule.quotas:
                    quotas = quotas.merge(rule.quotas)
                break  # First match wins

        return quotas

    def is_action_allowed(
        self,
        action: str,
        identity: Optional[str] = None,
        source_ip: Optional[str] = None,
        namespace: Optional[str] = None,
    ) -> bool:
        """
        Check if an action is allowed for the given context.

        Args:
            action: Action to check (e.g., "ssh", "file_transfer")
            identity: User identity
            source_ip: Source IP address
            namespace: Namespace

        Returns:
            True if action is allowed
        """
        for rule in self._sorted_rules:
            if rule.matches(identity, source_ip, namespace):
                # Check explicit deny first
                if action in rule.deny or "*" in rule.deny:
                    return False
                # Check explicit allow
                if action in rule.allow or "*" in rule.allow:
                    return True

        # Default: allow if no rule matched
        return True

    def get_default(self, key: str, default: Any = None) -> Any:
        """Get a default value from config."""
        return self.config.defaults.get(key, default)


def load_policy(path: Union[str, Path]) -> Policy:
    """
    Load policy from a YAML file.

    Args:
        path: Path to policy YAML file

    Returns:
        Policy instance

    Raises:
        FileNotFoundError: If policy file doesn't exist
        yaml.YAMLError: If YAML is invalid
    """
    path = Path(path)

    if not path.exists():
        logger.warning(f"Policy file not found: {path}, using defaults")
        return Policy(PolicyConfig())

    with open(path, "r") as f:
        data = yaml.safe_load(f) or {}

    config = PolicyConfig.from_dict(data)
    logger.info(f"Loaded policy from {path}: {len(config.rules)} rules")

    return Policy(config)


def get_default_policy() -> Policy:
    """
    Get the default policy (no restrictions).

    Returns:
        Policy with no limits
    """
    return Policy(PolicyConfig())


# Default policy file locations
DEFAULT_POLICY_PATHS = [
    Path("/etc/wh/policy.yml"),
    Path("/etc/wh/policy.yaml"),
    Path.home() / ".wh" / "policy.yml",
    Path.home() / ".wh" / "policy.yaml",
]


def load_default_policy() -> Policy:
    """
    Load policy from default locations.

    Tries each location in order, returns first found or default.
    """
    for path in DEFAULT_POLICY_PATHS:
        if path.exists():
            return load_policy(path)

    return get_default_policy()
