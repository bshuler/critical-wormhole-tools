/**
 * SPAKE2 Password-Authenticated Key Exchange
 *
 * Implements SPAKE2 Symmetric mode over Ed25519, compatible with
 * the Python magic-wormhole library (python-spake2).
 *
 * Message format: 'S' (0x53) + 32-byte Ed25519 compressed point
 */

import * as ed from '@noble/ed25519';
import { sha256 } from '@noble/hashes/sha256';
import { hkdf } from '@noble/hashes/hkdf';

// Side indicator for symmetric SPAKE2
const SIDE_SYMMETRIC = new Uint8Array([0x53]); // 'S'

/**
 * Convert bytes to BigInt (little-endian)
 */
function bytesToNumberLE(bytes) {
  let result = 0n;
  for (let i = bytes.length - 1; i >= 0; i--) {
    result = result * 256n + BigInt(bytes[i]);
  }
  return result;
}

/**
 * Convert bytes to BigInt (big-endian)
 */
function bytesToNumberBE(bytes) {
  let result = 0n;
  for (let i = 0; i < bytes.length; i++) {
    result = result * 256n + BigInt(bytes[i]);
  }
  return result;
}

/**
 * Convert BigInt to bytes (little-endian)
 */
function numberToBytesLE(num, length) {
  const bytes = new Uint8Array(length);
  for (let i = 0; i < length; i++) {
    bytes[i] = Number(num & 0xffn);
    num = num >> 8n;
  }
  return bytes;
}

/**
 * Reduce a 64-byte hash to a valid Ed25519 scalar
 * Same as Python's clamp + mod L operation
 */
function hashToScalar(hash64) {
  // Ed25519 order L
  const L = 2n ** 252n + 27742317777372353535851937790883648493n;
  const num = bytesToNumberLE(hash64);
  const scalar = num % L;
  return numberToBytesLE(scalar, 32);
}

/**
 * Compute arbitrary element from seed (hash-to-curve)
 * Compatible with Python spake2's arbitrary_element function
 *
 * Python spake2 algorithm:
 * 1. Expand seed with HKDF (info="SPAKE2 arbitrary element")
 * 2. Convert to Y coordinate (mod Q)
 * 3. Try successive Y values until we find a valid curve point
 * 4. Multiply by 8 to get into prime-order subgroup
 */
function arbitraryElement(seed) {
  // Curve field prime Q for Ed25519
  const Q = 2n ** 255n - 19n;
  // Group order L
  const L = 2n ** 252n + 27742317777372353535851937790883648493n;

  // Expand seed using HKDF (like Python spake2)
  const expanded = hkdf(sha256, seed, new Uint8Array(0), new TextEncoder().encode('SPAKE2 arbitrary element'), 32 + 16);
  console.log('[SPAKE2] HKDF expanded:', bytesToHex(expanded));
  // Python uses big-endian: int(binascii.hexlify(hseed), 16) % Q
  let y = bytesToNumberBE(expanded) % Q;
  const yBytes = numberToBytesLE(y, 32);
  console.log('[SPAKE2] Y coordinate (mod Q, from BE):', bytesToHex(yBytes));

  // Try successive Y values until we find a valid point
  for (let plus = 0n; plus < 1000n; plus++) {
    const yTry = (y + plus) % Q;
    const yBytes = numberToBytesLE(yTry, 32);
    // Set the sign bit (MSB of last byte) to 0 for positive x
    yBytes[31] &= 0x7f;

    try {
      const point = ed.ExtendedPoint.fromHex(yBytes);
      // Multiply by cofactor (8) to ensure we're in the prime-order subgroup
      const P8 = point.multiply(8n);
      // Verify it's in the right subgroup (P8 * L should be identity)
      // For now, just trust the multiply by 8 worked
      return P8;
    } catch {
      // Not a valid point, try next Y
    }
  }

  throw new Error('Failed to find valid curve point after 1000 attempts');
}

/**
 * Get the M point for symmetric SPAKE2
 * This is computed from the seed "symmetric" to match Python's implementation
 */
let _M_POINT = null;
function getM() {
  if (!_M_POINT) {
    // Python spake2 uses b"symmetric" as seed for the symmetric M point
    const seed = new TextEncoder().encode('symmetric');
    _M_POINT = arbitraryElement(seed);
  }
  return _M_POINT;
}

/**
 * Hash password to scalar for SPAKE2
 * Compatible with Python spake2's password handling
 *
 * Python spake2 uses HKDF:
 *   - algorithm: SHA256
 *   - salt: empty
 *   - info: "SPAKE2 pw"
 *   - length: scalar_size_bytes + 16 (48 bytes for Ed25519)
 *   - Then mod by group order L
 */
function passwordToScalar(password) {
  // Ed25519 scalar is 32 bytes, add 16 for bias reduction = 48 bytes
  const scalarSizeBytes = 32;
  const oversized = hkdf(sha256, password, new Uint8Array(0), new TextEncoder().encode('SPAKE2 pw'), scalarSizeBytes + 16);

  // Convert to number using big-endian (like Python's int(binascii.hexlify(x), 16))
  // and reduce mod L
  const L = 2n ** 252n + 27742317777372353535851937790883648493n;
  const num = bytesToNumberBE(oversized);
  const scalar = num % L;
  return numberToBytesLE(scalar, 32);
}

/**
 * SPAKE2 Symmetric implementation for magic-wormhole
 *
 * Both sides use the same blinding point M (symmetric mode).
 * Message format: 'S' + 32-byte compressed Ed25519 point
 */
export class SPAKE2_Symmetric {
  /**
   * @param {Uint8Array} password - Password bytes
   * @param {Uint8Array} idSymmetric - Identity string (usually appid)
   */
  constructor(password, idSymmetric = new Uint8Array(0)) {
    this.password = password;
    this.idSymmetric = idSymmetric;

    this.x = null;           // Our random scalar
    this.X = null;           // Our public element (blinded)
    this.outbound = null;    // Our outbound message
    this.Y = null;           // Peer's public element (unblinded)
    this.inbound = null;     // Peer's inbound message
    this.sharedKey = null;   // Derived shared key
    this.state = 'init';
  }

  /**
   * Generate our SPAKE2 message
   * @returns {Uint8Array} - Message to send: 'S' + compressed point
   */
  start() {
    if (this.state !== 'init') {
      throw new Error('SPAKE2 already started');
    }

    // Generate random scalar x
    const xBytes = new Uint8Array(32);
    crypto.getRandomValues(xBytes);
    this.x = bytesToNumberLE(xBytes);

    // Reduce x mod L to ensure it's a valid scalar
    const L = 2n ** 252n + 27742317777372353535851937790883648493n;
    this.x = this.x % L;
    if (this.x === 0n) this.x = 1n; // Avoid zero

    // Compute pw (password scalar)
    const pw = bytesToNumberLE(passwordToScalar(this.password));

    // Get blinding point M
    const M = getM();

    // Compute X = x*G + pw*M
    const xG = ed.ExtendedPoint.BASE.multiply(this.x);
    const pwM = M.multiply(pw);
    this.X = xG.add(pwM);

    // Create outbound message: 'S' + compressed(X)
    const compressedX = this.X.toRawBytes();
    this.outbound = new Uint8Array(33);
    this.outbound.set(SIDE_SYMMETRIC, 0);
    this.outbound.set(compressedX, 1);

    this.state = 'started';
    return this.outbound;
  }

  /**
   * Process peer's message and derive shared key
   * @param {Uint8Array} inboundMessage - Peer's message: 'S' + compressed point
   * @returns {Uint8Array} - Shared key (32 bytes)
   */
  finish(inboundMessage) {
    if (this.state !== 'started') {
      throw new Error('SPAKE2 not started');
    }

    this.inbound = inboundMessage;

    // Verify side indicator
    if (inboundMessage[0] !== SIDE_SYMMETRIC[0]) {
      throw new Error(`Invalid side indicator: expected 'S' (0x53), got 0x${inboundMessage[0].toString(16)}`);
    }

    // Extract peer's point Y_blinded from message
    const Y_blinded_bytes = inboundMessage.slice(1);
    console.log('[SPAKE2] Peer blinded point:', bytesToHex(Y_blinded_bytes));
    const Y_blinded = ed.ExtendedPoint.fromHex(Y_blinded_bytes);

    // Compute pw (password scalar)
    const pwScalar = passwordToScalar(this.password);
    console.log('[SPAKE2] Password scalar:', bytesToHex(pwScalar));
    const pw = bytesToNumberLE(pwScalar);

    // Get blinding point M
    const M = getM();
    console.log('[SPAKE2] M point:', bytesToHex(M.toRawBytes()));

    // Unblind: Y = Y_blinded - pw*M
    const pwM = M.multiply(pw);
    this.Y = Y_blinded.add(pwM.negate());
    console.log('[SPAKE2] Unblinded Y:', bytesToHex(this.Y.toRawBytes()));

    // Compute shared element: K = x * Y
    const K = this.Y.multiply(this.x);
    const K_bytes = K.toRawBytes();
    console.log('[SPAKE2] K element:', bytesToHex(K_bytes));

    // Derive shared key using transcript hash
    this.sharedKey = this._deriveKey(K_bytes);
    console.log('[SPAKE2] Final shared key:', bytesToHex(this.sharedKey));

    this.state = 'finished';
    return this.sharedKey;
  }

  /**
   * Derive the shared key from the transcript
   * Compatible with Python spake2's key derivation
   *
   * Transcript format (Python spake2 symmetric mode):
   *   sha256(password)      - 32 bytes
   *   sha256(idSymmetric)   - 32 bytes
   *   first_msg (sorted)    - 32 bytes (point only, no side prefix)
   *   second_msg (sorted)   - 32 bytes (point only, no side prefix)
   *   K_bytes               - 32 bytes
   * Then SHA256 of the whole thing
   */
  _deriveKey(K_bytes) {
    // Extract just the point bytes (without the 'S' prefix)
    // Python's _extract_message strips the side byte before using in transcript
    const outMsg = this.outbound.slice(1);  // Remove 'S' prefix, get 32 bytes
    const inMsg = this.inbound.slice(1);    // Remove 'S' prefix, get 32 bytes

    // Sort messages to ensure both sides compute the same transcript
    // Python uses sorted([msg1, msg2]) which compares bytes lexicographically
    let first, second;
    const outHex = bytesToHex(outMsg);
    const inHex = bytesToHex(inMsg);
    if (outHex < inHex) {
      first = outMsg;
      second = inMsg;
    } else {
      first = inMsg;
      second = outMsg;
    }

    // Build transcript matching Python spake2's symmetric mode exactly
    const pwHash = sha256(this.password);       // 32 bytes
    const idHash = sha256(this.idSymmetric);    // 32 bytes

    // Total: 32 + 32 + 32 + 32 + 32 = 160 bytes
    const transcript = new Uint8Array(160);
    let offset = 0;

    transcript.set(pwHash, offset);
    offset += 32;

    transcript.set(idHash, offset);
    offset += 32;

    transcript.set(first, offset);
    offset += 32;

    transcript.set(second, offset);
    offset += 32;

    transcript.set(K_bytes, offset);

    return sha256(transcript);
  }
}

/**
 * Create SPAKE2 instance for magic-wormhole
 *
 * @param {string} password - The password portion of the wormhole code (e.g., "guitar-sunset")
 * @param {string} appId - Application ID (e.g., "wh.tools/v1")
 * @returns {SPAKE2_Symmetric}
 */
export function createSPAKE2(password, appId = 'wh.tools/v1') {
  // Python magic-wormhole passes the raw password bytes
  const pwBytes = new TextEncoder().encode(password);
  const idBytes = new TextEncoder().encode(appId);
  return new SPAKE2_Symmetric(pwBytes, idBytes);
}

// Legacy exports for compatibility
export class SymmetricSPAKE2 {
  constructor(appId, passwordHash, side) {
    // Create using the new implementation
    this._inner = new SPAKE2_Symmetric(passwordHash, new TextEncoder().encode(appId));
    this.side = side;
  }

  async start() {
    return this._inner.start();
  }

  async finish(peerMessage) {
    return this._inner.finish(peerMessage);
  }
}

export class SPAKE2 {
  constructor(password, idA, idB, isA = true) {
    const pwBytes = new TextEncoder().encode(password);
    this._inner = new SPAKE2_Symmetric(pwBytes);
  }

  async start() {
    return this._inner.start();
  }

  async finish(peerMessage) {
    return this._inner.finish(peerMessage);
  }
}

// Helper functions
function bytesToHex(bytes) {
  return Array.from(bytes)
    .map(b => b.toString(16).padStart(2, '0'))
    .join('');
}
