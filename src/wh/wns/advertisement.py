"""
WNS Code Advertisement - Signed announcements of current wormhole codes.

When a WNS server wants to accept connections, it:
1. Generates an ephemeral wormhole code
2. Signs an advertisement containing the code
3. Publishes the advertisement (to DHT, file, HTTP, etc.)

Clients fetch the advertisement, verify the signature, and connect using the code.
"""

import base64
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from wh.wns.identity import WNSIdentity


@dataclass
class CodeAdvertisement:
    """
    A signed advertisement of a current wormhole code.

    The advertisement contains:
    - address: The WNS address of the server
    - code: The current ephemeral wormhole code
    - timestamp: When the advertisement was created
    - expires: When the advertisement expires
    - public_key: The server's public key (for verification)
    - signature: Ed25519 signature of the above fields
    - scoped_name: Optional human-readable name prefix (e.g., "laptop")
    """

    address: str
    code: str
    timestamp: datetime
    expires: datetime
    public_key: bytes
    signature: bytes

    # Metadata (not signed)
    version: int = 1
    scoped_name: Optional[str] = None  # Human-readable name prefix

    @classmethod
    def create(
        cls,
        identity: WNSIdentity,
        code: str,
        ttl_seconds: int = 300,
    ) -> "CodeAdvertisement":
        """
        Create and sign a new code advertisement.

        Args:
            identity: The WNS identity to sign with (must have private key)
            code: The ephemeral wormhole code to advertise
            ttl_seconds: How long the advertisement is valid (default 5 minutes)
        """
        if not identity.can_sign:
            raise ValueError("Identity must have private key to create advertisement")

        now = datetime.now(timezone.utc)
        expires = datetime.fromtimestamp(
            now.timestamp() + ttl_seconds, tz=timezone.utc
        )

        # Create the message to sign
        message = cls._create_sign_message(
            address=identity.address,
            code=code,
            timestamp=now,
            expires=expires,
        )

        # Sign it
        signature = identity.sign(message)

        return cls(
            address=identity.address,
            code=code,
            timestamp=now,
            expires=expires,
            public_key=identity.public_key,
            signature=signature,
            scoped_name=identity.scoped_name,
        )

    @staticmethod
    def _create_sign_message(
        address: str,
        code: str,
        timestamp: datetime,
        expires: datetime,
    ) -> bytes:
        """Create the canonical message to sign."""
        # Use a deterministic format for signing
        msg = f"WNS-ADV-v1:{address}:{code}:{timestamp.isoformat()}:{expires.isoformat()}"
        return msg.encode("utf-8")

    def verify(self, expected_address: Optional[str] = None) -> bool:
        """
        Verify the advertisement signature and validity.

        Args:
            expected_address: If provided, verify the address matches

        Returns:
            True if valid, False otherwise
        """
        # Check expiry
        if self.is_expired():
            return False

        # Check address matches public key
        identity = WNSIdentity.from_public_key(self.public_key)
        if identity.address != self.address:
            return False

        # Check expected address if provided
        if expected_address and self.address != expected_address:
            return False

        # Verify signature
        message = self._create_sign_message(
            address=self.address,
            code=self.code,
            timestamp=self.timestamp,
            expires=self.expires,
        )
        return identity.verify(message, self.signature)

    def is_expired(self) -> bool:
        """Check if the advertisement has expired."""
        now = datetime.now(timezone.utc)
        return now >= self.expires

    def time_remaining(self) -> float:
        """Return seconds until expiry (negative if expired)."""
        now = datetime.now(timezone.utc)
        return (self.expires - now).total_seconds()

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        result = {
            "version": self.version,
            "address": self.address,
            "code": self.code,
            "timestamp": self.timestamp.isoformat(),
            "expires": self.expires.isoformat(),
            "public_key": base64.b64encode(self.public_key).decode("ascii"),
            "signature": base64.b64encode(self.signature).decode("ascii"),
        }
        if self.scoped_name:
            result["scoped_name"] = self.scoped_name
        return result

    @classmethod
    def from_json(cls, data: str) -> "CodeAdvertisement":
        """Deserialize from JSON string."""
        return cls.from_dict(json.loads(data))

    @classmethod
    def from_dict(cls, data: dict) -> "CodeAdvertisement":
        """Deserialize from dictionary."""
        return cls(
            version=data.get("version", 1),
            address=data["address"],
            code=data["code"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            expires=datetime.fromisoformat(data["expires"]),
            public_key=base64.b64decode(data["public_key"]),
            signature=base64.b64decode(data["signature"]),
            scoped_name=data.get("scoped_name"),
        )

    @property
    def full_address(self) -> str:
        """Get the full WNS address: wh://address.wns"""
        return f"wh://{self.address}.wns"

    @property
    def full_scoped_address(self) -> Optional[str]:
        """Get the full scoped address: wh://name.address.wns (or None if no scoped name)."""
        if not self.scoped_name:
            return None
        return f"wh://{self.scoped_name}.{self.address}.wns"

    def __str__(self) -> str:
        """Human-readable representation."""
        status = "EXPIRED" if self.is_expired() else f"{self.time_remaining():.0f}s remaining"
        addr = self.full_scoped_address or self.full_address
        return f"CodeAdvertisement({addr} -> {self.code}, {status})"
