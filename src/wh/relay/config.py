"""
Multi-relay configuration management.

Stores relay configurations in ~/.wh/relays.yaml with support for:
- Multiple named relays
- Default relay selection
- Namespace encryption keys (for relay-scoped WNS)
- Import/export of configurations
"""

import os
import yaml
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List
from pathlib import Path


# Default relay (official magic-wormhole server)
DEFAULT_MAILBOX_URL = "ws://relay.magic-wormhole.io:4000/v1"
DEFAULT_TRANSIT_URL = "tcp:transit.magic-wormhole.io:4001"


@dataclass
class RelayConfig:
    """Configuration for a single relay."""

    name: str
    mailbox_url: str
    transit_url: str
    namespace_key: Optional[str] = None  # Base64-encoded key for WNS encryption
    description: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary, omitting None values."""
        d = asdict(self)
        return {k: v for k, v in d.items() if v is not None}

    @classmethod
    def from_dict(cls, data: dict) -> "RelayConfig":
        """Create from dictionary."""
        return cls(
            name=data["name"],
            mailbox_url=data["mailbox_url"],
            transit_url=data["transit_url"],
            namespace_key=data.get("namespace_key"),
            description=data.get("description"),
        )


@dataclass
class RelayConfigFile:
    """Full relay configuration file."""

    default: str = "public"
    relays: Dict[str, RelayConfig] = field(default_factory=dict)

    def __post_init__(self):
        # Ensure public relay exists
        if "public" not in self.relays:
            self.relays["public"] = RelayConfig(
                name="public",
                mailbox_url=DEFAULT_MAILBOX_URL,
                transit_url=DEFAULT_TRANSIT_URL,
                description="Official Magic Wormhole relay",
            )

    def to_dict(self) -> dict:
        """Convert to dictionary for YAML serialization."""
        return {
            "default": self.default,
            "relays": {name: relay.to_dict() for name, relay in self.relays.items()},
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RelayConfigFile":
        """Create from dictionary."""
        relays = {}
        for name, relay_data in data.get("relays", {}).items():
            relay_data["name"] = name
            relays[name] = RelayConfig.from_dict(relay_data)

        return cls(
            default=data.get("default", "public"),
            relays=relays,
        )


class RelayConfigManager:
    """Manages relay configurations stored in ~/.wh/relays.yaml."""

    def __init__(self, config_dir: Optional[Path] = None):
        if config_dir is None:
            config_dir = Path.home() / ".wh"
        self.config_dir = Path(config_dir)
        self.config_file = self.config_dir / "relays.yaml"
        self._config: Optional[RelayConfigFile] = None

    def _ensure_dir(self) -> None:
        """Ensure config directory exists."""
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def load(self) -> RelayConfigFile:
        """Load configuration from file, creating default if needed."""
        if self._config is not None:
            return self._config

        if self.config_file.exists():
            with open(self.config_file, "r") as f:
                data = yaml.safe_load(f) or {}
            self._config = RelayConfigFile.from_dict(data)
        else:
            self._config = RelayConfigFile()

        return self._config

    def save(self) -> None:
        """Save configuration to file."""
        if self._config is None:
            return

        self._ensure_dir()
        with open(self.config_file, "w") as f:
            yaml.dump(
                self._config.to_dict(),
                f,
                default_flow_style=False,
                sort_keys=False,
            )

    def add_relay(
        self,
        name: str,
        mailbox_url: str,
        transit_url: str,
        namespace_key: Optional[str] = None,
        description: Optional[str] = None,
        set_default: bool = False,
    ) -> RelayConfig:
        """Add a new relay configuration."""
        config = self.load()

        relay = RelayConfig(
            name=name,
            mailbox_url=mailbox_url,
            transit_url=transit_url,
            namespace_key=namespace_key,
            description=description,
        )
        config.relays[name] = relay

        if set_default:
            config.default = name

        self.save()
        return relay

    def remove_relay(self, name: str) -> bool:
        """Remove a relay configuration. Returns True if removed."""
        config = self.load()

        if name == "public":
            raise ValueError("Cannot remove the 'public' relay")

        if name not in config.relays:
            return False

        del config.relays[name]

        # Reset default if needed
        if config.default == name:
            config.default = "public"

        self.save()
        return True

    def get_relay(self, name: Optional[str] = None) -> Optional[RelayConfig]:
        """Get a relay by name, or the default relay."""
        config = self.load()

        if name is None:
            name = config.default

        return config.relays.get(name)

    def get_default_relay(self) -> RelayConfig:
        """Get the default relay configuration."""
        config = self.load()
        return config.relays[config.default]

    def set_default(self, name: str) -> None:
        """Set the default relay."""
        config = self.load()

        if name not in config.relays:
            raise ValueError(f"Relay '{name}' not found")

        config.default = name
        self.save()

    def list_relays(self) -> List[RelayConfig]:
        """List all configured relays."""
        config = self.load()
        return list(config.relays.values())

    def export_relay(self, name: str) -> dict:
        """Export a relay configuration for sharing."""
        relay = self.get_relay(name)
        if relay is None:
            raise ValueError(f"Relay '{name}' not found")

        return {
            "version": 1,
            "relay": relay.to_dict(),
        }

    def import_relay(
        self,
        data: dict,
        name_override: Optional[str] = None,
        set_default: bool = False,
    ) -> RelayConfig:
        """Import a relay configuration from exported data."""
        if data.get("version") != 1:
            raise ValueError("Unsupported relay config version")

        relay_data = data["relay"]
        name = name_override or relay_data["name"]

        return self.add_relay(
            name=name,
            mailbox_url=relay_data["mailbox_url"],
            transit_url=relay_data["transit_url"],
            namespace_key=relay_data.get("namespace_key"),
            description=relay_data.get("description"),
            set_default=set_default,
        )


# Singleton instance
_manager: Optional[RelayConfigManager] = None


def get_relay_manager(config_dir: Optional[Path] = None) -> RelayConfigManager:
    """Get the relay configuration manager singleton."""
    global _manager
    if _manager is None or config_dir is not None:
        _manager = RelayConfigManager(config_dir)
    return _manager
