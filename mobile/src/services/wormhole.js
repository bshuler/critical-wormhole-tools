/**
 * WormholeService - Manages wormhole protocol connections
 *
 * This service integrates the magic wormhole protocol for React Native.
 * Uses the browser extension's implementation adapted for mobile.
 */

// TODO: Switch to @wormhole-tools/protocol once packages are published
// For now, import from browser extension
import { Wormhole, WormholeState } from '../../../browser-extension/src/lib/protocol/wormhole.js';

const RELAY_URL = 'wss://relay.magic-wormhole.io/v1';
const APP_ID = 'wh.tools/v1';

class WormholeService {
  constructor() {
    this.connections = new Map();
    this.subscribers = new Set();
  }

  /**
   * Subscribe to connection state changes
   * @param {Function} callback - Callback for state changes
   * @returns {Function} Unsubscribe function
   */
  subscribe(callback) {
    this.subscribers.add(callback);
    return () => this.subscribers.delete(callback);
  }

  /**
   * Notify all subscribers of events
   * @param {Object} event - Event object
   */
  _notifySubscribers(event) {
    this.subscribers.forEach(callback => callback(event));
  }

  /**
   * Allocate a new wormhole code (sender side)
   * @param {number} numWords - Number of words in code (default: 3)
   * @returns {Promise<Object>} Result with code
   */
  async allocate(numWords = 3) {
    try {
      const wormhole = new Wormhole({
        relayUrl: RELAY_URL,
        appId: APP_ID,
      });

      // Set up event handlers
      this._setupWormholeHandlers(wormhole, null);

      const code = await wormhole.allocate(numWords);
      this.connections.set(code, wormhole);

      this._notifySubscribers({
        type: 'allocated',
        code,
      });

      return { success: true, code };
    } catch (error) {
      this._notifySubscribers({
        type: 'error',
        error: error.message,
      });
      return { success: false, error: error.message };
    }
  }

  /**
   * Connect to a peer using a wormhole code (receiver side)
   * @param {string} code - The wormhole code
   * @returns {Promise<Object>} Result with verifier
   */
  async connect(code) {
    try {
      const wormhole = new Wormhole({
        relayUrl: RELAY_URL,
        appId: APP_ID,
      });

      // Set up event handlers
      this._setupWormholeHandlers(wormhole, code);

      await wormhole.connect(code);

      // Enable WebRTC dilation for streaming protocols
      try {
        await wormhole.dilate();
      } catch (dilationError) {
        console.warn('[WormholeService] Dilation failed, continuing without it:', dilationError);
      }

      this.connections.set(code, wormhole);

      this._notifySubscribers({
        type: 'connected',
        code,
        verifier: wormhole.verifier,
      });

      return { success: true, verifier: wormhole.verifier };
    } catch (error) {
      this._notifySubscribers({
        type: 'error',
        code,
        error: error.message,
      });
      return { success: false, error: error.message };
    }
  }

  /**
   * Set up event handlers for a wormhole instance
   * @param {Wormhole} wormhole - The wormhole instance
   * @param {string} code - The wormhole code (may be null for allocate)
   */
  _setupWormholeHandlers(wormhole, code) {
    wormhole.onStateChange = (newState, oldState) => {
      this._notifySubscribers({
        type: 'stateChange',
        code,
        state: newState,
        previousState: oldState,
      });
    };

    wormhole.onError = (error) => {
      this._notifySubscribers({
        type: 'error',
        code,
        error: error.message,
      });
    };

    wormhole.onDilationStateChange = (newState, oldState) => {
      this._notifySubscribers({
        type: 'dilationStateChange',
        code,
        state: newState,
        previousState: oldState,
      });
    };
  }

  /**
   * Wait for peer to connect (after allocate)
   * @param {string} code - The allocated wormhole code
   * @returns {Promise<Object>} Result with verifier
   */
  async waitForPeer(code) {
    const wormhole = this.connections.get(code);
    if (!wormhole) {
      throw new Error('No wormhole allocated with this code');
    }

    try {
      await wormhole.waitForPeer();

      // Enable WebRTC dilation for streaming protocols
      try {
        await wormhole.dilate();
      } catch (dilationError) {
        console.warn('[WormholeService] Dilation failed, continuing without it:', dilationError);
      }

      this._notifySubscribers({
        type: 'connected',
        code,
        verifier: wormhole.verifier,
      });

      return { success: true, verifier: wormhole.verifier };
    } catch (error) {
      this._notifySubscribers({
        type: 'error',
        code,
        error: error.message,
      });
      return { success: false, error: error.message };
    }
  }

  /**
   * Disconnect a wormhole connection
   * @param {string} code - The wormhole code
   */
  async disconnect(code) {
    const wormhole = this.connections.get(code);
    if (wormhole) {
      await wormhole.close();
      this.connections.delete(code);
      this._notifySubscribers({
        type: 'disconnected',
        code,
      });
    }
  }

  /**
   * Send data through a wormhole connection
   * @param {string} code - The wormhole code
   * @param {Uint8Array|string} data - Data to send
   */
  async send(code, data) {
    const wormhole = this.connections.get(code);
    if (!wormhole) {
      throw new Error('Not connected');
    }
    await wormhole.send(data);
  }

  /**
   * Receive data from a wormhole connection
   * @param {string} code - The wormhole code
   * @param {number} timeout - Timeout in milliseconds
   * @returns {Promise<Uint8Array>} Received data
   */
  async receive(code, timeout = 30000) {
    const wormhole = this.connections.get(code);
    if (!wormhole) {
      throw new Error('Not connected');
    }
    return await wormhole.receive(timeout);
  }

  /**
   * Get a wormhole connection instance
   * @param {string} code - The wormhole code
   * @returns {Wormhole|undefined} Wormhole instance
   */
  getConnection(code) {
    return this.connections.get(code);
  }

  /**
   * Check if a wormhole is connected
   * @param {string} code - The wormhole code
   * @returns {boolean} True if connected
   */
  isConnected(code) {
    const wormhole = this.connections.get(code);
    return wormhole && (wormhole.state === WormholeState.CONNECTED || wormhole.state === WormholeState.DILATED);
  }

  /**
   * Check if a wormhole is dilated
   * @param {string} code - The wormhole code
   * @returns {boolean} True if dilated
   */
  isDilated(code) {
    const wormhole = this.connections.get(code);
    return wormhole && wormhole.state === WormholeState.DILATED;
  }

  /**
   * Get all active connections
   * @returns {Array<Object>} Array of connection info objects
   */
  getActiveConnections() {
    const active = [];
    for (const [code, wormhole] of this.connections.entries()) {
      if (this.isConnected(code)) {
        active.push({
          code,
          state: wormhole.state,
          verifier: wormhole.verifier,
          isDilated: wormhole.isDilated,
        });
      }
    }
    return active;
  }
}

// Singleton export
export const wormholeService = new WormholeService();
export default wormholeService;

// Re-export WormholeState for convenience
export { WormholeState };
