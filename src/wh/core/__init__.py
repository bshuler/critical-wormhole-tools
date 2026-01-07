"""Core wormhole abstractions and utilities."""

from wh.core.wormhole_manager import WormholeManager
from wh.core.protocol import StreamingProtocol, BidirectionalPipe

__all__ = ["WormholeManager", "StreamingProtocol", "BidirectionalPipe"]
