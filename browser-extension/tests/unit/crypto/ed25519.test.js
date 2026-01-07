/**
 * Ed25519 Signature Unit Tests
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import * as ed from '../../../src/lib/crypto/ed25519.js';

describe('generateKeypair', () => {
  it('generates keypair with correct lengths', async () => {
    const { privateKey, publicKey } = await ed.generateKeypair();

    expect(privateKey).toBeInstanceOf(Uint8Array);
    expect(publicKey).toBeInstanceOf(Uint8Array);
    expect(privateKey.length).toBe(32);
    expect(publicKey.length).toBe(32);
  });

  it('generates different keypairs each time', async () => {
    const kp1 = await ed.generateKeypair();
    const kp2 = await ed.generateKeypair();

    expect(kp1.privateKey).not.toEqual(kp2.privateKey);
    expect(kp1.publicKey).not.toEqual(kp2.publicKey);
  });

  it('generates deterministic public key from private key', async () => {
    const kp1 = await ed.generateKeypair();
    const derivedPubKey = await ed.derivePublicKey(kp1.privateKey);

    expect(derivedPubKey).toEqual(kp1.publicKey);
  });
});

describe('derivePublicKey', () => {
  it('produces 32-byte public key', async () => {
    const privateKey = new Uint8Array(32);
    crypto.getRandomValues(privateKey);

    const publicKey = await ed.derivePublicKey(privateKey);
    expect(publicKey.length).toBe(32);
  });

  it('produces deterministic output', async () => {
    const privateKey = new Uint8Array(32).fill(0x42);

    const pk1 = await ed.derivePublicKey(privateKey);
    const pk2 = await ed.derivePublicKey(privateKey);

    expect(pk1).toEqual(pk2);
  });

  it('produces different output for different input', async () => {
    const priv1 = new Uint8Array(32).fill(0x00);
    const priv2 = new Uint8Array(32).fill(0xff);

    const pub1 = await ed.derivePublicKey(priv1);
    const pub2 = await ed.derivePublicKey(priv2);

    expect(pub1).not.toEqual(pub2);
  });
});

describe('sign', () => {
  it('produces 64-byte signature', async () => {
    const { privateKey } = await ed.generateKeypair();
    const message = new TextEncoder().encode('test message');

    const signature = await ed.sign(message, privateKey);

    expect(signature).toBeInstanceOf(Uint8Array);
    expect(signature.length).toBe(64);
  });

  it('produces deterministic signatures', async () => {
    const { privateKey } = await ed.generateKeypair();
    const message = new TextEncoder().encode('test message');

    const sig1 = await ed.sign(message, privateKey);
    const sig2 = await ed.sign(message, privateKey);

    expect(sig1).toEqual(sig2);
  });

  it('produces different signatures for different messages', async () => {
    const { privateKey } = await ed.generateKeypair();
    const msg1 = new TextEncoder().encode('message 1');
    const msg2 = new TextEncoder().encode('message 2');

    const sig1 = await ed.sign(msg1, privateKey);
    const sig2 = await ed.sign(msg2, privateKey);

    expect(sig1).not.toEqual(sig2);
  });

  it('handles empty message', async () => {
    const { privateKey } = await ed.generateKeypair();
    const signature = await ed.sign(new Uint8Array(0), privateKey);
    expect(signature.length).toBe(64);
  });

  it('handles large message', async () => {
    const { privateKey } = await ed.generateKeypair();
    const largeMessage = new Uint8Array(100000).fill(0x42);
    const signature = await ed.sign(largeMessage, privateKey);
    expect(signature.length).toBe(64);
  });
});

describe('verify', () => {
  it('returns true for valid signature', async () => {
    const { privateKey, publicKey } = await ed.generateKeypair();
    const message = new TextEncoder().encode('test message');
    const signature = await ed.sign(message, privateKey);

    const isValid = await ed.verify(signature, message, publicKey);
    expect(isValid).toBe(true);
  });

  it('returns false for wrong message', async () => {
    const { privateKey, publicKey } = await ed.generateKeypair();
    const message = new TextEncoder().encode('test message');
    const wrongMessage = new TextEncoder().encode('wrong message');
    const signature = await ed.sign(message, privateKey);

    const isValid = await ed.verify(signature, wrongMessage, publicKey);
    expect(isValid).toBe(false);
  });

  it('returns false for wrong public key', async () => {
    const kp1 = await ed.generateKeypair();
    const kp2 = await ed.generateKeypair();
    const message = new TextEncoder().encode('test message');
    const signature = await ed.sign(message, kp1.privateKey);

    const isValid = await ed.verify(signature, message, kp2.publicKey);
    expect(isValid).toBe(false);
  });

  it('returns false for tampered signature', async () => {
    const { privateKey, publicKey } = await ed.generateKeypair();
    const message = new TextEncoder().encode('test message');
    const signature = await ed.sign(message, privateKey);

    // Tamper with signature
    const tampered = new Uint8Array(signature);
    tampered[0] ^= 0xff;

    const isValid = await ed.verify(tampered, message, publicKey);
    expect(isValid).toBe(false);
  });

  it('verifies empty message', async () => {
    const { privateKey, publicKey } = await ed.generateKeypair();
    const message = new Uint8Array(0);
    const signature = await ed.sign(message, privateKey);

    const isValid = await ed.verify(signature, message, publicKey);
    expect(isValid).toBe(true);
  });
});

describe('sign/verify roundtrip', () => {
  it('works for various message sizes', async () => {
    const { privateKey, publicKey } = await ed.generateKeypair();

    for (const size of [0, 1, 16, 64, 256, 1024, 4096]) {
      const message = new Uint8Array(size).fill(size % 256);
      const signature = await ed.sign(message, privateKey);
      const isValid = await ed.verify(signature, message, publicKey);

      expect(isValid).toBe(true);
    }
  });

  it('works for multiple keypairs', async () => {
    const message = new TextEncoder().encode('shared message');

    for (let i = 0; i < 5; i++) {
      const { privateKey, publicKey } = await ed.generateKeypair();
      const signature = await ed.sign(message, privateKey);
      const isValid = await ed.verify(signature, message, publicKey);

      expect(isValid).toBe(true);
    }
  });
});

describe('fingerprint', () => {
  it('produces colon-separated hex string', async () => {
    const { publicKey } = await ed.generateKeypair();
    const fp = await ed.fingerprint(publicKey);

    // Format: aa:bb:cc:dd:ee:ff:gg:hh (8 bytes)
    expect(fp).toMatch(/^([0-9a-f]{2}:){7}[0-9a-f]{2}$/);
  });

  it('produces deterministic output', async () => {
    const { publicKey } = await ed.generateKeypair();

    const fp1 = await ed.fingerprint(publicKey);
    const fp2 = await ed.fingerprint(publicKey);

    expect(fp1).toBe(fp2);
  });

  it('produces different output for different keys', async () => {
    const kp1 = await ed.generateKeypair();
    const kp2 = await ed.generateKeypair();

    const fp1 = await ed.fingerprint(kp1.publicKey);
    const fp2 = await ed.fingerprint(kp2.publicKey);

    expect(fp1).not.toBe(fp2);
  });
});
