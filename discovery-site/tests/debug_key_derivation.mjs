#!/usr/bin/env node
/**
 * Debug script to compare key derivation between JavaScript and Python.
 */

import { createHash, createHmac } from 'crypto';

/**
 * HKDF Extract
 */
function hkdfExtract(salt, ikm) {
  // If salt is empty, use a zero-filled buffer of hash length
  const actualSalt = salt.length > 0 ? salt : Buffer.alloc(32);
  const hmac = createHmac('sha256', actualSalt);
  hmac.update(ikm);
  return hmac.digest();
}

/**
 * HKDF Expand
 */
function hkdfExpand(prk, info, length) {
  const hashLen = 32; // SHA-256
  const n = Math.ceil(length / hashLen);
  const okm = Buffer.alloc(n * hashLen);
  let prev = Buffer.alloc(0);

  for (let i = 0; i < n; i++) {
    const hmac = createHmac('sha256', prk);
    hmac.update(prev);
    hmac.update(info);
    hmac.update(Buffer.from([i + 1]));
    prev = hmac.digest();
    prev.copy(okm, i * hashLen);
  }

  return okm.slice(0, length);
}

/**
 * HKDF key derivation
 */
function hkdf(salt, ikm, info, length = 32) {
  const prk = hkdfExtract(salt, ikm);
  return hkdfExpand(prk, info, length);
}

/**
 * Derive phase-specific key (JavaScript version matching discovery-site)
 */
function derivePhaseKey(key, side, phase) {
  const sideBytes = Buffer.from(side, 'utf8');
  const phaseBytes = Buffer.from(phase, 'utf8');

  const sideHash = createHash('sha256').update(sideBytes).digest();
  const phaseHash = createHash('sha256').update(phaseBytes).digest();

  // Build purpose: "wormhole:phase:" + sha256(side) + sha256(phase)
  const prefix = Buffer.from('wormhole:phase:', 'utf8');
  const purpose = Buffer.concat([prefix, sideHash, phaseHash]);

  return hkdf(Buffer.alloc(0), key, purpose, 32);
}

function main() {
  // Test with known values from browser logs
  const sharedKeyHex = "3f23cb5760e94021044d05eb3cd40f9934408c320cf88e2a179e329de432b41b";
  const sharedKey = Buffer.from(sharedKeyHex, 'hex');

  // Test cases
  const testCases = [
    ["side-e8822b8720", "version"],
    ["side-e8822b8720", "0"],
    ["9f32afdec1", "version"],
    ["9f32afdec1", "0"],
  ];

  console.log("JavaScript key derivation test");
  console.log("=".repeat(60));
  console.log(`Shared key: ${sharedKeyHex}`);
  console.log();

  for (const [side, phase] of testCases) {
    const key = derivePhaseKey(sharedKey, side, phase);
    console.log(`side=${JSON.stringify(side)}, phase=${JSON.stringify(phase)}`);
    console.log(`  -> key: ${key.toString('hex')}`);

    // Also print intermediate values
    const sideHash = createHash('sha256').update(Buffer.from(side, 'utf8')).digest().toString('hex');
    const phaseHash = createHash('sha256').update(Buffer.from(phase, 'utf8')).digest().toString('hex');
    console.log(`  -> side_hash: ${sideHash}`);
    console.log(`  -> phase_hash: ${phaseHash}`);
    console.log();
  }
}

main();
