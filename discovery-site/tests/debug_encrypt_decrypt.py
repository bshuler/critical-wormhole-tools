#!/usr/bin/env python3
"""
Test encryption/decryption compatibility between Python and JavaScript.
"""

import hashlib
from nacl.secret import SecretBox
from nacl import utils
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes


def derive_phase_key(key: bytes, side: str, phase: str) -> bytes:
    """Python magic-wormhole's derive_phase_key implementation."""
    side_bytes = side.encode("ascii")
    phase_bytes = phase.encode("ascii")

    side_hash = hashlib.sha256(side_bytes).digest()
    phase_hash = hashlib.sha256(phase_bytes).digest()

    purpose = b"wormhole:phase:" + side_hash + phase_hash

    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=purpose,
    )
    return hkdf.derive(key)


def decrypt_data(key: bytes, encrypted: bytes) -> bytes:
    """Decrypt data using NaCl SecretBox."""
    box = SecretBox(key)
    return box.decrypt(encrypted)


def main():
    # Use captured values from actual test run
    shared_key_hex = "88d1ae138ba85ba49e6bff10897c0184e55a8a61934ee15bba3bcb0d96d7414d"
    shared_key = bytes.fromhex(shared_key_hex)

    browser_side = "side-4166204b33"
    phase = "0"

    # Derive the phase key
    phase_key = derive_phase_key(shared_key, browser_side, phase)
    print(f"Shared key: {shared_key_hex}")
    print(f"Browser side: {browser_side}")
    print(f"Phase: {phase}")
    print(f"Phase key: {phase_key.hex()}")

    # Create a test message and encrypt it
    test_message = b'{"method": "GET", "path": "/", "headers": {}}'
    print(f"\nTest message: {test_message}")

    # Encrypt like browser does: nonce || ciphertext
    box = SecretBox(phase_key)
    nonce = utils.random(SecretBox.NONCE_SIZE)
    ciphertext = box.encrypt(test_message, nonce)
    print(f"Encrypted length: {len(ciphertext)}")
    print(f"Encrypted hex: {ciphertext.hex()}")

    # Now try to decrypt
    try:
        decrypted = box.decrypt(ciphertext)
        print(f"Decrypted: {decrypted}")
        print("SUCCESS: Encryption/decryption works!")
    except Exception as e:
        print(f"FAILED: {e}")

    # Also test with a hex-encoded body from the browser logs
    print("\n" + "=" * 60)
    print("Testing with actual browser message (if available):")

    # Captured from actual test run - browser's phase 0 message
    example_body = "87486196b83bc46195fa15cc3adccf13741c12cfa592638c7baeb921c99cd46c1e7d61501b557c3ba645929a46fcda98469b3c4336d9e26caed72ed96e26ee97e26bbdc4f2fa1547b722df682b873acba9fddbebc70a013a6972845cfe8638e2ced096dc778164ca8ee6defcb06a9227cd70cefa8f165aeab3c6a813ed22f6d2d433af9ef1ed174a9f6317db6a9786c437051f0a8302540a3bf20130"

    try:
        encrypted_bytes = bytes.fromhex(example_body)
        print(f"Encrypted bytes length: {len(encrypted_bytes)}")

        # Extract nonce (first 24 bytes) and ciphertext
        nonce = encrypted_bytes[:24]
        ct = encrypted_bytes[24:]
        print(f"Nonce: {nonce.hex()}")
        print(f"Ciphertext length: {len(ct)}")

        decrypted = box.decrypt(encrypted_bytes)
        print(f"Decrypted: {decrypted}")
        print("SUCCESS!")
    except Exception as e:
        print(f"FAILED: {e}")

        # Try with different side (in case browser used wrong side)
        print("\nTrying with Python's side (77f0e5daaa):")
        python_side = "77f0e5daaa"
        phase_key2 = derive_phase_key(shared_key, python_side, phase)
        print(f"Phase key (Python side): {phase_key2.hex()}")
        box2 = SecretBox(phase_key2)
        try:
            decrypted = box2.decrypt(encrypted_bytes)
            print(f"Decrypted: {decrypted}")
            print("SUCCESS with Python's side!")
        except Exception as e2:
            print(f"FAILED: {e2}")


if __name__ == "__main__":
    main()
