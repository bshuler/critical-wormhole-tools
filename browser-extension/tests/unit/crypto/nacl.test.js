/**
 * NaCl Encryption Unit Tests
 */

import { describe, it, expect } from 'vitest';
import {
  secretbox,
  secretboxOpen,
  randomNonce,
  NonceCounter,
  encrypt,
  decrypt
} from '../../../src/lib/crypto/nacl.js';
import { randomBytes } from '../../../src/lib/crypto/index.js';

describe('secretbox', () => {
  it('encrypts message', async () => {
    const message = new TextEncoder().encode('Hello, World!');
    const nonce = randomNonce();
    const key = randomBytes(32);

    const ciphertext = await secretbox(message, nonce, key);

    expect(ciphertext).toBeInstanceOf(Uint8Array);
    expect(ciphertext.length).toBeGreaterThan(message.length); // Auth tag adds length
  });

  it('produces different ciphertext for different nonces', async () => {
    const message = new TextEncoder().encode('test');
    const key = randomBytes(32);

    const ct1 = await secretbox(message, randomNonce(), key);
    const ct2 = await secretbox(message, randomNonce(), key);

    expect(ct1).not.toEqual(ct2);
  });

  it('produces deterministic output for same inputs', async () => {
    const message = new TextEncoder().encode('test');
    const nonce = new Uint8Array(24).fill(0x42);
    const key = new Uint8Array(32).fill(0x42);

    const ct1 = await secretbox(message, nonce, key);
    const ct2 = await secretbox(message, nonce, key);

    expect(ct1).toEqual(ct2);
  });

  it('handles empty message', async () => {
    const message = new Uint8Array(0);
    const nonce = randomNonce();
    const key = randomBytes(32);

    const ciphertext = await secretbox(message, nonce, key);
    expect(ciphertext.length).toBeGreaterThan(0); // Auth tag only
  });

  it('handles large message', async () => {
    // Use 32KB which is under crypto.getRandomValues limit
    const message = randomBytes(32000);
    const nonce = randomNonce();
    const key = randomBytes(32);

    const ciphertext = await secretbox(message, nonce, key);
    expect(ciphertext.length).toBeGreaterThan(message.length);
  });
});

describe('secretboxOpen', () => {
  it('decrypts valid ciphertext', async () => {
    const original = new TextEncoder().encode('Hello, World!');
    const nonce = randomNonce();
    const key = randomBytes(32);

    const ciphertext = await secretbox(original, nonce, key);
    const decrypted = await secretboxOpen(ciphertext, nonce, key);

    expect(decrypted).toEqual(original);
  });

  it('returns null for wrong key', async () => {
    const message = new TextEncoder().encode('test');
    const nonce = randomNonce();
    const key1 = randomBytes(32);
    const key2 = randomBytes(32);

    const ciphertext = await secretbox(message, nonce, key1);
    const decrypted = await secretboxOpen(ciphertext, nonce, key2);

    expect(decrypted).toBeNull();
  });

  it('returns null for wrong nonce', async () => {
    const message = new TextEncoder().encode('test');
    const nonce1 = randomNonce();
    const nonce2 = randomNonce();
    const key = randomBytes(32);

    const ciphertext = await secretbox(message, nonce1, key);
    const decrypted = await secretboxOpen(ciphertext, nonce2, key);

    expect(decrypted).toBeNull();
  });

  it('returns null for tampered ciphertext', async () => {
    const message = new TextEncoder().encode('test');
    const nonce = randomNonce();
    const key = randomBytes(32);

    const ciphertext = await secretbox(message, nonce, key);
    const tampered = new Uint8Array(ciphertext);
    tampered[0] ^= 0xff;

    const decrypted = await secretboxOpen(tampered, nonce, key);
    expect(decrypted).toBeNull();
  });

  it('decrypts empty message', async () => {
    const message = new Uint8Array(0);
    const nonce = randomNonce();
    const key = randomBytes(32);

    const ciphertext = await secretbox(message, nonce, key);
    const decrypted = await secretboxOpen(ciphertext, nonce, key);

    expect(decrypted).toEqual(message);
  });
});

describe('encrypt/decrypt roundtrip', () => {
  it('roundtrips various message sizes', async () => {
    const key = randomBytes(32);

    for (const size of [0, 1, 16, 64, 256, 1024, 4096]) {
      const original = randomBytes(size);
      const encrypted = await encrypt(original, key);
      const decrypted = await decrypt(encrypted, key);

      expect(decrypted).toEqual(original);
    }
  });

  it('returns null for tampered data', async () => {
    const original = new TextEncoder().encode('secret message');
    const key = randomBytes(32);

    const encrypted = await encrypt(original, key);
    const tampered = new Uint8Array(encrypted);
    tampered[30] ^= 0xff; // Tamper with ciphertext part

    const decrypted = await decrypt(tampered, key);
    expect(decrypted).toBeNull();
  });

  it('returns null for truncated data', async () => {
    const decrypted = await decrypt(new Uint8Array(10), randomBytes(32));
    expect(decrypted).toBeNull();
  });
});

describe('randomNonce', () => {
  it('generates 24-byte nonce', () => {
    const nonce = randomNonce();
    expect(nonce).toBeInstanceOf(Uint8Array);
    expect(nonce.length).toBe(24);
  });

  it('generates different nonces each time', () => {
    const nonce1 = randomNonce();
    const nonce2 = randomNonce();
    expect(nonce1).not.toEqual(nonce2);
  });
});

describe('NonceCounter', () => {
  it('starts at zero', () => {
    const counter = new NonceCounter();
    const nonce = counter.next();
    expect(nonce).toEqual(new Uint8Array(24));
  });

  it('increments correctly', () => {
    const counter = new NonceCounter();

    const n0 = counter.next();
    const n1 = counter.next();
    const n2 = counter.next();

    expect(n0[0]).toBe(0);
    expect(n1[0]).toBe(1);
    expect(n2[0]).toBe(2);
  });

  it('handles overflow of first byte', () => {
    const counter = new NonceCounter();

    // Set counter to 0xff
    for (let i = 0; i < 255; i++) {
      counter.next();
    }

    const before = counter.next(); // 0xff
    expect(before[0]).toBe(255);
    expect(before[1]).toBe(0);

    const after = counter.next(); // 0x00, 0x01 (overflow)
    expect(after[0]).toBe(0);
    expect(after[1]).toBe(1);
  });

  it('returns unique nonces', () => {
    const counter = new NonceCounter();
    const seen = new Set();

    for (let i = 0; i < 1000; i++) {
      const nonce = counter.next();
      const hex = Array.from(nonce).map(b => b.toString(16).padStart(2, '0')).join('');
      expect(seen.has(hex)).toBe(false);
      seen.add(hex);
    }
  });

  it('each call returns a copy', () => {
    const counter = new NonceCounter();
    const n1 = counter.next();
    const n2 = counter.next();

    // Modifying n1 should not affect counter
    n1[0] = 0xff;

    const n3 = counter.next();
    expect(n3[0]).toBe(2);
  });
});

describe('encrypt', () => {
  it('produces output with prepended nonce', async () => {
    const message = new TextEncoder().encode('test');
    const key = randomBytes(32);

    const encrypted = await encrypt(message, key);

    // Should be: 24 bytes nonce + ciphertext (message + auth tag)
    expect(encrypted.length).toBeGreaterThan(24 + message.length);
  });

  it('uses different nonce each time', async () => {
    const message = new TextEncoder().encode('test');
    const key = randomBytes(32);

    const e1 = await encrypt(message, key);
    const e2 = await encrypt(message, key);

    // Nonces (first 24 bytes) should differ
    const nonce1 = e1.slice(0, 24);
    const nonce2 = e2.slice(0, 24);
    expect(nonce1).not.toEqual(nonce2);
  });
});

describe('decrypt', () => {
  it('returns null for too-short data', async () => {
    const key = randomBytes(32);

    expect(await decrypt(new Uint8Array(0), key)).toBeNull();
    expect(await decrypt(new Uint8Array(10), key)).toBeNull();
    expect(await decrypt(new Uint8Array(23), key)).toBeNull();
  });
});
