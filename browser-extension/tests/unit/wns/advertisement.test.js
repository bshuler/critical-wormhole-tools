/**
 * WNS Advertisement Unit Tests
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { Advertisement, verifyAdvertisement } from '../../../src/lib/wns/advertisement.js';
import { Identity } from '../../../src/lib/wns/identity.js';

describe('Advertisement', () => {
  let identity;

  beforeEach(async () => {
    identity = await Identity.generate({ name: 'Test Server' });
  });

  describe('create', () => {
    it('creates advertisement with required fields', async () => {
      const ad = await Advertisement.create({
        identity,
        code: '7-guitar-sunset'
      });

      expect(ad.version).toBe(1);
      expect(ad.address).toBe(identity.address);
      expect(ad.publicKey).toBeDefined();
      expect(ad.code).toBe('7-guitar-sunset');
      expect(ad.timestamp).toBeDefined();
      expect(ad.expires).toBeDefined();
      expect(ad.signature).toBeDefined();
    });

    it('sets correct expiry based on TTL', async () => {
      const ttlSeconds = 300;
      const before = Date.now();

      const ad = await Advertisement.create({
        identity,
        code: '7-guitar-sunset',
        ttlSeconds
      });

      const after = Date.now();
      const expires = new Date(ad.expires).getTime();

      // Expiry should be within TTL seconds from creation
      expect(expires).toBeGreaterThanOrEqual(before + (ttlSeconds - 1) * 1000);
      expect(expires).toBeLessThanOrEqual(after + (ttlSeconds + 1) * 1000);
    });

    it('includes services if provided', async () => {
      const ad = await Advertisement.create({
        identity,
        code: '7-guitar-sunset',
        services: ['ssh', 'http']
      });

      expect(ad.services).toEqual(['ssh', 'http']);
    });

    it('includes scoped name from identity', async () => {
      identity.setScopedName('myserver');

      const ad = await Advertisement.create({
        identity,
        code: '7-guitar-sunset'
      });

      expect(ad.scopedName).toBe('myserver');
    });

    it('is signed', async () => {
      const ad = await Advertisement.create({
        identity,
        code: '7-guitar-sunset'
      });

      expect(ad.signature).toBeTypeOf('string');
      expect(ad.signature.length).toBeGreaterThan(0);
    });
  });

  describe('fromJSON', () => {
    it('parses JSON string', async () => {
      const ad = await Advertisement.create({
        identity,
        code: '7-guitar-sunset'
      });

      const json = JSON.stringify(ad.toJSON());
      const parsed = Advertisement.fromJSON(json);

      expect(parsed.address).toBe(ad.address);
      expect(parsed.code).toBe(ad.code);
    });

    it('parses JSON object', async () => {
      const ad = await Advertisement.create({
        identity,
        code: '7-guitar-sunset'
      });

      const parsed = Advertisement.fromJSON(ad.toJSON());

      expect(parsed.address).toBe(ad.address);
      expect(parsed.signature).toBe(ad.signature);
    });
  });

  describe('getCanonicalJSON', () => {
    it('produces deterministic output', async () => {
      const ad = await Advertisement.create({
        identity,
        code: '7-guitar-sunset'
      });

      const json1 = ad.getCanonicalJSON();
      const json2 = ad.getCanonicalJSON();

      expect(json1).toBe(json2);
    });

    it('excludes signature', async () => {
      const ad = await Advertisement.create({
        identity,
        code: '7-guitar-sunset'
      });

      const canonical = ad.getCanonicalJSON();
      const parsed = JSON.parse(canonical);

      expect(parsed.signature).toBeUndefined();
    });

    it('has sorted keys', async () => {
      const ad = await Advertisement.create({
        identity,
        code: '7-guitar-sunset',
        services: ['ssh']
      });

      const canonical = ad.getCanonicalJSON();
      const keys = Object.keys(JSON.parse(canonical));

      const sorted = [...keys].sort();
      expect(keys).toEqual(sorted);
    });

    it('excludes null values', async () => {
      const ad = await Advertisement.create({
        identity,
        code: '7-guitar-sunset'
      });

      const canonical = ad.getCanonicalJSON();
      const parsed = JSON.parse(canonical);

      expect(parsed.scoped_name).toBeUndefined();
    });
  });

  describe('sign', () => {
    it('produces base64 signature', async () => {
      const ad = new Advertisement({
        version: 1,
        address: identity.address,
        publicKey: btoa(String.fromCharCode(...identity.publicKey)),
        code: '7-guitar-sunset',
        timestamp: new Date().toISOString(),
        expires: new Date(Date.now() + 300000).toISOString()
      });

      await ad.sign(identity);

      expect(ad.signature).toMatch(/^[A-Za-z0-9+/]+=*$/);
    });
  });

  describe('verify', () => {
    it('returns true for valid signature', async () => {
      const ad = await Advertisement.create({
        identity,
        code: '7-guitar-sunset'
      });

      const valid = await ad.verify();
      expect(valid).toBe(true);
    });

    it('returns false for missing signature', async () => {
      const ad = new Advertisement({
        address: identity.address,
        publicKey: btoa(String.fromCharCode(...identity.publicKey)),
        code: '7-guitar-sunset',
        timestamp: new Date().toISOString(),
        expires: new Date(Date.now() + 300000).toISOString()
      });

      const valid = await ad.verify();
      expect(valid).toBe(false);
    });

    it('returns false for tampered code', async () => {
      const ad = await Advertisement.create({
        identity,
        code: '7-guitar-sunset'
      });

      // Tamper with code after signing
      ad.code = '8-piano-sunrise';

      const valid = await ad.verify();
      expect(valid).toBe(false);
    });

    it('returns false for wrong public key', async () => {
      const ad = await Advertisement.create({
        identity,
        code: '7-guitar-sunset'
      });

      // Create different identity
      const other = await Identity.generate();

      const valid = await ad.verify(other.publicKey);
      expect(valid).toBe(false);
    });
  });

  describe('isExpired', () => {
    it('returns false for fresh advertisement', async () => {
      const ad = await Advertisement.create({
        identity,
        code: '7-guitar-sunset',
        ttlSeconds: 300
      });

      expect(ad.isExpired()).toBe(false);
    });

    it('returns true for expired advertisement', () => {
      const ad = new Advertisement({
        address: 'test',
        code: '7-guitar-sunset',
        timestamp: new Date(Date.now() - 600000).toISOString(),
        expires: new Date(Date.now() - 300000).toISOString()
      });

      expect(ad.isExpired()).toBe(true);
    });
  });

  describe('expiresWithin', () => {
    it('returns true if expires within threshold', async () => {
      const ad = await Advertisement.create({
        identity,
        code: '7-guitar-sunset',
        ttlSeconds: 60 // 1 minute
      });

      expect(ad.expiresWithin(120)).toBe(true); // Expires within 2 min
      expect(ad.expiresWithin(30)).toBe(false); // Not within 30 sec
    });
  });

  describe('ttl', () => {
    it('returns seconds until expiry', async () => {
      const ad = await Advertisement.create({
        identity,
        code: '7-guitar-sunset',
        ttlSeconds: 300
      });

      const ttl = ad.ttl;
      expect(ttl).toBeGreaterThan(290);
      expect(ttl).toBeLessThanOrEqual(300);
    });

    it('returns 0 for expired advertisement', () => {
      const ad = new Advertisement({
        address: 'test',
        code: '7-guitar-sunset',
        expires: new Date(Date.now() - 1000).toISOString()
      });

      expect(ad.ttl).toBe(0);
    });
  });

  describe('toJSON', () => {
    it('includes all fields', async () => {
      identity.setScopedName('myserver');

      const ad = await Advertisement.create({
        identity,
        code: '7-guitar-sunset',
        services: ['ssh', 'http']
      });

      const json = ad.toJSON();

      expect(json.version).toBe(1);
      expect(json.address).toBe(identity.address);
      expect(json.public_key).toBeDefined();
      expect(json.code).toBe('7-guitar-sunset');
      expect(json.timestamp).toBeDefined();
      expect(json.expires).toBeDefined();
      expect(json.signature).toBeDefined();
      expect(json.scoped_name).toBe('myserver');
      expect(json.services).toEqual(['ssh', 'http']);
    });

    it('omits empty services', async () => {
      const ad = await Advertisement.create({
        identity,
        code: '7-guitar-sunset'
      });

      const json = ad.toJSON();
      expect(json.services).toBeUndefined();
    });
  });

  describe('resolutionAddress', () => {
    it('returns bare address without scoped name', async () => {
      const ad = await Advertisement.create({
        identity,
        code: '7-guitar-sunset'
      });

      expect(ad.resolutionAddress).toBe(identity.address);
    });

    it('returns scoped address with scoped name', async () => {
      identity.setScopedName('myserver');

      const ad = await Advertisement.create({
        identity,
        code: '7-guitar-sunset'
      });

      expect(ad.resolutionAddress).toBe(`myserver.${identity.address}`);
    });
  });
});

describe('verifyAdvertisement', () => {
  let identity;

  beforeEach(async () => {
    identity = await Identity.generate();
  });

  it('returns valid=true for valid advertisement', async () => {
    const ad = await Advertisement.create({
      identity,
      code: '7-guitar-sunset'
    });

    const result = await verifyAdvertisement(ad.toJSON());

    expect(result.valid).toBe(true);
    expect(result.code).toBe('7-guitar-sunset');
    expect(result.error).toBeNull();
    expect(result.advertisement).toBeDefined();
  });

  it('returns valid=false for expired advertisement', async () => {
    const ad = new Advertisement({
      address: identity.address,
      publicKey: btoa(String.fromCharCode(...identity.publicKey)),
      code: '7-guitar-sunset',
      timestamp: new Date(Date.now() - 600000).toISOString(),
      expires: new Date(Date.now() - 1000).toISOString(),
      signature: 'fake'
    });

    const result = await verifyAdvertisement(ad.toJSON());

    expect(result.valid).toBe(false);
    expect(result.code).toBeNull();
    expect(result.error).toBe('Advertisement expired');
  });

  it('returns valid=false for address mismatch', async () => {
    const ad = await Advertisement.create({
      identity,
      code: '7-guitar-sunset'
    });

    const result = await verifyAdvertisement(
      ad.toJSON(),
      'aaaaaaaaaaaaaaaaaaaaaaaaaa' // Different address
    );

    expect(result.valid).toBe(false);
    expect(result.error).toBe('Address mismatch');
  });

  it('returns valid=false for scoped name mismatch', async () => {
    identity.setScopedName('server1');

    const ad = await Advertisement.create({
      identity,
      code: '7-guitar-sunset'
    });

    const result = await verifyAdvertisement(
      ad.toJSON(),
      `server2.${identity.address}` // Different scoped name
    );

    expect(result.valid).toBe(false);
    expect(result.error).toBe('Scoped name mismatch');
  });

  it('returns valid=false for invalid signature', async () => {
    const ad = await Advertisement.create({
      identity,
      code: '7-guitar-sunset'
    });

    const json = ad.toJSON();
    json.code = 'tampered-code';

    const result = await verifyAdvertisement(json);

    expect(result.valid).toBe(false);
    expect(result.error).toBe('Invalid signature');
  });

  it('handles JSON string input', async () => {
    const ad = await Advertisement.create({
      identity,
      code: '7-guitar-sunset'
    });

    const result = await verifyAdvertisement(JSON.stringify(ad.toJSON()));

    expect(result.valid).toBe(true);
  });

  it('handles parse errors gracefully', async () => {
    const result = await verifyAdvertisement('not valid json');

    expect(result.valid).toBe(false);
    expect(result.error).toBeDefined();
  });
});
