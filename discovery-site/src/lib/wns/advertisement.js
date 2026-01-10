/**
 * WNS Code Advertisement
 *
 * Handles creation, signing, and verification of code advertisements.
 * An advertisement announces that a WNS address is currently
 * accepting connections on a specific ephemeral wormhole code.
 */

import * as ed from '../crypto/ed25519.js';
import { sha256 } from '../crypto/hash.js';
import { deriveAddress, verifyAddress, parseWNSAddress } from './identity.js';

/**
 * Code Advertisement
 *
 * A signed message announcing the current wormhole code for a WNS address.
 */
export class Advertisement {
  /**
   * @param {object} data - Advertisement data
   */
  constructor(data) {
    this.version = data.version || 1;
    this.address = data.address;
    // Accept both camelCase (internal) and snake_case (JSON)
    this.publicKey = data.publicKey || data.public_key;
    this.code = data.code;
    this.timestamp = data.timestamp;
    this.expires = data.expires;
    this.scopedName = data.scopedName || data.scoped_name || null;
    this.services = data.services || [];
    this.signature = data.signature || null;
  }

  /**
   * Create a new advertisement
   * @param {object} options
   * @param {Identity} options.identity - WNS identity
   * @param {string} options.code - Ephemeral wormhole code
   * @param {number} options.ttlSeconds - Time to live (default: 300)
   * @param {string[]} options.services - Available services
   * @returns {Promise<Advertisement>}
   */
  static async create(options) {
    const {
      identity,
      code,
      ttlSeconds = 300,
      services = []
    } = options;

    const now = new Date();
    const expires = new Date(now.getTime() + ttlSeconds * 1000);

    const ad = new Advertisement({
      version: 1,
      address: identity.address,
      publicKey: bytesToBase64(identity.publicKey),
      code,
      timestamp: now.toISOString(),
      expires: expires.toISOString(),
      scopedName: identity.metadata.scopedName,
      services
    });

    // Sign the advertisement
    await ad.sign(identity);

    return ad;
  }

  /**
   * Parse advertisement from JSON
   * @param {object|string} data
   * @returns {Advertisement}
   */
  static fromJSON(data) {
    if (typeof data === 'string') {
      data = JSON.parse(data);
    }
    return new Advertisement(data);
  }

  /**
   * Get canonical JSON for signing
   * @returns {string}
   */
  getCanonicalJSON() {
    // Create object with sorted keys (excluding signature)
    const obj = {
      address: this.address,
      code: this.code,
      expires: this.expires,
      public_key: this.publicKey,
      scoped_name: this.scopedName,
      services: this.services,
      timestamp: this.timestamp,
      version: this.version
    };

    // Remove null values
    for (const key of Object.keys(obj)) {
      if (obj[key] === null || obj[key] === undefined) {
        delete obj[key];
      }
    }

    // Sort keys and stringify without whitespace
    return JSON.stringify(obj, Object.keys(obj).sort());
  }

  /**
   * Sign the advertisement
   * @param {Identity} identity
   */
  async sign(identity) {
    const canonical = this.getCanonicalJSON();
    const message = new TextEncoder().encode(canonical);
    const sig = await identity.sign(message);
    this.signature = bytesToBase64(sig);
  }

  /**
   * Verify the advertisement signature
   * @param {Uint8Array} publicKey - Optional public key to verify against
   * @returns {Promise<boolean>}
   */
  async verify(publicKey = null) {
    if (!this.signature) {
      return false;
    }

    // Get public key from advertisement if not provided
    const pk = publicKey || base64ToBytes(this.publicKey);

    // Verify address matches public key
    const addressValid = await verifyAddress(this.address, pk);
    if (!addressValid) {
      return false;
    }

    // Verify signature
    const canonical = this.getCanonicalJSON();
    const message = new TextEncoder().encode(canonical);
    const sig = base64ToBytes(this.signature);

    return ed.verify(sig, message, pk);
  }

  /**
   * Check if advertisement is expired
   * @returns {boolean}
   */
  isExpired() {
    return new Date() > new Date(this.expires);
  }

  /**
   * Check if advertisement will expire within given seconds
   * @param {number} seconds
   * @returns {boolean}
   */
  expiresWithin(seconds) {
    const expiresAt = new Date(this.expires);
    const threshold = new Date(Date.now() + seconds * 1000);
    return expiresAt <= threshold;
  }

  /**
   * Get time until expiry in seconds
   * @returns {number}
   */
  get ttl() {
    const expiresAt = new Date(this.expires);
    const now = Date.now();
    return Math.max(0, Math.floor((expiresAt.getTime() - now) / 1000));
  }

  /**
   * Export to JSON
   * @returns {object}
   */
  toJSON() {
    const obj = {
      version: this.version,
      address: this.address,
      public_key: this.publicKey,
      code: this.code,
      timestamp: this.timestamp,
      expires: this.expires,
      signature: this.signature
    };

    if (this.scopedName) {
      obj.scoped_name = this.scopedName;
    }

    if (this.services.length > 0) {
      obj.services = this.services;
    }

    return obj;
  }

  /**
   * Get the address to use for resolution
   * Returns scoped address if available, otherwise bare address
   * @returns {string}
   */
  get resolutionAddress() {
    if (this.scopedName) {
      return `${this.scopedName}.${this.address}`;
    }
    return this.address;
  }
}

/**
 * Verify and extract code from an advertisement
 * @param {object|string} adData - Advertisement JSON
 * @param {string} expectedAddress - Expected WNS address (optional)
 * @returns {Promise<{valid: boolean, code: string|null, error: string|null}>}
 */
export async function verifyAdvertisement(adData, expectedAddress = null) {
  try {
    const ad = Advertisement.fromJSON(adData);

    // Check expiry
    if (ad.isExpired()) {
      return { valid: false, code: null, error: 'Advertisement expired' };
    }

    // Check address matches if expected
    if (expectedAddress) {
      const parsed = parseWNSAddress(expectedAddress);
      if (parsed && parsed.address !== ad.address) {
        return { valid: false, code: null, error: 'Address mismatch' };
      }
      if (parsed && parsed.scopedName && parsed.scopedName !== ad.scopedName) {
        return { valid: false, code: null, error: 'Scoped name mismatch' };
      }
    }

    // Verify signature
    const valid = await ad.verify();
    if (!valid) {
      return { valid: false, code: null, error: 'Invalid signature' };
    }

    return { valid: true, code: ad.code, error: null, advertisement: ad };
  } catch (e) {
    return { valid: false, code: null, error: e.message };
  }
}

// Helper functions

function bytesToBase64(bytes) {
  return btoa(String.fromCharCode(...bytes));
}

function base64ToBytes(base64) {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes;
}
