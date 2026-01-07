"""
Built-in wormhole relay server.

This module provides a self-contained relay server that eliminates
dependency on external infrastructure.
"""

from .mailbox import MailboxServer
from .transit import TransitRelay
from .server import RelayServer

__all__ = ["MailboxServer", "TransitRelay", "RelayServer"]
