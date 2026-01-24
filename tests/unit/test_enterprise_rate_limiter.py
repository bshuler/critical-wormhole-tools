"""Unit tests for enterprise rate limiter module."""

import time

import pytest

from wh.enterprise.policy import (
    Policy,
    PolicyConfig,
    RateLimitConfig,
    QuotaConfig,
)
from wh.enterprise.rate_limiter import (
    TokenBucket,
    ConnectionTracker,
    RateLimiter,
    BandwidthThrottler,
    RateLimitExceeded,
    BandwidthQuotaExceeded,
    ConnectionLimitExceeded,
)


class TestTokenBucket:
    """Tests for TokenBucket class."""

    def test_initial_state(self):
        """Test bucket starts full."""
        bucket = TokenBucket(capacity=10.0, refill_rate=1.0)
        assert bucket.tokens == 10.0

    def test_acquire_success(self):
        """Test successful token acquisition."""
        bucket = TokenBucket(capacity=10.0, refill_rate=1.0)

        assert bucket.try_acquire(5.0) is True
        assert bucket.tokens == 5.0

    def test_acquire_failure(self):
        """Test failed token acquisition."""
        bucket = TokenBucket(capacity=10.0, refill_rate=1.0)

        # Empty the bucket
        bucket.tokens = 0.0
        bucket.last_update = time.monotonic()

        assert bucket.try_acquire(5.0) is False

    def test_refill(self):
        """Test token refill over time."""
        bucket = TokenBucket(capacity=10.0, refill_rate=10.0)  # 10 tokens/sec

        # Empty the bucket
        bucket.tokens = 0.0
        bucket.last_update = time.monotonic()

        # Wait a bit
        time.sleep(0.1)

        bucket.refill()
        assert bucket.tokens >= 0.5  # Should have refilled some

    def test_capacity_limit(self):
        """Test bucket doesn't exceed capacity."""
        bucket = TokenBucket(capacity=10.0, refill_rate=100.0)

        # Wait for refill
        time.sleep(0.1)
        bucket.refill()

        assert bucket.tokens <= 10.0

    def test_time_until_available(self):
        """Test calculating wait time."""
        bucket = TokenBucket(capacity=10.0, refill_rate=10.0)

        # Empty the bucket
        bucket.tokens = 0.0
        bucket.last_update = time.monotonic()

        # Should need to wait 0.5 seconds for 5 tokens at 10/sec
        wait_time = bucket.time_until_available(5.0)
        assert 0.4 <= wait_time <= 0.6


class TestConnectionTracker:
    """Tests for ConnectionTracker class."""

    def test_initial_state(self):
        """Test initial state."""
        tracker = ConnectionTracker()

        assert tracker.active_connections == 0
        assert tracker.connections_today == 0
        assert tracker.bytes_today == 0

    def test_reset_if_needed(self):
        """Test daily reset."""
        tracker = ConnectionTracker()
        tracker.connections_today = 100
        tracker.bytes_today = 1000000
        tracker.last_reset_day = 0  # Force reset

        tracker.reset_if_needed()

        # After reset
        assert tracker.connections_today == 0
        assert tracker.bytes_today == 0


class TestRateLimiter:
    """Tests for RateLimiter class."""

    @pytest.fixture
    def policy(self):
        """Create a test policy."""
        config = PolicyConfig(
            rate_limits=RateLimitConfig(
                connections_per_minute=10,
                requests_per_second=100.0,
            ),
            quotas=QuotaConfig(
                max_concurrent_connections=5,
                max_sessions_per_identity=3,
            ),
        )
        return Policy(config)

    @pytest.mark.asyncio
    async def test_acquire_success(self, policy):
        """Test successful acquisition."""
        limiter = RateLimiter(policy)

        await limiter.acquire(
            identity="jdoe",
            source_ip="192.168.1.100",
            session_id="session1",
        )

        stats = limiter.get_stats()
        assert stats["active_sessions"] == 1

    @pytest.mark.asyncio
    async def test_release(self, policy):
        """Test releasing a session."""
        limiter = RateLimiter(policy)

        await limiter.acquire(
            identity="jdoe",
            source_ip="192.168.1.100",
            session_id="session1",
        )

        await limiter.release(
            session_id="session1",
            identity="jdoe",
            source_ip="192.168.1.100",
        )

        stats = limiter.get_stats()
        assert stats["active_sessions"] == 0

    @pytest.mark.asyncio
    async def test_connection_limit_exceeded(self, policy):
        """Test connection limit exceeded (per-identity session limit)."""
        limiter = RateLimiter(policy)

        # Open max sessions for identity (max_sessions_per_identity=3)
        for i in range(3):
            await limiter.acquire(
                identity="jdoe",
                source_ip=f"192.168.1.{i}",  # Different IPs
                session_id=f"session{i}",
            )

        # Next should fail (identity limit exceeded)
        with pytest.raises(ConnectionLimitExceeded):
            await limiter.acquire(
                identity="jdoe",
                source_ip="192.168.1.100",
                session_id="session_overflow",
            )

    @pytest.mark.asyncio
    async def test_identity_session_limit(self, policy):
        """Test per-identity session limit."""
        limiter = RateLimiter(policy)

        # Open max sessions for identity
        for i in range(3):
            await limiter.acquire(
                identity="jdoe",
                source_ip=f"192.168.1.{i}",  # Different IPs
                session_id=f"session{i}",
            )

        # Next should fail for same identity
        with pytest.raises(ConnectionLimitExceeded):
            await limiter.acquire(
                identity="jdoe",
                source_ip="192.168.1.200",
                session_id="session_overflow",
            )

    @pytest.mark.asyncio
    async def test_record_bytes(self, policy):
        """Test recording bytes transferred."""
        limiter = RateLimiter(policy)

        await limiter.record_bytes(
            bytes_transferred=1024,
            identity="jdoe",
            source_ip="192.168.1.100",
        )

        stats = limiter.get_stats()
        assert stats["global"]["bytes_today"] == 1024

    @pytest.mark.asyncio
    async def test_bandwidth_quota_exceeded(self, policy):
        """Test bandwidth quota exceeded."""
        import time

        # Create policy with bandwidth limit
        config = PolicyConfig(
            quotas=QuotaConfig(
                max_transfer_bytes_per_day=1000,  # 1KB limit
            ),
        )
        limited_policy = Policy(config)
        limiter = RateLimiter(limited_policy)

        # Initialize the tracker's last_reset_day so it doesn't reset
        now = time.localtime()
        limiter._global_tracker.last_reset_day = now.tm_yday
        limiter._global_tracker.last_reset_month = now.tm_mon

        # Record bytes to use up most of the quota
        await limiter.record_bytes(bytes_transferred=800)

        # Verify bytes were recorded
        assert limiter._global_tracker.bytes_today == 800

        # Trying to transfer more than remaining should fail
        with pytest.raises(BandwidthQuotaExceeded):
            await limiter.check_bandwidth(bytes_to_transfer=500)

    @pytest.mark.asyncio
    async def test_reset(self, policy):
        """Test resetting limiter state."""
        limiter = RateLimiter(policy)

        await limiter.acquire(
            identity="jdoe",
            session_id="session1",
        )

        await limiter.reset()

        stats = limiter.get_stats()
        assert stats["active_sessions"] == 0

    @pytest.mark.asyncio
    async def test_stats(self, policy):
        """Test getting statistics."""
        limiter = RateLimiter(policy)

        await limiter.acquire(
            identity="jdoe",
            source_ip="192.168.1.100",
            session_id="session1",
        )

        await limiter.record_bytes(bytes_transferred=1024, identity="jdoe")

        stats = limiter.get_stats()

        assert stats["active_sessions"] == 1
        assert stats["global"]["active_connections"] == 1
        assert stats["global"]["bytes_today"] == 1024
        assert "jdoe" in stats["by_identity"]


class TestBandwidthThrottler:
    """Tests for BandwidthThrottler class."""

    def test_init_with_mbps(self):
        """Test initialization with Mbps."""
        throttler = BandwidthThrottler(max_mbps=10.0)
        expected = int(10.0 * 1024 * 1024 / 8)  # 10 Mbps in bytes/sec
        assert throttler.max_bytes_per_second == expected

    def test_init_with_bytes(self):
        """Test initialization with bytes/sec."""
        throttler = BandwidthThrottler(max_bytes_per_second=1024000)
        assert throttler.max_bytes_per_second == 1024000

    def test_init_no_limit(self):
        """Test initialization with no limit."""
        throttler = BandwidthThrottler()
        assert throttler.max_bytes_per_second is None

    @pytest.mark.asyncio
    async def test_throttle_no_limit(self):
        """Test throttling with no limit."""
        throttler = BandwidthThrottler()

        # Should return immediately
        start = time.monotonic()
        await throttler.throttle(1000000)
        elapsed = time.monotonic() - start

        assert elapsed < 0.1  # Should be nearly instant

    @pytest.mark.asyncio
    async def test_throttle_stream(self):
        """Test throttled streaming."""
        throttler = BandwidthThrottler(max_bytes_per_second=10000)  # 10KB/s

        data = b"x" * 1000  # 1KB
        chunks = []

        async for chunk in throttler.throttle_stream(data, chunk_size=100):
            chunks.append(chunk)

        assert len(chunks) == 10
        assert b"".join(chunks) == data


class TestRateLimitExceptions:
    """Tests for rate limit exception classes."""

    def test_rate_limit_exceeded(self):
        """Test RateLimitExceeded exception."""
        exc = RateLimitExceeded("Too many requests", retry_after=5.0)

        assert str(exc) == "Too many requests"
        assert exc.retry_after == 5.0

    def test_bandwidth_quota_exceeded(self):
        """Test BandwidthQuotaExceeded exception."""
        exc = BandwidthQuotaExceeded("Daily limit exceeded")
        assert str(exc) == "Daily limit exceeded"

    def test_connection_limit_exceeded(self):
        """Test ConnectionLimitExceeded exception."""
        exc = ConnectionLimitExceeded("Max connections reached")
        assert str(exc) == "Max connections reached"
