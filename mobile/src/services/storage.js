import AsyncStorage from '@react-native-async-storage/async-storage';

/**
 * StorageService - AsyncStorage adapter for persistent data
 *
 * Provides a simplified interface for storing and retrieving
 * data that persists across app sessions.
 */
class StorageService {
  constructor(prefix = '@wormhole') {
    this.prefix = prefix;
  }

  /**
   * Generate a prefixed key
   * @param {string} key - The storage key
   * @returns {string} Prefixed key
   */
  _key(key) {
    return `${this.prefix}:${key}`;
  }

  /**
   * Store a value
   * @param {string} key - Storage key
   * @param {*} value - Value to store (will be JSON serialized)
   * @returns {Promise<void>}
   */
  async set(key, value) {
    try {
      const jsonValue = JSON.stringify(value);
      await AsyncStorage.setItem(this._key(key), jsonValue);
    } catch (error) {
      console.error('[Storage] Error setting value:', error);
      throw error;
    }
  }

  /**
   * Retrieve a value
   * @param {string} key - Storage key
   * @param {*} defaultValue - Default value if key doesn't exist
   * @returns {Promise<*>} Stored value or default
   */
  async get(key, defaultValue = null) {
    try {
      const jsonValue = await AsyncStorage.getItem(this._key(key));
      return jsonValue != null ? JSON.parse(jsonValue) : defaultValue;
    } catch (error) {
      console.error('[Storage] Error getting value:', error);
      return defaultValue;
    }
  }

  /**
   * Remove a value
   * @param {string} key - Storage key
   * @returns {Promise<void>}
   */
  async remove(key) {
    try {
      await AsyncStorage.removeItem(this._key(key));
    } catch (error) {
      console.error('[Storage] Error removing value:', error);
      throw error;
    }
  }

  /**
   * Get all keys with our prefix
   * @returns {Promise<string[]>} Array of keys (without prefix)
   */
  async getAllKeys() {
    try {
      const allKeys = await AsyncStorage.getAllKeys();
      return allKeys
        .filter(k => k.startsWith(this.prefix + ':'))
        .map(k => k.slice(this.prefix.length + 1));
    } catch (error) {
      console.error('[Storage] Error getting keys:', error);
      return [];
    }
  }

  /**
   * Clear all data with our prefix
   * @returns {Promise<void>}
   */
  async clear() {
    try {
      const keys = await this.getAllKeys();
      const prefixedKeys = keys.map(k => this._key(k));
      await AsyncStorage.multiRemove(prefixedKeys);
    } catch (error) {
      console.error('[Storage] Error clearing storage:', error);
      throw error;
    }
  }

  /**
   * Store connection history
   * @param {Object} connection - Connection object to store
   * @returns {Promise<void>}
   */
  async addConnectionHistory(connection) {
    const history = await this.get('connectionHistory', []);
    history.unshift({
      code: connection.code,
      connectedAt: connection.connectedAt,
      timestamp: Date.now(),
    });
    // Keep only last 50 connections
    await this.set('connectionHistory', history.slice(0, 50));
  }

  /**
   * Get connection history
   * @returns {Promise<Array>} Array of past connections
   */
  async getConnectionHistory() {
    return this.get('connectionHistory', []);
  }

  /**
   * Store an identity
   * @param {Object} identity - Identity object
   * @returns {Promise<void>}
   */
  async saveIdentity(identity) {
    const identities = await this.get('identities', []);
    const existingIndex = identities.findIndex(i => i.id === identity.id);
    if (existingIndex >= 0) {
      identities[existingIndex] = identity;
    } else {
      identities.push(identity);
    }
    await this.set('identities', identities);
  }

  /**
   * Get all identities
   * @returns {Promise<Array>} Array of identities
   */
  async getIdentities() {
    return this.get('identities', []);
  }

  /**
   * Remove an identity
   * @param {string} id - Identity ID
   * @returns {Promise<void>}
   */
  async removeIdentity(id) {
    const identities = await this.get('identities', []);
    await this.set('identities', identities.filter(i => i.id !== id));
  }

  /**
   * Get app settings
   * @returns {Promise<Object>} Settings object
   */
  async getSettings() {
    return this.get('settings', {
      relayServer: 'wss://relay.wormhole.app',
      autoConnect: false,
      notificationsEnabled: true,
      theme: 'system',
    });
  }

  /**
   * Update app settings
   * @param {Object} updates - Settings to update
   * @returns {Promise<void>}
   */
  async updateSettings(updates) {
    const current = await this.getSettings();
    await this.set('settings', { ...current, ...updates });
  }
}

// Singleton instance
export const storageService = new StorageService();
