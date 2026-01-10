/**
 * Wormhole Crypto Module
 *
 * Provides cryptographic primitives for the Wormhole Protocol:
 * - Ed25519 signatures
 * - SPAKE2 key exchange
 * - XSalsa20-Poly1305 encryption
 * - HKDF key derivation
 * - SHA-256 hashing
 */

import * as ed from './ed25519.js';
import * as nacl from './nacl.js';
import * as hkdf from './hkdf.js';
import * as spake2 from './spake2.js';
import { sha256, sha256Hex } from './hash.js';

export {
  ed,
  nacl,
  hkdf,
  spake2,
  sha256,
  sha256Hex
};

/**
 * Generate a random byte array
 * @param {number} length - Number of bytes
 * @returns {Uint8Array}
 */
export function randomBytes(length) {
  const bytes = new Uint8Array(length);
  crypto.getRandomValues(bytes);
  return bytes;
}

/**
 * Derive a WNS address from an Ed25519 public key
 * @param {Uint8Array} publicKey - 32-byte Ed25519 public key
 * @returns {string} - 26-character base32 address
 */
export async function deriveAddress(publicKey) {
  const hash = await sha256(publicKey);
  const first16 = hash.slice(0, 16);
  return base32Encode(first16);
}

/**
 * Base32 encode (lowercase, no padding)
 * @param {Uint8Array} data
 * @returns {string}
 */
export function base32Encode(data) {
  const alphabet = 'abcdefghijklmnopqrstuvwxyz234567';
  let result = '';
  let bits = 0;
  let value = 0;

  for (const byte of data) {
    value = (value << 8) | byte;
    bits += 8;

    while (bits >= 5) {
      bits -= 5;
      result += alphabet[(value >> bits) & 0x1f];
    }
  }

  if (bits > 0) {
    result += alphabet[(value << (5 - bits)) & 0x1f];
  }

  return result;
}

/**
 * Base32 decode
 * @param {string} str
 * @returns {Uint8Array}
 */
export function base32Decode(str) {
  const alphabet = 'abcdefghijklmnopqrstuvwxyz234567';
  const lookup = {};
  for (let i = 0; i < alphabet.length; i++) {
    lookup[alphabet[i]] = i;
  }

  const bytes = [];
  let bits = 0;
  let value = 0;

  for (const char of str.toLowerCase()) {
    if (!(char in lookup)) continue;
    value = (value << 5) | lookup[char];
    bits += 5;

    if (bits >= 8) {
      bits -= 8;
      bytes.push((value >> bits) & 0xff);
    }
  }

  return new Uint8Array(bytes);
}

/**
 * Convert bytes to hex string
 * @param {Uint8Array} bytes
 * @returns {string}
 */
export function bytesToHex(bytes) {
  return Array.from(bytes)
    .map(b => b.toString(16).padStart(2, '0'))
    .join('');
}

/**
 * Convert hex string to bytes
 * @param {string} hex
 * @returns {Uint8Array}
 */
export function hexToBytes(hex) {
  const bytes = new Uint8Array(hex.length / 2);
  for (let i = 0; i < bytes.length; i++) {
    bytes[i] = parseInt(hex.substr(i * 2, 2), 16);
  }
  return bytes;
}

/**
 * Concatenate multiple Uint8Arrays
 * @param {...Uint8Array} arrays
 * @returns {Uint8Array}
 */
export function concatBytes(...arrays) {
  const totalLength = arrays.reduce((sum, arr) => sum + arr.length, 0);
  const result = new Uint8Array(totalLength);
  let offset = 0;
  for (const arr of arrays) {
    result.set(arr, offset);
    offset += arr.length;
  }
  return result;
}

/**
 * Compare two byte arrays for equality (constant time)
 * @param {Uint8Array} a
 * @param {Uint8Array} b
 * @returns {boolean}
 */
export function constantTimeEqual(a, b) {
  if (a.length !== b.length) return false;
  let result = 0;
  for (let i = 0; i < a.length; i++) {
    result |= a[i] ^ b[i];
  }
  return result === 0;
}
