"""
Enterprise Rate Limiting Module.

Implements token bucket rate limiting and quota enforcement:
- Per-IP rate limiting
- Per-identity rate limiting
- Global rate limiting
- Bandwidth throttling
- Concurrent connection limits

Usage:
    limiter = RateLimiter(policy)

    # Check if request is allowed
    try:
        await limiter.acquire(identity="jdoe", source_ip="192.168.1.100")
    except RateLimitExceeded as e:
        print(f"Rate limit exceeded: {e}")

    # Track bandwidth
    limiter.record_bytes(identity="jdoe", bytes=1024)
"""

import asyncio
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Set

from wh.enterprise.policy import Policy, RateLimitConfig, QuotaConfig


logger = logging.getLogger(__name__)


class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded."""

    def __init__(self, message: str, retry_after: Optional[float] = None):
        super().__init__(message)
        self.retry_after = retry_after


class BandwidthQuotaExceeded(Exception):
    """Raised when bandwidth quota is exceeded."""
    pass


class ConnectionLimitExceeded(Exception):
    """Raised when connection limit is exceeded."""
    pass


@dataclass
class TokenBucket:
    """
    Token bucket for rate limiting.

    Allows a certain number of requests per time period,
    with support for bursting.
    """
    capacity: float  # Maximum tokens
    refill_rate: float  # Tokens per second
    tokens: float = field(default=0.0)
    last_update: float = field(default_factory=time.monotonic)

    def __post_init__(self):
        # Start with full bucket
        self.tokens = self.capacity

    def refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.monotonic()
        elapsed = now - self.last_update
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_update = now

    def try_acquire(self, tokens: float = 1.0) -> bool:
        """
        Try to acquire tokens from the bucket.

        Args:
            tokens: Number of tokens to acquire

        Returns:
            True if tokens were acquired
        """
        self.refill()
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

    def time_until_available(self, tokens: float = 1.0) -> float:
        """Get time until tokens will be available."""
        self.refill()
        if self.tokens >= tokens:
            return 0.0
        needed = tokens - self.tokens
        return needed / self.refill_rate


@dataclass
class ConnectionTracker:
    """Tracks active connections and usage."""
    active_connections: int = 0
    connections_today: int = 0
    bytes_today: int = 0
    bytes_this_month: int = 0
    last_reset_day: int = 0
    last_reset_month: int = 0

    def reset_if_needed(self) -> None:
        """Reset daily/monthly counters if needed."""
        now = time.localtime()

        if now.tm_yday != self.last_reset_day:
            self.connections_today = 0
            self.bytes_today = 0
            self.last_reset_day = now.tm_yday

        if now.tm_mon != self.last_reset_month:
            self.bytes_this_month = 0
            self.last_reset_month = now.tm_mon


class RateLimiter:
    """
    Rate limiter with per-IP, per-identity, and global limits.

    Implements:
    - Token bucket rate limiting for requests
    - Sliding window for connection counts
    - Quota tracking for bandwidth and connections
    """

    def __init__(self, policy: Policy):
        self.policy = policy

        # Token buckets: key -> TokenBucket
        self._ip_buckets: Dict[str, TokenBucket] = {}
        self._identity_buckets: Dict[str, TokenBucket] = {}
        self._global_bucket: Optional[TokenBucket] = None

        # Connection tracking: key -> ConnectionTracker
        self._ip_connections: Dict[str, ConnectionTracker] = defaultdict(ConnectionTracker)
        self._identity_connections: Dict[str, ConnectionTracker] = defaultdict(ConnectionTracker)
        self._global_tracker = ConnectionTracker()

        # Active connection sets
        self._active_sessions: Set[str] = set()  # session_id

        # Lock for thread safety
        self._lock = asyncio.Lock()

        # Initialize global bucket from policy
        global_limits = policy.get_rate_limits()
        if global_limits.requests_per_second:
            self._global_bucket = TokenBucket(
                capacity=global_limits.requests_per_second * global_limits.burst_multiplier,
                refill_rate=global_limits.requests_per_second,
            )

    def _get_bucket(
        self,
        buckets: Dict[str, TokenBucket],
        key: str,
        limits: RateLimitConfig,
    ) -> TokenBucket:
        """Get or create a token bucket for the given key."""
        if key not in buckets:
            # Calculate rate from config
            rate = limits.requests_per_second or (limits.requests_per_minute or 60) / 60.0
            capacity = rate * limits.burst_multiplier
            buckets[key] = TokenBucket(capacity=capacity, refill_rate=rate)
        return buckets[key]

    async def acquire(
        self,
        identity: Optional[str] = None,
        source_ip: Optional[str] = None,
        namespace: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> None:
        """
        Acquire permission for a request/connection.

        Args:
            identity: User identity
            source_ip: Source IP address
            namespace: Namespace
            session_id: Session identifier for connection tracking

        Raises:
            RateLimitExceeded: If rate limit is exceeded
            ConnectionLimitExceeded: If connection limit is exceeded
        """
        async with self._lock:
            limits = self.policy.get_rate_limits(identity, source_ip, namespace)
            quotas = self.policy.get_quotas(identity, source_ip, namespace)

            # Check global rate limit
            if self._global_bucket and not self._global_bucket.try_acquire():
                retry_after = self._global_bucket.time_until_available()
                raise RateLimitExceeded("Global rate limit exceeded", retry_after)

            # Check per-IP rate limit
            if source_ip and limits.connections_per_minute:
                ip_bucket = self._get_bucket(self._ip_buckets, source_ip, limits)
                if not ip_bucket.try_acquire():
                    retry_after = ip_bucket.time_until_available()
                    raise RateLimitExceeded(f"IP rate limit exceeded: {source_ip}", retry_after)

            # Check per-identity rate limit
            if identity and limits.connections_per_minute:
                id_bucket = self._get_bucket(self._identity_buckets, identity, limits)
                if not id_bucket.try_acquire():
                    retry_after = id_bucket.time_until_available()
                    raise RateLimitExceeded(f"Identity rate limit exceeded: {identity}", retry_after)

            # Check concurrent connection limits
            if quotas.max_concurrent_connections:
                if source_ip:
                    tracker = self._ip_connections[source_ip]
                    if tracker.active_connections >= quotas.max_concurrent_connections:
                        raise ConnectionLimitExceeded(f"Max connections exceeded for IP: {source_ip}")

                if identity:
                    tracker = self._identity_connections[identity]
                    if quotas.max_sessions_per_identity and tracker.active_connections >= quotas.max_sessions_per_identity:
                        raise ConnectionLimitExceeded(f"Max sessions exceeded for identity: {identity}")

            # Track new connection
            if session_id:
                self._active_sessions.add(session_id)
                self._global_tracker.active_connections += 1
                self._global_tracker.connections_today += 1

                if source_ip:
                    self._ip_connections[source_ip].active_connections += 1
                    self._ip_connections[source_ip].connections_today += 1

                if identity:
                    self._identity_connections[identity].active_connections += 1
                    self._identity_connections[identity].connections_today += 1

    async def release(
        self,
        session_id: str,
        identity: Optional[str] = None,
        source_ip: Optional[str] = None,
    ) -> None:
        """
        Release a connection.

        Args:
            session_id: Session identifier
            identity: User identity
            source_ip: Source IP address
        """
        async with self._lock:
            if session_id in self._active_sessions:
                self._active_sessions.remove(session_id)
                self._global_tracker.active_connections -= 1

                if source_ip and source_ip in self._ip_connections:
                    self._ip_connections[source_ip].active_connections -= 1

                if identity and identity in self._identity_connections:
                    self._identity_connections[identity].active_connections -= 1

    async def check_bandwidth(
        self,
        bytes_to_transfer: int,
        identity: Optional[str] = None,
        source_ip: Optional[str] = None,
        namespace: Optional[str] = None,
    ) -> None:
        """
        Check if a bandwidth transfer is allowed.

        Args:
            bytes_to_transfer: Number of bytes to transfer
            identity: User identity
            source_ip: Source IP address
            namespace: Namespace

        Raises:
            BandwidthQuotaExceeded: If quota is exceeded
        """
        async with self._lock:
            quotas = self.policy.get_quotas(identity, source_ip, namespace)

            # Reset counters if needed
            self._global_tracker.reset_if_needed()

            # Check daily quota
            if quotas.max_transfer_bytes_per_day:
                projected = self._global_tracker.bytes_today + bytes_to_transfer
                if projected > quotas.max_transfer_bytes_per_day:
                    raise BandwidthQuotaExceeded("Daily transfer quota exceeded")

            # Check monthly quota
            if quotas.max_transfer_bytes_per_month:
                projected = self._global_tracker.bytes_this_month + bytes_to_transfer
                if projected > quotas.max_transfer_bytes_per_month:
                    raise BandwidthQuotaExceeded("Monthly transfer quota exceeded")

            # Check per-identity quotas
            if identity:
                tracker = self._identity_connections[identity]
                tracker.reset_if_needed()
                if quotas.max_transfer_bytes_per_day:
                    if tracker.bytes_today + bytes_to_transfer > quotas.max_transfer_bytes_per_day:
                        raise BandwidthQuotaExceeded(f"Daily quota exceeded for {identity}")

    async def record_bytes(
        self,
        bytes_transferred: int,
        identity: Optional[str] = None,
        source_ip: Optional[str] = None,
    ) -> None:
        """
        Record bytes transferred for quota tracking.

        Args:
            bytes_transferred: Number of bytes transferred
            identity: User identity
            source_ip: Source IP address
        """
        async with self._lock:
            self._global_tracker.bytes_today += bytes_transferred
            self._global_tracker.bytes_this_month += bytes_transferred

            if identity:
                self._identity_connections[identity].bytes_today += bytes_transferred
                self._identity_connections[identity].bytes_this_month += bytes_transferred

            if source_ip:
                self._ip_connections[source_ip].bytes_today += bytes_transferred
                self._ip_connections[source_ip].bytes_this_month += bytes_transferred

    def get_stats(self) -> Dict[str, Any]:
        """Get rate limiter statistics."""
        return {
            "active_sessions": len(self._active_sessions),
            "global": {
                "active_connections": self._global_tracker.active_connections,
                "connections_today": self._global_tracker.connections_today,
                "bytes_today": self._global_tracker.bytes_today,
                "bytes_this_month": self._global_tracker.bytes_this_month,
            },
            "by_ip": {
                ip: {
                    "active": t.active_connections,
                    "today": t.connections_today,
                    "bytes_today": t.bytes_today,
                }
                for ip, t in self._ip_connections.items()
            },
            "by_identity": {
                id_: {
                    "active": t.active_connections,
                    "today": t.connections_today,
                    "bytes_today": t.bytes_today,
                }
                for id_, t in self._identity_connections.items()
            },
        }

    async def reset(self) -> None:
        """Reset all rate limiting state."""
        async with self._lock:
            self._ip_buckets.clear()
            self._identity_buckets.clear()
            self._ip_connections.clear()
            self._identity_connections.clear()
            self._active_sessions.clear()
            self._global_tracker = ConnectionTracker()

            # Reinitialize global bucket
            global_limits = self.policy.get_rate_limits()
            if global_limits.requests_per_second:
                self._global_bucket = TokenBucket(
                    capacity=global_limits.requests_per_second * global_limits.burst_multiplier,
                    refill_rate=global_limits.requests_per_second,
                )


class BandwidthThrottler:
    """
    Throttles bandwidth to enforce rate limits.

    Usage:
        throttler = BandwidthThrottler(max_mbps=10.0)

        # Before sending data
        await throttler.throttle(len(data))
    """

    def __init__(
        self,
        max_mbps: Optional[float] = None,
        max_bytes_per_second: Optional[int] = None,
    ):
        if max_mbps:
            self.max_bytes_per_second = int(max_mbps * 1024 * 1024 / 8)
        elif max_bytes_per_second:
            self.max_bytes_per_second = max_bytes_per_second
        else:
            self.max_bytes_per_second = None

        self._bucket: Optional[TokenBucket] = None
        if self.max_bytes_per_second:
            # Allow bursts of up to 1 second of data
            self._bucket = TokenBucket(
                capacity=float(self.max_bytes_per_second),
                refill_rate=float(self.max_bytes_per_second),
            )

    async def throttle(self, bytes_to_send: int) -> None:
        """
        Wait if necessary to maintain bandwidth limit.

        Args:
            bytes_to_send: Number of bytes about to be sent
        """
        if not self._bucket:
            return

        while not self._bucket.try_acquire(float(bytes_to_send)):
            wait_time = self._bucket.time_until_available(float(bytes_to_send))
            await asyncio.sleep(min(wait_time, 0.1))  # Wait in small increments

    async def throttle_stream(self, data: bytes, chunk_size: int = 8192):
        """
        Yield data in throttled chunks.

        Args:
            data: Data to send
            chunk_size: Maximum chunk size

        Yields:
            Data chunks
        """
        offset = 0
        while offset < len(data):
            chunk = data[offset:offset + chunk_size]
            await self.throttle(len(chunk))
            yield chunk
            offset += chunk_size
