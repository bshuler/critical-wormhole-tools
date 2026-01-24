/**
 * NaCl Encryption (XSalsa20-Poly1305)
 *
 * Wraps tweetnacl for symmetric encryption.
 * Used for encrypting wormhole traffic.
 */

import nacl from 'tweetnacl';

/**
 * Encrypt data using XSalsa20-Poly1305
 * @param {Uint8Array} message - Plaintext
 * @param {Uint8Array} nonce - 24-byte nonce
 * @param {Uint8Array} key - 32-byte key
 * @returns {Uint8Array} - Ciphertext with auth tag
 */
export async function secretbox(message, nonce, key) {
  return nacl.secretbox(message, nonce, key);
}

/**
 * Decrypt data using XSalsa20-Poly1305
 * @param {Uint8Array} ciphertext - Ciphertext with auth tag
 * @param {Uint8Array} nonce - 24-byte nonce
 * @param {Uint8Array} key - 32-byte key
 * @returns {Uint8Array|null} - Plaintext or null if auth fails
 */
export async function secretboxOpen(ciphertext, nonce, key) {
  return nacl.secretbox.open(ciphertext, nonce, key);
}

/**
 * Generate a random nonce
 * @returns {Uint8Array} - 24-byte nonce
 */
export function randomNonce() {
  const nonce = new Uint8Array(24);
  crypto.getRandomValues(nonce);
  return nonce;
}

/**
 * Incrementing nonce for sequential messages
 */
export class NonceCounter {
  constructor() {
    this.counter = new Uint8Array(24);
  }

  /**
   * Get next nonce and increment counter
   * @returns {Uint8Array}
   */
  next() {
    const nonce = new Uint8Array(this.counter);
    this.increment();
    return nonce;
  }

  /**
   * Increment the counter
   */
  increment() {
    for (let i = 0; i < this.counter.length; i++) {
      this.counter[i]++;
      if (this.counter[i] !== 0) break;
    }
  }
}

/**
 * Encrypt a message with automatic nonce
 * @param {Uint8Array} message
 * @param {Uint8Array} key
 * @returns {Promise<Uint8Array>} - nonce || ciphertext
 */
export async function encrypt(message, key) {
  const nonce = randomNonce();
  const ciphertext = await secretbox(message, nonce, key);

  // Prepend nonce to ciphertext
  const result = new Uint8Array(nonce.length + ciphertext.length);
  result.set(nonce, 0);
  result.set(ciphertext, nonce.length);

  return result;
}

/**
 * Decrypt a message with prepended nonce
 * @param {Uint8Array} data - nonce || ciphertext
 * @param {Uint8Array} key
 * @returns {Promise<Uint8Array|null>}
 */
export async function decrypt(data, key) {
  if (data.length < 24) return null;

  const nonce = data.slice(0, 24);
  const ciphertext = data.slice(24);

  return secretboxOpen(ciphertext, nonce, key);
}
