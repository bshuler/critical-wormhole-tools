/**
 * SHA-256 Hashing
 *
 * Uses Web Crypto API for native performance.
 */

/**
 * Compute SHA-256 hash
 * @param {Uint8Array|string} data - Data to hash
 * @returns {Promise<Uint8Array>} - 32-byte hash
 */
export async function sha256(data) {
  if (typeof data === 'string') {
    data = new TextEncoder().encode(data);
  }
  const hashBuffer = await crypto.subtle.digest('SHA-256', data);
  return new Uint8Array(hashBuffer);
}

/**
 * Compute SHA-256 hash and return as hex string
 * @param {Uint8Array|string} data
 * @returns {Promise<string>}
 */
export async function sha256Hex(data) {
  const hash = await sha256(data);
  return Array.from(hash)
    .map(b => b.toString(16).padStart(2, '0'))
    .join('');
}
