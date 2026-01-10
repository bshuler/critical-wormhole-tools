/**
 * WNS Identity Management
 *
 * Handles generation, storage, and management of WNS identities.
 * Each identity is an Ed25519 keypair with a derived address.
 */

import * as ed from '../crypto/ed25519.js';
import { sha256 } from '../crypto/hash.js';
import { base32Encode, randomBytes } from '../crypto/index.js';

/**
 * WNS Identity
 */
export class Identity {
  /**
   * @param {Uint8Array} privateKey - 32-byte Ed25519 private key
   * @param {Uint8Array} publicKey - 32-byte Ed25519 public key
   * @param {string} address - 26-character WNS address
   * @param {object} metadata - Optional metadata
   */
  constructor(privateKey, publicKey, address, metadata = {}) {
    this.privateKey = privateKey;
    this.publicKey = publicKey;
    this.address = address;
    this.metadata = {
      name: metadata.name || null,
      scopedName: metadata.scopedName || null,
      created: metadata.created || new Date().toISOString(),
      ...metadata
    };
  }

  /**
   * Generate a new identity
   * @param {object} options
   * @param {string} options.name - Optional display name
   * @returns {Promise<Identity>}
   */
  static async generate(options = {}) {
    const { privateKey, publicKey } = await ed.generateKeypair();
    const address = await deriveAddress(publicKey);

    return new Identity(privateKey, publicKey, address, {
      name: options.name,
      created: new Date().toISOString()
    });
  }

  /**
   * Load identity from stored data
   * @param {object} data - Stored identity data
   * @returns {Promise<Identity>}
   */
  static async fromJSON(data) {
    const privateKey = base64ToBytes(data.privateKey);
    const publicKey = base64ToBytes(data.publicKey);

    // Verify address matches public key
    const derivedAddress = await deriveAddress(publicKey);
    if (derivedAddress !== data.address) {
      throw new Error('Address does not match public key');
    }

    return new Identity(privateKey, publicKey, data.address, data.metadata);
  }

  /**
   * Export identity for storage
   * @param {boolean} includePrivate - Include private key (default: true)
   * @returns {object}
   */
  toJSON(includePrivate = true) {
    const data = {
      address: this.address,
      publicKey: bytesToBase64(this.publicKey),
      metadata: this.metadata
    };

    if (includePrivate) {
      data.privateKey = bytesToBase64(this.privateKey);
    }

    return data;
  }

  /**
   * Get full WNS address URL
   * @returns {string}
   */
  get fullAddress() {
    return `wh://${this.address}.wns`;
  }

  /**
   * Get scoped address (if scoped name is set)
   * @returns {string|null}
   */
  get scopedAddress() {
    if (!this.metadata.scopedName) return null;
    return `wh://${this.metadata.scopedName}.${this.address}.wns`;
  }

  /**
   * Set scoped name
   * @param {string|null} name
   */
  setScopedName(name) {
    if (name && !isValidScopedName(name)) {
      throw new Error('Invalid scoped name');
    }
    this.metadata.scopedName = name;
  }

  /**
   * Sign a message
   * @param {Uint8Array|string} message
   * @returns {Promise<Uint8Array>}
   */
  async sign(message) {
    if (typeof message === 'string') {
      message = new TextEncoder().encode(message);
    }
    return ed.sign(message, this.privateKey);
  }

  /**
   * Get public key fingerprint for display
   * @returns {Promise<string>}
   */
  async fingerprint() {
    return ed.fingerprint(this.publicKey);
  }
}

/**
 * Derive WNS address from public key
 * @param {Uint8Array} publicKey - 32-byte Ed25519 public key
 * @returns {Promise<string>} - 26-character address
 */
export async function deriveAddress(publicKey) {
  const hash = await sha256(publicKey);
  const first16 = hash.slice(0, 16);
  return base32Encode(first16);
}

/**
 * Verify that an address matches a public key
 * @param {string} address
 * @param {Uint8Array} publicKey
 * @returns {Promise<boolean>}
 */
export async function verifyAddress(address, publicKey) {
  const derived = await deriveAddress(publicKey);
  return derived === address.toLowerCase();
}

/**
 * Parse a WNS address URL
 * @param {string} url - URL like "wh://address.wns" or "wh://user@address.wns"
 * @returns {object|null}
 */
export function parseWNSAddress(url) {
  // Handle various formats:
  // wh://address.wns
  // wh://name.address.wns
  // wh://user@address.wns
  // wh://user@name.address.wns
  // address.wns
  // address

  if (!url) return null;

  let normalized = url.toLowerCase().trim();

  // Remove wh:// prefix
  if (normalized.startsWith('wh://')) {
    normalized = normalized.slice(5);
  }

  // Remove .wns suffix
  if (normalized.endsWith('.wns')) {
    normalized = normalized.slice(0, -4);
  }

  // Extract username if present
  let username = null;
  const atIndex = normalized.indexOf('@');
  if (atIndex !== -1) {
    username = normalized.slice(0, atIndex);
    normalized = normalized.slice(atIndex + 1);
  }

  // Check for scoped name (name.address)
  const parts = normalized.split('.');
  let address, scopedName;

  if (parts.length === 1) {
    // Just address
    address = parts[0];
    scopedName = null;
  } else if (parts.length === 2) {
    // scoped.address
    scopedName = parts[0];
    address = parts[1];
  } else {
    return null; // Invalid format
  }

  // Validate address format (26 chars, base32)
  if (!isValidAddress(address)) {
    return null;
  }

  return {
    address,
    scopedName,
    username,
    fullUrl: `wh://${username ? username + '@' : ''}${scopedName ? scopedName + '.' : ''}${address}.wns`
  };
}

/**
 * Check if a string is a valid WNS address
 * @param {string} address
 * @returns {boolean}
 */
export function isValidAddress(address) {
  if (!address || typeof address !== 'string') return false;

  // 26 characters, base32 alphabet (a-z, 2-7)
  return /^[a-z2-7]{26}$/.test(address.toLowerCase());
}

/**
 * Check if a string is a valid scoped name
 * @param {string} name
 * @returns {boolean}
 */
export function isValidScopedName(name) {
  if (!name || typeof name !== 'string') return false;

  // 1-63 chars, lowercase alphanumeric + hyphen, can't start/end with hyphen
  return /^[a-z0-9][a-z0-9-]{0,61}[a-z0-9]$/.test(name.toLowerCase()) ||
         /^[a-z0-9]$/.test(name.toLowerCase());
}

/**
 * Check if a string looks like a WNS address (vs ephemeral code)
 * @param {string} str
 * @returns {boolean}
 */
export function isWNSAddress(str) {
  if (!str) return false;

  // WNS addresses start with wh:// or end with .wns
  // or are 26-char base32 strings
  const normalized = str.toLowerCase().trim();

  if (normalized.startsWith('wh://')) return true;
  if (normalized.endsWith('.wns')) return true;
  if (isValidAddress(normalized)) return true;

  return false;
}

/**
 * Check if a string is an ephemeral wormhole code
 * @param {string} str
 * @returns {boolean}
 */
export function isEphemeralCode(str) {
  if (!str) return false;

  // Ephemeral codes match: N-word-word[-word...]
  return /^\d+-[a-z]+-[a-z]+(-[a-z]+)*$/i.test(str.trim());
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
