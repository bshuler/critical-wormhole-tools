"""
WNS Aliases - Local petnames for WNS addresses.

Provides SSH-config style aliases for WNS addresses, allowing users
to assign memorable names to cryptographic addresses.

Storage: ~/.wh/aliases.json
"""

import json
import logging
from pathlib import Path
from typing import Optional, Dict, List
from dataclasses import dataclass, asdict

from wh.wns.identity import parse_wns_address, is_wns_address


logger = logging.getLogger(__name__)


@dataclass
class Alias:
    """A local alias for a WNS address."""

    name: str
    address: str  # Full WNS address (wh://xxx.wns)
    description: Optional[str] = None
    username: Optional[str] = None  # Default username for this alias

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {k: v for k, v in asdict(self).items() if v is not None}

    @classmethod
    def from_dict(cls, data: dict) -> "Alias":
        """Create from dictionary."""
        return cls(
            name=data["name"],
            address=data["address"],
            description=data.get("description"),
            username=data.get("username"),
        )


class AliasStore:
    """
    Manages local aliases for WNS addresses.

    Aliases are stored in ~/.wh/aliases.json and provide a way to
    assign memorable names to cryptographic WNS addresses.

    Usage:
        store = AliasStore()
        store.add("laptop", "wh://abc123def456.wns", description="My laptop")
        address = store.resolve("laptop")  # Returns "wh://abc123def456.wns"
    """

    def __init__(self, base_path: Optional[Path] = None):
        """Initialize alias store."""
        if base_path is None:
            base_path = Path.home() / ".wh"
        self.base_path = Path(base_path)
        self.aliases_file = self.base_path / "aliases.json"
        self._aliases: Dict[str, Alias] = {}
        self._load()

    def _load(self) -> None:
        """Load aliases from disk."""
        if not self.aliases_file.exists():
            self._aliases = {}
            return

        try:
            with open(self.aliases_file) as f:
                data = json.load(f)

            self._aliases = {
                name: Alias.from_dict(alias_data)
                for name, alias_data in data.get("aliases", {}).items()
            }
        except Exception as e:
            logger.warning(f"Failed to load aliases: {e}")
            self._aliases = {}

    def _save(self) -> None:
        """Save aliases to disk."""
        self.base_path.mkdir(parents=True, exist_ok=True)

        data = {
            "version": 1,
            "aliases": {name: alias.to_dict() for name, alias in self._aliases.items()},
        }

        with open(self.aliases_file, "w") as f:
            json.dump(data, f, indent=2)

    def add(
        self,
        name: str,
        address: str,
        description: Optional[str] = None,
        username: Optional[str] = None,
        overwrite: bool = False,
    ) -> None:
        """
        Add a new alias.

        Args:
            name: The alias name (e.g., "laptop", "work-server")
            address: The WNS address (wh://xxx.wns or bare address)
            description: Optional description
            username: Optional default username
            overwrite: If True, overwrite existing alias

        Raises:
            ValueError: If alias exists and overwrite=False, or address invalid
        """
        # Validate name
        if not name or not name.replace("-", "").replace("_", "").isalnum():
            raise ValueError(
                f"Invalid alias name: {name}. Use alphanumeric, dash, or underscore."
            )

        # Normalize address to full format
        if not address.startswith("wh://"):
            if not address.endswith(".wns"):
                address = f"wh://{address}.wns"
            else:
                address = f"wh://{address}"

        # Validate address format
        parsed = parse_wns_address(address)
        if not parsed:
            raise ValueError(f"Invalid WNS address: {address}")

        # Check for existing
        if name in self._aliases and not overwrite:
            raise ValueError(f"Alias '{name}' already exists. Use --force to overwrite.")

        self._aliases[name] = Alias(
            name=name,
            address=address,
            description=description,
            username=username,
        )
        self._save()
        logger.info(f"Added alias: {name} -> {address}")

    def remove(self, name: str) -> bool:
        """
        Remove an alias.

        Returns:
            True if alias was removed, False if it didn't exist.
        """
        if name not in self._aliases:
            return False

        del self._aliases[name]
        self._save()
        logger.info(f"Removed alias: {name}")
        return True

    def get(self, name: str) -> Optional[Alias]:
        """Get an alias by name."""
        return self._aliases.get(name)

    def resolve(self, name_or_address: str) -> Optional[str]:
        """
        Resolve an alias or pass through an address.

        If the input is an alias name, returns the WNS address.
        If the input is already a WNS address, returns it unchanged.
        If the input is a regular wormhole code, returns None.

        Args:
            name_or_address: Alias name or WNS address

        Returns:
            WNS address if resolvable, None otherwise
        """
        # Check if it's already a WNS address
        if is_wns_address(name_or_address):
            return name_or_address

        # Check if it's an alias
        alias = self._aliases.get(name_or_address)
        if alias:
            return alias.address

        # Not an alias or WNS address
        return None

    def resolve_with_username(self, name_or_address: str) -> tuple:
        """
        Resolve an alias and return address with optional username.

        Returns:
            Tuple of (address, username) where username may be None
        """
        # Handle user@alias format
        username = None
        if "@" in name_or_address and not is_wns_address(name_or_address):
            username, name_or_address = name_or_address.split("@", 1)

        # Check if it's already a WNS address
        if is_wns_address(name_or_address):
            return name_or_address, username

        # Check if it's an alias
        alias = self._aliases.get(name_or_address)
        if alias:
            # Use provided username, fall back to alias default
            return alias.address, username or alias.username

        return None, None

    def list(self) -> List[Alias]:
        """List all aliases."""
        return list(self._aliases.values())

    def search(self, query: str) -> List[Alias]:
        """Search aliases by name or description."""
        query = query.lower()
        return [
            alias
            for alias in self._aliases.values()
            if query in alias.name.lower()
            or (alias.description and query in alias.description.lower())
        ]


def resolve_name(name_or_address: str) -> Optional[str]:
    """
    Convenience function to resolve a name to a WNS address.

    Checks local aliases first, then returns WNS addresses as-is.
    Returns None for regular wormhole codes.
    """
    store = AliasStore()
    return store.resolve(name_or_address)


def is_alias_or_wns(name_or_address: str) -> bool:
    """Check if a string is an alias or WNS address (vs regular code)."""
    store = AliasStore()
    return store.resolve(name_or_address) is not None
