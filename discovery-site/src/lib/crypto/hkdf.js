/**
 * HKDF-SHA256 Key Derivation
 *
 * Implements RFC 5869 HKDF using Web Crypto API.
 * Used for deriving session keys from SPAKE2 output.
 */

/**
 * HKDF Extract step
 * @param {Uint8Array} salt - Salt value
 * @param {Uint8Array} ikm - Input keying material
 * @returns {Promise<Uint8Array>} - PRK (pseudorandom key)
 */
async function hkdfExtract(salt, ikm) {
  const key = await crypto.subtle.importKey(
    'raw',
    salt.length > 0 ? salt : new Uint8Array(32),
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign']
  );
  const prk = await crypto.subtle.sign('HMAC', key, ikm);
  return new Uint8Array(prk);
}

/**
 * HKDF Expand step
 * @param {Uint8Array} prk - Pseudorandom key from Extract
 * @param {Uint8Array} info - Context info
 * @param {number} length - Desired output length
 * @returns {Promise<Uint8Array>}
 */
async function hkdfExpand(prk, info, length) {
  const key = await crypto.subtle.importKey(
    'raw',
    prk,
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign']
  );

  const hashLen = 32; // SHA-256 output length
  const n = Math.ceil(length / hashLen);
  const okm = new Uint8Array(n * hashLen);
  let prev = new Uint8Array(0);

  for (let i = 0; i < n; i++) {
    const input = new Uint8Array(prev.length + info.length + 1);
    input.set(prev, 0);
    input.set(info, prev.length);
    input[prev.length + info.length] = i + 1;

    prev = new Uint8Array(await crypto.subtle.sign('HMAC', key, input));
    okm.set(prev, i * hashLen);
  }

  return okm.slice(0, length);
}

/**
 * HKDF key derivation
 * @param {Uint8Array|string} salt - Salt (or empty for default)
 * @param {Uint8Array} ikm - Input keying material
 * @param {Uint8Array|string} info - Context info
 * @param {number} length - Desired output length (default: 32)
 * @returns {Promise<Uint8Array>}
 */
export async function hkdf(salt, ikm, info, length = 32) {
  if (typeof salt === 'string') {
    salt = new TextEncoder().encode(salt);
  }
  if (typeof info === 'string') {
    info = new TextEncoder().encode(info);
  }

  const prk = await hkdfExtract(salt, ikm);
  return hkdfExpand(prk, info, length);
}

/**
 * Derive wormhole master key
 * @param {Uint8Array} sharedSecret - SPAKE2 shared secret
 * @param {string} sideA - Side A identifier
 * @param {string} sideB - Side B identifier
 * @returns {Promise<Uint8Array>}
 */
export async function deriveMasterKey(sharedSecret, sideA, sideB) {
  // Sort sides for deterministic key
  const sides = [sideA, sideB].sort();
  const info = sides.join('');

  return hkdf(
    'wormhole:master_key',
    sharedSecret,
    info,
    32
  );
}

/**
 * Derive session key from SPAKE2 shared secret
 * Compatible with Python magic-wormhole's derive_key()
 * @param {Uint8Array} sharedSecret - SPAKE2 shared secret
 * @returns {Promise<Uint8Array>}
 */
export async function deriveSessionKey(sharedSecret) {
  // Python magic-wormhole uses:
  // derive_key(key, purpose, length) which does HKDF with:
  // - salt: empty
  // - ikm: key
  // - info: purpose
  return hkdf(
    new Uint8Array(0),  // empty salt
    sharedSecret,
    'wormhole:key',     // purpose for main encryption key
    32
  );
}

/**
 * Derive transit key from SPAKE2 shared secret
 * Compatible with Python magic-wormhole's transit key derivation
 * @param {Uint8Array} sharedSecret - SPAKE2 shared secret
 * @returns {Promise<Uint8Array>}
 */
export async function deriveTransitKey(sharedSecret) {
  // Transit key uses purpose "wormhole:transit"
  return hkdf(
    new Uint8Array(0),  // empty salt
    sharedSecret,
    'wormhole:transit',
    32
  );
}

/**
 * SHA256 hash
 * @param {Uint8Array} data
 * @returns {Promise<Uint8Array>}
 */
async function sha256(data) {
  const hash = await crypto.subtle.digest('SHA-256', data);
  return new Uint8Array(hash);
}

/**
 * Derive phase-specific key from SPAKE2 shared key
 * Compatible with Python magic-wormhole's derive_phase_key()
 *
 * Python formula:
 *   purpose = b"wormhole:phase:" + sha256(side_bytes).digest() + sha256(phase_bytes).digest()
 *   return HKDF(key, purpose)
 *
 * @param {Uint8Array} key - SPAKE2 shared key
 * @param {string} side - Sender's side identifier (e.g., "side-abc123")
 * @param {string} phase - Phase name (e.g., "version")
 * @returns {Promise<Uint8Array>}
 */
export async function derivePhaseKey(key, side, phase) {
  const sideBytes = new TextEncoder().encode(side);
  const phaseBytes = new TextEncoder().encode(phase);

  const sideHash = await sha256(sideBytes);
  const phaseHash = await sha256(phaseBytes);

  // Build purpose: "wormhole:phase:" + sha256(side) + sha256(phase)
  const prefix = new TextEncoder().encode('wormhole:phase:');
  const purpose = new Uint8Array(prefix.length + sideHash.length + phaseHash.length);
  purpose.set(prefix, 0);
  purpose.set(sideHash, prefix.length);
  purpose.set(phaseHash, prefix.length + sideHash.length);

  return hkdf(
    new Uint8Array(0),  // empty salt
    key,
    purpose,
    32
  );
}

/**
 * Derive subkey for a specific purpose
 * @param {Uint8Array} masterKey
 * @param {string} purpose
 * @returns {Promise<Uint8Array>}
 */
export async function deriveSubkey(masterKey, purpose) {
  return hkdf(
    'wormhole:subkey',
    masterKey,
    purpose,
    32
  );
}
