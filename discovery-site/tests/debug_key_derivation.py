#!/usr/bin/env python3
"""
Debug script to compare key derivation between Python and JavaScript.
"""

import hashlib
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes


def derive_phase_key_python(key: bytes, side: str, phase: str) -> bytes:
    """Python magic-wormhole's derive_phase_key implementation."""
    side_bytes = side.encode("ascii")
    phase_bytes = phase.encode("ascii")

    side_hash = hashlib.sha256(side_bytes).digest()
    phase_hash = hashlib.sha256(phase_bytes).digest()

    purpose = b"wormhole:phase:" + side_hash + phase_hash

    # HKDF with no salt
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=purpose,
    )
    return hkdf.derive(key)


def main():
    # Test with known values from browser logs
    # Example shared key from test run
    shared_key_hex = "3f23cb5760e94021044d05eb3cd40f9934408c320cf88e2a179e329de432b41b"
    shared_key = bytes.fromhex(shared_key_hex)

    # Test cases
    test_cases = [
        # (side, phase)
        ("side-e8822b8720", "version"),
        ("side-e8822b8720", "0"),
        ("9f32afdec1", "version"),
        ("9f32afdec1", "0"),
    ]

    print("Python key derivation test")
    print("=" * 60)
    print(f"Shared key: {shared_key_hex}")
    print()

    for side, phase in test_cases:
        key = derive_phase_key_python(shared_key, side, phase)
        print(f"side={side!r}, phase={phase!r}")
        print(f"  -> key: {key.hex()}")

        # Also print intermediate values
        side_hash = hashlib.sha256(side.encode("ascii")).hexdigest()
        phase_hash = hashlib.sha256(phase.encode("ascii")).hexdigest()
        print(f"  -> side_hash: {side_hash}")
        print(f"  -> phase_hash: {phase_hash}")
        print()


if __name__ == "__main__":
    main()
