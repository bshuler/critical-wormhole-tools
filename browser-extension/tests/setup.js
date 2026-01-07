/**
 * Vitest Test Setup
 *
 * This file runs before all tests to set up the test environment.
 */

import { vi } from 'vitest';
import * as ed from '@noble/ed25519';

// Mock crypto.getRandomValues for Node.js environment
if (typeof globalThis.crypto === 'undefined') {
  const { webcrypto } = await import('crypto');
  globalThis.crypto = webcrypto;
}

// Make @noble/ed25519 available globally for tests
globalThis.nobleEd25519 = ed;

// Mock Chrome extension APIs
globalThis.chrome = {
  runtime: {
    sendMessage: vi.fn(),
    onMessage: {
      addListener: vi.fn(),
      removeListener: vi.fn()
    },
    getURL: vi.fn((path) => `chrome-extension://test-id/${path}`),
    id: 'test-extension-id'
  },
  storage: {
    local: {
      get: vi.fn().mockResolvedValue({}),
      set: vi.fn().mockResolvedValue(undefined),
      remove: vi.fn().mockResolvedValue(undefined)
    },
    sync: {
      get: vi.fn().mockResolvedValue({}),
      set: vi.fn().mockResolvedValue(undefined)
    }
  },
  tabs: {
    query: vi.fn().mockResolvedValue([]),
    create: vi.fn().mockResolvedValue({ id: 1 }),
    update: vi.fn().mockResolvedValue({})
  },
  webRequest: {
    onBeforeRequest: {
      addListener: vi.fn()
    }
  },
  action: {
    setBadgeText: vi.fn(),
    setBadgeBackgroundColor: vi.fn()
  }
};

// Mock WebSocket for tests
class MockWebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  constructor(url) {
    this.url = url;
    this.readyState = MockWebSocket.CONNECTING;
    this.onopen = null;
    this.onmessage = null;
    this.onerror = null;
    this.onclose = null;

    // Auto-connect after a tick
    setTimeout(() => {
      this.readyState = MockWebSocket.OPEN;
      if (this.onopen) this.onopen({ type: 'open' });
    }, 0);
  }

  send(data) {
    if (this.readyState !== MockWebSocket.OPEN) {
      throw new Error('WebSocket not open');
    }
    // Override in tests to capture sent messages
    if (this._onSend) this._onSend(data);
  }

  close() {
    this.readyState = MockWebSocket.CLOSED;
    if (this.onclose) this.onclose({ type: 'close' });
  }

  // Test helper: simulate receiving a message
  _receive(data) {
    if (this.onmessage) {
      this.onmessage({ data: JSON.stringify(data) });
    }
  }
}

globalThis.WebSocket = MockWebSocket;

// Mock fetch for HTTP tests
globalThis.fetch = vi.fn();

// Test utilities
globalThis.testUtils = {
  /**
   * Create a mock WebSocket that captures messages
   */
  createMockWebSocket(url) {
    const ws = {
      url,
      readyState: 1, // WebSocket.OPEN
      sentMessages: [],
      send(data) {
        this.sentMessages.push(typeof data === 'string' ? JSON.parse(data) : data);
      },
      close() {
        this.readyState = 3;
      }
    };
    return ws;
  },

  /**
   * Wait for a condition to be true
   */
  async waitFor(condition, timeout = 5000, interval = 50) {
    const start = Date.now();
    while (!condition()) {
      if (Date.now() - start > timeout) {
        throw new Error('Timeout waiting for condition');
      }
      await new Promise(r => setTimeout(r, interval));
    }
  },

  /**
   * Hex string to Uint8Array
   */
  hexToBytes(hex) {
    const bytes = new Uint8Array(hex.length / 2);
    for (let i = 0; i < hex.length; i += 2) {
      bytes[i / 2] = parseInt(hex.slice(i, i + 2), 16);
    }
    return bytes;
  },

  /**
   * Uint8Array to hex string
   */
  bytesToHex(bytes) {
    return Array.from(bytes)
      .map(b => b.toString(16).padStart(2, '0'))
      .join('');
  }
};
