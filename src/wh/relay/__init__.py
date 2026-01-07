"""
Built-in wormhole relay server and configuration management.

This module provides a self-contained relay server that eliminates
dependency on external infrastructure, plus multi-relay configuration
for organizations with private relays.
"""

from .mailbox import MailboxServer
from .transit import TransitRelay
from .server import RelayServer
from .config import RelayConfig, RelayConfigManager, get_relay_manager

__all__ = [
    "MailboxServer",
    "TransitRelay",
    "RelayServer",
    "RelayConfig",
    "RelayConfigManager",
    "get_relay_manager",
]
