"""
Enterprise Multi-Tenancy Namespace Module.

Provides namespace isolation for multi-tenant deployments:
- Namespace-specific DHT prefixes
- Isolated identity stores
- Namespace management commands

Usage:
    manager = NamespaceManager()

    # Create namespace
    ns = await manager.create("engineering")

    # Use namespace
    with manager.use("engineering"):
        # All operations use engineering namespace
        wh listen --ssh

    # CLI usage
    wh --namespace=engineering listen --ssh
    wh --namespace=engineering ssh team-server
"""

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


logger = logging.getLogger(__name__)


class NamespaceNotFoundError(Exception):
    """Raised when a namespace doesn't exist."""
    pass


class NamespaceExistsError(Exception):
    """Raised when trying to create a namespace that already exists."""
    pass


@dataclass
class Namespace:
    """
    Represents an isolated namespace.

    Each namespace has:
    - Unique name
    - DHT prefix for isolation
    - Optional admin identities
    - Quota and policy overrides
    """
    name: str
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    description: Optional[str] = None
    dht_prefix: Optional[str] = None  # Auto-generated if not provided
    admins: List[str] = field(default_factory=list)  # Admin identity addresses
    members: List[str] = field(default_factory=list)  # Member identity addresses
    public: bool = False  # Whether anyone can join
    max_members: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        # Generate DHT prefix if not provided
        if not self.dht_prefix:
            self.dht_prefix = self._generate_dht_prefix()

    def _generate_dht_prefix(self) -> str:
        """Generate a unique DHT prefix for this namespace."""
        # Use SHA256 of namespace name, take first 8 bytes
        hash_bytes = hashlib.sha256(f"wns-namespace:{self.name}".encode()).digest()
        return hash_bytes[:8].hex()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "created_at": self.created_at,
            "description": self.description,
            "dht_prefix": self.dht_prefix,
            "admins": self.admins,
            "members": self.members,
            "public": self.public,
            "max_members": self.max_members,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Namespace":
        """Create from dictionary."""
        return cls(
            name=data["name"],
            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
            description=data.get("description"),
            dht_prefix=data.get("dht_prefix"),
            admins=data.get("admins", []),
            members=data.get("members", []),
            public=data.get("public", False),
            max_members=data.get("max_members"),
            metadata=data.get("metadata", {}),
        )

    def is_admin(self, identity: str) -> bool:
        """Check if an identity is a namespace admin."""
        return identity in self.admins

    def is_member(self, identity: str) -> bool:
        """Check if an identity is a namespace member."""
        return identity in self.members or identity in self.admins or self.public

    def can_join(self, identity: str) -> bool:
        """Check if an identity can join this namespace."""
        if self.is_member(identity):
            return True
        if self.public:
            # Check member limit (count admins and members)
            total_members = len(self.members) + len(self.admins)
            if self.max_members and total_members >= self.max_members:
                return False
            return True
        return False


class NamespaceManager:
    """
    Manages namespaces for multi-tenancy.

    Stores namespace configuration in ~/.wh/namespaces/
    """

    DEFAULT_NAMESPACE = "default"

    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or (Path.home() / ".wh" / "namespaces")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._current_namespace: Optional[str] = None
        self._namespaces: Dict[str, Namespace] = {}
        self._load_namespaces()

    def _get_namespace_path(self, name: str) -> Path:
        """Get path to namespace config file."""
        return self.data_dir / f"{name}.yaml"

    def _load_namespaces(self) -> None:
        """Load all namespace configurations."""
        self._namespaces.clear()

        # Always have default namespace
        default = Namespace(
            name=self.DEFAULT_NAMESPACE,
            description="Default namespace",
            public=True,
        )
        self._namespaces[self.DEFAULT_NAMESPACE] = default

        # Load from files
        for path in self.data_dir.glob("*.yaml"):
            try:
                with open(path, "r") as f:
                    data = yaml.safe_load(f) or {}
                ns = Namespace.from_dict(data)
                self._namespaces[ns.name] = ns
            except Exception as e:
                logger.warning(f"Failed to load namespace from {path}: {e}")

    def _save_namespace(self, ns: Namespace) -> None:
        """Save namespace to file."""
        path = self._get_namespace_path(ns.name)
        with open(path, "w") as f:
            yaml.safe_dump(ns.to_dict(), f)

    def _delete_namespace_file(self, name: str) -> None:
        """Delete namespace file."""
        path = self._get_namespace_path(name)
        if path.exists():
            path.unlink()

    def list(self) -> List[Namespace]:
        """List all namespaces."""
        return list(self._namespaces.values())

    def get(self, name: str) -> Namespace:
        """
        Get a namespace by name.

        Args:
            name: Namespace name

        Returns:
            Namespace object

        Raises:
            NamespaceNotFoundError: If namespace doesn't exist
        """
        if name not in self._namespaces:
            raise NamespaceNotFoundError(f"Namespace not found: {name}")
        return self._namespaces[name]

    def exists(self, name: str) -> bool:
        """Check if a namespace exists."""
        return name in self._namespaces

    def create(
        self,
        name: str,
        description: Optional[str] = None,
        admins: Optional[List[str]] = None,
        public: bool = False,
        max_members: Optional[int] = None,
    ) -> Namespace:
        """
        Create a new namespace.

        Args:
            name: Unique namespace name
            description: Optional description
            admins: List of admin identity addresses
            public: Whether namespace is public
            max_members: Maximum number of members

        Returns:
            Created Namespace

        Raises:
            NamespaceExistsError: If namespace already exists
            ValueError: If name is invalid
        """
        # Validate name
        if not name or not name.replace("-", "").replace("_", "").isalnum():
            raise ValueError(f"Invalid namespace name: {name}")

        if name in self._namespaces:
            raise NamespaceExistsError(f"Namespace already exists: {name}")

        ns = Namespace(
            name=name,
            description=description,
            admins=admins or [],
            public=public,
            max_members=max_members,
        )

        self._namespaces[name] = ns
        self._save_namespace(ns)

        logger.info(f"Created namespace: {name}")
        return ns

    def delete(self, name: str, force: bool = False) -> None:
        """
        Delete a namespace.

        Args:
            name: Namespace name
            force: Force delete even if not empty

        Raises:
            NamespaceNotFoundError: If namespace doesn't exist
            ValueError: If trying to delete default namespace
        """
        if name == self.DEFAULT_NAMESPACE:
            raise ValueError("Cannot delete default namespace")

        if name not in self._namespaces:
            raise NamespaceNotFoundError(f"Namespace not found: {name}")

        ns = self._namespaces[name]

        if not force and ns.members:
            raise ValueError(f"Namespace has {len(ns.members)} members. Use force=True to delete.")

        del self._namespaces[name]
        self._delete_namespace_file(name)

        logger.info(f"Deleted namespace: {name}")

    def update(
        self,
        name: str,
        description: Optional[str] = None,
        public: Optional[bool] = None,
        max_members: Optional[int] = None,
    ) -> Namespace:
        """
        Update namespace settings.

        Args:
            name: Namespace name
            description: New description
            public: New public setting
            max_members: New member limit

        Returns:
            Updated Namespace
        """
        ns = self.get(name)

        if description is not None:
            ns.description = description
        if public is not None:
            ns.public = public
        if max_members is not None:
            ns.max_members = max_members

        self._save_namespace(ns)
        return ns

    def add_admin(self, name: str, identity: str) -> Namespace:
        """Add an admin to a namespace."""
        ns = self.get(name)
        if identity not in ns.admins:
            ns.admins.append(identity)
            self._save_namespace(ns)
        return ns

    def remove_admin(self, name: str, identity: str) -> Namespace:
        """Remove an admin from a namespace."""
        ns = self.get(name)
        if identity in ns.admins:
            ns.admins.remove(identity)
            self._save_namespace(ns)
        return ns

    def add_member(self, name: str, identity: str) -> Namespace:
        """Add a member to a namespace."""
        ns = self.get(name)

        if ns.max_members and len(ns.members) >= ns.max_members:
            raise ValueError(f"Namespace has reached member limit: {ns.max_members}")

        if identity not in ns.members:
            ns.members.append(identity)
            self._save_namespace(ns)
        return ns

    def remove_member(self, name: str, identity: str) -> Namespace:
        """Remove a member from a namespace."""
        ns = self.get(name)
        if identity in ns.members:
            ns.members.remove(identity)
            self._save_namespace(ns)
        return ns

    def get_dht_prefix(self, name: str) -> str:
        """Get the DHT prefix for a namespace."""
        ns = self.get(name)
        return ns.dht_prefix or ""

    def get_current(self) -> Namespace:
        """Get the currently active namespace."""
        name = self._current_namespace or self.DEFAULT_NAMESPACE
        return self.get(name)

    def set_current(self, name: str) -> None:
        """Set the current namespace."""
        if not self.exists(name):
            raise NamespaceNotFoundError(f"Namespace not found: {name}")
        self._current_namespace = name

    def clear_current(self) -> None:
        """Clear the current namespace (revert to default)."""
        self._current_namespace = None


# Global namespace manager
_namespace_manager: Optional[NamespaceManager] = None


def get_namespace_manager() -> NamespaceManager:
    """Get the global namespace manager."""
    global _namespace_manager
    if _namespace_manager is None:
        _namespace_manager = NamespaceManager()
    return _namespace_manager


def get_current_namespace() -> Namespace:
    """Get the currently active namespace."""
    return get_namespace_manager().get_current()


def get_namespace_dht_key(address: str, namespace: Optional[str] = None) -> bytes:
    """
    Get a namespace-prefixed DHT key for an address.

    Args:
        address: The WNS address
        namespace: Namespace name (uses current if not specified)

    Returns:
        32-byte DHT key with namespace prefix
    """
    manager = get_namespace_manager()
    ns = manager.get(namespace) if namespace else manager.get_current()

    # Combine namespace prefix with address for DHT key
    combined = f"{ns.dht_prefix}:{address}"
    return hashlib.sha256(combined.encode()).digest()
