import 'react-native-get-random-values';

/**
 * WormholeService - Manages wormhole protocol connections
 *
 * This service handles peer-to-peer connections using wormhole codes.
 * Currently implements a placeholder for the full wormhole protocol,
 * which will be integrated from the browser-extension lib.
 */
class WormholeService {
  constructor() {
    this.connections = new Map();
    this.listeners = new Set();
  }

  /**
   * Subscribe to connection state changes
   * @param {Function} listener - Callback for state changes
   * @returns {Function} Unsubscribe function
   */
  subscribe(listener) {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  /**
   * Notify all listeners of state change
   */
  _notifyListeners() {
    const connections = this.getActiveConnections();
    this.listeners.forEach(listener => listener(connections));
  }

  /**
   * Generate a random wormhole code
   * @returns {string} A wormhole code in format "N-word-word"
   */
  generateCode() {
    const words = [
      'correct', 'horse', 'battery', 'staple', 'purple',
      'monkey', 'rainbow', 'castle', 'dragon', 'wizard',
      'crystal', 'thunder', 'glacier', 'phoenix', 'nebula'
    ];
    const num = Math.floor(Math.random() * 99) + 1;
    const word1 = words[Math.floor(Math.random() * words.length)];
    const word2 = words[Math.floor(Math.random() * words.length)];
    return `${num}-${word1}-${word2}`;
  }

  /**
   * Connect to a peer using a wormhole code
   * @param {string} code - The wormhole code to connect with
   * @returns {Promise<Object>} Connection object
   */
  async connect(code) {
    if (!code || typeof code !== 'string') {
      throw new Error('Invalid wormhole code');
    }

    const normalizedCode = code.trim().toLowerCase();

    if (this.connections.has(normalizedCode)) {
      const existing = this.connections.get(normalizedCode);
      if (existing.state === 'connected') {
        return existing;
      }
    }

    const connection = {
      id: Date.now().toString(36) + Math.random().toString(36).substr(2),
      code: normalizedCode,
      state: 'connecting',
      connectedAt: null,
      error: null,
    };

    this.connections.set(normalizedCode, connection);
    this._notifyListeners();

    try {
      // TODO: Implement real wormhole protocol handshake
      // This is where we'd integrate with the browser-extension's wormhole lib:
      // - SPAKE2 key exchange
      // - Relay server connection
      // - Peer discovery and connection

      // Simulate connection delay for now
      await new Promise(resolve => setTimeout(resolve, 1500));

      // Simulate occasional connection failures for testing
      if (Math.random() < 0.1) {
        throw new Error('Peer not found or connection timeout');
      }

      connection.state = 'connected';
      connection.connectedAt = Date.now();
      this._notifyListeners();

      return connection;
    } catch (error) {
      connection.state = 'failed';
      connection.error = error.message;
      this._notifyListeners();
      throw error;
    }
  }

  /**
   * Get a connection by code
   * @param {string} code - The wormhole code
   * @returns {Object|undefined} Connection object
   */
  getConnection(code) {
    return this.connections.get(code?.toLowerCase());
  }

  /**
   * Disconnect a connection by code
   * @param {string} code - The wormhole code to disconnect
   */
  disconnect(code) {
    const conn = this.connections.get(code?.toLowerCase());
    if (conn) {
      conn.state = 'closed';
      this.connections.delete(code.toLowerCase());
      this._notifyListeners();
    }
  }

  /**
   * Get all active (connected) connections
   * @returns {Array<Object>} Array of active connection objects
   */
  getActiveConnections() {
    return Array.from(this.connections.values())
      .filter(c => c.state === 'connected');
  }

  /**
   * Get all connections regardless of state
   * @returns {Array<Object>} Array of all connection objects
   */
  getAllConnections() {
    return Array.from(this.connections.values());
  }

  /**
   * Send data through a connection
   * @param {string} code - The connection code
   * @param {*} data - Data to send
   * @returns {Promise<void>}
   */
  async send(code, data) {
    const conn = this.getConnection(code);
    if (!conn || conn.state !== 'connected') {
      throw new Error('No active connection for this code');
    }

    // TODO: Implement actual data sending via wormhole protocol
    // This would encrypt and send data through the established channel
    console.log(`[Wormhole] Sending data on ${code}:`, data);

    await new Promise(resolve => setTimeout(resolve, 100));
  }

  /**
   * Fetch content through a wormhole connection
   * @param {string} code - The connection code
   * @param {string} path - The path/resource to fetch
   * @returns {Promise<Object>} Fetched content
   */
  async fetch(code, path) {
    const conn = this.getConnection(code);
    if (!conn || conn.state !== 'connected') {
      throw new Error('No active connection for this code');
    }

    // TODO: Implement actual content fetching
    // This would request content from the connected peer

    await new Promise(resolve => setTimeout(resolve, 500));

    return {
      path,
      content: `Content fetched from peer at ${path}`,
      timestamp: Date.now(),
    };
  }
}

// Singleton instance
export const wormholeService = new WormholeService();
