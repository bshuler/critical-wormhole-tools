# Enterprise Rate Limiting

Critical Wormhole Tools supports rate limiting and quotas for enterprise deployments.

## Overview

Rate limiting helps:
- Prevent abuse and denial-of-service
- Enforce fair usage policies
- Control bandwidth consumption
- Limit concurrent connections

## Policy File

Create a policy file at `/etc/wh/policy.yml`:

```yaml
# Rate limits (applied to all connections)
rate_limits:
  connections_per_minute: 10
  requests_per_second: 100
  bandwidth_mbps: 100

# Quotas (cumulative limits)
quotas:
  max_concurrent_connections: 50
  max_transfer_gb_per_day: 100
  max_sessions_per_identity: 5

# Rules (override defaults based on identity/IP)
rules:
  # Admins get unlimited access
  - match:
      identity: "admin@*"
    allow:
      - "*"
    rate_limits:
      connections_per_minute: 1000

  # Internal network gets higher limits
  - match:
      source_ip: "10.0.0.0/8"
    rate_limits:
      connections_per_minute: 100
      bandwidth_mbps: 1000

  # Guests get restricted access
  - match:
      identity: "guest"
    deny:
      - "file_transfer"
    rate_limits:
      connections_per_minute: 5
    quotas:
      max_concurrent_connections: 2

# Defaults
defaults:
  auth_required: false
  namespace: "default"
```

## Rate Limit Types

### Connection Rate

Limit how often new connections can be established:

```yaml
rate_limits:
  connections_per_minute: 10
  connections_per_hour: 100
```

### Request Rate

Limit requests per second (for HTTP/API operations):

```yaml
rate_limits:
  requests_per_second: 100
  requests_per_minute: 1000
  burst_multiplier: 2.0  # Allow bursts up to 2x limit
```

### Bandwidth

Limit data transfer rate:

```yaml
rate_limits:
  bandwidth_mbps: 100  # Megabits per second
```

## Quota Types

### Concurrent Connections

Limit simultaneous connections:

```yaml
quotas:
  max_concurrent_connections: 50
  max_sessions_per_identity: 5
```

### Daily/Monthly Transfer

Limit data transfer volume:

```yaml
quotas:
  max_transfer_gb_per_day: 100
  max_transfer_bytes_per_month: 1099511627776  # 1 TB
```

### File Size

Limit individual file sizes:

```yaml
quotas:
  max_file_size: 1GB  # Human-readable sizes supported
```

## Rule Matching

Rules are evaluated in priority order (highest first):

```yaml
rules:
  # High priority: specific admin
  - match:
      identity: "superadmin"
    priority: 100
    allow:
      - "*"

  # Medium priority: admin pattern
  - match:
      identity: "admin@*"
    priority: 50
    rate_limits:
      connections_per_minute: 100

  # Low priority: default for everyone
  - match:
      identity: "*"
    priority: 0
    rate_limits:
      connections_per_minute: 10
```

### Match Conditions

| Condition | Description | Example |
|-----------|-------------|---------|
| `identity` | User identity pattern | `"admin@*"`, `"*@company.com"` |
| `source_ip` | IP address or CIDR | `"192.168.1.100"`, `"10.0.0.0/8"` |
| `namespace` | Namespace name | `"engineering"` |

### Wildcards

- `*` matches anything
- `prefix*` matches anything starting with prefix
- `*suffix` matches anything ending with suffix

## Using with CLI

### Daemon with Policy

```bash
wh daemon start --policy=/etc/wh/policy.yml
```

### Per-listener Policy

```bash
wh listen --ssh --policy=/etc/wh/policy.yml
```

## Programmatic Usage

```python
from wh.enterprise.policy import load_policy
from wh.enterprise.rate_limiter import RateLimiter

# Load policy
policy = load_policy("/etc/wh/policy.yml")

# Create rate limiter
limiter = RateLimiter(policy)

# Check limits before allowing connection
try:
    await limiter.acquire(
        identity="jdoe",
        source_ip="192.168.1.100",
        session_id="session123",
    )
    # Connection allowed
except RateLimitExceeded as e:
    print(f"Rate limit exceeded, retry in {e.retry_after}s")
except ConnectionLimitExceeded as e:
    print(f"Connection limit exceeded: {e}")

# Track bandwidth
await limiter.record_bytes(bytes_transferred=1024, identity="jdoe")

# Check bandwidth quota before transfer
try:
    await limiter.check_bandwidth(bytes_to_transfer=1024000)
except BandwidthQuotaExceeded:
    print("Bandwidth quota exceeded")

# Release when done
await limiter.release(session_id="session123", identity="jdoe")
```

## Bandwidth Throttling

Throttle data transfer rate:

```python
from wh.enterprise.rate_limiter import BandwidthThrottler

# Create throttler (10 Mbps)
throttler = BandwidthThrottler(max_mbps=10.0)

# Throttle before sending
await throttler.throttle(len(data))
send(data)

# Or stream with throttling
async for chunk in throttler.throttle_stream(large_data):
    send(chunk)
```

## Monitoring

Get rate limiter statistics:

```python
stats = limiter.get_stats()
print(f"Active sessions: {stats['active_sessions']}")
print(f"Bytes today: {stats['global']['bytes_today']}")
```

## Error Handling

| Exception | Description |
|-----------|-------------|
| `RateLimitExceeded` | Request rate exceeded |
| `BandwidthQuotaExceeded` | Transfer quota exceeded |
| `ConnectionLimitExceeded` | Concurrent connection limit exceeded |

Handle gracefully:

```python
from wh.enterprise.rate_limiter import (
    RateLimitExceeded,
    BandwidthQuotaExceeded,
    ConnectionLimitExceeded,
)

try:
    await limiter.acquire(...)
except RateLimitExceeded as e:
    # Retry after delay
    await asyncio.sleep(e.retry_after)
except ConnectionLimitExceeded:
    # Queue or reject
    pass
except BandwidthQuotaExceeded:
    # Wait until quota resets
    pass
```

## See Also

- [Authentication](authentication.md)
- [Audit Logging](audit-logging.md)
- [Multi-Tenancy](multi-tenancy.md)
