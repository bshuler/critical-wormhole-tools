"""
Wormhole Name Service (WNS) - Persistent addressing for Magic Wormhole.

WNS provides self-certifying addresses (like Tor .onion) that map to
dynamically changing ephemeral wormhole codes. This allows persistent
server addresses even though wormhole codes are single-use.

Address format: wh://a7b3c9d2e1f4g5h6.wns

The address is derived from: base32(sha256(ed25519_public_key)[:16])
"""

from wh.wns.identity import WNSIdentity, WNSIdentityStore

__all__ = ["WNSIdentity", "WNSIdentityStore"]
