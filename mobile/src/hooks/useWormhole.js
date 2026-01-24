import { useState, useEffect, useCallback } from 'react';
import { wormholeService } from '../services/wormhole';
import { storageService } from '../services/storage';

/**
 * useWormhole - React hook for wormhole connection state management
 *
 * Provides reactive state and actions for managing wormhole connections.
 */
export function useWormhole() {
  const [connections, setConnections] = useState([]);
  const [connecting, setConnecting] = useState(false);
  const [error, setError] = useState(null);

  // Subscribe to wormhole service updates
  useEffect(() => {
    const unsubscribe = wormholeService.subscribe((activeConnections) => {
      setConnections(activeConnections);
    });

    // Initialize with current connections
    setConnections(wormholeService.getActiveConnections());

    return unsubscribe;
  }, []);

  /**
   * Connect to a peer using a wormhole code
   */
  const connect = useCallback(async (code) => {
    setConnecting(true);
    setError(null);

    try {
      const connection = await wormholeService.connect(code);

      // Store in connection history
      await storageService.addConnectionHistory(connection);

      return connection;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setConnecting(false);
    }
  }, []);

  /**
   * Disconnect from a peer
   */
  const disconnect = useCallback((code) => {
    wormholeService.disconnect(code);
  }, []);

  /**
   * Generate a new wormhole code
   */
  const generateCode = useCallback(() => {
    return wormholeService.generateCode();
  }, []);

  /**
   * Clear the current error
   */
  const clearError = useCallback(() => {
    setError(null);
  }, []);

  /**
   * Get a specific connection by code
   */
  const getConnection = useCallback((code) => {
    return wormholeService.getConnection(code);
  }, []);

  /**
   * Send data through a connection
   */
  const send = useCallback(async (code, data) => {
    try {
      await wormholeService.send(code, data);
    } catch (err) {
      setError(err.message);
      throw err;
    }
  }, []);

  /**
   * Fetch content through a connection
   */
  const fetch = useCallback(async (code, path) => {
    try {
      return await wormholeService.fetch(code, path);
    } catch (err) {
      setError(err.message);
      throw err;
    }
  }, []);

  return {
    // State
    connections,
    connecting,
    error,
    isConnected: connections.length > 0,

    // Actions
    connect,
    disconnect,
    generateCode,
    getConnection,
    send,
    fetch,
    clearError,
  };
}

/**
 * useConnectionHistory - Hook for accessing connection history
 */
export function useConnectionHistory() {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);

  const loadHistory = useCallback(async () => {
    setLoading(true);
    try {
      const data = await storageService.getConnectionHistory();
      setHistory(data);
    } catch (err) {
      console.error('Failed to load connection history:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  return {
    history,
    loading,
    refresh: loadHistory,
  };
}
