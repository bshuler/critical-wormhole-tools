# Enterprise Audit Logging

Critical Wormhole Tools provides structured audit logging for compliance and security monitoring.

## Overview

Audit logs are written in JSON format, suitable for ingestion by SIEM systems:
- Splunk
- Elasticsearch/ELK Stack
- Datadog
- Azure Sentinel
- AWS CloudWatch

## Enabling Audit Logging

### CLI Usage

```bash
# Enable audit logging for a listener
wh listen --ssh --audit-log=/var/log/wh/audit.log

# With authentication
wh listen --ssh \
    --auth-method=ldap \
    --ldap-server=ldap://ad.company.com \
    --audit-log=/var/log/wh/audit.log
```

### Daemon Configuration

```bash
wh daemon start --audit-log=/var/log/wh/daemon-audit.log
```

## Log Format

Each log entry is a single JSON line:

```json
{
  "event": "auth_success",
  "timestamp": "2024-01-15T10:30:00.000Z",
  "success": true,
  "identity": "jdoe@company.com",
  "namespace": "engineering",
  "source_ip": "192.168.1.100",
  "session_id": "abc123",
  "details": {
    "method": "ldap",
    "dn": "uid=jdoe,ou=users,dc=company,dc=com"
  }
}
```

## Event Types

### connection_start
Logged when a wormhole connection is established.

```json
{
  "event": "connection_start",
  "details": {
    "code": "7-guitar-sunset",
    "peer_address": "192.168.1.100"
  }
}
```

### connection_end
Logged when a wormhole connection is closed.

```json
{
  "event": "connection_end",
  "details": {
    "code": "7-guitar-sunset",
    "duration_seconds": 120.5,
    "bytes_sent": 1024,
    "bytes_received": 2048
  }
}
```

### auth_success
Logged on successful authentication.

```json
{
  "event": "auth_success",
  "identity": "jdoe",
  "details": {
    "method": "ldap"
  }
}
```

### auth_failure
Logged on failed authentication.

```json
{
  "event": "auth_failure",
  "success": false,
  "details": {
    "method": "password",
    "attempted_identity": "jdoe",
    "reason": "Invalid password"
  }
}
```

### file_transfer
Logged when files are transferred.

```json
{
  "event": "file_transfer",
  "identity": "jdoe",
  "details": {
    "filename": "document.pdf",
    "direction": "upload",
    "size_bytes": 102400
  }
}
```

### command_exec
Logged when commands are executed (SSH).

```json
{
  "event": "command_exec",
  "identity": "jdoe",
  "details": {
    "command": "ls -la",
    "exit_code": 0
  }
}
```

### policy_violation
Logged when a policy is violated.

```json
{
  "event": "policy_violation",
  "success": false,
  "details": {
    "policy_type": "rate_limit",
    "violation": "Exceeded 10 connections per minute"
  }
}
```

### namespace_change
Logged when namespaces are modified.

```json
{
  "event": "namespace_change",
  "identity": "admin",
  "namespace": "engineering",
  "details": {
    "action": "create"
  }
}
```

## Log Rotation

Logs are automatically rotated when they reach 10MB (configurable):

```python
from wh.enterprise.audit import AuditLogger, AuditConfig

config = AuditConfig(
    log_file="/var/log/wh/audit.log",
    max_file_size=10 * 1024 * 1024,  # 10 MB
    backup_count=5,  # Keep 5 rotated files
)

logger = AuditLogger(config=config)
```

## Filtering Events

Log only specific event types:

```python
from wh.enterprise.audit import AuditEventType, AuditConfig

config = AuditConfig(
    log_file="/var/log/wh/audit.log",
    filter_events=[
        AuditEventType.AUTH_FAILURE,
        AuditEventType.POLICY_VIOLATION,
    ],
)
```

## Programmatic Usage

```python
from wh.enterprise.audit import AuditLogger

# Create logger
logger = AuditLogger("/var/log/wh/audit.log")

# Log events
logger.connection_start(code="7-guitar-sunset", identity="jdoe")
logger.auth_success(method="ldap", identity="jdoe")
logger.file_transfer(
    filename="report.pdf",
    direction="upload",
    size_bytes=102400,
    identity="jdoe",
)
logger.connection_end(code="7-guitar-sunset", duration_seconds=120.5)

# Close when done
logger.close()
```

## Real-time Callbacks

Process events in real-time:

```python
def alert_on_failure(event):
    if event.event_type == AuditEventType.AUTH_FAILURE:
        send_alert(f"Auth failure from {event.source_ip}")

logger = AuditLogger("/var/log/wh/audit.log")
logger.add_callback(alert_on_failure)
```

## SIEM Integration

### Splunk

```
# props.conf
[wormhole_audit]
TIME_FORMAT = %Y-%m-%dT%H:%M:%S.%3NZ
TIME_PREFIX = "timestamp":\s*"
SHOULD_LINEMERGE = false
KV_MODE = json
```

### Elasticsearch

Use Filebeat with JSON input:

```yaml
filebeat.inputs:
  - type: log
    paths:
      - /var/log/wh/audit.log
    json.keys_under_root: true
    json.add_error_key: true
```

## See Also

- [Authentication](authentication.md)
- [Rate Limiting](rate-limiting.md)
- [Multi-Tenancy](multi-tenancy.md)
