/**
 * Wormhole Protocol Flow Functional Tests
 *
 * Tests the complete wormhole handshake flow using mock transports.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { MailboxClient, parseCode, generateCode } from '../../src/lib/protocol/mailbox.js';
import { Identity } from '../../src/lib/wns/identity.js';
import { Advertisement, verifyAdvertisement } from '../../src/lib/wns/advertisement.js';
import { hkdf, deriveMasterKey } from '../../src/lib/crypto/hkdf.js';
import { encrypt, decrypt } from '../../src/lib/crypto/nacl.js';
import { sha256 } from '../../src/lib/crypto/hash.js';
import { randomBytes } from '../../src/lib/crypto/index.js';

/**
 * Mock mailbox server for testing
 */
class MockMailboxServer {
  constructor() {
    this.clients = new Map();
    this.nameplates = new Map();
    this.mailboxes = new Map();
    this.nextNameplate = 1;
  }

  addClient(client) {
    const id = `client-${Math.random().toString(36).slice(2)}`;
    this.clients.set(id, {
      client,
      side: null,
      mailbox: null
    });
    return id;
  }

  handleMessage(clientId, msg) {
    const clientState = this.clients.get(clientId);
    if (!clientState) return null;

    switch (msg.type) {
      case 'bind':
        clientState.side = msg.side;
        return { type: 'welcome', server_version: '1.0' };

      case 'allocate': {
        const nameplate = String(this.nextNameplate++);
        this.nameplates.set(nameplate, { claimed: [clientState.side] });
        return { type: 'allocated', id: msg.id, nameplate };
      }

      case 'claim': {
        const np = this.nameplates.get(msg.nameplate) || { claimed: [] };
        if (!np.claimed.includes(clientState.side)) {
          np.claimed.push(clientState.side);
        }
        this.nameplates.set(msg.nameplate, np);
        // Send ACK first (with id), then send claimed message (without id)
        // This matches real wormhole relay behavior
        setTimeout(() => {
          clientState.client.handleMessage({
            type: 'claimed',
            mailbox: `mb-${msg.nameplate}`
          });
        }, 2);
        return { type: 'ack', id: msg.id };
      }

      case 'open': {
        clientState.mailbox = msg.mailbox;
        if (!this.mailboxes.has(msg.mailbox)) {
          this.mailboxes.set(msg.mailbox, { messages: [], clients: [] });
        }
        this.mailboxes.get(msg.mailbox).clients.push(clientId);

        // Send any pending messages
        const mb = this.mailboxes.get(msg.mailbox);
        const pending = mb.messages.filter(m => m.side !== clientState.side);
        for (const pendingMsg of pending) {
          clientState.client.handleMessage({
            type: 'message',
            phase: pendingMsg.phase,
            body: pendingMsg.body,
            side: pendingMsg.side
          });
        }

        return { type: 'ack', id: msg.id };
      }

      case 'add': {
        const mb = this.mailboxes.get(clientState.mailbox);
        if (!mb) return { type: 'error', id: msg.id, error: 'Mailbox not open' };

        const message = {
          phase: msg.phase,
          body: msg.body,
          side: clientState.side
        };
        mb.messages.push(message);

        // Deliver to other clients in mailbox ASYNCHRONOUSLY
        // This allows waitForPhase handlers to be set up before delivery
        setTimeout(() => {
          for (const otherId of mb.clients) {
            if (otherId !== clientId) {
              const otherState = this.clients.get(otherId);
              if (otherState && otherState.client) {
                otherState.client.handleMessage({
                  type: 'message',
                  ...message
                });
              }
            }
          }
        }, 5);

        return { type: 'ack', id: msg.id };
      }

      case 'release':
        return { type: 'released', id: msg.id };

      case 'close':
        clientState.mailbox = null;
        return { type: 'closed', id: msg.id };

      default:
        return { type: 'error', id: msg.id, error: `Unknown message type: ${msg.type}` };
    }
  }
}

/**
 * Create a mock MailboxClient connected to mock server
 */
function createMockClient(server) {
  const client = new MailboxClient('mock://server', 'test/v1');

  const clientId = server.addClient(client);

  // Override send to route through mock server
  client.send = (msg) => {
    const response = server.handleMessage(clientId, msg);
    if (response) {
      // Deliver response async to allow handlers to be set up
      setTimeout(() => {
        client.handleMessage(response);
      }, 1);
    }
  };

  // Simulate WebSocket connection
  client.state = 'connected';
  client.side = MailboxClient.generateSide();
  client.ws = {
    readyState: 1, // OPEN
    close: () => {}
  };

  // Bind to server
  server.handleMessage(clientId, { type: 'bind', side: client.side });

  return client;
}

describe('Wormhole Code Exchange', () => {
  let server;

  beforeEach(() => {
    server = new MockMailboxServer();
  });

  it('two clients can exchange messages via mailbox', async () => {
    const sender = createMockClient(server);
    const receiver = createMockClient(server);

    // Sender allocates
    const nameplate = await sender.allocate();
    const code = generateCode(nameplate);
    const { password } = parseCode(code);

    // Receiver claims
    const { nameplate: rNameplate } = parseCode(code);
    await receiver.claim(rNameplate);

    // Both open mailbox
    await sender.open();
    await receiver.open();

    // Set up message handlers
    const receiverMessages = [];
    receiver.onMessage((phase, body) => {
      receiverMessages.push({ phase, body });
    });

    const senderMessages = [];
    sender.onMessage((phase, body) => {
      senderMessages.push({ phase, body });
    });

    // Exchange messages
    await sender.addMessage('test', 'hello from sender');
    await receiver.addMessage('test', 'hello from receiver');

    // Wait for message delivery
    await new Promise(r => setTimeout(r, 50));

    expect(receiverMessages).toContainEqual({
      phase: 'test',
      body: 'hello from sender'
    });
    expect(senderMessages).toContainEqual({
      phase: 'test',
      body: 'hello from receiver'
    });
  });

  it('PAKE handshake flow works', async () => {
    const sender = createMockClient(server);
    const receiver = createMockClient(server);

    // Allocate and generate code
    const nameplate = await sender.allocate();
    const code = generateCode(nameplate);
    const { password } = parseCode(code);

    // Receiver claims
    const parsed = parseCode(code);
    await receiver.claim(parsed.nameplate);

    // Both open
    await sender.open();
    await receiver.open();

    // Simulate PAKE exchange
    const senderPakeMsg = randomBytes(32);
    const receiverPakeMsg = randomBytes(32);

    // Exchange PAKE messages
    const senderReceivePromise = sender.waitForPhase('pake', 1000);
    const receiverReceivePromise = receiver.waitForPhase('pake', 1000);

    await sender.addMessage('pake', btoa(String.fromCharCode(...senderPakeMsg)));
    await receiver.addMessage('pake', btoa(String.fromCharCode(...receiverPakeMsg)));

    const receivedBySender = await senderReceivePromise;
    const receivedByReceiver = await receiverReceivePromise;

    expect(receivedBySender).toBe(btoa(String.fromCharCode(...receiverPakeMsg)));
    expect(receivedByReceiver).toBe(btoa(String.fromCharCode(...senderPakeMsg)));
  });
});

describe('WNS Identity Flow', () => {
  it('creates and serializes identity', async () => {
    const identity = await Identity.generate({ name: 'Test Server' });

    expect(identity.address).toMatch(/^[a-z2-7]{26}$/);

    const json = identity.toJSON();
    const restored = await Identity.fromJSON(json);

    expect(restored.address).toBe(identity.address);
    expect(restored.metadata.name).toBe('Test Server');
  });

  it('creates and verifies advertisement', async () => {
    const identity = await Identity.generate();

    const ad = await Advertisement.create({
      identity,
      code: '7-guitar-sunset',
      services: ['ssh', 'http'],
      ttlSeconds: 300
    });

    expect(ad.address).toBe(identity.address);
    expect(ad.code).toBe('7-guitar-sunset');
    expect(ad.services).toEqual(['ssh', 'http']);

    // Verify signature
    const isValid = await ad.verify();
    expect(isValid).toBe(true);
  });

  it('detects tampered advertisement', async () => {
    const identity = await Identity.generate();

    const ad = await Advertisement.create({
      identity,
      code: '7-guitar-sunset'
    });

    // Tamper with code
    ad.code = 'tampered-code';

    const isValid = await ad.verify();
    expect(isValid).toBe(false);
  });

  it('verifyAdvertisement validates correctly', async () => {
    const identity = await Identity.generate();

    const ad = await Advertisement.create({
      identity,
      code: '7-guitar-sunset'
    });

    const result = await verifyAdvertisement(ad.toJSON());

    expect(result.valid).toBe(true);
    expect(result.code).toBe('7-guitar-sunset');
  });

  it('verifyAdvertisement rejects expired', async () => {
    const identity = await Identity.generate();

    // Create expired advertisement
    const ad = new Advertisement({
      version: 1,
      address: identity.address,
      publicKey: btoa(String.fromCharCode(...identity.publicKey)),
      code: '7-guitar-sunset',
      timestamp: new Date(Date.now() - 600000).toISOString(),
      expires: new Date(Date.now() - 1000).toISOString(),
      signature: 'fake'
    });

    const result = await verifyAdvertisement(ad.toJSON());

    expect(result.valid).toBe(false);
    expect(result.error).toBe('Advertisement expired');
  });
});

describe('Key Derivation Flow', () => {
  it('derives consistent master key for both sides', async () => {
    const sharedSecret = randomBytes(32);
    const sideA = 'side-alice';
    const sideB = 'side-bob';

    const keyFromAlice = await deriveMasterKey(sharedSecret, sideA, sideB);
    const keyFromBob = await deriveMasterKey(sharedSecret, sideB, sideA);

    expect(keyFromAlice).toEqual(keyFromBob);
  });

  it('encrypted message can be decrypted with same key', async () => {
    const key = randomBytes(32);
    const message = new TextEncoder().encode('Hello, Wormhole!');

    const encrypted = await encrypt(message, key);
    const decrypted = await decrypt(encrypted, key);

    expect(decrypted).toEqual(message);
  });

  it('encrypted message fails with wrong key', async () => {
    const key1 = randomBytes(32);
    const key2 = randomBytes(32);
    const message = new TextEncoder().encode('Secret message');

    const encrypted = await encrypt(message, key1);
    const decrypted = await decrypt(encrypted, key2);

    expect(decrypted).toBeNull();
  });
});

describe('Full Wormhole Handshake Simulation', () => {
  let server;

  beforeEach(() => {
    server = new MockMailboxServer();
  });

  it('simulates complete handshake with encryption', async () => {
    const sender = createMockClient(server);
    const receiver = createMockClient(server);

    // 1. Sender allocates nameplate
    const nameplate = await sender.allocate();
    const code = generateCode(nameplate, 2);
    const { password } = parseCode(code);

    // 2. Receiver claims nameplate
    const parsed = parseCode(code);
    await receiver.claim(parsed.nameplate);

    // 3. Both open mailbox
    await sender.open();
    await receiver.open();

    // 4. Exchange PAKE messages (simulated)
    // In real impl, this would be SPAKE2
    const senderPake = randomBytes(32);
    const receiverPake = randomBytes(32);

    const senderPakePromise = sender.waitForPhase('pake', 1000);
    const receiverPakePromise = receiver.waitForPhase('pake', 1000);

    await sender.addMessage('pake', bytesToBase64(senderPake));
    await receiver.addMessage('pake', bytesToBase64(receiverPake));

    await senderPakePromise;
    await receiverPakePromise;

    // 5. Derive shared secret (simulated - in real impl this comes from SPAKE2)
    // Both would derive same key from SPAKE2 output
    const passwordHash = await sha256(password);
    const sharedSecret = await hkdf('spake2', passwordHash, 'simulated', 32);

    // 6. Derive encryption key
    const senderKey = await deriveMasterKey(sharedSecret, sender.side, receiver.side);
    const receiverKey = await deriveMasterKey(sharedSecret, receiver.side, sender.side);

    // Keys should match (order independent)
    expect(senderKey).toEqual(receiverKey);

    // 7. Exchange version info (encrypted)
    const senderVersion = JSON.stringify({ app: 'wh.tools', version: '0.4.0' });
    const receiverVersion = JSON.stringify({ app: 'wh.tools', version: '0.4.0' });

    const senderVersionPromise = sender.waitForPhase('version', 1000);
    const receiverVersionPromise = receiver.waitForPhase('version', 1000);

    const senderVersionEnc = await encrypt(
      new TextEncoder().encode(senderVersion),
      senderKey
    );
    const receiverVersionEnc = await encrypt(
      new TextEncoder().encode(receiverVersion),
      receiverKey
    );

    await sender.addMessage('version', bytesToBase64(senderVersionEnc));
    await receiver.addMessage('version', bytesToBase64(receiverVersionEnc));

    const receivedSenderVersion = await receiverVersionPromise;
    const receivedReceiverVersion = await senderVersionPromise;

    // Decrypt and verify
    const decSenderVersion = await decrypt(
      base64ToBytes(receivedSenderVersion),
      receiverKey
    );
    const decReceiverVersion = await decrypt(
      base64ToBytes(receivedReceiverVersion),
      senderKey
    );

    expect(new TextDecoder().decode(decSenderVersion)).toBe(senderVersion);
    expect(new TextDecoder().decode(decReceiverVersion)).toBe(receiverVersion);

    // 8. Cleanup
    await sender.close();
    await receiver.close();
  });
});

// Helper functions
function bytesToBase64(bytes) {
  return btoa(String.fromCharCode(...bytes));
}

function base64ToBytes(base64) {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes;
}
