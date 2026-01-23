# Enterprise Multi-Tenancy

Critical Wormhole Tools supports namespace isolation for multi-tenant deployments.

## Overview

Namespaces provide:
- Isolated DHT address spaces
- Separate identity management
- Access control (public/private)
- Per-namespace policies

## Creating Namespaces

### Using CLI

```bash
# Create a new namespace
wh namespace create engineering --description "Engineering team"

# Create a public namespace
wh namespace create public-demo --public

# Create with member limit
wh namespace create limited --max-members 10

# Create with admin
wh namespace create private --admin admin@example.com
```

### List Namespaces

```bash
wh namespace list
# Output:
# default (public) - 0 members
# engineering (private) - 5 members
#   Engineering team namespace
```

### Show Details

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

## Using Namespaces

### Global Flag

Use the `--namespace` flag with any command:

```bash
# Listen in a specific namespace
wh --namespace=engineering listen --ssh

# Connect in a specific namespace
wh --namespace=engineering ssh 7-guitar-sunset
```

### Environment Variable

Set the default namespace:

```bash
export WH_NAMESPACE=engineering
wh listen --ssh  # Uses engineering namespace
```

## Namespace Isolation

Each namespace has its own:

### DHT Prefix

Addresses are prefixed to prevent collisions:

```
default namespace:     DHT key = SHA256(address)
engineering namespace: DHT key = SHA256(prefix + ":" + address)
```

Different namespaces can use the same wormhole codes without conflict.

### Identity Store

Identities are scoped to namespaces:

```
~/.wh/namespaces/engineering/identity/
~/.wh/namespaces/sales/identity/
```

## Access Control

### Private Namespaces

Only members can discover addresses:

```bash
wh namespace create private-team

# Add members
wh namespace add-member private-team dev1@example.com
wh namespace add-member private-team dev2@example.com

# Only members can use
wh --namespace=private-team listen --ssh  # Works for members
```

### Public Namespaces

Anyone can join:

```bash
wh namespace create public-demo --public
```

### Admin Management

Admins can manage namespace membership:

```bash
# Add admin
wh namespace add-admin engineering admin@example.com

# Remove admin
wh namespace remove-admin engineering old-admin@example.com
```

### Member Management

```bash
# Add member
wh namespace add-member engineering developer@example.com

# Remove member
wh namespace remove-member engineering former-dev@example.com
```

## Member Limits

Limit namespace size:

```bash
wh namespace create limited --max-members 10
```

## Programmatic Usage

```python
from wh.enterprise.namespace import (
    NamespaceManager,
    get_namespace_manager,
    get_current_namespace,
)

# Get manager
manager = get_namespace_manager()

# Create namespace
ns = manager.create(
    name="engineering",
    description="Engineering team",
    admins=["admin@example.com"],
    public=False,
)

# Set current namespace
manager.set_current("engineering")

# Get current
current = get_current_namespace()
print(f"Current namespace: {current.name}")

# Check membership
if current.is_member("jdoe@example.com"):
    print("User is a member")

# Add member
manager.add_member("engineering", "newdev@example.com")

# Get DHT prefix
prefix = manager.get_dht_prefix("engineering")
```

## Namespace-Aware DHT Keys

Get DHT keys scoped to namespace:

```python
from wh.enterprise.namespace import get_namespace_dht_key

# Key for address in current namespace
key = get_namespace_dht_key("abc123")

# Key for address in specific namespace
key = get_namespace_dht_key("abc123", namespace="engineering")
```

## Storage Structure

Namespace data is stored in `~/.wh/namespaces/`:

```
~/.wh/namespaces/
├── engineering.yaml
├── sales.yaml
└── default.yaml
```

Each file contains:

```yaml
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

## Best Practices

### Naming Conventions

- Use lowercase, alphanumeric names
- Use hyphens for word separation
- Keep names short but descriptive

### Security

1. **Private by Default** - Create namespaces as private
2. **Minimal Admins** - Limit admin access
3. **Regular Audits** - Review membership periodically
4. **Namespace Policies** - Apply rate limits per namespace

### Organization

- One namespace per team/project
- Separate dev/staging/prod namespaces
- Archive unused namespaces

## See Also

- [Authentication](authentication.md)
- [Audit Logging](audit-logging.md)
- [Rate Limiting](rate-limiting.md)
