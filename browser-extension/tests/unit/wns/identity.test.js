/**
 * WNS Identity Unit Tests
 */

import { describe, it, expect } from 'vitest';
import {
  Identity,
  deriveAddress,
  verifyAddress,
  parseWNSAddress,
  isValidAddress,
  isValidScopedName,
  isWNSAddress,
  isEphemeralCode
} from '../../../src/lib/wns/identity.js';

describe('Identity', () => {
  describe('generate', () => {
    it('creates identity with all required fields', async () => {
      const identity = await Identity.generate();

      expect(identity.privateKey).toBeInstanceOf(Uint8Array);
      expect(identity.publicKey).toBeInstanceOf(Uint8Array);
      expect(identity.address).toBeTypeOf('string');
      expect(identity.metadata).toBeTypeOf('object');
    });

    it('generates 32-byte keys', async () => {
      const identity = await Identity.generate();

      expect(identity.privateKey.length).toBe(32);
      expect(identity.publicKey.length).toBe(32);
    });

    it('generates 26-character address', async () => {
      const identity = await Identity.generate();
      expect(identity.address.length).toBe(26);
    });

    it('generates valid base32 address', async () => {
      const identity = await Identity.generate();
      expect(identity.address).toMatch(/^[a-z2-7]{26}$/);
    });

    it('includes name in metadata if provided', async () => {
      const identity = await Identity.generate({ name: 'My Server' });
      expect(identity.metadata.name).toBe('My Server');
    });

    it('includes created timestamp', async () => {
      const before = new Date().toISOString();
      const identity = await Identity.generate();
      const after = new Date().toISOString();

      expect(identity.metadata.created).toBeDefined();
      expect(identity.metadata.created >= before).toBe(true);
      expect(identity.metadata.created <= after).toBe(true);
    });

    it('generates unique identities', async () => {
      const id1 = await Identity.generate();
      const id2 = await Identity.generate();

      expect(id1.address).not.toBe(id2.address);
      expect(id1.privateKey).not.toEqual(id2.privateKey);
    });
  });

  describe('fromJSON / toJSON', () => {
    it('roundtrips identity', async () => {
      const original = await Identity.generate({ name: 'Test' });
      const json = original.toJSON();
      const restored = await Identity.fromJSON(json);

      expect(restored.address).toBe(original.address);
      expect(restored.privateKey).toEqual(original.privateKey);
      expect(restored.publicKey).toEqual(original.publicKey);
      expect(restored.metadata.name).toBe(original.metadata.name);
    });

    it('exports public-only version', async () => {
      const identity = await Identity.generate();
      const json = identity.toJSON(false);

      expect(json.publicKey).toBeDefined();
      expect(json.address).toBeDefined();
      expect(json.privateKey).toBeUndefined();
    });

    it('rejects mismatched address/key', async () => {
      const identity = await Identity.generate();
      const json = identity.toJSON();
      json.address = 'aaaaaaaaaaaaaaaaaaaaaaaaaa'; // Wrong address

      await expect(Identity.fromJSON(json)).rejects.toThrow('Address does not match');
    });
  });

  describe('fullAddress', () => {
    it('returns wh:// URL', async () => {
      const identity = await Identity.generate();
      expect(identity.fullAddress).toMatch(/^wh:\/\/[a-z2-7]{26}\.wns$/);
    });
  });

  describe('scopedAddress', () => {
    it('returns null without scoped name', async () => {
      const identity = await Identity.generate();
      expect(identity.scopedAddress).toBeNull();
    });

    it('returns scoped URL with scoped name', async () => {
      const identity = await Identity.generate();
      identity.setScopedName('myserver');
      expect(identity.scopedAddress).toMatch(/^wh:\/\/myserver\.[a-z2-7]{26}\.wns$/);
    });
  });

  describe('setScopedName', () => {
    it('accepts valid scoped names', async () => {
      const identity = await Identity.generate();

      identity.setScopedName('server');
      expect(identity.metadata.scopedName).toBe('server');

      identity.setScopedName('my-server');
      expect(identity.metadata.scopedName).toBe('my-server');

      identity.setScopedName('a');
      expect(identity.metadata.scopedName).toBe('a');
    });

    it('clears scoped name with null', async () => {
      const identity = await Identity.generate();
      identity.setScopedName('test');
      identity.setScopedName(null);
      expect(identity.metadata.scopedName).toBeNull();
    });

    it('rejects invalid scoped names', async () => {
      const identity = await Identity.generate();

      expect(() => identity.setScopedName('-invalid')).toThrow();
      expect(() => identity.setScopedName('invalid-')).toThrow();
      expect(() => identity.setScopedName('has spaces')).toThrow();
    });
  });

  describe('sign', () => {
    it('signs string message', async () => {
      const identity = await Identity.generate();
      const signature = await identity.sign('test message');

      expect(signature).toBeInstanceOf(Uint8Array);
      expect(signature.length).toBe(64);
    });

    it('signs bytes message', async () => {
      const identity = await Identity.generate();
      const message = new Uint8Array([1, 2, 3, 4]);
      const signature = await identity.sign(message);

      expect(signature.length).toBe(64);
    });

    it('produces deterministic signatures', async () => {
      const identity = await Identity.generate();
      const message = 'test';

      const sig1 = await identity.sign(message);
      const sig2 = await identity.sign(message);

      expect(sig1).toEqual(sig2);
    });
  });

  describe('fingerprint', () => {
    it('returns colon-separated hex', async () => {
      const identity = await Identity.generate();
      const fp = await identity.fingerprint();

      expect(fp).toMatch(/^([0-9a-f]{2}:){7}[0-9a-f]{2}$/);
    });

    it('is deterministic', async () => {
      const identity = await Identity.generate();

      const fp1 = await identity.fingerprint();
      const fp2 = await identity.fingerprint();

      expect(fp1).toBe(fp2);
    });
  });
});

describe('deriveAddress', () => {
  it('produces 26-character address', async () => {
    const publicKey = new Uint8Array(32).fill(0x42);
    const address = await deriveAddress(publicKey);
    expect(address.length).toBe(26);
  });

  it('produces valid base32', async () => {
    const publicKey = new Uint8Array(32).fill(0x42);
    const address = await deriveAddress(publicKey);
    expect(address).toMatch(/^[a-z2-7]{26}$/);
  });

  it('is deterministic', async () => {
    const publicKey = new Uint8Array(32).fill(0x42);

    const addr1 = await deriveAddress(publicKey);
    const addr2 = await deriveAddress(publicKey);

    expect(addr1).toBe(addr2);
  });
});

describe('verifyAddress', () => {
  it('returns true for matching address/key', async () => {
    const identity = await Identity.generate();
    const valid = await verifyAddress(identity.address, identity.publicKey);
    expect(valid).toBe(true);
  });

  it('returns false for wrong key', async () => {
    const identity = await Identity.generate();
    const wrongKey = new Uint8Array(32).fill(0xff);
    const valid = await verifyAddress(identity.address, wrongKey);
    expect(valid).toBe(false);
  });

  it('handles uppercase address', async () => {
    const identity = await Identity.generate();
    const valid = await verifyAddress(identity.address.toUpperCase(), identity.publicKey);
    expect(valid).toBe(true);
  });
});

describe('parseWNSAddress', () => {
  it('parses bare address', () => {
    const result = parseWNSAddress('abcdefghijklmnopqrstuvwxyz');
    expect(result).toEqual({
      address: 'abcdefghijklmnopqrstuvwxyz',
      scopedName: null,
      username: null,
      fullUrl: 'wh://abcdefghijklmnopqrstuvwxyz.wns'
    });
  });

  it('parses wh:// URL', () => {
    const result = parseWNSAddress('wh://abcdefghijklmnopqrstuvwxyz.wns');
    expect(result.address).toBe('abcdefghijklmnopqrstuvwxyz');
    expect(result.scopedName).toBeNull();
  });

  it('parses scoped address', () => {
    const result = parseWNSAddress('server.abcdefghijklmnopqrstuvwxyz');
    expect(result.address).toBe('abcdefghijklmnopqrstuvwxyz');
    expect(result.scopedName).toBe('server');
  });

  it('parses full scoped URL', () => {
    const result = parseWNSAddress('wh://myserver.abcdefghijklmnopqrstuvwxyz.wns');
    expect(result.address).toBe('abcdefghijklmnopqrstuvwxyz');
    expect(result.scopedName).toBe('myserver');
  });

  it('parses with username', () => {
    const result = parseWNSAddress('wh://user@abcdefghijklmnopqrstuvwxyz.wns');
    expect(result.address).toBe('abcdefghijklmnopqrstuvwxyz');
    expect(result.username).toBe('user');
  });

  it('parses username with scoped name', () => {
    const result = parseWNSAddress('wh://admin@server.abcdefghijklmnopqrstuvwxyz.wns');
    expect(result.address).toBe('abcdefghijklmnopqrstuvwxyz');
    expect(result.scopedName).toBe('server');
    expect(result.username).toBe('admin');
  });

  it('handles case insensitivity', () => {
    const result = parseWNSAddress('WH://ABCDEFGHIJKLMNOPQRSTUVWXYZ.WNS');
    expect(result.address).toBe('abcdefghijklmnopqrstuvwxyz');
  });

  it('returns null for invalid input', () => {
    expect(parseWNSAddress(null)).toBeNull();
    expect(parseWNSAddress('')).toBeNull();
    expect(parseWNSAddress('invalid')).toBeNull();
    expect(parseWNSAddress('a.b.c.d')).toBeNull(); // Too many parts
  });
});

describe('isValidAddress', () => {
  it('accepts valid 26-char base32', () => {
    expect(isValidAddress('abcdefghijklmnopqrstuvwxyz')).toBe(true);
    expect(isValidAddress('22222222222222222222222222')).toBe(true);
    expect(isValidAddress('77777777777777777777777777')).toBe(true);
  });

  it('rejects invalid characters', () => {
    expect(isValidAddress('abcdefghijklmnopqrstuvwxy0')).toBe(false); // 0 not in base32
    expect(isValidAddress('abcdefghijklmnopqrstuvwxy1')).toBe(false); // 1 not in base32
    expect(isValidAddress('abcdefghijklmnopqrstuvwxy8')).toBe(false); // 8 not in base32
  });

  it('rejects wrong length', () => {
    expect(isValidAddress('abcdefghijklmnopqrstuvwxy')).toBe(false); // 25 chars
    expect(isValidAddress('abcdefghijklmnopqrstuvwxyzz')).toBe(false); // 27 chars
  });

  it('handles edge cases', () => {
    expect(isValidAddress(null)).toBe(false);
    expect(isValidAddress(undefined)).toBe(false);
    expect(isValidAddress('')).toBe(false);
    expect(isValidAddress(123)).toBe(false);
  });
});

describe('isValidScopedName', () => {
  it('accepts valid names', () => {
    expect(isValidScopedName('a')).toBe(true);
    expect(isValidScopedName('server')).toBe(true);
    expect(isValidScopedName('my-server')).toBe(true);
    expect(isValidScopedName('server123')).toBe(true);
    expect(isValidScopedName('a'.repeat(63))).toBe(true);
  });

  it('rejects invalid names', () => {
    expect(isValidScopedName('')).toBe(false);
    expect(isValidScopedName('-server')).toBe(false); // starts with hyphen
    expect(isValidScopedName('server-')).toBe(false); // ends with hyphen
    expect(isValidScopedName('my server')).toBe(false); // space
    expect(isValidScopedName('SERVER')).toBe(true); // uppercase ok (normalized)
    expect(isValidScopedName('a'.repeat(64))).toBe(false); // too long
  });

  it('handles edge cases', () => {
    expect(isValidScopedName(null)).toBe(false);
    expect(isValidScopedName(undefined)).toBe(false);
    expect(isValidScopedName(123)).toBe(false);
  });
});

describe('isWNSAddress', () => {
  it('identifies WNS addresses', () => {
    expect(isWNSAddress('wh://address.wns')).toBe(true);
    expect(isWNSAddress('address.wns')).toBe(true);
    expect(isWNSAddress('abcdefghijklmnopqrstuvwxyz')).toBe(true);
  });

  it('rejects non-WNS strings', () => {
    expect(isWNSAddress('7-guitar-sunset')).toBe(false);
    expect(isWNSAddress('http://example.com')).toBe(false);
    expect(isWNSAddress('')).toBe(false);
    expect(isWNSAddress(null)).toBe(false);
  });
});

describe('isEphemeralCode', () => {
  it('identifies ephemeral codes', () => {
    expect(isEphemeralCode('7-guitar-sunset')).toBe(true);
    expect(isEphemeralCode('123-alpha-beta-gamma')).toBe(true);
    expect(isEphemeralCode('1-a-b')).toBe(true);
  });

  it('rejects non-ephemeral strings', () => {
    expect(isEphemeralCode('abcdefghijklmnopqrstuvwxyz')).toBe(false);
    expect(isEphemeralCode('wh://address.wns')).toBe(false);
    expect(isEphemeralCode('guitar-sunset')).toBe(false); // missing number
    expect(isEphemeralCode('7-guitar')).toBe(false); // too few words
    expect(isEphemeralCode('')).toBe(false);
    expect(isEphemeralCode(null)).toBe(false);
  });
});
