"""
LDAP Client utilities for enterprise authentication.

This module provides additional LDAP utilities beyond basic authentication:
- Connection pooling
- Group membership queries
- User attribute lookups
- Health checks

The main authentication is in auth.py (LDAPAuthenticator).
This module is for advanced LDAP operations.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


@dataclass
class LDAPConfig:
    """LDAP connection configuration."""
    server: str
    base_dn: str
    bind_dn: Optional[str] = None
    bind_password: Optional[str] = None
    use_tls: bool = True
    pool_size: int = 5
    timeout: float = 10.0
    retry_count: int = 3
    retry_delay: float = 1.0


@dataclass
class LDAPUser:
    """Represents an LDAP user."""
    dn: str
    username: str
    display_name: Optional[str] = None
    email: Optional[str] = None
    groups: List[str] = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)


class LDAPConnectionPool:
    """
    Connection pool for LDAP operations.

    Maintains a pool of connections to reduce connection overhead.
    """

    def __init__(self, config: LDAPConfig):
        self.config = config
        self._pool: List[Any] = []
        self._pool_lock = asyncio.Lock()
        self._available = asyncio.Semaphore(config.pool_size)
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the connection pool."""
        if self._initialized:
            return

        try:
            import ldap3
            self._ldap3 = ldap3
            self._initialized = True
            logger.info(f"LDAP pool initialized: {self.config.server}")
        except ImportError:
            raise ImportError("ldap3 library required: pip install ldap3")

    async def _create_connection(self) -> Any:
        """Create a new LDAP connection."""
        import ssl
        from ldap3 import Server, Connection, ALL, Tls

        tls_config = None
        if self.config.use_tls:
            tls_config = Tls(validate=ssl.CERT_OPTIONAL)

        server = Server(
            self.config.server,
            get_info=ALL,
            tls=tls_config,
            connect_timeout=self.config.timeout,
        )

        conn = Connection(
            server,
            user=self.config.bind_dn,
            password=self.config.bind_password,
            auto_bind=True,
            read_only=True,
        )

        return conn

    @asynccontextmanager
    async def acquire(self):
        """Acquire a connection from the pool."""
        await self._available.acquire()

        try:
            async with self._pool_lock:
                if self._pool:
                    conn = self._pool.pop()
                    # Verify connection is still valid
                    if not conn.bound:
                        conn = await self._create_connection()
                else:
                    conn = await self._create_connection()

            yield conn

            # Return to pool
            async with self._pool_lock:
                if len(self._pool) < self.config.pool_size:
                    self._pool.append(conn)
                else:
                    conn.unbind()
        finally:
            self._available.release()

    async def close(self) -> None:
        """Close all connections in the pool."""
        async with self._pool_lock:
            for conn in self._pool:
                try:
                    conn.unbind()
                except Exception:
                    pass
            self._pool.clear()
        self._initialized = False


class LDAPClient:
    """
    High-level LDAP client for user and group operations.

    Usage:
        config = LDAPConfig(
            server="ldap://ldap.example.com:389",
            base_dn="dc=example,dc=com",
            bind_dn="cn=service,dc=example,dc=com",
            bind_password="secret",
        )

        client = LDAPClient(config)
        await client.connect()

        user = await client.get_user("jdoe")
        groups = await client.get_user_groups("jdoe")

        await client.close()
    """

    def __init__(self, config: LDAPConfig):
        self.config = config
        self._pool: Optional[LDAPConnectionPool] = None

    async def connect(self) -> None:
        """Initialize connection pool."""
        self._pool = LDAPConnectionPool(self.config)
        await self._pool.initialize()

    async def close(self) -> None:
        """Close connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None

    async def get_user(
        self,
        username: str,
        user_filter: str = "(uid={username})",
        attributes: Optional[List[str]] = None,
    ) -> Optional[LDAPUser]:
        """
        Look up a user by username.

        Args:
            username: The username to search for
            user_filter: LDAP filter template (default: uid search)
            attributes: Specific attributes to fetch

        Returns:
            LDAPUser if found, None otherwise
        """
        if not self._pool:
            raise RuntimeError("Client not connected")

        from ldap3 import SUBTREE

        search_filter = user_filter.format(username=username)
        attrs = attributes or ["cn", "mail", "memberOf", "displayName"]

        async with self._pool.acquire() as conn:
            conn.search(
                search_base=self.config.base_dn,
                search_filter=search_filter,
                search_scope=SUBTREE,
                attributes=attrs,
            )

            if not conn.entries:
                return None

            entry = conn.entries[0]

            # Extract standard attributes
            display_name = None
            email = None
            groups = []

            if hasattr(entry, "displayName") and entry.displayName:
                display_name = str(entry.displayName)
            if hasattr(entry, "cn") and entry.cn:
                display_name = display_name or str(entry.cn)
            if hasattr(entry, "mail") and entry.mail:
                email = str(entry.mail)
            if hasattr(entry, "memberOf") and entry.memberOf:
                groups = list(entry.memberOf)

            # Collect all attributes
            all_attrs = {}
            for attr in attrs:
                if hasattr(entry, attr):
                    value = getattr(entry, attr)
                    if value:
                        all_attrs[attr] = value.value if hasattr(value, "value") else str(value)

            return LDAPUser(
                dn=entry.entry_dn,
                username=username,
                display_name=display_name,
                email=email,
                groups=groups,
                attributes=all_attrs,
            )

    async def get_user_groups(
        self,
        username: str,
        group_attribute: str = "memberOf",
    ) -> List[str]:
        """
        Get all groups a user belongs to.

        Args:
            username: The username to look up
            group_attribute: Attribute containing group membership

        Returns:
            List of group DNs
        """
        user = await self.get_user(username, attributes=[group_attribute])
        if not user:
            return []
        return user.groups

    async def is_member_of(
        self,
        username: str,
        group_dn: str,
    ) -> bool:
        """
        Check if user is a member of a specific group.

        Args:
            username: The username to check
            group_dn: The group DN to check membership in

        Returns:
            True if user is a member
        """
        groups = await self.get_user_groups(username)
        return any(group_dn.lower() in g.lower() for g in groups)

    async def search_users(
        self,
        search_filter: str,
        attributes: Optional[List[str]] = None,
        limit: int = 100,
    ) -> List[LDAPUser]:
        """
        Search for users matching a filter.

        Args:
            search_filter: LDAP search filter
            attributes: Attributes to return
            limit: Maximum number of results

        Returns:
            List of matching LDAPUser objects
        """
        if not self._pool:
            raise RuntimeError("Client not connected")

        from ldap3 import SUBTREE

        attrs = attributes or ["uid", "cn", "mail", "memberOf", "displayName"]

        async with self._pool.acquire() as conn:
            conn.search(
                search_base=self.config.base_dn,
                search_filter=search_filter,
                search_scope=SUBTREE,
                attributes=attrs,
                size_limit=limit,
            )

            users = []
            for entry in conn.entries[:limit]:
                username = None
                if hasattr(entry, "uid") and entry.uid:
                    username = str(entry.uid)

                if not username:
                    continue

                display_name = None
                email = None
                groups = []

                if hasattr(entry, "displayName") and entry.displayName:
                    display_name = str(entry.displayName)
                if hasattr(entry, "cn") and entry.cn:
                    display_name = display_name or str(entry.cn)
                if hasattr(entry, "mail") and entry.mail:
                    email = str(entry.mail)
                if hasattr(entry, "memberOf") and entry.memberOf:
                    groups = list(entry.memberOf)

                users.append(LDAPUser(
                    dn=entry.entry_dn,
                    username=username,
                    display_name=display_name,
                    email=email,
                    groups=groups,
                ))

            return users

    async def health_check(self) -> bool:
        """
        Check if LDAP server is accessible.

        Returns:
            True if server is healthy
        """
        if not self._pool:
            return False

        try:
            async with self._pool.acquire() as conn:
                return conn.bound
        except Exception as e:
            logger.warning(f"LDAP health check failed: {e}")
            return False


async def create_ldap_client(
    server: str,
    base_dn: str,
    bind_dn: Optional[str] = None,
    bind_password: Optional[str] = None,
    use_tls: bool = True,
) -> LDAPClient:
    """
    Create and connect an LDAP client.

    Args:
        server: LDAP server URL
        base_dn: Base DN for searches
        bind_dn: Optional bind DN for authentication
        bind_password: Optional bind password
        use_tls: Whether to use TLS

    Returns:
        Connected LDAPClient instance
    """
    config = LDAPConfig(
        server=server,
        base_dn=base_dn,
        bind_dn=bind_dn,
        bind_password=bind_password,
        use_tls=use_tls,
    )

    client = LDAPClient(config)
    await client.connect()
    return client
