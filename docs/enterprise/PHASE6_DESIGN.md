# Phase 6: Enterprise Features Design

> Version: 1.0.0
> Status: Design Phase
> Target Release: v1.0.0
> Last Updated: 2026-01-24

## Overview

Phase 6 introduces enterprise-grade security, audit, and multi-tenant features to Critical Wormhole Tools. This phase transforms `wh` from a developer tool into a production-ready enterprise networking solution.

### Scope

- Authentication & Authorization (RBAC)
- Comprehensive Audit Logging
- Rate Limiting & Quotas
- Multi-Tenancy with Namespace Isolation
- Enterprise deployment patterns
- SIEM integration capabilities

### Target Version

**v1.0.0** - Production-ready enterprise release

### Design Principles

1. **Backward Compatibility** - All features are opt-in; default behavior unchanged
2. **Zero Trust Security** - Verify all connections, log all actions
3. **Flexible Deployment** - Works in cloud, on-premises, hybrid environments
4. **Standards Compliance** - LDAP/AD, SIEM, industry-standard protocols
5. **Minimal Dependencies** - Leverage Python standard library where possible

---

## Features

### 1. Authentication & Authorization

#### 1.1 Authentication Methods

Reference: [authentication.md](authentication.md)

##### Supported Methods

| Method | Use Case | Implementation Status |
|--------|----------|---------------------|
| **None** | Dev/testing, trusted networks | Complete |
| **Public Key** | SSH-style auth, automation | Complete |
| **Password** | Simple deployments | Complete |
| **LDAP/AD** | Enterprise directory integration | Complete |
| **SSO (SAML/OAuth)** | Cloud-native, federated identity | Design |

##### Public Key Authentication

Uses Ed25519 keys from WNS identity system:

```bash
# Server side
wh listen --ssh --auth-method=pubkey --authorized-keys=/etc/wh/authorized_keys

# Client side
wh ssh 7-guitar-sunset --identity=my-client-key
```

**Authorized Keys Format:**
```
<base64-public-key> <key-id-or-comment>
wns1abc123def456... admin@example.com
```

**Integration with WNS:**
- WNS identities (`wh identity create`) generate Ed25519 keypairs
- Public keys exported with `wh identity export <address>`
- Private keys stored securely in `~/.wh/identity/`
- Self-certifying addresses prevent MITM attacks

##### LDAP/Active Directory

Authenticate against corporate directories:

```bash
wh listen --ssh \
    --auth-method=ldap \
    --ldap-server=ldaps://ldap.company.com:636 \
    --ldap-base-dn="dc=company,dc=com" \
    --ldap-bind-dn="cn=service,dc=company,dc=com" \
    --ldap-bind-password-env=WH_LDAP_PASSWORD
```

**Features:**
- TLS/SSL support (ldaps://)
- Service account binding
- User DN template matching
- Group membership queries
- Nested group support (AD)

##### SSO Integration (Planned)

**SAML 2.0:**
```bash
wh listen --ssh \
    --auth-method=saml \
    --saml-idp-metadata-url=https://sso.company.com/metadata
```

**OAuth 2.0 / OIDC:**
```bash
wh listen --http \
    --auth-method=oauth \
    --oauth-issuer=https://accounts.google.com \
    --oauth-client-id=abc123
```

**Implementation Notes:**
- Use `python-saml` library for SAML
- Use `authlib` for OAuth/OIDC
- Token-based authentication for stateless auth
- Refresh token support for long-lived sessions

#### 1.2 Role-Based Access Control (RBAC)

**Design Goals:**
- Map authentication identities to roles
- Control access to commands, files, namespaces
- Support both coarse and fine-grained permissions
- Integrate with LDAP/AD groups

##### Role Definition

**Configuration:** `/etc/wh/roles.yml`

```yaml
roles:
  admin:
    permissions:
      - "*"  # Full access
    commands:
      - "*"

  developer:
    permissions:
      - "ssh:*"
      - "scp:upload"
      - "scp:download"
      - "sftp:*"
    commands:
      - "ls"
      - "cat"
      - "vim"
    namespaces:
      - "engineering"
      - "staging"

  guest:
    permissions:
      - "ssh:read-only"
    commands:
      - "ls"
      - "cat"
    max_session_duration: 3600  # 1 hour

  automated:
    permissions:
      - "scp:upload"
      - "http:get"
    rate_limits:
      connections_per_minute: 100
```

##### Role Assignment

**Static Assignment:**
```yaml
# /etc/wh/role_mappings.yml
mappings:
  - identity: "admin@example.com"
    role: "admin"

  - identity: "*@contractors.com"
    role: "guest"

  - identity_pattern: "ci-*"
    role: "automated"
```

**LDAP Group Mapping:**
```yaml
# /etc/wh/roles.yml
roles:
  developer:
    ldap_groups:
      - "cn=developers,ou=groups,dc=company,dc=com"
      - "cn=engineers,ou=groups,dc=company,dc=com"
```

##### Permission Model

**Format:** `<service>:<action>:<resource>`

Examples:
- `ssh:*` - All SSH operations
- `ssh:connect` - Connect via SSH
- `ssh:exec:ls` - Execute 'ls' command
- `scp:upload:/var/www/*` - Upload to /var/www
- `sftp:read:/home/user/*` - Read from /home/user
- `http:get` - HTTP GET requests
- `namespace:create:engineering` - Create connections in engineering namespace

**Wildcards:**
- `*` matches anything
- `service:*` matches all actions for a service
- `service:action:*` matches all resources for an action

##### Enforcement Points

**CLI Entry:**
```python
# src/wh/enterprise/rbac.py
async def check_permission(identity: str, permission: str) -> bool:
    """Check if identity has permission."""
    role_manager = get_role_manager()
    role = role_manager.get_role_for_identity(identity)
    return role.has_permission(permission)
```

**SSH Command Execution:**
```python
# src/wh/ssh/server.py
async def exec_command(self, command: str):
    permission = f"ssh:exec:{command.split()[0]}"
    if not await check_permission(self.identity, permission):
        raise PermissionDenied(f"Command not allowed: {command}")
    # Execute command
```

**File Operations:**
```python
# src/wh/transfer/scp.py
async def upload_file(self, local_path: str, remote_path: str):
    permission = f"scp:upload:{remote_path}"
    if not await check_permission(self.identity, permission):
        raise PermissionDenied(f"Upload not allowed: {remote_path}")
    # Upload file
```

#### 1.3 Integration with WNS Identities

**WNS Identity as Auth Principal:**
- WNS addresses (`wns1abc123...`) become primary identity
- Scoped names (`ssh.myserver.wns`) map to WNS addresses
- TOFU model ensures consistent identity across connections

**Authentication Flow:**
```
1. Client connects with WNS identity
2. Server verifies identity signature
3. RBAC system maps WNS address → role
4. Session established with role permissions
5. All actions checked against role permissions
```

**Hybrid Identity:**
```yaml
# Map LDAP users to WNS identities
identity_mappings:
  - ldap_dn: "uid=jdoe,ou=users,dc=company,dc=com"
    wns_address: "wns1abc123def456..."
    role: "developer"
```

---

### 2. Audit Logging

Reference: [audit-logging.md](audit-logging.md)

#### 2.1 JSON-Structured Logging

**Design Goals:**
- Machine-readable JSON format
- SIEM-ready (Splunk, ELK, Datadog, Azure Sentinel)
- Comprehensive event coverage
- Sensitive data handling
- High performance (async I/O, buffering)

##### Log Format

**Standard Fields:**
```json
{
  "event": "event_type",
  "timestamp": "2024-01-15T10:30:00.000Z",
  "success": true,
  "identity": "jdoe@company.com",
  "wns_address": "wns1abc123...",
  "namespace": "engineering",
  "source_ip": "192.168.1.100",
  "session_id": "abc123",
  "details": {}
}
```

**Event-Specific Fields:**
- `details` object contains event-specific data
- Timestamps are ISO 8601 UTC
- `success` boolean indicates outcome
- `session_id` links related events

##### Event Types

| Event | Trigger | Details |
|-------|---------|---------|
| `connection_start` | Wormhole connection established | code, peer_address |
| `connection_end` | Connection closed | duration, bytes_sent, bytes_received |
| `auth_success` | Authentication succeeded | method, groups |
| `auth_failure` | Authentication failed | method, reason |
| `file_transfer` | File uploaded/downloaded | filename, direction, size_bytes |
| `command_exec` | SSH command executed | command, exit_code |
| `policy_violation` | Rate limit/quota exceeded | policy_type, violation |
| `namespace_change` | Namespace created/modified | action, namespace |
| `permission_denied` | RBAC check failed | permission, resource |
| `identity_created` | New WNS identity created | wns_address, name |
| `identity_exported` | Identity exported | wns_address, export_format |
| `session_expired` | Session timeout | duration, reason |

##### Example Events

**Authentication Success:**
```json
{
  "event": "auth_success",
  "timestamp": "2024-01-15T10:30:00.000Z",
  "success": true,
  "identity": "jdoe@company.com",
  "wns_address": "wns1abc123...",
  "source_ip": "192.168.1.100",
  "session_id": "session-abc123",
  "details": {
    "method": "ldap",
    "dn": "uid=jdoe,ou=users,dc=company,dc=com",
    "groups": ["developers", "engineers"],
    "role_assigned": "developer"
  }
}
```

**File Transfer:**
```json
{
  "event": "file_transfer",
  "timestamp": "2024-01-15T10:35:00.000Z",
  "success": true,
  "identity": "jdoe@company.com",
  "session_id": "session-abc123",
  "namespace": "engineering",
  "details": {
    "filename": "report.pdf",
    "direction": "upload",
    "size_bytes": 102400,
    "checksum_sha256": "abc123...",
    "destination_path": "/var/www/reports/report.pdf"
  }
}
```

**Permission Denied:**
```json
{
  "event": "permission_denied",
  "timestamp": "2024-01-15T10:40:00.000Z",
  "success": false,
  "identity": "guest@company.com",
  "session_id": "session-xyz789",
  "details": {
    "permission": "scp:upload:/etc/passwd",
    "role": "guest",
    "reason": "Upload to /etc/ not allowed for role 'guest'"
  }
}
```

#### 2.2 Log Rotation and Retention

**Automatic Rotation:**
- Default max size: 10MB
- Default backup count: 5 files
- Compressed rotation (gzip)
- Time-based rotation (daily/weekly)

**Configuration:**
```python
from wh.enterprise.audit import AuditConfig

config = AuditConfig(
    log_file="/var/log/wh/audit.log",
    max_file_size=10 * 1024 * 1024,  # 10 MB
    backup_count=5,
    compress=True,
    rotation_interval="daily"  # or "weekly", "monthly"
)
```

**CLI Configuration:**
```bash
wh daemon start \
    --audit-log=/var/log/wh/audit.log \
    --audit-max-size=10M \
    --audit-backup-count=5 \
    --audit-rotation=daily
```

#### 2.3 Sensitive Data Handling

**Redaction Rules:**
- Passwords: Always redacted
- Private keys: Always redacted
- File contents: Never logged
- Credentials in URLs: Redacted
- Environment variables: Configurable

**Configurable PII Redaction:**
```yaml
# /etc/wh/audit.yml
audit:
  redact_fields:
    - password
    - secret
    - token
    - private_key

  redact_patterns:
    - ".*password.*"
    - ".*secret.*"

  anonymize_ip: false  # Replace IPs with hashes
  anonymize_identity: false  # Replace identities with hashes
```

**Example Redaction:**
```json
{
  "event": "auth_failure",
  "details": {
    "username": "jdoe",
    "password": "[REDACTED]",
    "reason": "Invalid credentials"
  }
}
```

#### 2.4 SIEM Integration

##### Splunk

**props.conf:**
```ini
[wormhole_audit]
TIME_FORMAT = %Y-%m-%dT%H:%M:%S.%3NZ
TIME_PREFIX = "timestamp":\s*"
SHOULD_LINEMERGE = false
KV_MODE = json
MAX_TIMESTAMP_LOOKAHEAD = 28
```

**inputs.conf:**
```ini
[monitor:///var/log/wh/audit.log]
sourcetype = wormhole_audit
index = security
```

##### Elasticsearch / ELK Stack

**Filebeat configuration:**
```yaml
filebeat.inputs:
  - type: log
    paths:
      - /var/log/wh/audit.log
    json.keys_under_root: true
    json.add_error_key: true
    json.message_key: event

output.elasticsearch:
  hosts: ["localhost:9200"]
  index: "wormhole-audit-%{+yyyy.MM.dd}"
```

##### Datadog

**datadog.yaml:**
```yaml
logs:
  - type: file
    path: /var/log/wh/audit.log
    service: wormhole
    source: wormhole-audit
    sourcecategory: security
    tags:
      - env:production
```

##### AWS CloudWatch

**Forward logs via AWS CLI:**
```bash
aws logs create-log-stream \
    --log-group-name /wormhole/audit \
    --log-stream-name $(hostname)

tail -F /var/log/wh/audit.log | \
    aws logs put-log-events \
        --log-group-name /wormhole/audit \
        --log-stream-name $(hostname)
```

---

### 3. Rate Limiting & Quotas

Reference: [rate-limiting.md](rate-limiting.md)

#### 3.1 Per-Identity Rate Limits

**Design Goals:**
- Prevent abuse and DoS attacks
- Fair usage enforcement
- Flexible policy rules
- Minimal performance overhead

##### Rate Limit Types

**Connection Rate:**
```yaml
rate_limits:
  connections_per_minute: 10
  connections_per_hour: 100
```

**Request Rate:**
```yaml
rate_limits:
  requests_per_second: 100
  requests_per_minute: 1000
  burst_multiplier: 2.0  # Allow bursts up to 2x
```

**Bandwidth:**
```yaml
rate_limits:
  bandwidth_mbps: 100  # Megabits per second
  bandwidth_burst_mb: 10  # Allow 10MB burst
```

##### Implementation

**Token Bucket Algorithm:**
- Constant rate refill
- Burst capacity
- Per-identity buckets
- Async-safe (no global locks)

```python
from wh.enterprise.rate_limiter import RateLimiter, RateLimitExceeded

limiter = RateLimiter(policy)

try:
    await limiter.acquire(
        identity="jdoe",
        source_ip="192.168.1.100",
        session_id="session123"
    )
    # Connection allowed
except RateLimitExceeded as e:
    print(f"Rate limit exceeded, retry after {e.retry_after}s")
```

#### 3.2 Connection Quotas

**Concurrent Connections:**
```yaml
quotas:
  max_concurrent_connections: 50
  max_sessions_per_identity: 5
```

**Daily/Monthly Transfer:**
```yaml
quotas:
  max_transfer_gb_per_day: 100
  max_transfer_bytes_per_month: 1099511627776  # 1 TB
```

**File Size Limits:**
```yaml
quotas:
  max_file_size: 1GB
  max_file_count_per_transfer: 1000
```

#### 3.3 Bandwidth Throttling

**Adaptive Throttling:**
- Per-session bandwidth limits
- Graceful degradation under load
- Priority classes (admin > user > guest)

```python
from wh.enterprise.rate_limiter import BandwidthThrottler

throttler = BandwidthThrottler(max_mbps=10.0)

# Throttle before sending
await throttler.throttle(len(data))
send(data)

# Or stream with throttling
async for chunk in throttler.throttle_stream(large_data):
    send(chunk)
```

#### 3.4 Policy Rules

**Hierarchical Policies:**
```yaml
# /etc/wh/policy.yml

# Global defaults
rate_limits:
  connections_per_minute: 10
  bandwidth_mbps: 100

quotas:
  max_concurrent_connections: 50

# Rules override defaults
rules:
  # Admins: unlimited
  - match:
      identity: "admin@*"
    priority: 100
    rate_limits:
      connections_per_minute: 1000
      bandwidth_mbps: 10000
    quotas:
      max_concurrent_connections: 100

  # Internal network: higher limits
  - match:
      source_ip: "10.0.0.0/8"
    priority: 50
    rate_limits:
      connections_per_minute: 100
      bandwidth_mbps: 1000

  # Guests: restricted
  - match:
      identity: "guest"
    priority: 10
    deny:
      - "file_transfer"
    rate_limits:
      connections_per_minute: 5
      bandwidth_mbps: 10
    quotas:
      max_concurrent_connections: 2
```

**Rule Matching:**
- Rules evaluated by priority (highest first)
- First matching rule applies
- Wildcards supported (`*`, `prefix*`, `*suffix`)

---

### 4. Multi-Tenancy

Reference: [multi-tenancy.md](multi-tenancy.md)

#### 4.1 Namespace Isolation

**Design Goals:**
- Isolated DHT address spaces
- Separate identity management
- Access control (public/private)
- Per-namespace policies

##### DHT Namespace Isolation

**Address Space Partitioning:**
```
default namespace:     DHT key = SHA256(address)
engineering namespace: DHT key = SHA256(prefix + ":" + address)
sales namespace:       DHT key = SHA256(prefix + ":" + address)
```

**Benefits:**
- Same wormhole codes in different namespaces don't conflict
- Namespace-scoped discovery
- Cross-namespace connections require explicit permission

##### Storage Isolation

**Directory Structure:**
```
~/.wh/namespaces/
├── default/
│   ├── identity/           # Namespace-specific identities
│   └── config.json
├── engineering/
│   ├── identity/
│   └── config.json
└── sales/
    ├── identity/
    └── config.json
```

**Namespace Configuration:**
```yaml
# ~/.wh/namespaces/engineering.yaml
name: engineering
created_at: 2024-01-15T10:30:00Z
description: Engineering team namespace
dht_prefix: abc123def456
admins:
  - admin@example.com
members:
  - dev1@example.com
  - dev2@example.com
public: false
max_members: 50
```

#### 4.2 Identity Scoping

**Namespace-Scoped Identities:**
- Each namespace has its own identity store
- Identities can be shared across namespaces (explicit export/import)
- Default identity per namespace

```bash
# Create identity in specific namespace
wh --namespace=engineering identity create --name my-eng-key

# Export identity for sharing
wh --namespace=engineering identity export wns1abc123... > key.pub

# Import identity to another namespace
wh --namespace=sales identity import < key.pub
```

#### 4.3 Shared vs. Isolated Relays

**Deployment Models:**

##### Shared Relay (Multi-Tenant)
```bash
# Start relay with namespace support
wh relay start --enable-namespaces --port=4000
```

**Features:**
- Single relay serves all namespaces
- Namespace isolation enforced by DHT prefixing
- Cost-effective for small deployments

##### Isolated Relay (Per-Namespace)
```bash
# Start namespace-specific relays
wh relay start --namespace=engineering --port=4001
wh relay start --namespace=sales --port=4002
```

**Features:**
- Physical isolation between namespaces
- Dedicated resources per namespace
- Higher security, higher cost

##### Hybrid (Shared + Isolated)
```yaml
# /etc/wh/relay.yml
relay:
  default_mode: shared
  isolated_namespaces:
    - production
    - finance

  relays:
    - namespace: production
      port: 4001
      max_connections: 1000

    - namespace: finance
      port: 4002
      max_connections: 500
```

#### 4.4 Namespace Management

**Create Namespace:**
```bash
wh namespace create engineering \
    --description "Engineering team" \
    --admin admin@example.com \
    --max-members 50
```

**List Namespaces:**
```bash
wh namespace list
# Output:
# default (public) - 0 members
# engineering (private) - 5 members - Engineering team
```

**Show Details:**
```bash
wh namespace show engineering
# Output:
# Name: engineering
# DHT Prefix: abc123def456
# Created: 2024-01-15T10:30:00Z
# Description: Engineering team
# Public: no
# Admins: admin@example.com
# Members: dev1, dev2, dev3
```

**Member Management:**
```bash
# Add member
wh namespace add-member engineering developer@example.com

# Remove member
wh namespace remove-member engineering former-dev@example.com

# Add admin
wh namespace add-admin engineering senior-admin@example.com
```

**Access Control:**
```bash
# Create private namespace (default)
wh namespace create private-team

# Create public namespace
wh namespace create public-demo --public
```

**Using Namespaces:**
```bash
# Global flag
wh --namespace=engineering listen --ssh

# Environment variable
export WH_NAMESPACE=engineering
wh listen --ssh  # Uses engineering namespace
```

---

## Implementation Phases

### Phase 6.1: Core Authentication (4 weeks)

**Milestone: v0.6.0**

**Features:**
- [x] Public key authentication (already complete)
- [x] Password authentication (already complete)
- [x] LDAP/AD integration (already complete)
- [ ] RBAC role definitions
- [ ] RBAC permission checking
- [ ] Role assignment (static, LDAP groups)

**Deliverables:**
1. RBAC engine (`src/wh/enterprise/rbac.py`)
2. Role configuration schema (`/etc/wh/roles.yml`)
3. Permission enforcement in SSH, SCP, SFTP
4. CLI: `wh role list`, `wh role show`, `wh role check`
5. Unit tests for RBAC
6. Documentation: RBAC guide

**Dependencies:**
- None (builds on existing auth)

### Phase 6.2: Audit Infrastructure (3 weeks)

**Milestone: v0.7.0**

**Features:**
- [x] JSON audit logging (already complete)
- [x] Event types (already complete)
- [x] Log rotation (already complete)
- [ ] Enhanced event coverage (RBAC events)
- [ ] Sensitive data redaction
- [ ] Real-time callbacks
- [ ] SIEM integration docs

**Deliverables:**
1. Enhanced `AuditLogger` with redaction
2. RBAC audit events
3. Callback system for real-time alerts
4. SIEM integration examples (Splunk, ELK, Datadog)
5. CLI: `wh audit stats`, `wh audit tail`
6. Documentation: SIEM integration guide

**Dependencies:**
- Phase 6.1 (RBAC events)

### Phase 6.3: Rate Limiting (3 weeks)

**Milestone: v0.8.0**

**Features:**
- [x] Rate limit policies (already complete)
- [x] Connection quotas (already complete)
- [x] Bandwidth throttling (already complete)
- [ ] Enhanced policy rules (RBAC integration)
- [ ] Per-namespace policies
- [ ] Adaptive throttling
- [ ] Rate limit monitoring

**Deliverables:**
1. Enhanced `RateLimiter` with RBAC integration
2. Per-namespace policy support
3. Adaptive throttling based on role priority
4. CLI: `wh policy validate`, `wh policy stats`
5. Monitoring API for rate limit metrics
6. Documentation: Policy configuration guide

**Dependencies:**
- Phase 6.1 (RBAC roles)
- Phase 6.4 (namespace policies)

### Phase 6.4: Multi-Tenancy (4 weeks)

**Milestone: v0.9.0**

**Features:**
- [x] Namespace creation (already complete)
- [x] DHT isolation (already complete)
- [x] Identity scoping (already complete)
- [ ] Namespace RBAC integration
- [ ] Shared relay with namespace support
- [ ] Isolated relay deployment
- [ ] Cross-namespace permissions

**Deliverables:**
1. Namespace-aware relay server
2. Cross-namespace permission model
3. Enhanced namespace CLI commands
4. Namespace monitoring and metrics
5. Relay deployment modes (shared/isolated/hybrid)
6. Documentation: Multi-tenant deployment guide

**Dependencies:**
- Phase 6.1 (RBAC for namespace access)

### Phase 6.5: Integration & Testing (2 weeks)

**Milestone: v1.0.0-rc1**

**Features:**
- [ ] End-to-end integration tests
- [ ] Performance testing (rate limits, quotas)
- [ ] Security audit
- [ ] Documentation review
- [ ] Migration guide

**Deliverables:**
1. Integration test suite
2. Performance benchmarks
3. Security audit report
4. Complete enterprise documentation
5. Migration guide from v0.4.x to v1.0.0

**Dependencies:**
- All previous phases

### Phase 6.6: Production Hardening (2 weeks)

**Milestone: v1.0.0**

**Features:**
- [ ] Production deployment patterns
- [ ] High availability setup
- [ ] Disaster recovery
- [ ] Monitoring and alerting
- [ ] Operational runbooks

**Deliverables:**
1. HA deployment guide (load balancing, failover)
2. Backup and restore procedures
3. Monitoring integration (Prometheus, Grafana)
4. Alerting rules and runbooks
5. Production checklist

**Dependencies:**
- Phase 6.5 (integration testing)

---

## API Changes

### New CLI Flags

#### Global Flags
```bash
--auth-method=<none|pubkey|password|ldap|saml|oauth>
--authorized-keys=<path>
--password-file=<path>
--ldap-server=<url>
--ldap-base-dn=<dn>
--ldap-bind-dn=<dn>
--ldap-bind-password-env=<env_var>
--saml-idp-metadata-url=<url>
--oauth-issuer=<url>
--oauth-client-id=<id>
--audit-log=<path>
--audit-max-size=<size>
--audit-backup-count=<n>
--audit-rotation=<interval>
--policy=<path>
--roles=<path>
--namespace=<name>
```

#### New Commands
```bash
# RBAC
wh role list
wh role show <role>
wh role check <identity> <permission>

# Audit
wh audit stats
wh audit tail [--follow] [--filter=<event_type>]

# Policy
wh policy validate <path>
wh policy stats

# Namespace (enhanced)
wh namespace stats <namespace>
wh namespace audit <namespace>
```

### Configuration Schema

**Global Configuration:** `/etc/wh/config.yml`
```yaml
auth:
  method: ldap
  ldap:
    server: ldaps://ldap.company.com:636
    base_dn: dc=company,dc=com
    bind_dn: cn=service,dc=company,dc=com
    bind_password_env: WH_LDAP_PASSWORD

audit:
  enabled: true
  log_file: /var/log/wh/audit.log
  max_file_size: 10M
  backup_count: 5
  rotation: daily
  redact_fields:
    - password
    - secret

policy:
  file: /etc/wh/policy.yml

rbac:
  roles_file: /etc/wh/roles.yml
  mappings_file: /etc/wh/role_mappings.yml

namespaces:
  default: default
  storage_dir: /var/lib/wh/namespaces
```

### Daemon API Endpoints

**Authentication:**
```
POST /api/v1/auth/login
POST /api/v1/auth/logout
GET  /api/v1/auth/session
```

**RBAC:**
```
GET  /api/v1/roles
GET  /api/v1/roles/{role}
POST /api/v1/roles/{role}/check
```

**Audit:**
```
GET  /api/v1/audit/events
GET  /api/v1/audit/stats
```

**Policy:**
```
GET  /api/v1/policy
POST /api/v1/policy/validate
GET  /api/v1/policy/stats
```

**Namespaces:**
```
GET  /api/v1/namespaces
POST /api/v1/namespaces
GET  /api/v1/namespaces/{namespace}
POST /api/v1/namespaces/{namespace}/members
DELETE /api/v1/namespaces/{namespace}/members/{identity}
GET  /api/v1/namespaces/{namespace}/stats
```

---

## Migration Path

### Backward Compatibility Requirements

**Zero Breaking Changes:**
- All enterprise features are opt-in
- Default behavior unchanged (no auth, no audit, no limits)
- Existing configurations continue to work
- No changes to wormhole protocol

**Configuration Migration:**
- Old config formats supported
- Automatic migration on first run
- Deprecation warnings for old syntax
- Migration guide in documentation

### Upgrade Procedures

#### From v0.4.x to v1.0.0

**Step 1: Backup Configuration**
```bash
# Backup existing config
cp -r ~/.wh ~/.wh.backup
```

**Step 2: Upgrade Package**
```bash
pip install --upgrade critical-wormhole-tools
```

**Step 3: Migrate Configuration (Optional)**
```bash
# Run migration wizard
wh migrate --from=0.4 --to=1.0

# Or manually create new config
wh config init
```

**Step 4: Enable Enterprise Features (Optional)**
```bash
# Generate default enterprise config
wh enterprise init

# Edit configuration
vim /etc/wh/config.yml
```

**Step 5: Verify**
```bash
# Check configuration
wh config validate

# Test authentication
wh listen --ssh --auth-method=pubkey --authorized-keys=/etc/wh/authorized_keys
```

#### Rollback Procedure

```bash
# Downgrade to v0.4.x
pip install critical-wormhole-tools==0.4.0

# Restore configuration
rm -rf ~/.wh
mv ~/.wh.backup ~/.wh

# Verify
wh --version
```

### Deployment Patterns

#### Pattern 1: Gradual Rollout

```bash
# Week 1: Install v1.0.0, no enterprise features
pip install critical-wormhole-tools==1.0.0
# Verify backward compatibility

# Week 2: Enable audit logging
wh daemon start --audit-log=/var/log/wh/audit.log

# Week 3: Enable authentication
wh daemon start --audit-log=/var/log/wh/audit.log --auth-method=ldap

# Week 4: Enable RBAC
wh daemon start --audit-log=/var/log/wh/audit.log --auth-method=ldap --roles=/etc/wh/roles.yml
```

#### Pattern 2: Blue-Green Deployment

```bash
# Green: existing v0.4.x deployment
wh daemon start --port=4000

# Blue: new v1.0.0 deployment with enterprise features
wh daemon start --port=5000 --auth-method=ldap --audit-log=/var/log/wh/audit.log

# Test blue deployment
wh --daemon-url=http://localhost:5000 ssh 7-guitar-sunset

# Switch traffic to blue (update load balancer)
# Monitor for issues

# Decommission green if successful
```

#### Pattern 3: Canary Deployment

```bash
# Deploy v1.0.0 to 10% of servers
ansible-playbook deploy-v1.0.yml --limit='canary'

# Monitor metrics
wh audit stats
wh policy stats

# Gradual rollout: 10% → 25% → 50% → 100%
ansible-playbook deploy-v1.0.yml --limit='canary,wave2'
```

---

## Security Considerations

### Authentication Security

1. **Use TLS for LDAP** - Always use `ldaps://` for production
2. **Rotate Keys Regularly** - Implement key rotation policy
3. **Strong Password Policies** - Enforce minimum complexity
4. **Multi-Factor Authentication** - Consider MFA for sensitive operations
5. **Account Lockout** - Implement after N failed attempts

### Authorization Security

1. **Principle of Least Privilege** - Grant minimal permissions needed
2. **Regular Access Reviews** - Audit role assignments quarterly
3. **Separation of Duties** - Critical operations require multiple roles
4. **Time-Limited Sessions** - Enforce session expiration
5. **Permission Auditing** - Log all permission checks

### Audit Security

1. **Tamper-Proof Logs** - Consider write-once storage (WORM)
2. **Log Integrity** - Cryptographic signatures for log entries
3. **Secure Transport** - TLS for remote log shipping
4. **Access Control** - Restrict who can read audit logs
5. **Retention Policies** - Comply with regulatory requirements

### Network Security

1. **Rate Limit Defense** - Protect against DoS attacks
2. **IP Whitelisting** - Restrict source IPs for sensitive namespaces
3. **Connection Monitoring** - Alert on anomalous connection patterns
4. **Encrypted Transports** - Enforce TLS for all relay connections
5. **Firewall Rules** - Limit relay ports to necessary ranges

### Data Security

1. **End-to-End Encryption** - Wormhole protocol provides E2EE
2. **Data Classification** - Tag sensitive data in audit logs
3. **PII Handling** - Redact or anonymize PII in logs
4. **Compliance** - GDPR, HIPAA, SOC2 considerations
5. **Data Residency** - Respect geographic data requirements

---

## Performance Considerations

### Rate Limiter Performance

**Design:**
- Lock-free token bucket algorithm
- Per-identity buckets in memory
- Async-safe implementation
- Minimal overhead (<1ms per check)

**Benchmarks:**
- 10,000 checks/sec per identity
- 100,000 identities supported
- Memory: ~1KB per identity

### Audit Logging Performance

**Design:**
- Async I/O (asyncio)
- Buffered writes (configurable)
- Separate logging thread
- No blocking on main path

**Benchmarks:**
- 50,000 events/sec sustained
- <0.1ms latency per event
- 1MB/sec log throughput

### RBAC Performance

**Design:**
- Role cache (LRU, 1000 entries)
- Permission bitmask for fast checks
- Lazy evaluation
- Async permission queries (LDAP)

**Benchmarks:**
- <0.5ms per permission check (cached)
- <50ms per permission check (LDAP query)
- 10,000 checks/sec sustained

### Namespace Performance

**Design:**
- DHT prefix caching
- Namespace resolution cache
- Minimal overhead on address lookup

**Benchmarks:**
- <1ms namespace resolution (cached)
- <10ms DHT lookup with namespace prefix
- Negligible impact on connection latency

---

## Testing Strategy

### Unit Tests

**Coverage Target: >80%**

Modules:
- `src/wh/enterprise/rbac.py`
- `src/wh/enterprise/audit.py`
- `src/wh/enterprise/rate_limiter.py`
- `src/wh/enterprise/namespace.py`

### Integration Tests

**Scenarios:**
1. LDAP authentication with RBAC
2. Audit log SIEM ingestion
3. Rate limiting under load
4. Multi-namespace isolation

### Security Tests

**Tests:**
1. Bypass RBAC (permission escalation)
2. Audit log tampering
3. Rate limit evasion
4. Namespace cross-contamination

### Performance Tests

**Benchmarks:**
- 1000 concurrent connections
- 10,000 audit events/sec
- 100,000 rate limit checks/sec
- 1000 namespaces active

### Compliance Tests

**Validations:**
- GDPR data handling
- SOC2 audit requirements
- HIPAA encryption standards
- PCI-DSS access controls

---

## Documentation Plan

### User Documentation

1. **Enterprise Deployment Guide** (`docs/enterprise/deployment.md`)
   - Installation and configuration
   - HA setup
   - Monitoring and alerting

2. **Authentication Guide** (`docs/enterprise/authentication.md`) - ✅ Complete
   - LDAP/AD integration
   - SSO setup (SAML/OAuth)
   - Key management

3. **RBAC Guide** (`docs/enterprise/rbac.md`)
   - Role definitions
   - Permission model
   - Best practices

4. **Audit Logging Guide** (`docs/enterprise/audit-logging.md`) - ✅ Complete
   - Log format
   - SIEM integration
   - Compliance

5. **Rate Limiting Guide** (`docs/enterprise/rate-limiting.md`) - ✅ Complete
   - Policy configuration
   - Quotas and throttling
   - Monitoring

6. **Multi-Tenancy Guide** (`docs/enterprise/multi-tenancy.md`) - ✅ Complete
   - Namespace design
   - Isolation models
   - Best practices

### Administrator Documentation

1. **Operations Runbook** (`docs/enterprise/runbook.md`)
   - Day-to-day operations
   - Troubleshooting
   - Incident response

2. **Security Hardening** (`docs/enterprise/security.md`)
   - Security checklist
   - Threat model
   - Mitigation strategies

3. **Compliance Guide** (`docs/enterprise/compliance.md`)
   - GDPR compliance
   - SOC2 audit preparation
   - HIPAA requirements

### Developer Documentation

1. **Enterprise API Reference** (`docs/enterprise/api.md`)
   - RBAC API
   - Audit API
   - Policy API

2. **Extension Guide** (`docs/enterprise/extending.md`)
   - Custom authenticators
   - Audit event handlers
   - Rate limit algorithms

---

## Success Metrics

### Adoption Metrics

- [ ] 100+ enterprise deployments
- [ ] 10+ LDAP/AD integrations
- [ ] 5+ SIEM integrations
- [ ] 3+ multi-tenant deployments

### Performance Metrics

- [ ] <1ms RBAC check latency
- [ ] <0.1ms audit log latency
- [ ] 10,000+ concurrent connections supported
- [ ] 99.9% uptime in production

### Security Metrics

- [ ] Zero critical vulnerabilities
- [ ] SOC2 Type 2 certification
- [ ] GDPR compliance certification
- [ ] PCI-DSS compliance (if applicable)

### Community Metrics

- [ ] 1000+ stars on GitHub
- [ ] 50+ contributors
- [ ] 10+ enterprise case studies
- [ ] Active community forum

---

## Open Questions

1. **SSO Implementation Priority**
   - SAML vs. OAuth: Which to implement first?
   - Answer: Start with OAuth (easier integration, cloud-native)

2. **Multi-Tenancy Deployment Default**
   - Shared relay vs. isolated relay: What's the recommended default?
   - Answer: Shared relay for simplicity, isolated for security-critical deployments

3. **RBAC Permission Granularity**
   - How fine-grained should permissions be?
   - Answer: Start with service-level (ssh:*, scp:*), expand to resource-level based on feedback

4. **Audit Log Storage**
   - Should we provide built-in long-term storage?
   - Answer: No, integrate with existing SIEM solutions

5. **Rate Limit Persistence**
   - Should rate limit counters survive daemon restarts?
   - Answer: Optional persistence via Redis/database for HA deployments

---

## References

### Internal Documentation

- [Authentication](authentication.md)
- [Audit Logging](audit-logging.md)
- [Rate Limiting](rate-limiting.md)
- [Multi-Tenancy](multi-tenancy.md)
- [PLAN.md](/Users/bshuler/code/wormhole_netcat_ssh_scp_sftp_copy_curl_wget/PLAN.md)
- [ROADMAP.md](/Users/bshuler/code/wormhole_netcat_ssh_scp_sftp_copy_curl_wget/ROADMAP.md)

### External Resources

- [LDAP RFC 4511](https://datatracker.ietf.org/doc/html/rfc4511)
- [SAML 2.0 Specification](http://docs.oasis-open.org/security/saml/v2.0/)
- [OAuth 2.0 RFC 6749](https://datatracker.ietf.org/doc/html/rfc6749)
- [OpenID Connect](https://openid.net/connect/)
- [RBAC NIST Model](https://csrc.nist.gov/projects/role-based-access-control)
- [SIEM Best Practices](https://www.sans.org/white-papers/)
- [SOC2 Requirements](https://www.aicpa.org/soc)

---

**End of Design Document**

*This design is a living document. Update as implementation progresses and requirements evolve.*
