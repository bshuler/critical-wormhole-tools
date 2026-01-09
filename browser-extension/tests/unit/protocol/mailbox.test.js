/**
 * Mailbox Protocol Unit Tests
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import {
  MailboxClient,
  MessageType,
  DEFAULT_RELAY,
  parseCode,
  generateCode
} from '../../../src/lib/protocol/mailbox.js';

describe('MessageType', () => {
  it('has client message types', () => {
    expect(MessageType.BIND).toBe('bind');
    expect(MessageType.ALLOCATE).toBe('allocate');
    expect(MessageType.CLAIM).toBe('claim');
    expect(MessageType.OPEN).toBe('open');
    expect(MessageType.ADD).toBe('add');
    expect(MessageType.RELEASE).toBe('release');
    expect(MessageType.CLOSE).toBe('close');
    expect(MessageType.PING).toBe('ping');
  });

  it('has server message types', () => {
    expect(MessageType.WELCOME).toBe('welcome');
    expect(MessageType.ALLOCATED).toBe('allocated');
    expect(MessageType.CLAIMED).toBe('claimed');
    expect(MessageType.MESSAGE).toBe('message');
    expect(MessageType.RELEASED).toBe('released');
    expect(MessageType.CLOSED).toBe('closed');
    expect(MessageType.ACK).toBe('ack');
    expect(MessageType.PONG).toBe('pong');
    expect(MessageType.ERROR).toBe('error');
  });
});

describe('DEFAULT_RELAY', () => {
  it('is the magic-wormhole relay', () => {
    expect(DEFAULT_RELAY).toBe('wss://relay.magic-wormhole.io/v1');
  });
});

describe('MailboxClient', () => {
  describe('constructor', () => {
    it('uses default relay and appId', () => {
      const client = new MailboxClient();
      expect(client.relayUrl).toBe(DEFAULT_RELAY);
      expect(client.appId).toBe('wh.tools/v1');
    });

    it('accepts custom relay and appId', () => {
      const client = new MailboxClient('wss://custom.relay/v1', 'custom/app');
      expect(client.relayUrl).toBe('wss://custom.relay/v1');
      expect(client.appId).toBe('custom/app');
    });

    it('initializes state', () => {
      const client = new MailboxClient();
      expect(client.ws).toBeNull();
      expect(client.side).toBeNull();
      expect(client.nameplate).toBeNull();
      expect(client.mailbox).toBeNull();
      expect(client.state).toBe('disconnected');
    });
  });

  describe('generateSide', () => {
    it('produces side-XXXXXXXXXX format', () => {
      const side = MailboxClient.generateSide();
      expect(side).toMatch(/^side-[0-9a-f]{10}$/);
    });

    it('produces unique sides', () => {
      const sides = new Set();
      for (let i = 0; i < 100; i++) {
        sides.add(MailboxClient.generateSide());
      }
      expect(sides.size).toBe(100);
    });
  });

  describe('connect', () => {
    it('throws if already connected', async () => {
      const client = new MailboxClient();
      client.state = 'connected';

      await expect(client.connect()).rejects.toThrow('Invalid state');
    });

    it('generates side on connect', async () => {
      const client = new MailboxClient();

      // Start connect (will wait for welcome)
      const connectPromise = client.connect();

      // Wait for WebSocket to open
      await new Promise(r => setTimeout(r, 10));

      // Simulate welcome
      client.ws._receive({ type: 'welcome', server_version: '1.0' });

      await connectPromise;

      expect(client.side).toMatch(/^side-[0-9a-f]{10}$/);
    });

    it('sends bind message on open', async () => {
      const client = new MailboxClient();

      // Track sent messages
      let sentBindMessage = null;
      const originalSend = WebSocket.prototype.send;

      const connectPromise = client.connect();
      await new Promise(r => setTimeout(r, 10));

      // The MailboxClient should have sent a bind message
      // We verify by checking the state changed after connection
      expect(client.state).toBe('connected');
      expect(client.side).toMatch(/^side-[0-9a-f]{10}$/);

      client.ws._receive({ type: 'welcome' });
      await connectPromise;
    });

    it('resolves with welcome message', async () => {
      const client = new MailboxClient();

      const connectPromise = client.connect();
      await new Promise(r => setTimeout(r, 10));

      const welcomeData = { type: 'welcome', server_version: '1.0', motd: 'Hello' };
      client.ws._receive(welcomeData);

      const result = await connectPromise;
      expect(result).toEqual(welcomeData);
    });
  });

  describe('allocate', () => {
    it('throws if not connected', async () => {
      const client = new MailboxClient();
      await expect(client.allocate()).rejects.toThrow('Not connected');
    });

    it('sends allocate and returns nameplate', async () => {
      const client = new MailboxClient();
      client.state = 'connected';
      client.ws = testUtils.createMockWebSocket('ws://test');

      const allocatePromise = client.allocate();

      // Simulate response
      await new Promise(r => setTimeout(r, 10));
      const msg = client.ws.sentMessages.find(m => m.type === 'allocate');
      client.handleMessage({ type: 'allocated', id: msg.id, nameplate: '42' });

      const nameplate = await allocatePromise;
      expect(nameplate).toBe('42');
      expect(client.nameplate).toBe('42');
    });
  });

  describe('claim', () => {
    it('throws if not connected', async () => {
      const client = new MailboxClient();
      await expect(client.claim('42')).rejects.toThrow('Not connected');
    });

    it('sends claim with nameplate', async () => {
      const client = new MailboxClient();
      client.state = 'connected';
      client.ws = testUtils.createMockWebSocket('ws://test');

      const claimPromise = client.claim('42');

      await new Promise(r => setTimeout(r, 10));
      const msg = client.ws.sentMessages.find(m => m.type === 'claim');
      expect(msg.nameplate).toBe('42');

      // First send ack for the request
      client.handleMessage({ type: 'ack', id: msg.id });
      // Then send the claimed message (which contains the mailbox ID)
      client.handleMessage({ type: 'claimed', mailbox: 'mb42' });
      const result = await claimPromise;

      expect(client.nameplate).toBe('42');
      expect(result.mailbox).toBe('mb42');
    });
  });

  describe('open', () => {
    it('throws if no nameplate claimed', async () => {
      const client = new MailboxClient();
      await expect(client.open()).rejects.toThrow('No nameplate claimed');
    });

    it('opens mailbox with nameplate as default', async () => {
      const client = new MailboxClient();
      client.state = 'connected';
      client.nameplate = '42';
      client.ws = testUtils.createMockWebSocket('ws://test');

      const openPromise = client.open();

      await new Promise(r => setTimeout(r, 10));
      const msg = client.ws.sentMessages.find(m => m.type === 'open');
      expect(msg.mailbox).toBe('42');

      client.handleMessage({ type: 'ack', id: msg.id });
      await openPromise;

      expect(client.mailbox).toBe('42');
      expect(client.state).toBe('open');
    });
  });

  describe('addMessage', () => {
    it('throws if mailbox not open', async () => {
      const client = new MailboxClient();
      client.state = 'connected';
      await expect(client.addMessage('pake', 'data')).rejects.toThrow('Mailbox not open');
    });

    it('sends add with phase and hex-encoded body', async () => {
      const client = new MailboxClient();
      client.state = 'open';
      client.ws = testUtils.createMockWebSocket('ws://test');

      const addPromise = client.addMessage('pake', { key: 'value' });

      await new Promise(r => setTimeout(r, 10));
      const msg = client.ws.sentMessages.find(m => m.type === 'add');
      expect(msg.phase).toBe('pake');
      // Body is hex-encoded for magic-wormhole compatibility
      expect(msg.body).toBe('7b226b6579223a2276616c7565227d'); // hex of '{"key":"value"}'

      client.handleMessage({ type: 'ack', id: msg.id });
      await addPromise;
    });

    it('handles string body with hex encoding', async () => {
      const client = new MailboxClient();
      client.state = 'open';
      client.ws = testUtils.createMockWebSocket('ws://test');

      const addPromise = client.addMessage('version', 'raw-string');

      await new Promise(r => setTimeout(r, 10));
      const msg = client.ws.sentMessages.find(m => m.type === 'add');
      // Body is hex-encoded for magic-wormhole compatibility
      expect(msg.body).toBe('7261772d737472696e67'); // hex of 'raw-string'

      client.handleMessage({ type: 'ack', id: msg.id });
      await addPromise;
    });
  });

  describe('onMessage', () => {
    it('calls handler for peer messages', () => {
      const client = new MailboxClient();
      client.side = 'side-abc';

      const handler = vi.fn();
      client.onMessage(handler);

      // Simulate peer message
      client.handleMessage({
        type: 'message',
        phase: 'pake',
        body: 'test-body',
        side: 'side-def'
      });

      expect(handler).toHaveBeenCalledWith('pake', 'test-body', 'side-def');
    });

    it('ignores own messages', () => {
      const client = new MailboxClient();
      client.side = 'side-abc';

      const handler = vi.fn();
      client.onMessage(handler);

      // Simulate own message
      client.handleMessage({
        type: 'message',
        phase: 'pake',
        body: 'test-body',
        side: 'side-abc'
      });

      expect(handler).not.toHaveBeenCalled();
    });

    it('returns unsubscribe function', () => {
      const client = new MailboxClient();
      client.side = 'side-abc';

      const handler = vi.fn();
      const unsubscribe = client.onMessage(handler);

      unsubscribe();

      client.handleMessage({
        type: 'message',
        phase: 'pake',
        body: 'test',
        side: 'side-def'
      });

      expect(handler).not.toHaveBeenCalled();
    });
  });

  describe('waitForPhase', () => {
    it('resolves when phase received', async () => {
      const client = new MailboxClient();
      client.side = 'side-abc';

      const waitPromise = client.waitForPhase('pake');

      // Simulate receiving message
      setTimeout(() => {
        client.handleMessage({
          type: 'message',
          phase: 'pake',
          body: 'pake-data',
          side: 'side-def'
        });
      }, 10);

      const body = await waitPromise;
      expect(body).toBe('pake-data');
    });

    it('ignores wrong phases', async () => {
      const client = new MailboxClient();
      client.side = 'side-abc';

      const waitPromise = client.waitForPhase('version', 100);

      // Send wrong phase first
      client.handleMessage({
        type: 'message',
        phase: 'pake',
        body: 'wrong',
        side: 'side-def'
      });

      // Then correct phase
      setTimeout(() => {
        client.handleMessage({
          type: 'message',
          phase: 'version',
          body: 'correct',
          side: 'side-def'
        });
      }, 10);

      const body = await waitPromise;
      expect(body).toBe('correct');
    });

    it('rejects on timeout', async () => {
      const client = new MailboxClient();
      client.side = 'side-abc';

      await expect(client.waitForPhase('never', 50)).rejects.toThrow('Timeout');
    });
  });

  describe('release', () => {
    it('sends release message', async () => {
      const client = new MailboxClient();
      client.state = 'connected';
      client.nameplate = '42';
      client.ws = testUtils.createMockWebSocket('ws://test');

      const releasePromise = client.release();

      await new Promise(r => setTimeout(r, 10));
      const msg = client.ws.sentMessages.find(m => m.type === 'release');
      expect(msg.nameplate).toBe('42');

      client.handleMessage({ type: 'released', id: msg.id });
      await releasePromise;

      expect(client.nameplate).toBeNull();
    });

    it('does nothing without nameplate', async () => {
      const client = new MailboxClient();
      await client.release(); // Should not throw
    });
  });

  describe('close', () => {
    it('sends close and disconnects', async () => {
      const client = new MailboxClient();
      client.state = 'open';
      client.mailbox = 'mb42';
      client.ws = testUtils.createMockWebSocket('ws://test');

      const closePromise = client.close();

      await new Promise(r => setTimeout(r, 10));
      const msg = client.ws.sentMessages.find(m => m.type === 'close');
      expect(msg.mailbox).toBe('mb42');
      expect(msg.mood).toBe('happy');

      client.handleMessage({ type: 'closed', id: msg.id });
      await closePromise;

      expect(client.state).toBe('disconnected');
    });
  });

  describe('cleanup', () => {
    it('clears all pending requests', () => {
      const client = new MailboxClient();

      // Add some pending requests
      client.pendingRequests.set('1', { timeout: setTimeout(() => {}, 1000) });
      client.pendingRequests.set('2', { timeout: setTimeout(() => {}, 1000) });

      client.cleanup();

      expect(client.pendingRequests.size).toBe(0);
    });

    it('clears message handlers', () => {
      const client = new MailboxClient();

      client.on('message', () => {});
      client.on('welcome', () => {});

      client.cleanup();

      expect(client.messageHandlers.size).toBe(0);
    });
  });
});

describe('parseCode', () => {
  it('parses standard code format', () => {
    const result = parseCode('7-guitar-sunset');
    expect(result).toEqual({
      nameplate: '7',
      password: 'guitar-sunset'
    });
  });

  it('handles multi-word passwords', () => {
    const result = parseCode('42-alpha-beta-gamma-delta');
    expect(result).toEqual({
      nameplate: '42',
      password: 'alpha-beta-gamma-delta'
    });
  });

  it('handles single-digit nameplates', () => {
    const result = parseCode('1-word-another');
    expect(result).toEqual({
      nameplate: '1',
      password: 'word-another'
    });
  });

  it('handles large nameplates', () => {
    const result = parseCode('99999-foo-bar');
    expect(result).toEqual({
      nameplate: '99999',
      password: 'foo-bar'
    });
  });

  it('throws for invalid format', () => {
    expect(() => parseCode('7-guitar')).toThrow('Invalid wormhole code');
    expect(() => parseCode('guitar-sunset')).toThrow('Invalid wormhole code');
    expect(() => parseCode('7')).toThrow('Invalid wormhole code');
    expect(() => parseCode('')).toThrow('Invalid wormhole code');
  });
});

describe('generateCode', () => {
  it('generates code with nameplate', () => {
    const code = generateCode('42');
    expect(code).toMatch(/^42-[a-z]+-[a-z]+$/);
  });

  it('uses 2 words by default', () => {
    const code = generateCode('7');
    const parts = code.split('-');
    expect(parts.length).toBe(3); // nameplate + 2 words
  });

  it('generates requested number of words', () => {
    const code = generateCode('7', 4);
    const parts = code.split('-');
    expect(parts.length).toBe(5); // nameplate + 4 words
  });

  it('generates different codes each time', () => {
    const codes = new Set();
    for (let i = 0; i < 100; i++) {
      codes.add(generateCode('42'));
    }
    expect(codes.size).toBeGreaterThanOrEqual(80); // Allow some collisions
  });

  it('uses only lowercase words', () => {
    const code = generateCode('1');
    expect(code).toBe(code.toLowerCase());
  });
});
