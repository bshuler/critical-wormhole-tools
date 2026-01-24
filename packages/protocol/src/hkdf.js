/**
 * HKDF key derivation
 * Re-exported from @noble/hashes for protocol package
 */

import { hkdf } from '@noble/hashes/hkdf';
import { sha256 } from '@noble/hashes/sha256';

/**
 * Derive wormhole master key
 * @param {Uint8Array} sharedSecret - SPAKE2 shared secret
 * @param {string} sideA - Side A identifier
 * @param {string} sideB - Side B identifier
 * @returns {Promise<Uint8Array>}
 */
export async function deriveMasterKey(sharedSecret, sideA, sideB) {
  const sides = [sideA, sideB].sort();
  const info = new TextEncoder().encode(sides.join(''));

  return hkdf(
    sha256,
    sharedSecret,
    new TextEncoder().encode('wormhole:master_key'),
    info,
    32
  );
}

/**
 * Derive session key from SPAKE2 shared secret
 * @param {Uint8Array} sharedSecret - SPAKE2 shared secret
 * @returns {Promise<Uint8Array>}
 */
export async function deriveSessionKey(sharedSecret) {
  return hkdf(
    sha256,
    sharedSecret,
    new Uint8Array(0),
    new TextEncoder().encode('wormhole:key'),
    32
  );
}

/**
 * Derive transit key from SPAKE2 shared secret
 * @param {Uint8Array} sharedSecret - SPAKE2 shared secret
 * @returns {Promise<Uint8Array>}
 */
export async function deriveTransitKey(sharedSecret) {
  return hkdf(
    sha256,
    sharedSecret,
    new Uint8Array(0),
    new TextEncoder().encode('wormhole:transit'),
    32
  );
}

/**
 * Derive phase-specific key from SPAKE2 shared key
 * @param {Uint8Array} key - SPAKE2 shared key
 * @param {string} side - Sender's side identifier
 * @param {string} phase - Phase name
 * @returns {Promise<Uint8Array>}
 */
export async function derivePhaseKey(key, side, phase) {
  const sideBytes = new TextEncoder().encode(side);
  const phaseBytes = new TextEncoder().encode(phase);

  const sideHash = sha256(sideBytes);
  const phaseHash = sha256(phaseBytes);

  const prefix = new TextEncoder().encode('wormhole:phase:');
  const purpose = new Uint8Array(prefix.length + sideHash.length + phaseHash.length);
  purpose.set(prefix, 0);
  purpose.set(sideHash, prefix.length);
  purpose.set(phaseHash, prefix.length + sideHash.length);

  return hkdf(
    sha256,
    key,
    new Uint8Array(0),
    purpose,
    32
  );
}
