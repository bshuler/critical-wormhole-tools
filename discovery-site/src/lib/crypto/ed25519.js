/**
 * Ed25519 Digital Signatures
 *
 * Wraps @noble/ed25519 for Ed25519 operations.
 * Used for WNS identity and advertisement signing.
 */

import * as nobleEd from '@noble/ed25519';

/**
 * Generate a new Ed25519 keypair
 * @returns {Promise<{privateKey: Uint8Array, publicKey: Uint8Array}>}
 */
export async function generateKeypair() {
  // Generate 32 random bytes for private key
  const privateKey = new Uint8Array(32);
  crypto.getRandomValues(privateKey);

  // Derive public key
  const publicKey = await derivePublicKey(privateKey);

  return { privateKey, publicKey };
}

/**
 * Derive public key from private key
 * @param {Uint8Array} privateKey - 32-byte private key
 * @returns {Promise<Uint8Array>} - 32-byte public key
 */
export async function derivePublicKey(privateKey) {
  return nobleEd.getPublicKeyAsync(privateKey);
}

/**
 * Sign a message with Ed25519
 * @param {Uint8Array} message - Message to sign
 * @param {Uint8Array} privateKey - 32-byte private key
 * @returns {Promise<Uint8Array>} - 64-byte signature
 */
export async function sign(message, privateKey) {
  return nobleEd.signAsync(message, privateKey);
}

/**
 * Verify an Ed25519 signature
 * @param {Uint8Array} signature - 64-byte signature
 * @param {Uint8Array} message - Original message
 * @param {Uint8Array} publicKey - 32-byte public key
 * @returns {Promise<boolean>}
 */
export async function verify(signature, message, publicKey) {
  return nobleEd.verifyAsync(signature, message, publicKey);
}

/**
 * Get the fingerprint of a public key (for display)
 * @param {Uint8Array} publicKey
 * @returns {Promise<string>} - Hex fingerprint (first 8 bytes of SHA-256)
 */
export async function fingerprint(publicKey) {
  const hash = await crypto.subtle.digest('SHA-256', publicKey);
  const bytes = new Uint8Array(hash).slice(0, 8);
  return Array.from(bytes)
    .map(b => b.toString(16).padStart(2, '0'))
    .join(':');
}
