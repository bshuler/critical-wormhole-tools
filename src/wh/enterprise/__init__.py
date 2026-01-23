"""
Enterprise features for Critical Wormhole Tools.

This module provides enterprise-grade functionality:
- Authentication (pubkey, password, LDAP)
- Audit logging for SIEM integration
- Rate limiting and policy enforcement
- Multi-tenancy with namespace isolation
"""

from wh.enterprise.auth import (
    AuthMethod,
    AuthConfig,
    AuthResult,
    Authenticator,
    PubkeyAuthenticator,
    PasswordAuthenticator,
    LDAPAuthenticator,
    create_authenticator,
)

from wh.enterprise.audit import (
    AuditEvent,
    AuditEventType,
    AuditLogger,
    get_audit_logger,
)

from wh.enterprise.rate_limiter import (
    RateLimiter,
    RateLimitExceeded,
    BandwidthQuotaExceeded,
    ConnectionLimitExceeded,
)

from wh.enterprise.policy import (
    Policy,
    PolicyConfig,
    RateLimitConfig,
    QuotaConfig,
    load_policy,
)

from wh.enterprise.namespace import (
    Namespace,
    NamespaceManager,
    NamespaceNotFoundError,
    NamespaceExistsError,
)

__all__ = [
    # Auth
    "AuthMethod",
    "AuthConfig",
    "AuthResult",
    "Authenticator",
    "PubkeyAuthenticator",
    "PasswordAuthenticator",
    "LDAPAuthenticator",
    "create_authenticator",
    # Audit
    "AuditEvent",
    "AuditEventType",
    "AuditLogger",
    "get_audit_logger",
    # Rate limiting
    "RateLimiter",
    "RateLimitExceeded",
    "BandwidthQuotaExceeded",
    "ConnectionLimitExceeded",
    # Policy
    "Policy",
    "PolicyConfig",
    "RateLimitConfig",
    "QuotaConfig",
    "load_policy",
    # Namespace
    "Namespace",
    "NamespaceManager",
    "NamespaceNotFoundError",
    "NamespaceExistsError",
]
