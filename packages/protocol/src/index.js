/**
 * High-Level Wormhole API
 *
 * Provides a unified interface for wormhole connections.
 * Handles mailbox communication, key exchange, and transit setup.
 */

import { MailboxClient, parseCode, generateCode } from '@wormhole-tools/mailbox';
import { TransitHandler, negotiateTransit } from './transit.js';
import { DilationManager, DilationState, createEndpoints } from '@wormhole-tools/dilation';
import { createSPAKE2 } from '@wormhole-tools/spake2';
import { deriveMasterKey, deriveTransitKey, deriveSessionKey, derivePhaseKey } from './hkdf.js';
import { encrypt, decrypt } from './nacl.js';
import { sha256 } from './hash.js';
import { randomBytes } from './crypto.js';

/**
 * Wormhole connection states
 */
export const WormholeState = {
  DISCONNECTED: 'disconnected',
  ALLOCATING: 'allocating',
  WAITING: 'waiting',
  EXCHANGING: 'exchanging',
  CONNECTED: 'connected',
  DILATING: 'dilating',
  DILATED: 'dilated',
  FAILED: 'failed',
  CLOSED: 'closed'
};

/**
 * Wormhole connection
 *
 * Main class for establishing and using wormhole connections.
 */
export class Wormhole {
  /**
   * @param {object} options
   * @param {string} options.relayUrl - Mailbox relay URL
   * @param {string} options.appId - Application identifier
   */
  constructor(options = {}) {
    this.relayUrl = options.relayUrl;
    this.appId = options.appId || 'wh.tools/v1';

    this.mailbox = null;
    this.transit = null;
    this.spake = null;

    this.code = null;
    this.sharedKey = null;
    this.sessionKey = null;
    this.transitKey = null;
    this.verifier = null;

    this.isInitiator = false;
    this.state = WormholeState.DISCONNECTED;

    // Phase counters for application messages (like Python magic-wormhole)
    this.nextTxPhase = 0;
    this.nextRxPhase = 0;

    // Dilation support
    this.dilation = null;
    this.dilationEndpoints = null;
    this._isDilated = false;

    // Event handlers
    this.onStateChange = null;
    this.onMessage = null;
    this.onError = null;
    this.onDilationStateChange = null;
  }

  /**
   * Create a new wormhole code (sender side)
   * @param {number} numWords - Number of words in code
   * @returns {Promise<string>} - The wormhole code
   */
  async allocate(numWords = 2) {
    this.isInitiator = true;
    this.setState(WormholeState.ALLOCATING);

    try {
      // Connect to mailbox
      this.mailbox = new MailboxClient(this.relayUrl, this.appId);
      await this.mailbox.connect();

      // Allocate nameplate
      const nameplate = await this.mailbox.allocate();
      this.code = generateCode(nameplate, numWords);

      this.setState(WormholeState.WAITING);
      return this.code;
    } catch (error) {
      this.setState(WormholeState.FAILED);
      throw error;
    }
  }

  /**
   * Connect using an existing code (receiver side)
   * @param {string} code - Wormhole code
   * @returns {Promise<void>}
   */
  async connect(code) {
    this.code = code;
    this.isInitiator = false;
    this.setState(WormholeState.WAITING);

    try {
      // Parse code
      const { nameplate, password } = parseCode(code);

      // Connect to mailbox
      this.mailbox = new MailboxClient(this.relayUrl, this.appId);
      await this.mailbox.connect();

      // Claim nameplate and get mailbox ID
      const claimResponse = await this.mailbox.claim(nameplate);
      console.log('[Wormhole] Claim response:', claimResponse);
      await this.mailbox.open(claimResponse.mailbox);

      // Perform key exchange - magic-wormhole uses the FULL code (including nameplate) as SPAKE2 password
      await this.performKeyExchange(code);
    } catch (error) {
      this.setState(WormholeState.FAILED);
      throw error;
    }
  }

  /**
   * Wait for peer to connect and complete handshake (sender side)
   * @returns {Promise<void>}
   */
  async waitForPeer() {
    if (!this.isInitiator) {
      throw new Error('waitForPeer() is only for initiator');
    }

    try {
      // Open mailbox
      await this.mailbox.open();

      // Perform key exchange - magic-wormhole uses the FULL code (including nameplate) as SPAKE2 password
      await this.performKeyExchange(this.code);
    } catch (error) {
      this.setState(WormholeState.FAILED);
      throw error;
    }
  }

  /**
   * Perform SPAKE2 key exchange
   * @param {string} password
   */
  async performKeyExchange(password) {
    this.setState(WormholeState.EXCHANGING);

    // Initialize SPAKE2 with password and app ID
    // createSPAKE2 handles password encoding internally
    this.spake = createSPAKE2(password, this.appId);

    // Generate SPAKE2 message (33 bytes: 'S' + 32-byte Ed25519 point)
    const pakeMsg = this.spake.start();
    console.log('[Wormhole] PAKE message length:', pakeMsg.length, 'first byte:', pakeMsg[0].toString(16));

    // Start listening for peer's PAKE BEFORE we send ours
    // (the peer may have already sent theirs)
    const peerPakePromise = this.mailbox.waitForPhaseWithSide('pake');

    // Send as hex-encoded JSON (magic-wormhole format)
    const pakeBody = JSON.stringify({ pake_v1: bytesToHex(pakeMsg) });
    console.log('[Wormhole] Sending PAKE body:', pakeBody);
    await this.mailbox.addMessage('pake', pakeBody);

    // Now wait for peer's PAKE message
    const { body: peerPakeBody, side: peerSide } = await peerPakePromise;
    this.peerSide = peerSide;  // Store peer's side for phase key derivation
    console.log('[Wormhole] Received peer PAKE body:', peerPakeBody, 'from side:', peerSide);
    const peerPakeJson = JSON.parse(peerPakeBody);
    const peerPake = hexToBytes(peerPakeJson.pake_v1);
    console.log('[Wormhole] Peer PAKE length:', peerPake.length, 'first byte:', peerPake[0].toString(16));

    // Complete SPAKE2 and derive shared key
    const sharedSecret = this.spake.finish(peerPake);
    console.log('[Wormhole] SPAKE2 shared secret derived');

    // Use the SPAKE2 shared key directly (it's already hashed)
    this.sharedKey = sharedSecret;
    console.log('[Wormhole] Shared key:', bytesToHex(this.sharedKey));

    // Derive session and transit keys
    this.sessionKey = await deriveSessionKey(this.sharedKey);
    console.log('[Wormhole] Session key:', bytesToHex(this.sessionKey));
    this.transitKey = await deriveTransitKey(this.sharedKey);

    // Generate verifier for display
    this.verifier = await this.generateVerifier();

    // Exchange version info
    await this.exchangeVersionInfo();

    this.setState(WormholeState.CONNECTED);
  }

  /**
   * Exchange encrypted version information
   * Uses phase-specific keys derived from SPAKE2 shared key and sender's side ID
   */
  async exchangeVersionInfo() {
    const versionInfo = {
      app: this.appId,
      implementation: 'wormhole-browser',
      version: '0.4.0',
      capabilities: ['transit-webrtc', 'dilation']
    };

    // Get our side ID for key derivation
    const ourSide = this.mailbox.side;
    console.log('[Wormhole] Our side:', ourSide, 'Peer side:', this.peerSide);

    // Derive phase-specific keys
    // Each side encrypts with a key derived from their own side ID
    const ourVersionKey = await derivePhaseKey(this.sharedKey, ourSide, 'version');
    const peerVersionKey = await derivePhaseKey(this.sharedKey, this.peerSide, 'version');
    console.log('[Wormhole] Our version key:', bytesToHex(ourVersionKey));
    console.log('[Wormhole] Peer version key:', bytesToHex(peerVersionKey));

    // Start waiting for peer's version BEFORE sending ours
    const peerVersionPromise = this.mailbox.waitForPhase('version');

    // Encrypt and send our version with OUR phase key
    const versionJson = JSON.stringify(versionInfo);
    const encrypted = await encrypt(
      new TextEncoder().encode(versionJson),
      ourVersionKey
    );
    console.log('[Wormhole] Sending version, encrypted length:', encrypted.length);
    await this.mailbox.addMessage('version', encrypted);

    // Receive and decrypt peer's version using PEER's phase key
    const peerVersionBody = await peerVersionPromise;
    console.log('[Wormhole] Received peer version, type:', typeof peerVersionBody,
      peerVersionBody instanceof Uint8Array ? `${peerVersionBody.length} bytes` : peerVersionBody.substring?.(0, 50));

    // Handle both cases: Uint8Array (new) or string that needs decoding
    let peerVersionEnc;
    if (peerVersionBody instanceof Uint8Array) {
      peerVersionEnc = peerVersionBody;
    } else if (typeof peerVersionBody === 'string') {
      // Fallback: might be hex string if decode failed differently
      peerVersionEnc = hexToBytes(peerVersionBody);
    } else {
      throw new Error('Unexpected version body type');
    }

    const peerVersionBytes = await decrypt(peerVersionEnc, peerVersionKey);

    if (!peerVersionBytes) {
      throw new Error('Failed to decrypt peer version info');
    }

    const peerVersion = JSON.parse(new TextDecoder().decode(peerVersionBytes));
    console.log('[Wormhole] Peer version:', peerVersion);
    this.peerVersion = peerVersion;
  }

  /**
   * Generate a human-readable verifier
   * @returns {Promise<string>}
   */
  async generateVerifier() {
    const hash = await sha256(this.sharedKey);
    const bytes = hash.slice(0, 8);
    return Array.from(bytes)
      .map(b => b.toString(16).padStart(2, '0'))
      .join(':');
  }

  /**
   * Establish transit connection for data transfer
   * @returns {Promise<void>}
   */
  async establishTransit() {
    this.transit = new TransitHandler({
      transitKey: this.transitKey
    });

    // Set up handlers
    this.transit.onMessage = (data) => {
      if (this.onMessage) {
        this.onMessage(data);
      }
    };

    this.transit.onError = (error) => {
      if (this.onError) {
        this.onError(error);
      }
    };

    this.transit.onClose = () => {
      // Transit closed, but mailbox may still be open
    };

    // Negotiate transit via mailbox
    await negotiateTransit(this.mailbox, this.isInitiator, this.transit);

    // Wait for connection to be established
    await this.waitForTransitConnection();
  }

  /**
   * Wait for transit connection to be ready
   */
  waitForTransitConnection() {
    return new Promise((resolve, reject) => {
      if (this.transit.isConnected) {
        resolve();
        return;
      }

      const checkInterval = setInterval(() => {
        if (this.transit.isConnected) {
          clearInterval(checkInterval);
          resolve();
        }
      }, 100);

      // Timeout after 30 seconds
      setTimeout(() => {
        clearInterval(checkInterval);
        if (!this.transit.isConnected) {
          reject(new Error('Transit connection timeout'));
        }
      }, 30000);
    });
  }

  /**
   * Send data to peer
   * Uses numeric phases ("0", "1", "2", ...) matching Python magic-wormhole
   * @param {Uint8Array|string} data
   */
  async send(data) {
    if (this.transit && this.transit.isConnected) {
      await this.transit.send(data);
    } else {
      // Send via mailbox if no transit
      if (typeof data === 'string') {
        data = new TextEncoder().encode(data);
      }
      // Use numeric phase like Python magic-wormhole
      const phase = String(this.nextTxPhase);
      this.nextTxPhase++;

      // Use phase-specific key, encrypted with OUR side
      const dataKey = await derivePhaseKey(this.sharedKey, this.mailbox.side, phase);
      const encrypted = await encrypt(data, dataKey);
      console.log('[Wormhole] Sending message on phase:', phase, 'length:', data.length);
      // Send encrypted bytes directly - mailbox will hex-encode
      await this.mailbox.addMessage(phase, encrypted);
    }
  }

  /**
   * Receive data (for mailbox-based transfer)
   * Uses numeric phases ("0", "1", "2", ...) matching Python magic-wormhole
   * @param {number} timeout
   * @returns {Promise<Uint8Array>}
   */
  async receive(timeout = 60000) {
    // Expect numeric phase like Python magic-wormhole
    const expectedPhase = String(this.nextRxPhase);
    this.nextRxPhase++;

    console.log('[Wormhole] Waiting for message on phase:', expectedPhase);
    const dataBody = await this.mailbox.waitForPhase(expectedPhase, timeout);
    console.log('[Wormhole] Received message on phase:', expectedPhase);

    // Body will be Uint8Array for binary data
    let encrypted;
    if (dataBody instanceof Uint8Array) {
      encrypted = dataBody;
    } else if (typeof dataBody === 'string') {
      encrypted = hexToBytes(dataBody);
    } else {
      throw new Error('Unexpected data body type');
    }
    // Use phase-specific key, decrypting with PEER's side
    const dataKey = await derivePhaseKey(this.sharedKey, this.peerSide, expectedPhase);
    return await decrypt(encrypted, dataKey);
  }

  /**
   * Send a file to peer
   * @param {File|Blob} file
   * @param {function} onProgress - Progress callback (received, total)
   */
  async sendFile(file, onProgress = null) {
    // Read file as ArrayBuffer
    const buffer = await file.arrayBuffer();
    const data = new Uint8Array(buffer);

    // Send file metadata
    const metadata = {
      type: 'file',
      name: file.name,
      size: data.length,
      mimeType: file.type || 'application/octet-stream'
    };
    await this.send(JSON.stringify(metadata));

    // Send file data in chunks
    const chunkSize = 64 * 1024; // 64KB chunks
    let sent = 0;

    while (sent < data.length) {
      const end = Math.min(sent + chunkSize, data.length);
      const chunk = data.slice(sent, end);
      await this.send(chunk);

      sent = end;
      if (onProgress) {
        onProgress(sent, data.length);
      }
    }

    // Send completion marker
    await this.send(JSON.stringify({ type: 'complete' }));
  }

  /**
   * Dilate the wormhole for streaming communication
   *
   * Dilation transforms a simple message-exchange wormhole into a full
   * streaming connection with multiple independent subchannels.
   *
   * @returns {Promise<{connect: function, listen: function}>} Endpoints for subchannels
   */
  async dilate() {
    if (this.state !== WormholeState.CONNECTED) {
      throw new Error('Wormhole must be connected before dilation');
    }

    if (this._isDilated) {
      return this.dilationEndpoints;
    }

    console.log('[Wormhole] Starting dilation');
    this.setState(WormholeState.DILATING);

    try {
      // Create dilation manager
      this.dilation = new DilationManager({
        mailbox: this.mailbox,
        sharedKey: this.sharedKey,
        mailboxSide: this.mailbox.side,
        peerSide: this.peerSide
      });

      // Set up event handlers
      this.dilation.onStateChange = (newState, oldState) => {
        console.log('[Wormhole] Dilation state:', oldState, '->', newState);
        if (this.onDilationStateChange) {
          this.onDilationStateChange(newState, oldState);
        }

        if (newState === DilationState.CONNECTED) {
          this._isDilated = true;
          this.setState(WormholeState.DILATED);
        } else if (newState === DilationState.FAILED) {
          this.setState(WormholeState.CONNECTED);  // Fall back to undilated
        }
      };

      this.dilation.onError = (error) => {
        console.error('[Wormhole] Dilation error:', error);
        if (this.onError) {
          this.onError(error);
        }
      };

      // Start dilation
      await this.dilation.dilate();

      // Create endpoints interface
      this.dilationEndpoints = createEndpoints(this.dilation);

      console.log('[Wormhole] Dilation complete');
      return this.dilationEndpoints;
    } catch (error) {
      console.error('[Wormhole] Dilation failed:', error);
      this.setState(WormholeState.CONNECTED);  // Fall back to undilated
      throw error;
    }
  }

  /**
   * Check if wormhole is dilated
   * @returns {boolean}
   */
  get isDilated() {
    return this._isDilated && this.dilation && this.dilation.isConnected;
  }

  /**
   * Get a connector for opening subchannels to peer
   * @param {string} protocol - Protocol name (e.g., 'wh-http')
   * @returns {SubchannelConnector}
   */
  connectorFor(protocol) {
    if (!this.isDilated) {
      throw new Error('Wormhole must be dilated first');
    }
    return this.dilationEndpoints.connect(protocol);
  }

  /**
   * Get a listener for accepting subchannel connections
   * @param {string} protocol - Protocol name (e.g., 'wh-http')
   * @returns {SubchannelListener}
   */
  listenerFor(protocol) {
    if (!this.isDilated) {
      throw new Error('Wormhole must be dilated first');
    }
    return this.dilationEndpoints.listen(protocol);
  }

  /**
   * Close the connection
   */
  async close() {
    // Close dilation first
    if (this.dilation) {
      await this.dilation.close();
      this.dilation = null;
      this.dilationEndpoints = null;
      this._isDilated = false;
    }

    if (this.transit) {
      this.transit.close();
      this.transit = null;
    }

    if (this.mailbox) {
      await this.mailbox.close();
      this.mailbox = null;
    }

    this.setState(WormholeState.CLOSED);
  }

  /**
   * Update state and notify
   * @param {string} newState
   */
  setState(newState) {
    const oldState = this.state;
    this.state = newState;

    if (this.onStateChange && oldState !== newState) {
      this.onStateChange(newState, oldState);
    }
  }
}

/**
 * Create a wormhole and allocate a code (sender)
 * @param {object} options
 * @returns {Promise<Wormhole>}
 */
export async function createWormhole(options = {}) {
  const wormhole = new Wormhole(options);
  await wormhole.allocate(options.numWords || 2);
  return wormhole;
}

/**
 * Connect to a wormhole using a code (receiver)
 * @param {string} code
 * @param {object} options
 * @returns {Promise<Wormhole>}
 */
export async function connectWormhole(code, options = {}) {
  const wormhole = new Wormhole(options);
  await wormhole.connect(code);
  return wormhole;
}

// Helper functions

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
