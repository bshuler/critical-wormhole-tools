/**
 * HKDF Key Derivation Unit Tests
 */

import { describe, it, expect } from 'vitest';
import {
  hkdf,
  deriveMasterKey,
  deriveSessionKey,
  deriveTransitKey,
  deriveSubkey
} from '../../../src/lib/crypto/hkdf.js';
import { bytesToHex, hexToBytes } from '../../../src/lib/crypto/index.js';

describe('hkdf', () => {
  it('derives 32-byte key by default', async () => {
    const ikm = new Uint8Array(32).fill(0x42);
    const salt = new Uint8Array(16);
    const info = new Uint8Array(8);

    const key = await hkdf(salt, ikm, info);

    expect(key).toBeInstanceOf(Uint8Array);
    expect(key.length).toBe(32);
  });

  it('derives custom length keys', async () => {
    const ikm = new Uint8Array(32).fill(0x42);
    const salt = new Uint8Array(0);
    const info = new Uint8Array(0);

    for (const length of [16, 32, 48, 64, 128]) {
      const key = await hkdf(salt, ikm, info, length);
      expect(key.length).toBe(length);
    }
  });

  it('produces deterministic output', async () => {
    const ikm = new Uint8Array(32).fill(0x42);
    const salt = 'test-salt';
    const info = 'test-info';

    const key1 = await hkdf(salt, ikm, info);
    const key2 = await hkdf(salt, ikm, info);

    expect(key1).toEqual(key2);
  });

  it('produces different output for different IKM', async () => {
    const ikm1 = new Uint8Array(32).fill(0x00);
    const ikm2 = new Uint8Array(32).fill(0xff);
    const salt = 'salt';
    const info = 'info';

    const key1 = await hkdf(salt, ikm1, info);
    const key2 = await hkdf(salt, ikm2, info);

    expect(key1).not.toEqual(key2);
  });

  it('produces different output for different salt', async () => {
    const ikm = new Uint8Array(32).fill(0x42);
    const info = 'info';

    const key1 = await hkdf('salt1', ikm, info);
    const key2 = await hkdf('salt2', ikm, info);

    expect(key1).not.toEqual(key2);
  });

  it('produces different output for different info', async () => {
    const ikm = new Uint8Array(32).fill(0x42);
    const salt = 'salt';

    const key1 = await hkdf(salt, ikm, 'info1');
    const key2 = await hkdf(salt, ikm, 'info2');

    expect(key1).not.toEqual(key2);
  });

  it('handles string inputs', async () => {
    const ikm = new Uint8Array(32).fill(0x42);

    const key1 = await hkdf('string-salt', ikm, 'string-info');
    const key2 = await hkdf(
      new TextEncoder().encode('string-salt'),
      ikm,
      new TextEncoder().encode('string-info')
    );

    expect(key1).toEqual(key2);
  });

  it('handles empty salt', async () => {
    const ikm = new Uint8Array(32).fill(0x42);
    const key = await hkdf(new Uint8Array(0), ikm, 'info');
    expect(key.length).toBe(32);
  });

  it('handles empty info', async () => {
    const ikm = new Uint8Array(32).fill(0x42);
    const key = await hkdf('salt', ikm, new Uint8Array(0));
    expect(key.length).toBe(32);
  });
});

// RFC 5869 Test Vectors
describe('HKDF RFC 5869 Test Vectors', () => {
  it('Test Case 1', async () => {
    // Test with SHA-256
    const ikm = hexToBytes('0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b');
    const salt = hexToBytes('000102030405060708090a0b0c');
    const info = hexToBytes('f0f1f2f3f4f5f6f7f8f9');
    const expectedOKM = hexToBytes(
      '3cb25f25faacd57a90434f64d0362f2a' +
      '2d2d0a90cf1a5a4c5db02d56ecc4c5bf' +
      '34007208d5b887185865'
    );

    const okm = await hkdf(salt, ikm, info, 42);
    expect(bytesToHex(okm)).toBe(bytesToHex(expectedOKM));
  });

  it('Test Case 2 (longer inputs)', async () => {
    const ikm = hexToBytes(
      '000102030405060708090a0b0c0d0e0f' +
      '101112131415161718191a1b1c1d1e1f' +
      '202122232425262728292a2b2c2d2e2f' +
      '303132333435363738393a3b3c3d3e3f' +
      '404142434445464748494a4b4c4d4e4f'
    );
    const salt = hexToBytes(
      '606162636465666768696a6b6c6d6e6f' +
      '707172737475767778797a7b7c7d7e7f' +
      '808182838485868788898a8b8c8d8e8f' +
      '909192939495969798999a9b9c9d9e9f' +
      'a0a1a2a3a4a5a6a7a8a9aaabacadaeaf'
    );
    const info = hexToBytes(
      'b0b1b2b3b4b5b6b7b8b9babbbcbdbebf' +
      'c0c1c2c3c4c5c6c7c8c9cacbcccdcecf' +
      'd0d1d2d3d4d5d6d7d8d9dadbdcdddedf' +
      'e0e1e2e3e4e5e6e7e8e9eaebecedeeef' +
      'f0f1f2f3f4f5f6f7f8f9fafbfcfdfeff'
    );
    const expectedOKM = hexToBytes(
      'b11e398dc80327a1c8e7f78c596a4934' +
      '4f012eda2d4efad8a050cc4c19afa97c' +
      '59045a99cac7827271cb41c65e590e09' +
      'da3275600c2f09b8367793a9aca3db71' +
      'cc30c58179ec3e87c14c01d5c1f3434f' +
      '1d87'
    );

    const okm = await hkdf(salt, ikm, info, 82);
    expect(bytesToHex(okm)).toBe(bytesToHex(expectedOKM));
  });

  it('Test Case 3 (zero-length salt/info)', async () => {
    const ikm = hexToBytes('0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b');
    const salt = new Uint8Array(0);
    const info = new Uint8Array(0);
    const expectedOKM = hexToBytes(
      '8da4e775a563c18f715f802a063c5a31' +
      'b8a11f5c5ee1879ec3454e5f3c738d2d' +
      '9d201395faa4b61a96c8'
    );

    const okm = await hkdf(salt, ikm, info, 42);
    expect(bytesToHex(okm)).toBe(bytesToHex(expectedOKM));
  });
});

describe('deriveMasterKey', () => {
  it('produces 32-byte key', async () => {
    const sharedSecret = new Uint8Array(32).fill(0x42);
    const key = await deriveMasterKey(sharedSecret, 'side-a', 'side-b');
    expect(key.length).toBe(32);
  });

  it('is deterministic with same inputs', async () => {
    const sharedSecret = new Uint8Array(32).fill(0x42);

    const key1 = await deriveMasterKey(sharedSecret, 'side-a', 'side-b');
    const key2 = await deriveMasterKey(sharedSecret, 'side-a', 'side-b');

    expect(key1).toEqual(key2);
  });

  it('produces same key regardless of side order', async () => {
    const sharedSecret = new Uint8Array(32).fill(0x42);

    const key1 = await deriveMasterKey(sharedSecret, 'side-a', 'side-b');
    const key2 = await deriveMasterKey(sharedSecret, 'side-b', 'side-a');

    expect(key1).toEqual(key2);
  });

  it('produces different keys for different secrets', async () => {
    const secret1 = new Uint8Array(32).fill(0x00);
    const secret2 = new Uint8Array(32).fill(0xff);

    const key1 = await deriveMasterKey(secret1, 'side-a', 'side-b');
    const key2 = await deriveMasterKey(secret2, 'side-a', 'side-b');

    expect(key1).not.toEqual(key2);
  });

  it('produces different keys for different sides', async () => {
    const sharedSecret = new Uint8Array(32).fill(0x42);

    const key1 = await deriveMasterKey(sharedSecret, 'alice', 'bob');
    const key2 = await deriveMasterKey(sharedSecret, 'charlie', 'dave');

    expect(key1).not.toEqual(key2);
  });
});

describe('deriveSessionKey', () => {
  it('produces 32-byte key', async () => {
    const masterKey = new Uint8Array(32).fill(0x42);
    const key = await deriveSessionKey(masterKey);
    expect(key.length).toBe(32);
  });

  it('is deterministic', async () => {
    const masterKey = new Uint8Array(32).fill(0x42);

    const key1 = await deriveSessionKey(masterKey);
    const key2 = await deriveSessionKey(masterKey);

    expect(key1).toEqual(key2);
  });

  it('differs from master key', async () => {
    const masterKey = new Uint8Array(32).fill(0x42);
    const sessionKey = await deriveSessionKey(masterKey);

    expect(sessionKey).not.toEqual(masterKey);
  });
});

describe('deriveTransitKey', () => {
  it('produces 32-byte key', async () => {
    const masterKey = new Uint8Array(32).fill(0x42);
    const key = await deriveTransitKey(masterKey);
    expect(key.length).toBe(32);
  });

  it('differs from session key', async () => {
    const masterKey = new Uint8Array(32).fill(0x42);

    const sessionKey = await deriveSessionKey(masterKey);
    const transitKey = await deriveTransitKey(masterKey);

    expect(sessionKey).not.toEqual(transitKey);
  });
});

describe('deriveSubkey', () => {
  it('produces 32-byte key', async () => {
    const masterKey = new Uint8Array(32).fill(0x42);
    const key = await deriveSubkey(masterKey, 'encryption');
    expect(key.length).toBe(32);
  });

  it('produces different keys for different purposes', async () => {
    const masterKey = new Uint8Array(32).fill(0x42);

    const key1 = await deriveSubkey(masterKey, 'encryption');
    const key2 = await deriveSubkey(masterKey, 'authentication');

    expect(key1).not.toEqual(key2);
  });

  it('is deterministic for same purpose', async () => {
    const masterKey = new Uint8Array(32).fill(0x42);

    const key1 = await deriveSubkey(masterKey, 'test-purpose');
    const key2 = await deriveSubkey(masterKey, 'test-purpose');

    expect(key1).toEqual(key2);
  });
});
