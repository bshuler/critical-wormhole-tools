/**
 * Mailbox WebSocket Client
 *
 * Handles communication with the wormhole mailbox relay server.
 * The mailbox provides a rendezvous point for two parties to
 * exchange SPAKE2 messages and connection hints.
 */

/**
 * Mailbox message types
 */
export const MessageType = {
  // Client → Server
  BIND: 'bind',
  ALLOCATE: 'allocate',
  CLAIM: 'claim',
  OPEN: 'open',
  ADD: 'add',
  RELEASE: 'release',
  CLOSE: 'close',
  PING: 'ping',

  // Server → Client
  WELCOME: 'welcome',
  ALLOCATED: 'allocated',
  CLAIMED: 'claimed',
  MESSAGE: 'message',
  RELEASED: 'released',
  CLOSED: 'closed',
  ACK: 'ack',
  PONG: 'pong',
  ERROR: 'error'
};

/**
 * Default relay servers
 */
export const DEFAULT_RELAY = 'wss://relay.magic-wormhole.io/v1';

/**
 * Mailbox client for wormhole rendezvous
 */
export class MailboxClient {
  /**
   * @param {string} relayUrl - WebSocket relay URL
   * @param {string} appId - Application identifier
   */
  constructor(relayUrl = DEFAULT_RELAY, appId = 'wh.tools/v1') {
    this.relayUrl = relayUrl;
    this.appId = appId;
    this.ws = null;
    this.side = null;
    this.nameplate = null;
    this.mailbox = null;

    // Message handling
    this.messageId = 0;
    this.pendingRequests = new Map();
    this.messageHandlers = new Map();

    // State
    this.state = 'disconnected';
    this.welcomeInfo = null;
  }

  /**
   * Generate a unique side identifier
   * @returns {string}
   */
  static generateSide() {
    const bytes = new Uint8Array(5);
    crypto.getRandomValues(bytes);
    const hex = Array.from(bytes)
      .map(b => b.toString(16).padStart(2, '0'))
      .join('');
    return `side-${hex}`;
  }

  /**
   * Connect to the relay server
   * @returns {Promise<object>} - Welcome message
   */
  async connect() {
    if (this.state !== 'disconnected') {
      throw new Error(`Invalid state: ${this.state}`);
    }

    this.side = MailboxClient.generateSide();
    this.state = 'connecting';
    console.log('[Mailbox] Our side:', this.side);
    console.log('[Mailbox] Connecting to:', this.relayUrl);

    return new Promise((resolve, reject) => {
      try {
        this.ws = new WebSocket(this.relayUrl);
        console.log('[Mailbox] WebSocket created');
      } catch (e) {
        console.error('[Mailbox] WebSocket creation failed:', e);
        reject(e);
        return;
      }

      this.ws.onopen = () => {
        console.log('[Mailbox] WebSocket opened');
        this.state = 'connected';
        // Send bind message
        this.send({ type: MessageType.BIND, appid: this.appId, side: this.side });
      };

      this.ws.onmessage = (event) => {
        console.log('[Mailbox] RAW message:', event.data);
        const msg = JSON.parse(event.data);
        console.log('[Mailbox] Message received: type=' + msg.type + ' side=' + msg.side + ' phase=' + msg.phase + ' id=' + msg.id);
        this.handleMessage(msg);
      };

      this.ws.onerror = (error) => {
        console.error('[Mailbox] WebSocket error:', error);
        this.state = 'error';
        reject(new Error('WebSocket error'));
      };

      this.ws.onclose = (event) => {
        console.log('[Mailbox] WebSocket closed:', event.code, event.reason);
        this.state = 'disconnected';
        this.cleanup();
      };

      // Wait for welcome message
      this.once(MessageType.WELCOME, (msg) => {
        console.log('[Mailbox] Welcome received');
        this.welcomeInfo = msg;
        resolve(msg);
      });

      this.once(MessageType.ERROR, (msg) => {
        reject(new Error(msg.error || 'Unknown error'));
      });
    });
  }

  /**
   * Allocate a new nameplate
   * @returns {Promise<string>} - Allocated nameplate
   */
  async allocate() {
    if (this.state !== 'connected') {
      throw new Error('Not connected');
    }

    const response = await this.request({ type: MessageType.ALLOCATE });
    this.nameplate = response.nameplate;
    return this.nameplate;
  }

  /**
   * Claim an existing nameplate
   * @param {string} nameplate
   * @returns {Promise<object>} - The claimed response with mailbox ID
   */
  async claim(nameplate) {
    if (this.state !== 'connected') {
      throw new Error('Not connected');
    }

    this.nameplate = nameplate;

    // Wait for the 'claimed' response which contains the mailbox ID
    const claimedPromise = new Promise((resolve) => {
      const handler = (msg) => {
        if (msg.type === MessageType.CLAIMED) {
          this.off(MessageType.CLAIMED, handler);
          resolve(msg);
        }
      };
      this.on(MessageType.CLAIMED, handler);
    });

    // Send the claim request
    await this.request({ type: MessageType.CLAIM, nameplate });

    // Wait for and return the claimed response
    return claimedPromise;
  }

  /**
   * Open the mailbox for message exchange
   * @param {string} mailbox - Mailbox identifier (usually same as nameplate)
   * @returns {Promise<void>}
   */
  async open(mailbox = null) {
    if (!this.nameplate) {
      throw new Error('No nameplate claimed');
    }

    this.mailbox = mailbox || this.nameplate;
    await this.request({ type: MessageType.OPEN, mailbox: this.mailbox });
    this.state = 'open';
  }

  /**
   * Add a message to the mailbox
   * @param {string} phase - Message phase (e.g., 'pake', 'version')
   * @param {string|object|Uint8Array} body - Message body (will be hex-encoded)
   * @returns {Promise<void>}
   */
  async addMessage(phase, body) {
    if (this.state !== 'open') {
      throw new Error('Mailbox not open');
    }

    let bodyHex;
    if (body instanceof Uint8Array) {
      // Binary data - hex-encode directly (for encrypted messages)
      bodyHex = bytesToHex(body);
      console.log('[Mailbox] addMessage phase:', phase, 'body: binary', body.length, 'bytes');
    } else {
      const bodyStr = typeof body === 'string' ? body : JSON.stringify(body);
      // Magic-wormhole expects body to be hex-encoded
      bodyHex = stringToHex(bodyStr);
      console.log('[Mailbox] addMessage phase:', phase, 'body (before hex):', bodyStr);
    }

    await this.request({
      type: MessageType.ADD,
      phase,
      body: bodyHex
    });
  }

  /**
   * Register a handler for incoming messages
   * @param {function} handler - Called with (phase, body, side)
   *   - body is a string for text messages (like PAKE JSON)
   *   - body is a Uint8Array for binary messages (like encrypted data)
   * @returns {function} - Unsubscribe function
   */
  onMessage(handler) {
    const wrappedHandler = (msg) => {
      console.log('[Mailbox] onMessage handler called:', msg.type, msg.phase, 'from side:', msg.side, 'our side:', this.side);

      // Ignore our own messages
      if (msg.side === this.side) {
        console.log('[Mailbox] Ignoring our own message (msg.side === this.side)');
        return;
      }
      console.log('[Mailbox] Processing peer message (different sides)');

      // Decode hex-encoded body from magic-wormhole protocol
      let body = msg.body;
      if (typeof body === 'string' && /^[0-9a-fA-F]+$/.test(body)) {
        try {
          // Try to decode as UTF-8 text (for PAKE, etc.)
          body = hexToString(body);
          console.log('[Mailbox] Decoded hex body as text:', body.substring(0, 100));
        } catch {
          // Binary data (encrypted messages) - return raw bytes
          body = hexToBytes(body);
          console.log('[Mailbox] Decoded hex body as binary:', body.length, 'bytes');
        }
      }
      console.log('[Mailbox] Dispatching phase:', msg.phase, 'to handler');
      handler(msg.phase, body, msg.side);
    };

    this.on(MessageType.MESSAGE, wrappedHandler);
    console.log('[Mailbox] onMessage handler registered for MESSAGE type');

    return () => {
      this.off(MessageType.MESSAGE, wrappedHandler);
    };
  }

  /**
   * Wait for a specific phase message from peer
   * @param {string} phase
   * @param {number} timeout - Timeout in ms
   * @returns {Promise<string>} - Message body
   */
  async waitForPhase(phase, timeout = 60000) {
    const result = await this.waitForPhaseWithSide(phase, timeout);
    return result.body;
  }

  /**
   * Wait for a specific phase message from peer, returning both body and sender's side
   * @param {string} phase
   * @param {number} timeout - Timeout in ms
   * @returns {Promise<{body: string|Uint8Array, side: string}>}
   */
  async waitForPhaseWithSide(phase, timeout = 60000) {
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        unsubscribe();
        reject(new Error(`Timeout waiting for phase: ${phase}`));
      }, timeout);

      const unsubscribe = this.onMessage((msgPhase, body, side) => {
        if (msgPhase === phase) {
          clearTimeout(timer);
          unsubscribe();
          resolve({ body, side });
        }
      });
    });
  }

  /**
   * Release the nameplate
   * @returns {Promise<void>}
   */
  async release() {
    if (!this.nameplate) return;

    await this.request({ type: MessageType.RELEASE, nameplate: this.nameplate });
    this.nameplate = null;
  }

  /**
   * Close the mailbox and disconnect
   * @returns {Promise<void>}
   */
  async close() {
    if (this.mailbox) {
      try {
        await this.request({ type: MessageType.CLOSE, mailbox: this.mailbox, mood: 'happy' });
      } catch {
        // Ignore close errors
      }
    }

    if (this.ws) {
      this.ws.close();
    }

    this.cleanup();
  }

  /**
   * Send a message to the server
   * @param {object} msg
   */
  send(msg) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      throw new Error('WebSocket not connected');
    }

    const json = JSON.stringify(msg);
    console.log('[Mailbox] SENDING:', json);
    this.ws.send(json);
  }

  /**
   * Send a request and wait for response
   * @param {object} msg
   * @returns {Promise<object>}
   */
  async request(msg) {
    const id = String(++this.messageId);
    msg.id = id;

    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        this.pendingRequests.delete(id);
        reject(new Error('Request timeout'));
      }, 30000);

      this.pendingRequests.set(id, { resolve, reject, timeout });
      this.send(msg);
    });
  }

  /**
   * Handle incoming message
   * @param {object} msg
   */
  handleMessage(msg) {
    // Handle response to pending request
    if (msg.id && this.pendingRequests.has(msg.id)) {
      const { resolve, reject, timeout } = this.pendingRequests.get(msg.id);
      this.pendingRequests.delete(msg.id);
      clearTimeout(timeout);

      if (msg.type === MessageType.ERROR) {
        reject(new Error(msg.error || 'Request failed'));
      } else {
        resolve(msg);
      }
      return;
    }

    // Dispatch to handlers
    const handlers = this.messageHandlers.get(msg.type) || [];
    console.log('[Mailbox] Dispatching type=' + msg.type + ' to ' + handlers.length + ' handlers');
    for (const handler of handlers) {
      try {
        handler(msg);
      } catch (e) {
        console.error('Handler error:', e);
      }
    }
  }

  /**
   * Register a message handler
   * @param {string} type
   * @param {function} handler
   */
  on(type, handler) {
    if (!this.messageHandlers.has(type)) {
      this.messageHandlers.set(type, []);
    }
    this.messageHandlers.get(type).push(handler);
  }

  /**
   * Register a one-time message handler
   * @param {string} type
   * @param {function} handler
   */
  once(type, handler) {
    const wrapper = (msg) => {
      this.off(type, wrapper);
      handler(msg);
    };
    this.on(type, wrapper);
  }

  /**
   * Remove a message handler
   * @param {string} type
   * @param {function} handler
   */
  off(type, handler) {
    const handlers = this.messageHandlers.get(type);
    if (handlers) {
      const index = handlers.indexOf(handler);
      if (index !== -1) {
        handlers.splice(index, 1);
      }
    }
  }

  /**
   * Clean up resources
   */
  cleanup() {
    for (const { timeout } of this.pendingRequests.values()) {
      clearTimeout(timeout);
    }
    this.pendingRequests.clear();
    this.messageHandlers.clear();
    this.ws = null;
    this.state = 'disconnected';
  }
}

// Hex encoding helpers for magic-wormhole protocol

function stringToHex(str) {
  return Array.from(new TextEncoder().encode(str))
    .map(b => b.toString(16).padStart(2, '0'))
    .join('');
}

function bytesToHex(bytes) {
  return Array.from(bytes)
    .map(b => b.toString(16).padStart(2, '0'))
    .join('');
}

function hexToBytes(hex) {
  const bytes = new Uint8Array(hex.length / 2);
  for (let i = 0; i < hex.length; i += 2) {
    bytes[i / 2] = parseInt(hex.substr(i, 2), 16);
  }
  return bytes;
}

function hexToString(hex) {
  const bytes = hexToBytes(hex);
  // Use fatal mode to throw for invalid UTF-8 (like encrypted binary data)
  return new TextDecoder('utf-8', { fatal: true }).decode(bytes);
}

/**
 * Parse a wormhole code into nameplate and password
 * @param {string} code - e.g., "7-guitar-sunset"
 * @returns {{nameplate: string, password: string}}
 */
export function parseCode(code) {
  const parts = code.split('-');
  if (parts.length < 3) {
    throw new Error('Invalid wormhole code format');
  }

  const nameplate = parts[0];
  const password = parts.slice(1).join('-');

  return { nameplate, password };
}

/**
 * Generate a wormhole code
 * @param {string} nameplate
 * @param {number} numWords - Number of words (default: 2)
 * @returns {string}
 */
export function generateCode(nameplate, numWords = 2) {
  // Simple word list for development
  // In production, use the full 256-word list from WORDLIST.md
  const words = [
    'alpha', 'beta', 'gamma', 'delta', 'echo', 'foxtrot', 'golf', 'hotel',
    'india', 'juliet', 'kilo', 'lima', 'mike', 'november', 'oscar', 'papa',
    'quebec', 'romeo', 'sierra', 'tango', 'uniform', 'victor', 'whiskey', 'xray',
    'yankee', 'zulu', 'guitar', 'sunset', 'castle', 'thunder', 'river', 'mountain'
  ];

  const selected = [];
  for (let i = 0; i < numWords; i++) {
    const index = Math.floor(Math.random() * words.length);
    selected.push(words[index]);
  }

  return `${nameplate}-${selected.join('-')}`;
}
