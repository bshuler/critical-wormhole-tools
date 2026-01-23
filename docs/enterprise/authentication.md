# Enterprise Authentication

Critical Wormhole Tools supports multiple authentication methods for enterprise deployments.

## Authentication Methods

### None (Default)

No authentication - any connection is allowed. This is the default for development and testing.

```bash
wh listen --ssh
```

### Public Key Authentication

SSH-style public key authentication using Ed25519 keys.

```bash
wh listen --ssh --auth-method=pubkey --authorized-keys=/etc/wh/authorized_keys
```

**Authorized Keys File Format:**
```
<base64-public-key> <key-id-or-comment>
<base64-public-key> admin@example.com
```

Generate a keypair:
```bash
# Using wh identity
wh identity create --name my-client
wh identity export <address>  # Get the public key
```

### Password Authentication

Simple username/password authentication using htpasswd-style files.

```bash
wh listen --ssh --auth-method=password --password-file=/etc/wh/passwd
```

**Password File Format:**
```
username:bcrypt_hash
admin:$2b$12$...
```

Generate password hash:
```bash
# Using Python
python -c "import bcrypt; print(bcrypt.hashpw(b'password', bcrypt.gensalt()).decode())"
```

### LDAP/Active Directory Authentication

Authenticate against LDAP or Active Directory servers.

```bash
wh listen --ssh \
    --auth-method=ldap \
    --ldap-server=ldap://ldap.company.com:389 \
    --ldap-base-dn="dc=company,dc=com"
```

**Advanced LDAP Options:**

| Option | Description |
|--------|-------------|
| `--ldap-server` | LDAP server URL |
| `--ldap-base-dn` | Base DN for user searches |
| `--ldap-bind-dn` | Service account DN (optional) |
| `--ldap-bind-password` | Service account password |

**Environment Variables:**
```bash
export WH_LDAP_BIND_DN="cn=service,dc=company,dc=com"
export WH_LDAP_BIND_PASSWORD="secret"
```

## Authentication Flow

1. Client connects to wormhole
2. Server sends authentication challenge
3. Client responds with credentials
4. Server verifies credentials
5. On success, connection proceeds
6. On failure, connection is rejected

## Programmatic Usage

```python
from wh.enterprise.auth import AuthMethod, create_authenticator

# Create authenticator
auth = create_authenticator(
    AuthMethod.LDAP,
    ldap_server="ldap://ldap.company.com",
    ldap_base_dn="dc=company,dc=com",
)

# Authenticate
result = await auth.authenticate({
    "username": "jdoe",
    "password": "secret",
})

if result.success:
    print(f"Authenticated as {result.identity}")
    print(f"Groups: {result.groups}")
else:
    print(f"Failed: {result.error}")
```

## Security Considerations

1. **Use TLS for LDAP** - Enable TLS for LDAP connections (ldaps://)
2. **Rotate Keys** - Regularly rotate authorized keys
3. **Use Strong Passwords** - Enforce password policies
4. **Audit Authentication** - Enable audit logging to track attempts
5. **Limit Retries** - Implement rate limiting for auth failures

## See Also

- [Audit Logging](audit-logging.md)
- [Rate Limiting](rate-limiting.md)
- [Multi-Tenancy](multi-tenancy.md)
