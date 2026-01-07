/**
 * SHA-256 Hash Unit Tests
 */

import { describe, it, expect } from 'vitest';
import { sha256, sha256Hex } from '../../../src/lib/crypto/hash.js';

describe('sha256', () => {
  it('hashes string correctly', async () => {
    // Known test vector: SHA-256 of empty string
    const hash = await sha256('');
    const hex = Array.from(hash).map(b => b.toString(16).padStart(2, '0')).join('');
    expect(hex).toBe('e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855');
  });

  it('hashes "hello" correctly', async () => {
    const hash = await sha256('hello');
    const hex = Array.from(hash).map(b => b.toString(16).padStart(2, '0')).join('');
    expect(hex).toBe('2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824');
  });

  it('hashes bytes correctly', async () => {
    // SHA-256 of [0x00, 0x01, 0x02]
    const hash = await sha256(new Uint8Array([0, 1, 2]));
    expect(hash).toBeInstanceOf(Uint8Array);
    expect(hash.length).toBe(32);
  });

  it('produces 32-byte output', async () => {
    const hash = await sha256('test data');
    expect(hash.length).toBe(32);
  });

  it('produces deterministic output', async () => {
    const data = 'consistent input';
    const hash1 = await sha256(data);
    const hash2 = await sha256(data);
    expect(hash1).toEqual(hash2);
  });

  it('produces different output for different input', async () => {
    const hash1 = await sha256('input1');
    const hash2 = await sha256('input2');
    expect(hash1).not.toEqual(hash2);
  });

  it('handles UTF-8 correctly', async () => {
    // SHA-256 should handle unicode properly
    const hash1 = await sha256('cafe');
    const hash2 = await sha256('café');
    expect(hash1).not.toEqual(hash2);
  });

  it('handles large input', async () => {
    const largeData = 'x'.repeat(100000);
    const hash = await sha256(largeData);
    expect(hash.length).toBe(32);
  });
});

describe('sha256Hex', () => {
  it('returns hex string', async () => {
    const hex = await sha256Hex('');
    expect(hex).toBe('e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855');
  });

  it('returns lowercase hex', async () => {
    const hex = await sha256Hex('test');
    expect(hex).toBe(hex.toLowerCase());
  });

  it('returns 64-character string', async () => {
    const hex = await sha256Hex('any data');
    expect(hex.length).toBe(64);
  });

  it('matches sha256 output', async () => {
    const data = 'test data';
    const hash = await sha256(data);
    const hex = await sha256Hex(data);

    const manualHex = Array.from(hash)
      .map(b => b.toString(16).padStart(2, '0'))
      .join('');

    expect(hex).toBe(manualHex);
  });

  it('handles bytes input', async () => {
    const bytes = new Uint8Array([1, 2, 3, 4, 5]);
    const hex = await sha256Hex(bytes);
    expect(hex.length).toBe(64);
    expect(hex).toMatch(/^[0-9a-f]{64}$/);
  });
});

// Test vectors from various sources
describe('sha256 test vectors', () => {
  const testVectors = [
    {
      input: '',
      expected: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'
    },
    {
      input: 'abc',
      expected: 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad'
    },
    {
      input: 'abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq',
      expected: '248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1'
    },
    {
      input: 'The quick brown fox jumps over the lazy dog',
      expected: 'd7a8fbb307d7809469ca9abcb0082e4f8d5651e46d3cdb762d02d0bf37c9e592'
    },
    {
      input: 'The quick brown fox jumps over the lazy dog.',
      expected: 'ef537f25c895bfa782526529a9b63d97aa631564d5d789c2b765448c8635fb6c'
    }
  ];

  testVectors.forEach(({ input, expected }, index) => {
    it(`test vector ${index + 1}: ${input.slice(0, 30)}...`, async () => {
      const hex = await sha256Hex(input);
      expect(hex).toBe(expected);
    });
  });
});
