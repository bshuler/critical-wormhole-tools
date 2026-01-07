/**
 * Crypto Utilities Unit Tests
 */

import { describe, it, expect } from 'vitest';
import {
  randomBytes,
  deriveAddress,
  base32Encode,
  base32Decode,
  bytesToHex,
  hexToBytes,
  concatBytes,
  constantTimeEqual
} from '../../../src/lib/crypto/index.js';

describe('randomBytes', () => {
  it('generates bytes of correct length', () => {
    const bytes16 = randomBytes(16);
    const bytes32 = randomBytes(32);
    const bytes64 = randomBytes(64);

    expect(bytes16).toBeInstanceOf(Uint8Array);
    expect(bytes16.length).toBe(16);
    expect(bytes32.length).toBe(32);
    expect(bytes64.length).toBe(64);
  });

  it('generates different values each time', () => {
    const a = randomBytes(32);
    const b = randomBytes(32);
    expect(a).not.toEqual(b);
  });

  it('handles zero length', () => {
    const bytes = randomBytes(0);
    expect(bytes.length).toBe(0);
  });
});

describe('base32Encode', () => {
  it('encodes known values correctly', () => {
    // Test vector: empty
    expect(base32Encode(new Uint8Array([]))).toBe('');

    // Test vector: single byte
    expect(base32Encode(new Uint8Array([0x00]))).toBe('aa');
    expect(base32Encode(new Uint8Array([0xff]))).toBe('74');

    // Test vector: "test"
    const testBytes = new TextEncoder().encode('test');
    expect(base32Encode(testBytes)).toBe('orsxg5a');
  });

  it('produces lowercase output', () => {
    const bytes = randomBytes(16);
    const encoded = base32Encode(bytes);
    expect(encoded).toBe(encoded.toLowerCase());
  });

  it('produces consistent length for 16 bytes', () => {
    // 16 bytes = 128 bits / 5 bits per char = 25.6 -> 26 chars
    const bytes = new Uint8Array(16);
    const encoded = base32Encode(bytes);
    expect(encoded.length).toBe(26);
  });
});

describe('base32Decode', () => {
  it('decodes known values correctly', () => {
    // Roundtrip test
    const original = new Uint8Array([1, 2, 3, 4, 5]);
    const encoded = base32Encode(original);
    const decoded = base32Decode(encoded);

    // May have extra zeros due to padding
    expect(decoded.slice(0, original.length)).toEqual(original);
  });

  it('handles uppercase input', () => {
    const encoded = 'ORSXG5A';
    const decoded = base32Decode(encoded);
    expect(decoded).toEqual(new TextEncoder().encode('test').slice(0, decoded.length));
  });

  it('ignores invalid characters', () => {
    const result = base32Decode('abc-def-123');
    expect(result).toBeInstanceOf(Uint8Array);
  });
});

describe('base32 roundtrip', () => {
  it('roundtrips arbitrary data', () => {
    for (let len = 0; len <= 32; len++) {
      const original = randomBytes(len);
      const encoded = base32Encode(original);
      const decoded = base32Decode(encoded);
      expect(decoded.slice(0, len)).toEqual(original);
    }
  });
});

describe('bytesToHex', () => {
  it('converts known values', () => {
    expect(bytesToHex(new Uint8Array([]))).toBe('');
    expect(bytesToHex(new Uint8Array([0]))).toBe('00');
    expect(bytesToHex(new Uint8Array([255]))).toBe('ff');
    expect(bytesToHex(new Uint8Array([1, 2, 3]))).toBe('010203');
    expect(bytesToHex(new Uint8Array([0xde, 0xad, 0xbe, 0xef]))).toBe('deadbeef');
  });

  it('produces lowercase hex', () => {
    const bytes = new Uint8Array([0xAB, 0xCD, 0xEF]);
    expect(bytesToHex(bytes)).toBe('abcdef');
  });
});

describe('hexToBytes', () => {
  it('converts known values', () => {
    expect(hexToBytes('')).toEqual(new Uint8Array([]));
    expect(hexToBytes('00')).toEqual(new Uint8Array([0]));
    expect(hexToBytes('ff')).toEqual(new Uint8Array([255]));
    expect(hexToBytes('010203')).toEqual(new Uint8Array([1, 2, 3]));
    expect(hexToBytes('deadbeef')).toEqual(new Uint8Array([0xde, 0xad, 0xbe, 0xef]));
  });

  it('handles uppercase', () => {
    expect(hexToBytes('DEADBEEF')).toEqual(new Uint8Array([0xde, 0xad, 0xbe, 0xef]));
  });
});

describe('hex roundtrip', () => {
  it('roundtrips arbitrary data', () => {
    for (let i = 0; i < 10; i++) {
      const original = randomBytes(32);
      const hex = bytesToHex(original);
      const back = hexToBytes(hex);
      expect(back).toEqual(original);
    }
  });
});

describe('concatBytes', () => {
  it('concatenates multiple arrays', () => {
    const a = new Uint8Array([1, 2]);
    const b = new Uint8Array([3, 4, 5]);
    const c = new Uint8Array([6]);

    expect(concatBytes(a, b, c)).toEqual(new Uint8Array([1, 2, 3, 4, 5, 6]));
  });

  it('handles empty arrays', () => {
    const a = new Uint8Array([1, 2]);
    const empty = new Uint8Array([]);

    expect(concatBytes(a, empty)).toEqual(new Uint8Array([1, 2]));
    expect(concatBytes(empty, a)).toEqual(new Uint8Array([1, 2]));
    expect(concatBytes(empty, empty)).toEqual(new Uint8Array([]));
  });

  it('handles single array', () => {
    const a = new Uint8Array([1, 2, 3]);
    expect(concatBytes(a)).toEqual(a);
  });

  it('handles no arrays', () => {
    expect(concatBytes()).toEqual(new Uint8Array([]));
  });
});

describe('constantTimeEqual', () => {
  it('returns true for equal arrays', () => {
    const a = new Uint8Array([1, 2, 3, 4]);
    const b = new Uint8Array([1, 2, 3, 4]);
    expect(constantTimeEqual(a, b)).toBe(true);
  });

  it('returns false for different arrays', () => {
    const a = new Uint8Array([1, 2, 3, 4]);
    const b = new Uint8Array([1, 2, 3, 5]);
    expect(constantTimeEqual(a, b)).toBe(false);
  });

  it('returns false for different lengths', () => {
    const a = new Uint8Array([1, 2, 3]);
    const b = new Uint8Array([1, 2, 3, 4]);
    expect(constantTimeEqual(a, b)).toBe(false);
  });

  it('handles empty arrays', () => {
    expect(constantTimeEqual(new Uint8Array([]), new Uint8Array([]))).toBe(true);
  });

  it('detects single bit differences', () => {
    const a = new Uint8Array([0b11111111]);
    const b = new Uint8Array([0b11111110]);
    expect(constantTimeEqual(a, b)).toBe(false);
  });
});

describe('deriveAddress', () => {
  it('produces 26-character address', async () => {
    const publicKey = randomBytes(32);
    const address = await deriveAddress(publicKey);
    expect(address.length).toBe(26);
  });

  it('produces valid base32 characters', async () => {
    const publicKey = randomBytes(32);
    const address = await deriveAddress(publicKey);
    expect(address).toMatch(/^[a-z2-7]{26}$/);
  });

  it('produces deterministic output', async () => {
    const publicKey = new Uint8Array(32).fill(0x42);
    const address1 = await deriveAddress(publicKey);
    const address2 = await deriveAddress(publicKey);
    expect(address1).toBe(address2);
  });

  it('produces different addresses for different keys', async () => {
    const pk1 = new Uint8Array(32).fill(0x00);
    const pk2 = new Uint8Array(32).fill(0xff);
    const addr1 = await deriveAddress(pk1);
    const addr2 = await deriveAddress(pk2);
    expect(addr1).not.toBe(addr2);
  });
});
