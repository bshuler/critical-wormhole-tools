/**
 * Unit tests for SPAKE2 Password-Authenticated Key Exchange
 *
 * Tests the SPAKE2 Symmetric implementation for magic-wormhole compatibility.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import {
  SPAKE2_Symmetric,
  createSPAKE2,
  SymmetricSPAKE2,
  SPAKE2
} from '../../../src/lib/crypto/spake2.js';

describe('SPAKE2_Symmetric', () => {
  describe('constructor', () => {
    it('should initialize with password bytes', () => {
      const password = new TextEncoder().encode('test-password');
      const spake = new SPAKE2_Symmetric(password);

      expect(spake.password).toEqual(password);
      expect(spake.state).toBe('init');
    });

    it('should accept idSymmetric parameter', () => {
      const password = new TextEncoder().encode('test-password');
      const idSymmetric = new TextEncoder().encode('test-app');
      const spake = new SPAKE2_Symmetric(password, idSymmetric);

      expect(spake.idSymmetric).toEqual(idSymmetric);
    });

    it('should default to empty idSymmetric', () => {
      const password = new TextEncoder().encode('test-password');
      const spake = new SPAKE2_Symmetric(password);

      expect(spake.idSymmetric).toEqual(new Uint8Array(0));
    });

    it('should initialize null keys and messages', () => {
      const password = new TextEncoder().encode('test-password');
      const spake = new SPAKE2_Symmetric(password);

      expect(spake.x).toBeNull();
      expect(spake.X).toBeNull();
      expect(spake.outbound).toBeNull();
      expect(spake.Y).toBeNull();
      expect(spake.inbound).toBeNull();
      expect(spake.sharedKey).toBeNull();
    });
  });

  describe('start', () => {
    it('should generate 33-byte message', () => {
      const password = new TextEncoder().encode('test-password');
      const spake = new SPAKE2_Symmetric(password);

      const msg = spake.start();

      expect(msg).toBeInstanceOf(Uint8Array);
      expect(msg.length).toBe(33);
    });

    it('should start with S (0x53) side indicator', () => {
      const password = new TextEncoder().encode('test-password');
      const spake = new SPAKE2_Symmetric(password);

      const msg = spake.start();

      expect(msg[0]).toBe(0x53); // 'S'
    });

    it('should set state to started', () => {
      const password = new TextEncoder().encode('test-password');
      const spake = new SPAKE2_Symmetric(password);

      spake.start();

      expect(spake.state).toBe('started');
    });

    it('should store outbound message', () => {
      const password = new TextEncoder().encode('test-password');
      const spake = new SPAKE2_Symmetric(password);

      const msg = spake.start();

      expect(spake.outbound).toBe(msg);
    });

    it('should throw if already started', () => {
      const password = new TextEncoder().encode('test-password');
      const spake = new SPAKE2_Symmetric(password);

      spake.start();

      expect(() => spake.start()).toThrow('SPAKE2 already started');
    });

    it('should generate different messages each time', () => {
      const password = new TextEncoder().encode('test-password');

      const spake1 = new SPAKE2_Symmetric(password);
      const spake2 = new SPAKE2_Symmetric(password);

      const msg1 = spake1.start();
      const msg2 = spake2.start();

      // Messages should differ due to random scalar
      expect(msg1).not.toEqual(msg2);
    });
  });

  describe('finish', () => {
    it('should throw if not started', () => {
      const password = new TextEncoder().encode('test-password');
      const spake = new SPAKE2_Symmetric(password);
      const mockMsg = new Uint8Array(33);
      mockMsg[0] = 0x53;

      expect(() => spake.finish(mockMsg)).toThrow('SPAKE2 not started');
    });

    it('should throw on invalid side indicator', () => {
      const password = new TextEncoder().encode('test-password');
      const spake = new SPAKE2_Symmetric(password);
      spake.start();

      const invalidMsg = new Uint8Array(33);
      invalidMsg[0] = 0x00; // Wrong side indicator

      expect(() => spake.finish(invalidMsg)).toThrow('Invalid side indicator');
    });

    it('should set state to finished', () => {
      const password = new TextEncoder().encode('same-password');

      // Create two SPAKE2 instances to simulate both sides
      const alice = new SPAKE2_Symmetric(password);
      const bob = new SPAKE2_Symmetric(password);

      const aliceMsg = alice.start();
      const bobMsg = bob.start();

      alice.finish(bobMsg);

      expect(alice.state).toBe('finished');
    });

    it('should return 32-byte shared key', () => {
      const password = new TextEncoder().encode('same-password');

      const alice = new SPAKE2_Symmetric(password);
      const bob = new SPAKE2_Symmetric(password);

      const aliceMsg = alice.start();
      const bobMsg = bob.start();

      const aliceKey = alice.finish(bobMsg);

      expect(aliceKey).toBeInstanceOf(Uint8Array);
      expect(aliceKey.length).toBe(32);
    });

    it('should store inbound message', () => {
      const password = new TextEncoder().encode('same-password');

      const alice = new SPAKE2_Symmetric(password);
      const bob = new SPAKE2_Symmetric(password);

      const aliceMsg = alice.start();
      const bobMsg = bob.start();

      alice.finish(bobMsg);

      expect(alice.inbound).toBe(bobMsg);
    });
  });

  describe('key agreement', () => {
    it('should derive same key with same password', () => {
      const password = new TextEncoder().encode('test-password-123');

      const alice = new SPAKE2_Symmetric(password);
      const bob = new SPAKE2_Symmetric(password);

      const aliceMsg = alice.start();
      const bobMsg = bob.start();

      const aliceKey = alice.finish(bobMsg);
      const bobKey = bob.finish(aliceMsg);

      expect(aliceKey).toEqual(bobKey);
    });

    it('should derive same key with same password and idSymmetric', () => {
      const password = new TextEncoder().encode('test-password');
      const appId = new TextEncoder().encode('wh.tools/v1');

      const alice = new SPAKE2_Symmetric(password, appId);
      const bob = new SPAKE2_Symmetric(password, appId);

      const aliceMsg = alice.start();
      const bobMsg = bob.start();

      const aliceKey = alice.finish(bobMsg);
      const bobKey = bob.finish(aliceMsg);

      expect(aliceKey).toEqual(bobKey);
    });

    it('should derive different keys with different passwords', () => {
      const password1 = new TextEncoder().encode('password-one');
      const password2 = new TextEncoder().encode('password-two');

      const alice = new SPAKE2_Symmetric(password1);
      const bob = new SPAKE2_Symmetric(password2);

      const aliceMsg = alice.start();
      const bobMsg = bob.start();

      const aliceKey = alice.finish(bobMsg);
      const bobKey = bob.finish(aliceMsg);

      // Keys should be different
      expect(aliceKey).not.toEqual(bobKey);
    });

    it('should produce deterministic key from same exchange', () => {
      const password = new TextEncoder().encode('test-password');

      const alice = new SPAKE2_Symmetric(password);
      const bob = new SPAKE2_Symmetric(password);

      const aliceMsg = alice.start();
      const bobMsg = bob.start();

      const aliceKey1 = alice.finish(bobMsg);
      // Note: We can't call finish again, but the stored key should be same
      expect(alice.sharedKey).toEqual(aliceKey1);
    });
  });
});

describe('createSPAKE2', () => {
  it('should create SPAKE2_Symmetric instance', () => {
    const spake = createSPAKE2('test-password', 'wh.tools/v1');
    expect(spake).toBeInstanceOf(SPAKE2_Symmetric);
  });

  it('should use default appId', () => {
    const spake = createSPAKE2('test-password');
    expect(spake.idSymmetric).toEqual(new TextEncoder().encode('wh.tools/v1'));
  });

  it('should accept custom appId', () => {
    const spake = createSPAKE2('test-password', 'custom/app');
    expect(spake.idSymmetric).toEqual(new TextEncoder().encode('custom/app'));
  });

  it('should encode password as bytes', () => {
    const spake = createSPAKE2('test-password');
    expect(spake.password).toEqual(new TextEncoder().encode('test-password'));
  });

  it('should work with typical wormhole code', () => {
    const spake = createSPAKE2('7-guitar-sunset', 'wh.tools/v1');
    const msg = spake.start();

    expect(msg.length).toBe(33);
    expect(msg[0]).toBe(0x53);
  });
});

describe('SymmetricSPAKE2 (legacy)', () => {
  it('should create instance with appId and passwordHash', () => {
    const passwordHash = new Uint8Array(32);
    const spake = new SymmetricSPAKE2('wh.tools/v1', passwordHash, 'side-abc');

    expect(spake.side).toBe('side-abc');
  });

  it('should have async start method', async () => {
    const passwordHash = new TextEncoder().encode('test-password');
    const spake = new SymmetricSPAKE2('wh.tools/v1', passwordHash, 'side-abc');

    const msg = await spake.start();

    expect(msg).toBeInstanceOf(Uint8Array);
    expect(msg.length).toBe(33);
  });

  it('should have async finish method', async () => {
    const password = new TextEncoder().encode('test-password');

    const alice = new SymmetricSPAKE2('app', password, 'side-a');
    const bob = new SymmetricSPAKE2('app', password, 'side-b');

    const aliceMsg = await alice.start();
    const bobMsg = await bob.start();

    const aliceKey = await alice.finish(bobMsg);
    const bobKey = await bob.finish(aliceMsg);

    expect(aliceKey).toEqual(bobKey);
  });
});

describe('SPAKE2 (legacy)', () => {
  it('should create instance', () => {
    const spake = new SPAKE2('password', 'idA', 'idB', true);
    expect(spake).toBeDefined();
  });

  it('should have async start method', async () => {
    const spake = new SPAKE2('password', 'idA', 'idB', true);
    const msg = await spake.start();

    expect(msg).toBeInstanceOf(Uint8Array);
    expect(msg.length).toBe(33);
  });

  it('should complete key exchange', async () => {
    const alice = new SPAKE2('same-password', 'idA', 'idB', true);
    const bob = new SPAKE2('same-password', 'idA', 'idB', false);

    const aliceMsg = await alice.start();
    const bobMsg = await bob.start();

    const aliceKey = await alice.finish(bobMsg);
    const bobKey = await bob.finish(aliceMsg);

    // Keys should match with same password
    expect(aliceKey).toEqual(bobKey);
  });
});

describe('SPAKE2 message format', () => {
  it('should produce 33-byte message (1 side + 32 point)', () => {
    const spake = createSPAKE2('test');
    const msg = spake.start();

    expect(msg.length).toBe(33);
  });

  it('should have S (0x53) as first byte for symmetric mode', () => {
    const spake = createSPAKE2('test');
    const msg = spake.start();

    expect(msg[0]).toBe(0x53);
  });

  it('should contain valid Ed25519 point in bytes 1-32', () => {
    const spake = createSPAKE2('test');
    const msg = spake.start();

    // Point bytes (32 bytes after side indicator)
    const pointBytes = msg.slice(1);
    expect(pointBytes.length).toBe(32);

    // Point should not be all zeros
    const isAllZeros = pointBytes.every(b => b === 0);
    expect(isAllZeros).toBe(false);
  });
});

describe('SPAKE2 integration scenarios', () => {
  it('should work with wormhole code format', () => {
    // Typical wormhole codes
    const codes = [
      '7-guitar-sunset',
      '42-purple-dinosaur',
      '1-a-b',
      '999-supercalifragilisticexpialidocious-antidisestablishmentarianism'
    ];

    for (const code of codes) {
      const alice = createSPAKE2(code, 'wh.tools/v1');
      const bob = createSPAKE2(code, 'wh.tools/v1');

      const aliceMsg = alice.start();
      const bobMsg = bob.start();

      const aliceKey = alice.finish(bobMsg);
      const bobKey = bob.finish(aliceMsg);

      expect(aliceKey).toEqual(bobKey);
    }
  });

  it('should handle unicode passwords', () => {
    const password = '🔐密码пароль';

    const alice = createSPAKE2(password);
    const bob = createSPAKE2(password);

    const aliceMsg = alice.start();
    const bobMsg = bob.start();

    const aliceKey = alice.finish(bobMsg);
    const bobKey = bob.finish(aliceMsg);

    expect(aliceKey).toEqual(bobKey);
  });

  it('should handle empty password', () => {
    const alice = createSPAKE2('');
    const bob = createSPAKE2('');

    const aliceMsg = alice.start();
    const bobMsg = bob.start();

    const aliceKey = alice.finish(bobMsg);
    const bobKey = bob.finish(aliceMsg);

    expect(aliceKey).toEqual(bobKey);
  });

  it('should handle very long password', () => {
    const longPassword = 'a'.repeat(10000);

    const alice = createSPAKE2(longPassword);
    const bob = createSPAKE2(longPassword);

    const aliceMsg = alice.start();
    const bobMsg = bob.start();

    const aliceKey = alice.finish(bobMsg);
    const bobKey = bob.finish(aliceMsg);

    expect(aliceKey).toEqual(bobKey);
  });
});
