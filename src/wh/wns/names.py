"""
WNS Global Names - First-come-first-served name registry via DHT.

Global names allow human-readable addresses like wh://laptop.wns without
the cryptographic address suffix. Names are claimed on a first-come-first-served
basis and stored in the DHT.

Security considerations:
- Names can be squatted (first claim wins)
- No dispute resolution mechanism
- Claims expire if not renewed
- For secure connections, verify the public key matches expected
"""

import base64
import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from wh.wns.identity import WNSIdentity, WNSIdentityStore, BASE32_ALPHABET


logger = logging.getLogger(__name__)


# Global name claim TTL (7 days)
NAME_CLAIM_TTL_SECONDS = 7 * 24 * 60 * 60

# Maximum name length
MAX_NAME_LENGTH = 32

# Reserved names that cannot be claimed
RESERVED_NAMES = {
    "wh", "wns", "wormhole", "admin", "root", "system",
    "localhost", "local", "test", "example",
}


def name_to_dht_key(name: str) -> bytes:
    """Convert a global name to a DHT key."""
    # Prefix to avoid collision with address-based keys
    key_string = f"wns-name:{name.lower()}"
    return hashlib.sha256(key_string.encode("utf-8")).digest()


def is_valid_global_name(name: str) -> bool:
    """Check if a name is valid for global registration."""
    if not name or len(name) > MAX_NAME_LENGTH:
        return False

    # Must be alphanumeric with dashes/underscores
    if not name.replace("-", "").replace("_", "").isalnum():
        return False

    # Cannot be reserved
    if name.lower() in RESERVED_NAMES:
        return False

    # Cannot look like a base32 address (26 chars, all base32)
    if len(name) == 26 and all(c in BASE32_ALPHABET for c in name.lower()):
        return False

    # Cannot look like a wormhole code (starts with digit-word pattern)
    # Wormhole codes are like "7-guitar-sunset"
    if name[0].isdigit() and "-" in name:
        return False

    return True


def is_global_name_address(uri: str) -> bool:
    """
    Check if a URI is a global name (vs scoped or full address).

    Global names: wh://laptop.wns (short name, no address suffix)
    Scoped names: wh://laptop.abc123def456.wns (name + address)
    Full address: wh://abc123def456.wns (just address)
    """
    uri = uri.strip()

    # Remove user@ prefix
    if "@" in uri:
        _, uri = uri.rsplit("@", 1)

    # Must have wh:// and .wns
    if not uri.startswith("wh://") or not uri.endswith(".wns"):
        return False

    # Extract the middle part
    middle = uri[5:-4]  # Remove "wh://" and ".wns"

    # Check if it's a simple name (no dots, not a 26-char address)
    if "." in middle:
        return False  # Has dots = scoped name

    if len(middle) == 26 and all(c in BASE32_ALPHABET for c in middle.lower()):
        return False  # It's a full address

    # It's a global name
    return is_valid_global_name(middle)


def parse_global_name(uri: str) -> Optional[str]:
    """
    Parse a global name URI and return the name.

    Returns the name if it's a valid global name URI, None otherwise.
    """
    uri = uri.strip()

    # Remove user@ prefix
    if "@" in uri:
        _, uri = uri.rsplit("@", 1)

    # Remove wh:// prefix
    if uri.startswith("wh://"):
        uri = uri[5:]

    # Remove .wns suffix
    if uri.endswith(".wns"):
        uri = uri[:-4]

    # Validate it's a global name
    if is_valid_global_name(uri) and "." not in uri:
        return uri.lower()

    return None


@dataclass
class NameClaim:
    """
    A signed claim for a global name.

    The claim proves ownership of a name by linking it to a WNS identity.
    Claims are published to the DHT and must be renewed before expiry.
    """

    name: str  # The claimed name (e.g., "laptop")
    address: str  # The WNS address that owns this name
    timestamp: datetime  # When the claim was made/renewed
    expires: datetime  # When the claim expires
    public_key: bytes  # Public key of the claimer
    signature: bytes  # Signature proving ownership

    version: int = 1

    @classmethod
    def create(
        cls,
        identity: WNSIdentity,
        name: str,
        ttl_seconds: int = NAME_CLAIM_TTL_SECONDS,
    ) -> "NameClaim":
        """
        Create and sign a new name claim.

        Args:
            identity: The WNS identity claiming the name
            name: The name to claim
            ttl_seconds: How long the claim is valid
        """
        if not identity.can_sign:
            raise ValueError("Identity must have private key")

        if not is_valid_global_name(name):
            raise ValueError(f"Invalid name: {name}")

        name = name.lower()
        now = datetime.now(timezone.utc)
        expires = datetime.fromtimestamp(
            now.timestamp() + ttl_seconds, tz=timezone.utc
        )

        message = cls._create_sign_message(name, identity.address, now, expires)
        signature = identity.sign(message)

        return cls(
            name=name,
            address=identity.address,
            timestamp=now,
            expires=expires,
            public_key=identity.public_key,
            signature=signature,
        )

    @staticmethod
    def _create_sign_message(
        name: str,
        address: str,
        timestamp: datetime,
        expires: datetime,
    ) -> bytes:
        """Create the canonical message to sign."""
        msg = f"WNS-NAME-v1:{name}:{address}:{timestamp.isoformat()}:{expires.isoformat()}"
        return msg.encode("utf-8")

    def verify(self, expected_name: Optional[str] = None) -> bool:
        """
        Verify the claim signature and validity.

        Args:
            expected_name: If provided, verify the name matches

        Returns:
            True if valid, False otherwise
        """
        # Check expiry
        if self.is_expired():
            return False

        # Check expected name if provided
        if expected_name and self.name.lower() != expected_name.lower():
            return False

        # Check address matches public key
        identity = WNSIdentity.from_public_key(self.public_key)
        if identity.address != self.address:
            return False

        # Verify signature
        message = self._create_sign_message(
            self.name, self.address, self.timestamp, self.expires
        )
        return identity.verify(message, self.signature)

    def is_expired(self) -> bool:
        """Check if the claim has expired."""
        now = datetime.now(timezone.utc)
        return now >= self.expires

    def time_remaining(self) -> float:
        """Return seconds until expiry (negative if expired)."""
        now = datetime.now(timezone.utc)
        return (self.expires - now).total_seconds()

    @property
    def full_address(self) -> str:
        """Get the full global name address: wh://name.wns"""
        return f"wh://{self.name}.wns"

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "version": self.version,
            "name": self.name,
            "address": self.address,
            "timestamp": self.timestamp.isoformat(),
            "expires": self.expires.isoformat(),
            "public_key": base64.b64encode(self.public_key).decode("ascii"),
            "signature": base64.b64encode(self.signature).decode("ascii"),
        }

    @classmethod
    def from_json(cls, data: str) -> "NameClaim":
        """Deserialize from JSON string."""
        return cls.from_dict(json.loads(data))

    @classmethod
    def from_dict(cls, data: dict) -> "NameClaim":
        """Deserialize from dictionary."""
        return cls(
            version=data.get("version", 1),
            name=data["name"],
            address=data["address"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            expires=datetime.fromisoformat(data["expires"]),
            public_key=base64.b64decode(data["public_key"]),
            signature=base64.b64decode(data["signature"]),
        )

    def __str__(self) -> str:
        """Human-readable representation."""
        status = "EXPIRED" if self.is_expired() else f"{self.time_remaining():.0f}s remaining"
        return f"NameClaim({self.name} -> {self.address}, {status})"


class NameClaimStore:
    """
    Local storage for name claims.

    Stores claimed names in ~/.wh/names/ for quick lookup and renewal.
    """

    def __init__(self, base_path: Optional[Path] = None):
        """Initialize name claim store."""
        if base_path is None:
            base_path = Path.home() / ".wh"
        self.base_path = Path(base_path)
        self.names_path = self.base_path / "names"

    def _ensure_dirs(self) -> None:
        """Ensure storage directories exist."""
        self.names_path.mkdir(parents=True, exist_ok=True)

    def save_claim(self, claim: NameClaim) -> Path:
        """Save a name claim to local storage."""
        self._ensure_dirs()

        claim_file = self.names_path / f"{claim.name}.json"
        with open(claim_file, "w") as f:
            json.dump(claim.to_dict(), f, indent=2)

        return claim_file

    def load_claim(self, name: str) -> Optional[NameClaim]:
        """Load a name claim from local storage."""
        claim_file = self.names_path / f"{name.lower()}.json"
        if not claim_file.exists():
            return None

        with open(claim_file) as f:
            data = json.load(f)
        return NameClaim.from_dict(data)

    def list_claims(self) -> list:
        """List all stored name claims."""
        if not self.names_path.exists():
            return []

        claims = []
        for claim_file in self.names_path.glob("*.json"):
            try:
                claim = self.load_claim(claim_file.stem)
                if claim:
                    claims.append(claim)
            except Exception:
                pass
        return claims

    def delete_claim(self, name: str) -> bool:
        """Delete a name claim from local storage."""
        claim_file = self.names_path / f"{name.lower()}.json"
        if claim_file.exists():
            claim_file.unlink()
            return True
        return False
