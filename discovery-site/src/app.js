/**
 * Wormhole Discovery Site - Core Application Module
 *
 * Standalone implementation - no browser extension or daemon required.
 * Uses the built-in protocol library for direct wormhole connections.
 */

import { Wormhole, WormholeState, connectWormhole } from './lib/protocol/wormhole.js';
import { DilationState } from './lib/protocol/dilation.js';
import { Advertisement, verifyAdvertisement } from './lib/wns/advertisement.js';
import { DEFAULT_RELAY } from './lib/protocol/mailbox.js';

// Configuration
export const CONFIG = {
  relayUrl: DEFAULT_RELAY,
  appId: 'wh.tools/v1',
  defaultTTL: 300,
  useDilation: true  // Enable dilation for better performance
};

// Session storage key for persisting connections across page reloads
const SESSION_KEY = 'wh-active-connections';

/**
 * Save connection to session storage for reconnection on reload
 */
function saveConnectionToSession(address, wormhole) {
  try {
    const sessions = JSON.parse(sessionStorage.getItem(SESSION_KEY) || '{}');
    sessions[address] = {
      code: wormhole.code,
      connectedAt: Date.now(),
      state: wormhole.state
    };
    sessionStorage.setItem(SESSION_KEY, JSON.stringify(sessions));
    console.log('[Session] Saved connection for:', address, wormhole.code);
  } catch (e) {
    console.warn('[Session] Failed to save connection:', e);
  }
}

/**
 * Get connection from session storage
 */
function getConnectionFromSession(address) {
  try {
    const sessions = JSON.parse(sessionStorage.getItem(SESSION_KEY) || '{}');
    return sessions[address] || null;
  } catch (e) {
    console.warn('[Session] Failed to get connection:', e);
    return null;
  }
}

/**
 * Clear connection from session storage
 */
export function clearConnectionFromSession(address) {
  try {
    const sessions = JSON.parse(sessionStorage.getItem(SESSION_KEY) || '{}');
    delete sessions[address];
    sessionStorage.setItem(SESSION_KEY, JSON.stringify(sessions));
    console.log('[Session] Cleared connection for:', address);
  } catch (e) {
    console.warn('[Session] Failed to clear connection:', e);
  }
}

// Active connections cache
const activeConnections = new Map();

// Known hosts cache (for WNS resolution)
const knownHosts = new Map();

// Track connection IDs to addresses
const connectionToAddress = new Map();

// Request queues per address to serialize wormhole requests
const requestQueues = new Map();

// State change callbacks
const stateChangeCallbacks = [];

/**
 * Storage adapter using localStorage
 */
const storage = {
  async get(keys) {
    const result = {};
    const keyList = Array.isArray(keys) ? keys : [keys];
    for (const key of keyList) {
      const value = localStorage.getItem(`wh-${key}`);
      if (value) {
        try {
          result[key] = JSON.parse(value);
        } catch {
          result[key] = value;
        }
      }
    }
    return result;
  },
  async set(data) {
    for (const [key, value] of Object.entries(data)) {
      localStorage.setItem(`wh-${key}`, JSON.stringify(value));
    }
  },
  async remove(keys) {
    const keyList = Array.isArray(keys) ? keys : [keys];
    for (const key of keyList) {
      localStorage.removeItem(`wh-${key}`);
    }
  }
};

/**
 * Register a callback for connection state changes
 * @param {Function} callback - Called with (address, state, connectionCount)
 */
export function onStateChange(callback) {
  stateChangeCallbacks.push(callback);
  return () => {
    const idx = stateChangeCallbacks.indexOf(callback);
    if (idx !== -1) stateChangeCallbacks.splice(idx, 1);
  };
}

/**
 * Notify all state change callbacks
 */
function notifyStateChange(address, state) {
  const count = activeConnections.size;
  for (const callback of stateChangeCallbacks) {
    try {
      callback(address, state, count);
    } catch (e) {
      console.error('State change callback error:', e);
    }
  }
}

/**
 * Parse a wh:// URL or WNS address
 * @param {string} input - URL or address
 * @returns {{address: string, path: string}}
 */
export function parseWormholeUrl(input) {
  // Remove wh:// prefix if present
  let cleaned = input.trim();
  if (cleaned.startsWith('wh://')) {
    cleaned = cleaned.slice(5);
  }

  // Parse as URL-like structure
  const slashIndex = cleaned.indexOf('/');
  let address, path;

  if (slashIndex !== -1) {
    address = cleaned.slice(0, slashIndex);
    path = cleaned.slice(slashIndex);
  } else {
    address = cleaned;
    path = '/';
  }

  // Check if it looks like a wormhole code (e.g., "7-guitar-sunset")
  const isWormholeCode = /^\d+-[a-z]+-[a-z]+$/i.test(address);

  // Normalize address (add .wns if no TLD, but not for wormhole codes)
  if (!address.includes('.') && !isWormholeCode) {
    address = address + '.wns';
  }

  return { address, path };
}

/**
 * Resolve a WNS address to a wormhole code
 *
 * Resolution order:
 * 1. Local cache (known hosts)
 * 2. HTTP well-known endpoint
 * 3. Direct wormhole code (if looks like a code)
 *
 * @param {string} address - WNS address (e.g., "abc123.wns")
 * @returns {Promise<{code: string, advertisement: Advertisement}|null>}
 */
export async function resolveAddress(address) {
  console.log('Resolving address:', address);

  // Check cache first
  const cached = knownHosts.get(address);
  if (cached && !cached.advertisement?.isExpired?.()) {
    console.log('Using cached resolution for:', address);
    return cached;
  }

  // Check if it looks like a direct wormhole code (e.g., "7-guitar-sunset")
  if (/^\d+-[a-z]+-[a-z]+$/i.test(address)) {
    console.log('Address looks like a wormhole code:', address);
    return { code: address, advertisement: null };
  }

  // Try HTTP well-known endpoint
  try {
    const wellKnownUrl = `https://${address}/.well-known/wormhole.json`;
    console.log('Trying well-known URL:', wellKnownUrl);

    const response = await fetch(wellKnownUrl, {
      method: 'GET',
      headers: { 'Accept': 'application/json' }
    });

    if (response.ok) {
      const adData = await response.json();
      const result = await verifyAdvertisement(adData, address);

      if (result.valid) {
        const resolution = { code: result.code, advertisement: result.advertisement };
        knownHosts.set(address, resolution);
        return resolution;
      }
    }
  } catch (e) {
    console.log('Well-known resolution failed:', e.message);
  }

  // Try direct code from storage (user might have saved it)
  try {
    const stored = await storage.get('addresses');
    if (stored.addresses && stored.addresses[address]) {
      return { code: stored.addresses[address], advertisement: null };
    }
  } catch (e) {
    console.log('Storage lookup failed:', e.message);
  }

  return null;
}

/**
 * Ensure a wormhole connection exists to the given address
 * @param {string} address - WNS address or wormhole code
 * @param {boolean} useDilation - Whether to dilate the connection (default: CONFIG.useDilation)
 * @returns {Promise<Wormhole>}
 */
export async function ensureConnection(address, useDilation = CONFIG.useDilation) {
  // Check for existing connection in memory
  let wormhole = activeConnections.get(address);

  if (wormhole && (wormhole.state === WormholeState.CONNECTED || wormhole.state === WormholeState.DILATED)) {
    // If we need dilation but aren't dilated yet, try to dilate
    if (useDilation && !wormhole.isDilated && wormhole.state === WormholeState.CONNECTED) {
      try {
        console.log('Dilating existing connection to:', address);
        await wormhole.dilate();
        notifyStateChange(address, 'dilated');
      } catch (e) {
        console.warn('Dilation failed, continuing with undilated connection:', e.message);
      }
    }
    return wormhole;
  }

  // Check session storage for previous connection (page reload case)
  const sessionConnection = getConnectionFromSession(address);
  let resolution;

  if (sessionConnection && sessionConnection.code) {
    // Try to reconnect with the previous code
    console.log('[Session] Attempting to reconnect with previous code:', sessionConnection.code);
    resolution = { code: sessionConnection.code, advertisement: null };
  } else {
    // Resolve address to code
    resolution = await resolveAddress(address);

    if (!resolution) {
      throw new Error(`Could not resolve address: ${address}`);
    }
  }

  console.log('Connecting with code:', resolution.code);
  console.log('Relay URL:', CONFIG.relayUrl);

  notifyStateChange(address, 'connecting');

  try {
    // Connect using the code with timeout
    const connectPromise = connectWormhole(resolution.code, {
      relayUrl: CONFIG.relayUrl,
      appId: CONFIG.appId
    });

    const timeoutPromise = new Promise((_, reject) => {
      setTimeout(() => reject(new Error('Connection timeout (15s)')), 15000);
    });

    wormhole = await Promise.race([connectPromise, timeoutPromise]);
    console.log('Wormhole connected, state:', wormhole.state);

    notifyStateChange(address, 'connected');

    // Try to dilate if enabled AND peer supports WebRTC dilation
    // Browser can only use WebRTC for dilation, not TCP-based transports
    // Python magic-wormhole advertises: direct-tcp-v1, relay-v1 (incompatible)
    // Browser needs: webrtc-v1 (or similar WebRTC-based transport)
    const peerAbilities = wormhole.peerVersion?.['dilation-abilities'] || [];
    const peerSupportsWebRTC = peerAbilities.some(
      ability => ability.type === 'webrtc-v1' || ability.type === 'webrtc'
    );
    const peerCanDilate = wormhole.peerVersion?.['can-dilate']?.length > 0;

    if (useDilation && peerSupportsWebRTC) {
      try {
        console.log('Attempting to dilate connection (peer supports WebRTC)...');
        await wormhole.dilate();
        console.log('Connection dilated successfully!');
        notifyStateChange(address, 'dilated');
      } catch (e) {
        console.warn('Dilation failed, continuing with undilated connection:', e.message);
      }
    } else if (useDilation && peerCanDilate && !peerSupportsWebRTC) {
      console.log('Peer supports dilation but not WebRTC transport, using phase-based messaging');
      console.log('Peer dilation abilities:', peerAbilities.map(a => a.type).join(', '));
    } else if (useDilation && !peerCanDilate) {
      console.log('Peer does not support dilation, using phase-based messaging');
    }

  } catch (error) {
    console.error('Connection failed:', error.message);
    notifyStateChange(address, 'failed');

    // If this was a session reconnect attempt with "crowded" error, clear session
    if (sessionConnection && error.message && error.message.includes('crowded')) {
      console.log('[Session] Crowded error on reconnect, clearing session');
      clearConnectionFromSession(address);
    }

    throw error;
  }

  // Store connection
  activeConnections.set(address, wormhole);

  // Save to session storage for reconnection on reload
  saveConnectionToSession(address, wormhole);

  // Clean up on close
  wormhole.onStateChange = (newState) => {
    if (newState === WormholeState.CLOSED || newState === WormholeState.FAILED) {
      activeConnections.delete(address);
      clearConnectionFromSession(address);
      notifyStateChange(address, 'closed');
    }
  };

  return wormhole;
}

/**
 * Connect to a wormhole address and proxy HTTP
 * @param {string} address - WNS address
 * @param {string} path - HTTP path to request
 * @returns {Promise<{wormhole: Wormhole, response: object}|null>}
 */
export async function connectAndFetch(address, path) {
  const wormhole = await ensureConnection(address);
  const response = await fetchOverWormhole(address, path);
  return { wormhole, response };
}

/**
 * Generate a unique connection ID
 */
export function generateConnectionId() {
  return 'conn-' + Math.random().toString(36).substring(2, 10);
}

/**
 * Register a connection ID to an address
 */
export function registerConnection(connectionId, address) {
  connectionToAddress.set(connectionId, address);
}

/**
 * Get address for a connection ID
 */
export function getAddressForConnection(connectionId) {
  return connectionToAddress.get(connectionId);
}

/**
 * Get or create a request queue for an address
 */
function getRequestQueue(address) {
  if (!requestQueues.has(address)) {
    requestQueues.set(address, Promise.resolve());
  }
  return requestQueues.get(address);
}

/**
 * Fetch a page over an existing wormhole connection
 * @param {string} address - Wormhole address
 * @param {string} path - HTTP path
 * @param {object|string} options - Options object or HTTP method string
 * @param {object} body - Request body for POST (deprecated, use options.body)
 * @returns {Promise<object>} - HTTP response
 */
export async function fetchOverWormhole(address, path, options = {}, body = null) {
  // Support both old signature (method, body) and new signature (options object)
  let method = 'GET';
  if (typeof options === 'string') {
    method = options;
  } else if (options.method) {
    method = options.method;
    body = options.body || body;
  }
  const wormhole = activeConnections.get(address);
  if (!wormhole || (wormhole.state !== WormholeState.CONNECTED && wormhole.state !== WormholeState.DILATED)) {
    throw new Error('No active connection to ' + address);
  }

  const httpRequest = {
    type: 'http_request',
    method: method,
    path: path,
    headers: {
      'User-Agent': 'Wormhole-Discovery/0.5.0',
      'Accept': '*/*'
    }
  };

  if (body) {
    httpRequest.body = body;
    httpRequest.headers['Content-Type'] = 'application/json';
  }

  console.log('Fetching over wormhole:', method, path, 'dilated:', wormhole.isDilated);

  // Use dilated subchannel if available
  if (wormhole.isDilated) {
    return fetchOverDilatedWormhole(wormhole, httpRequest);
  }

  // Fall back to serialized phase-based messaging
  return fetchOverUndilatedWormhole(address, wormhole, httpRequest);
}

/**
 * Fetch using dilated subchannel (supports concurrent requests)
 */
async function fetchOverDilatedWormhole(wormhole, httpRequest) {
  try {
    const connector = wormhole.connectorFor('wh-http');
    const subchannel = await connector.connect();

    await subchannel.send(JSON.stringify(httpRequest));

    const response = await new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        reject(new Error('HTTP request timeout'));
      }, 30000);

      let responseData = new Uint8Array(0);

      subchannel.onData = (data) => {
        const newData = new Uint8Array(responseData.length + data.length);
        newData.set(responseData);
        newData.set(data, responseData.length);
        responseData = newData;

        try {
          const text = new TextDecoder().decode(responseData);
          const parsed = JSON.parse(text);
          clearTimeout(timeout);
          resolve(parsed);
        } catch {
          // Not complete yet
        }
      };

      subchannel.onClose = () => {
        clearTimeout(timeout);
        if (responseData.length > 0) {
          try {
            const text = new TextDecoder().decode(responseData);
            resolve(JSON.parse(text));
          } catch {
            reject(new Error('Invalid response data'));
          }
        } else {
          reject(new Error('Subchannel closed without response'));
        }
      };

      subchannel.onError = (error) => {
        clearTimeout(timeout);
        reject(error);
      };
    });

    await subchannel.close();

    if (response.headers) {
      const contentType = response.headers['Content-Type'] ||
                          response.headers['content-type'] ||
                          'text/html';
      response.contentType = contentType;
    }

    return response;
  } catch (error) {
    console.error('Dilated fetch failed:', error);
    throw error;
  }
}

/**
 * Fetch using serialized phase-based messaging
 */
async function fetchOverUndilatedWormhole(address, wormhole, httpRequest) {
  const currentQueue = getRequestQueue(address);

  const requestPromise = currentQueue.then(async () => {
    console.log('Sending request via phase-based messaging');
    await wormhole.send(JSON.stringify(httpRequest));

    const responseData = await wormhole.receive(30000);
    const response = JSON.parse(new TextDecoder().decode(responseData));

    if (response.headers) {
      const contentType = response.headers['Content-Type'] ||
                          response.headers['content-type'] ||
                          'text/html';
      response.contentType = contentType;
    }

    return response;
  });

  requestQueues.set(address, requestPromise.catch(() => {}));

  return requestPromise;
}

/**
 * Open a WebSocket connection through the wormhole
 * @param {string} address - Wormhole address
 * @param {string} url - WebSocket URL to connect to
 * @param {Array<string>} protocols - WebSocket protocols
 * @returns {Promise<WebSocket>} - WebSocket-like object
 */
export async function openWebSocket(address, url, protocols = []) {
  const wormhole = activeConnections.get(address);
  if (!wormhole || (wormhole.state !== WormholeState.CONNECTED && wormhole.state !== WormholeState.DILATED)) {
    throw new Error('No active connection to ' + address);
  }

  // Create a WebSocket-like object that tunnels through the wormhole
  const wsRequest = {
    type: 'websocket_open',
    url: url,
    protocols: protocols
  };

  console.log('Opening WebSocket through wormhole:', url);

  if (wormhole.isDilated) {
    // Use dilated subchannel for WebSocket
    const connector = wormhole.connectorFor('wh-ws');
    const subchannel = await connector.connect();

    // Create WebSocket-like interface
    const ws = {
      readyState: WebSocket.CONNECTING,
      protocol: '',
      extensions: '',
      send: (data) => {
        if (ws.readyState === WebSocket.OPEN) {
          subchannel.send(JSON.stringify({ type: 'data', data }));
        }
      },
      close: (code = 1000, reason = '') => {
        ws.readyState = WebSocket.CLOSING;
        subchannel.send(JSON.stringify({ type: 'close', code, reason }));
        subchannel.close();
        ws.readyState = WebSocket.CLOSED;
      },
      onopen: null,
      onmessage: null,
      onerror: null,
      onclose: null
    };

    // Send open request
    await subchannel.send(JSON.stringify(wsRequest));

    // Handle subchannel events
    subchannel.onData = (data) => {
      try {
        const msg = JSON.parse(new TextDecoder().decode(data));
        if (msg.type === 'open') {
          ws.readyState = WebSocket.OPEN;
          ws.protocol = msg.protocol || '';
          ws.extensions = msg.extensions || '';
          if (ws.onopen) ws.onopen();
        } else if (msg.type === 'message') {
          if (ws.onmessage) ws.onmessage({ data: msg.data });
        } else if (msg.type === 'error') {
          if (ws.onerror) ws.onerror(new Error(msg.message));
        } else if (msg.type === 'close') {
          ws.readyState = WebSocket.CLOSED;
          if (ws.onclose) ws.onclose({ code: msg.code, reason: msg.reason, wasClean: msg.wasClean });
        }
      } catch (e) {
        console.error('WebSocket message parse error:', e);
      }
    };

    subchannel.onClose = () => {
      if (ws.readyState !== WebSocket.CLOSED) {
        ws.readyState = WebSocket.CLOSED;
        if (ws.onclose) ws.onclose({ code: 1006, reason: 'Connection lost', wasClean: false });
      }
    };

    subchannel.onError = (error) => {
      if (ws.onerror) ws.onerror(error);
    };

    return ws;
  }

  // For undilated connections, WebSocket is not supported
  throw new Error('WebSocket requires dilated connection');
}

/**
 * Disconnect from a wormhole address
 * @param {string} address - Address to disconnect
 */
export async function disconnectAddress(address) {
  const wormhole = activeConnections.get(address);
  if (wormhole) {
    await wormhole.close();
    activeConnections.delete(address);
    clearConnectionFromSession(address);
    notifyStateChange(address, 'closed');
  }
}

/**
 * Get all active connections
 * @returns {Object} Map of address -> connection info
 */
export function getActiveConnections() {
  const connections = {};
  for (const [addr, wh] of activeConnections.entries()) {
    connections[addr] = {
      state: wh.state,
      code: wh.code,
      isDilated: wh.isDilated || false
    };
  }
  return connections;
}

/**
 * Get known hosts
 * @returns {Map} Known hosts cache
 */
export function getKnownHosts() {
  return new Map(knownHosts);
}

/**
 * Save an address-code mapping
 * @param {string} address - WNS address
 * @param {string} code - Wormhole code
 */
export async function saveAddress(address, code) {
  const stored = await storage.get('addresses');
  const addresses = stored.addresses || {};
  addresses[address] = code;
  await storage.set({ addresses });
  knownHosts.set(address, { code, advertisement: null });
}

/**
 * Get saved addresses
 * @returns {Promise<Object>} Saved address-code mappings
 */
export async function getSavedAddresses() {
  const stored = await storage.get('addresses');
  return stored.addresses || {};
}

/**
 * Add to recent addresses
 * @param {string} address - Address to add
 */
export async function addRecentAddress(address) {
  const stored = await storage.get('recentAddresses');
  let recent = stored.recentAddresses || [];

  // Remove if already exists
  recent = recent.filter(a => a !== address);

  // Add to front
  recent.unshift(address);

  // Keep only last 10
  recent = recent.slice(0, 10);

  await storage.set({ recentAddresses: recent });
}

/**
 * Get recent addresses
 * @returns {Promise<Array>} Recent addresses
 */
export async function getRecentAddresses() {
  const stored = await storage.get('recentAddresses');
  return stored.recentAddresses || [];
}

/**
 * Get connection status
 * @returns {Object} Status object
 */
export function getStatus() {
  return {
    connected: activeConnections.size > 0,
    standalone: true,
    dilationEnabled: CONFIG.useDilation,
    connections: getActiveConnections()
  };
}

/**
 * Inject wormhole navigation metadata into HTML
 * @param {string} html - Original HTML content
 * @param {string} address - Wormhole address
 * @param {string} connectionId - Connection ID
 * @param {string} path - Current path
 * @returns {string} - Modified HTML with injected metadata
 */
export function injectWormholeMetadata(html, address, connectionId, path) {
  const bodyMatch = html.match(/<body([^>]*)>/i);
  if (bodyMatch) {
    const existingAttrs = bodyMatch[1] || '';
    const newAttrs = ` data-wh-address="${address}" data-wh-connection-id="${connectionId}" data-wh-path="${path}"`;
    html = html.replace(/<body([^>]*)>/i, `<body${existingAttrs}${newAttrs}>`);
  } else {
    html = `<body data-wh-address="${address}" data-wh-connection-id="${connectionId}" data-wh-path="${path}">${html}</body>`;
  }

  return html;
}

// Initialize on load
async function init() {
  console.log('Wormhole Discovery Site initializing...');

  // Load saved addresses into known hosts
  try {
    const stored = await storage.get('addresses');
    if (stored.addresses) {
      for (const [address, code] of Object.entries(stored.addresses)) {
        knownHosts.set(address, { code, advertisement: null });
      }
    }
  } catch (e) {
    console.log('Failed to load saved addresses:', e.message);
  }

  console.log('Wormhole Discovery Site initialized');
}

// Auto-initialize
init();

/**
 * Initialize index page UI if we're on the index page
 */
function initIndexPage() {
  const form = document.getElementById('connect-form');
  if (!form) return; // Not on index page

  const input = document.getElementById('address-input');
  const button = document.getElementById('connect-btn');
  const statusEl = document.getElementById('status');
  const connectionsSection = document.getElementById('connections-section');
  const connectionList = document.getElementById('connection-list');
  const recentSection = document.getElementById('recent-section');
  const recentList = document.getElementById('recent-list');

  // Load recent addresses
  async function loadRecent() {
    const recent = await getRecentAddresses();
    if (recent.length > 0) {
      recentSection.style.display = 'block';
      recentList.innerHTML = recent.map(addr => `
        <div class="recent-item" data-address="${addr}">
          <span class="address">${addr}</span>
          <span class="arrow">&rarr;</span>
        </div>
      `).join('');

      // Add click handlers
      recentList.querySelectorAll('.recent-item').forEach(item => {
        item.addEventListener('click', () => {
          const addr = item.dataset.address;
          input.value = addr;
          form.dispatchEvent(new Event('submit'));
        });
      });
    }
  }

  // Update connections display
  function updateConnections() {
    const connections = getActiveConnections();
    const entries = Object.entries(connections);

    if (entries.length > 0) {
      connectionsSection.style.display = 'block';
      connectionList.innerHTML = entries.map(([addr, info]) => `
        <div class="connection-item" data-address="${addr}">
          <div class="info">
            <div class="status-dot"></div>
            <span class="address">${addr}</span>
          </div>
          <button type="button" class="disconnect-btn">Disconnect</button>
        </div>
      `).join('');

      // Add disconnect handlers
      connectionList.querySelectorAll('.disconnect-btn').forEach(btn => {
        btn.addEventListener('click', async (e) => {
          e.stopPropagation();
          const item = btn.closest('.connection-item');
          const addr = item.dataset.address;
          await disconnectAddress(addr);
        });
      });

      // Click to navigate
      connectionList.querySelectorAll('.connection-item').forEach(item => {
        item.addEventListener('click', (e) => {
          if (e.target.tagName === 'BUTTON') return;
          const addr = item.dataset.address;
          navigateToViewer(addr, '/');
        });
      });
    } else {
      connectionsSection.style.display = 'none';
    }
  }

  // Viewer state
  let viewerAddress = null;
  let viewerPath = '/';
  let sandboxReady = false;
  let pendingContent = null;
  const siteStorage = { local: {}, session: {} };
  let siteCookies = {};

  // Viewer DOM elements (loaded lazily)
  const viewerContainer = document.getElementById('viewer-container');
  const loadingEl = document.getElementById('wh-loading');
  const loadingAddressEl = document.getElementById('wh-loading-address');
  const errorEl = document.getElementById('wh-error');
  const errorMessageEl = document.getElementById('wh-error-message');
  const sandboxEl = document.getElementById('wh-sandbox');
  const navLoadingEl = document.getElementById('wh-nav-loading');
  const backBtn = document.getElementById('wh-back-btn');

  // Back button handler
  if (backBtn) {
    backBtn.addEventListener('click', () => {
      hideViewer();
    });
  }

  // Show viewer loading
  function showViewerLoading(address) {
    document.body.classList.add('viewing');
    viewerContainer.classList.add('active');
    loadingEl.classList.add('active');
    loadingAddressEl.textContent = address;
    errorEl.classList.remove('active');
    sandboxEl.classList.remove('active');
  }

  // Hide viewer loading
  function hideViewerLoading() {
    loadingEl.classList.remove('active');
    navLoadingEl.style.display = 'none';
  }

  // Show viewer error
  function showViewerError(message) {
    hideViewerLoading();
    sandboxEl.classList.remove('active');
    errorEl.classList.add('active');
    errorMessageEl.textContent = message;
  }

  // Hide viewer and return to discovery
  function hideViewer() {
    document.body.classList.remove('viewing');
    viewerContainer.classList.remove('active');
    loadingEl.classList.remove('active');
    errorEl.classList.remove('active');
    sandboxEl.classList.remove('active');
    viewerAddress = null;
    viewerPath = '/';

    // Update URL
    window.history.pushState({}, '', window.location.pathname);
  }

  // Display content in sandbox
  function displayContent(html, path) {
    hideViewerLoading();
    errorEl.classList.remove('active');
    viewerPath = path;

    // Update URL
    const newUrl = new URL(window.location);
    newUrl.searchParams.set('address', viewerAddress);
    newUrl.searchParams.set('path', path);
    window.history.pushState({ address: viewerAddress, path }, '', newUrl);

    // Show sandbox
    sandboxEl.classList.add('active');

    // Send content to sandbox
    const message = {
      type: 'RENDER',
      html: html,
      path: path,
      address: viewerAddress,
      storage: siteStorage,
      cookies: siteCookies
    };

    if (sandboxReady) {
      sandboxEl.contentWindow.postMessage(message, '*');
      console.log('[Viewer] Sent content to sandbox for path:', path);
    } else {
      pendingContent = message;
      console.log('[Viewer] Sandbox not ready, queuing content');
    }
  }

  // Fetch resource through wormhole
  async function fetchViewerResource(path, options = {}) {
    const response = await fetchOverWormhole(viewerAddress, path, {
      method: options.method || 'GET',
      body: options.body || null,
      headers: options.headers || {}
    });
    return {
      body: response.body || '',
      status: response.status || 200,
      statusText: response.statusText || 'OK',
      headers: response.headers || {},
      contentType: response.contentType || 'text/html'
    };
  }

  // Navigate within viewer
  async function viewerNavigateTo(path, method = 'GET', body = null) {
    console.log('[Viewer] Navigating to:', path);
    navLoadingEl.style.display = 'block';

    // Split path and hash fragment
    // Hash fragments should not be sent to server
    const hashIndex = path.indexOf('#');
    const basePath = hashIndex >= 0 ? path.substring(0, hashIndex) : path;
    const hash = hashIndex >= 0 ? path.substring(hashIndex) : '';

    try {
      // Fetch content without hash
      const response = await fetchViewerResource(basePath, { method, body });
      // Display with full path (including hash) so sandbox can scroll
      displayContent(response.body, path);
    } catch (error) {
      console.error('[Viewer] Navigation error:', error);
      showViewerError(error.message);
    }
  }

  // Convert data to data URL
  function createDataUrl(data, contentType) {
    if (typeof data === 'string' && data.startsWith('data:')) return data;
    try {
      return `data:${contentType};base64,${btoa(data)}`;
    } catch {
      try {
        return `data:${contentType};base64,${btoa(unescape(encodeURIComponent(data)))}`;
      } catch {
        return data;
      }
    }
  }

  // Handle resource request from sandbox
  async function handleResourceRequest(data) {
    const { id, path, method, headers, body, responseType } = data;
    console.log('[Viewer] Resource request:', path, responseType);
    try {
      const response = await fetchViewerResource(path, { method, headers, body });
      if (responseType === 'blob') {
        sandboxEl.contentWindow.postMessage({
          type: 'RESOURCE_RESPONSE',
          id: id,
          blobUrl: createDataUrl(response.body, response.contentType),
          responseType: 'blob'
        }, '*');
      } else if (responseType === 'full') {
        sandboxEl.contentWindow.postMessage({
          type: 'RESOURCE_RESPONSE',
          id: id,
          data: { body: response.body, status: response.status, statusText: response.statusText, headers: response.headers },
          responseType: 'full'
        }, '*');
      } else {
        sandboxEl.contentWindow.postMessage({
          type: 'RESOURCE_RESPONSE',
          id: id,
          data: response.body,
          responseType: 'text'
        }, '*');
      }
    } catch (error) {
      sandboxEl.contentWindow.postMessage({
        type: 'RESOURCE_RESPONSE',
        id: id,
        error: error.message
      }, '*');
    }
  }

  // Handle messages from sandbox
  window.addEventListener('message', async (event) => {
    if (!sandboxEl || event.source !== sandboxEl.contentWindow) return;
    const { type, ...data } = event.data;

    switch (type) {
      case 'SANDBOX_READY':
        sandboxReady = true;
        console.log('[Viewer] Sandbox is ready');
        if (pendingContent) {
          sandboxEl.contentWindow.postMessage(pendingContent, '*');
          pendingContent = null;
        }
        break;
      case 'NAVIGATE':
        viewerNavigateTo(data.path);
        break;
      case 'FORM_SUBMIT':
        viewerNavigateTo(data.path, data.method, data.data);
        break;
      case 'EXTERNAL_LINK':
        window.open(data.url, '_blank');
        break;
      case 'TITLE_CHANGE':
        document.title = data.title + ' - Wormhole';
        break;
      case 'CONTENT_LOADED':
        console.log('[Viewer] Content loaded for path:', data.path);
        sandboxEl.contentWindow.scrollTo(0, 0);
        break;
      case 'RESOURCE_REQUEST':
        handleResourceRequest(data);
        break;
      case 'STORAGE_SET':
        if (data.storageType === 'local') siteStorage.local[data.key] = data.value;
        else siteStorage.session[data.key] = data.value;
        break;
      case 'STORAGE_REMOVE':
        if (data.storageType === 'local') delete siteStorage.local[data.key];
        else delete siteStorage.session[data.key];
        break;
      case 'STORAGE_CLEAR':
        if (data.storageType === 'local') siteStorage.local = {};
        else siteStorage.session = {};
        break;
      case 'COOKIE_SET':
        const cookieParts = data.cookie.split(';')[0].split('=');
        if (cookieParts.length >= 2) {
          siteCookies[cookieParts[0].trim()] = cookieParts.slice(1).join('=').trim();
        }
        break;
      case 'HISTORY_PUSH':
        try {
          const pushUrl = new URL(window.location);
          pushUrl.searchParams.set('path', data.path);
          window.history.pushState({ address: viewerAddress, path: data.path, state: data.state }, data.title || '', pushUrl);
          viewerPath = data.path;
        } catch (e) { console.warn('[Viewer] pushState error:', e); }
        break;
      case 'HISTORY_REPLACE':
        try {
          const replaceUrl = new URL(window.location);
          replaceUrl.searchParams.set('path', data.path);
          window.history.replaceState({ address: viewerAddress, path: data.path, state: data.state }, data.title || '', replaceUrl);
          viewerPath = data.path;
        } catch (e) { console.warn('[Viewer] replaceState error:', e); }
        break;
      case 'WH_IFRAME_REQUEST':
        handleResourceRequest({ id: data.id, path: data.url, method: data.method || 'GET', responseType: 'full' });
        break;
    }
  });

  // Handle browser back/forward
  window.addEventListener('popstate', (event) => {
    if (event.state && event.state.address && event.state.path) {
      if (viewerAddress === event.state.address) {
        viewerNavigateTo(event.state.path);
      }
    } else if (viewerAddress) {
      hideViewer();
    }
  });

  // Navigate to viewer (inline, no page navigation)
  async function navigateToViewer(address, path) {
    viewerAddress = address;
    viewerPath = path;

    showViewerLoading(address);

    try {
      const response = await fetchViewerResource(path);
      displayContent(response.body, path);
    } catch (error) {
      console.error('[Viewer] Initial load error:', error);
      showViewerError(error.message);
    }
  }

  // Show status message
  function showStatus(message, type) {
    statusEl.textContent = message;
    statusEl.className = 'status ' + type;
  }

  // Hide status
  function hideStatus() {
    statusEl.className = 'status';
  }

  // Handle form submission
  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const rawInput = input.value.trim();
    if (!rawInput) return;

    const { address, path } = parseWormholeUrl(rawInput);

    button.disabled = true;
    showStatus(`Connecting to ${address}...`, 'connecting');

    try {
      await ensureConnection(address);
      await addRecentAddress(address);

      hideStatus();
      navigateToViewer(address, path);
    } catch (error) {
      showStatus(`Connection failed: ${error.message}`, 'error');
      button.disabled = false;
    }
  });

  // Listen for state changes
  onStateChange((address, state, count) => {
    console.log('State change:', address, state, count);
    updateConnections();
  });

  // Check for hash-based navigation
  function checkHashNavigation() {
    const hash = window.location.hash;
    if (hash.startsWith('#/address/')) {
      const match = hash.match(/^#\/address\/([^\/]+)(\/.*)?$/);
      if (match) {
        input.value = match[1] + (match[2] || '');
        form.dispatchEvent(new Event('submit'));
      }
    }
  }

  // Initialize
  loadRecent();
  updateConnections();
  checkHashNavigation();

  // Handle hash changes
  window.addEventListener('hashchange', checkHashNavigation);
}

// Initialize index page when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initIndexPage);
} else {
  initIndexPage();
}
