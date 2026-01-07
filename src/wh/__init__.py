"""
Wormhole Tools (wh) - Network utilities with code-based addressing.

This module sets up the asyncio reactor for Twisted compatibility.
IMPORTANT: This must be imported before any other Twisted imports.
"""

import asyncio
import sys

# Install asyncio reactor for Twisted BEFORE any other Twisted imports
# This allows us to use asyncio with magic-wormhole (which uses Twisted)
def _install_reactor():
    """Install the asyncio reactor if not already installed."""
    # Check if reactor is already installed
    if 'twisted.internet.reactor' in sys.modules:
        # Reactor already installed, nothing we can do
        return

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        from twisted.internet import asyncioreactor
        asyncioreactor.install(loop)
    except Exception as e:
        # Reactor may already be installed in test environments
        print(f"Warning: Could not install asyncio reactor: {e}", file=sys.stderr)

_install_reactor()

__version__ = "0.3.0"
__all__ = ["__version__"]
