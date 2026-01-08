/**
 * Wormhole Browser Extension - Background Service Worker
 *
 * Standalone implementation - no external daemon required.
 * Uses the built-in protocol library for direct wormhole connections.
 */

import { Wormhole, WormholeState, connectWormhole } from './lib/protocol/wormhole.js';
import { Advertisement, verifyAdvertisement } from './lib/wns/advertisement.js';
import { DEFAULT_RELAY } from './lib/protocol/mailbox.js';

// Configuration
const CONFIG = {
  relayUrl: DEFAULT_RELAY,
  appId: 'wh.tools/v1',
  defaultTTL: 300
};

// Active connections cache
const activeConnections = new Map();

// Known hosts cache (for WNS resolution)
const knownHosts = new Map();

/**
 * Update extension icon based on state
 */
function updateIcon(hasActiveConnections) {
  const suffix = hasActiveConnections ? '' : '-disconnected';
  chrome.action.setIcon({
    path: {
      16: `icons/wormhole-16${suffix}.png`,
      32: `icons/wormhole-32${suffix}.png`,
      48: `icons/wormhole-48${suffix}.png`,
      128: `icons/wormhole-128${suffix}.png`
    }
  }).catch(() => {
    // Icon might not exist, ignore
  });

  chrome.action.setTitle({
    title: hasActiveConnections
      ? `Wormhole Browser (${activeConnections.size} connection${activeConnections.size !== 1 ? 's' : ''})`
      : 'Wormhole Browser'
  });
}

/**
 * Parse a wh:// URL or WNS address
 * @param {string} input - URL or address
 * @returns {{address: string, path: string}}
 */
function parseWormholeUrl(input) {
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
async function resolveAddress(address) {
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
  // Extract base address (without .wns)
  const baseAddress = address.replace(/\.wns$/, '').replace(/\.wh$/, '');

  try {
    // Try well-known URL for the address
    // This assumes there's a web server advertising the wormhole code
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
    const stored = await chrome.storage.local.get(['addresses']);
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
 * @returns {Promise<Wormhole>}
 */
async function ensureConnection(address) {
  // Check for existing connection
  let wormhole = activeConnections.get(address);

  if (wormhole && wormhole.state === WormholeState.CONNECTED) {
    return wormhole;
  }

  // Resolve address to code
  const resolution = await resolveAddress(address);

  if (!resolution) {
    throw new Error(`Could not resolve address: ${address}`);
  }

  console.log('Connecting with code:', resolution.code);
  console.log('Relay URL:', CONFIG.relayUrl);

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
    console.log('Peer connected!');

  } catch (error) {
    console.error('Connection failed:', error.message);
    throw error;
  }

  // Store connection
  activeConnections.set(address, wormhole);
  updateIcon(true);

  // Clean up on close
  wormhole.onStateChange = (newState) => {
    if (newState === WormholeState.CLOSED || newState === WormholeState.FAILED) {
      activeConnections.delete(address);
      updateIcon(activeConnections.size > 0);
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
async function connectAndFetch(address, path) {
  const wormhole = await ensureConnection(address);

  // Fetch the page
  const response = await fetchOverWormhole(address, path);

  return { wormhole, response };
}

/**
 * Generate a unique connection ID
 */
function generateConnectionId() {
  return 'conn-' + Math.random().toString(36).substring(2, 10);
}

/**
 * Inject wormhole navigation metadata into HTML
 * @param {string} html - Original HTML content
 * @param {string} address - Wormhole address
 * @param {string} connectionId - Connection ID
 * @param {string} path - Current path
 * @returns {string} - Modified HTML with injected metadata
 */
function injectWormholeMetadata(html, address, connectionId, path) {
  // Add data attributes to body for the content script
  const bodyMatch = html.match(/<body([^>]*)>/i);
  if (bodyMatch) {
    const existingAttrs = bodyMatch[1] || '';
    const newAttrs = ` data-wh-address="${address}" data-wh-connection-id="${connectionId}" data-wh-path="${path}"`;
    html = html.replace(/<body([^>]*)>/i, `<body${existingAttrs}${newAttrs}>`);
  } else {
    // No body tag, wrap content
    html = `<body data-wh-address="${address}" data-wh-connection-id="${connectionId}" data-wh-path="${path}">${html}</body>`;
  }

  return html;
}

/**
 * Create a data URL from response for rendering
 * @param {object} response - HTTP response from wormhole
 * @param {string} address - Wormhole address for navigation
 * @param {string} connectionId - Connection ID
 * @param {string} path - Current path
 * @returns {string}
 */
function createDataUrl(response, address, connectionId, path) {
  const contentType = response.headers?.['content-type'] || 'text/html';
  let body = response.body || '';

  // If HTML, inject navigation metadata
  if (contentType.includes('text/html')) {
    body = injectWormholeMetadata(body, address, connectionId, path);
  }

  // Encode body
  const encoded = btoa(unescape(encodeURIComponent(body)));

  return `data:${contentType};base64,${encoded}`;
}

// Track connection IDs to addresses
const connectionToAddress = new Map();

// Track WebSocket streams (wsId -> {address, streamId, port})
const activeWebSocketStreams = new Map();

/**
 * Fetch a page over an existing wormhole connection
 * @param {string} address - Wormhole address
 * @param {string} path - HTTP path
 * @param {string} method - HTTP method
 * @param {object} body - Request body for POST
 * @returns {Promise<object>} - HTTP response
 */
async function fetchOverWormhole(address, path, method = 'GET', body = null) {
  const wormhole = activeConnections.get(address);
  if (!wormhole || wormhole.state !== WormholeState.CONNECTED) {
    throw new Error('No active connection to ' + address);
  }

  const httpRequest = {
    type: 'http_request',
    method: method,
    path: path,
    headers: {
      'User-Agent': 'Wormhole-Browser/0.5.0',
      'Accept': '*/*'  // Accept all content types including images
    }
  };

  if (body) {
    httpRequest.body = body;
    httpRequest.headers['Content-Type'] = 'application/json';
  }

  console.log('Fetching over wormhole:', method, path);
  await wormhole.send(JSON.stringify(httpRequest));

  const responseData = await wormhole.receive(30000);
  const response = JSON.parse(new TextDecoder().decode(responseData));

  // Extract content type from headers if present
  if (response.headers) {
    const contentType = response.headers['Content-Type'] ||
                        response.headers['content-type'] ||
                        'text/html';
    response.contentType = contentType;
  }

  return response;
}

/**
 * Handle omnibox input
 */
chrome.omnibox.onInputEntered.addListener(async (text, disposition) => {
  console.log('Omnibox input:', text, 'disposition:', disposition);

  try {
    const { address, path } = parseWormholeUrl(text);

    // Show loading state
    chrome.omnibox.setDefaultSuggestion({
      description: `Connecting to ${address}...`
    });

    // Establish connection (but don't fetch yet - viewer will do that)
    await ensureConnection(address);

    // Generate connection ID for navigation tracking
    const connectionId = generateConnectionId();
    connectionToAddress.set(connectionId, address);

    // Navigate to the viewer page with connection info
    const viewerUrl = chrome.runtime.getURL('viewer.html') +
      `?address=${encodeURIComponent(address)}` +
      `&connectionId=${encodeURIComponent(connectionId)}` +
      `&path=${encodeURIComponent(path)}`;

    // Open in appropriate way based on disposition
    if (disposition === 'currentTab') {
      await chrome.tabs.update({ url: viewerUrl });
    } else if (disposition === 'newForegroundTab') {
      await chrome.tabs.create({ url: viewerUrl, active: true });
    } else {
      await chrome.tabs.create({ url: viewerUrl, active: false });
    }
  } catch (error) {
    console.error('Omnibox navigation failed:', error);

    // Show error page
    const errorHtml = `
      <!DOCTYPE html>
      <html>
      <head><title>Wormhole Error</title></head>
      <body style="font-family: system-ui, sans-serif; padding: 2rem; max-width: 600px; margin: 0 auto;">
        <h1>Connection Failed</h1>
        <p>Could not connect to <strong>${text}</strong></p>
        <p style="color: #666;">${error.message}</p>
        <h2>Troubleshooting</h2>
        <ul>
          <li>Make sure the address is correct</li>
          <li>The host might be offline</li>
          <li>Check if you have the wormhole code saved</li>
        </ul>
      </body>
      </html>
    `;
    const errorUrl = `data:text/html;base64,${btoa(errorHtml)}`;
    chrome.tabs.update({ url: errorUrl });
  }
});

/**
 * Provide omnibox suggestions
 */
chrome.omnibox.onInputChanged.addListener(async (text, suggest) => {
  const suggestions = [];

  // Suggest from known hosts
  for (const [address] of knownHosts) {
    if (address.includes(text)) {
      suggestions.push({
        content: address,
        description: `Connect to <match>${address}</match>`
      });
    }
  }

  // Suggest from saved addresses
  try {
    const stored = await chrome.storage.local.get(['addresses', 'recentAddresses']);

    if (stored.addresses) {
      for (const address of Object.keys(stored.addresses)) {
        if (address.includes(text) && !suggestions.find(s => s.content === address)) {
          suggestions.push({
            content: address,
            description: `Saved: <match>${address}</match>`
          });
        }
      }
    }

    if (stored.recentAddresses) {
      for (const address of stored.recentAddresses) {
        if (address.includes(text) && !suggestions.find(s => s.content === address)) {
          suggestions.push({
            content: address,
            description: `Recent: <match>${address}</match>`
          });
        }
      }
    }
  } catch (e) {
    // Ignore storage errors
  }

  // Add current input as suggestion if it looks valid
  if (text.length > 2 && !suggestions.find(s => s.content === text)) {
    suggestions.push({
      content: text,
      description: `Connect to <url>${text}</url>`
    });
  }

  suggest(suggestions.slice(0, 5));
});

/**
 * Set omnibox default suggestion
 */
chrome.omnibox.onInputStarted.addListener(() => {
  chrome.omnibox.setDefaultSuggestion({
    description: 'Enter a wormhole address (e.g., abc123.wns or 7-guitar-sunset)'
  });
});

/**
 * Handle messages from popup and content scripts
 */
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  switch (message.type) {
    case 'GET_STATUS':
      sendResponse({
        connected: true,
        standalone: true,
        connections: Object.fromEntries(
          Array.from(activeConnections.entries()).map(([addr, wh]) => [
            addr,
            { state: wh.state, code: wh.code }
          ])
        )
      });
      return false;

    case 'CONNECT':
      (async () => {
        try {
          const { address, path } = parseWormholeUrl(message.address);
          const result = await connectAndFetch(address, path || '/');
          sendResponse({ success: true, data: result.response });
        } catch (error) {
          sendResponse({ success: false, error: error.message });
        }
      })();
      return true;

    case 'NAVIGATE':
      // Handle navigation from viewer or content script
      (async () => {
        try {
          // Get address from connection ID or directly
          let address = message.address;
          if (message.connectionId && connectionToAddress.has(message.connectionId)) {
            address = connectionToAddress.get(message.connectionId);
          }

          if (!address) {
            sendResponse({ success: false, error: 'No connection found' });
            return;
          }

          // Ensure we have an active connection (establish if needed)
          await ensureConnection(address);

          // Fetch the new page over the wormhole
          const response = await fetchOverWormhole(
            address,
            message.path,
            message.method || 'GET',
            message.body
          );

          sendResponse({ success: true, data: response });
        } catch (error) {
          console.error('Navigation error:', error);
          sendResponse({ success: false, error: error.message });
        }
      })();
      return true;

    case 'RESOLVE':
      (async () => {
        try {
          const resolution = await resolveAddress(message.address);
          sendResponse({ success: !!resolution, data: resolution });
        } catch (error) {
          sendResponse({ success: false, error: error.message });
        }
      })();
      return true;

    case 'DISCONNECT':
      (async () => {
        const wormhole = activeConnections.get(message.address);
        if (wormhole) {
          await wormhole.close();
          activeConnections.delete(message.address);
          updateIcon(activeConnections.size > 0);
        }
        sendResponse({ success: true });
      })();
      return true;

    case 'SAVE_ADDRESS':
      (async () => {
        try {
          const stored = await chrome.storage.local.get(['addresses']);
          const addresses = stored.addresses || {};
          addresses[message.address] = message.code;
          await chrome.storage.local.set({ addresses });
          sendResponse({ success: true });
        } catch (error) {
          sendResponse({ success: false, error: error.message });
        }
      })();
      return true;

    case 'GET_SAVED_ADDRESSES':
      (async () => {
        try {
          const stored = await chrome.storage.local.get(['addresses']);
          sendResponse({ success: true, addresses: stored.addresses || {} });
        } catch (error) {
          sendResponse({ success: false, error: error.message });
        }
      })();
      return true;
  }
});

/**
 * Handle WebSocket connections over wormhole
 * WebSockets are proxied as a special message stream through the wormhole connection
 */
chrome.runtime.onConnect.addListener((port) => {
  // Check if this is a WebSocket port
  if (!port.name.startsWith('websocket-')) {
    return;
  }

  const wsId = port.name.replace('websocket-', '');
  console.log('[Background] WebSocket port connected:', wsId);

  let wsState = {
    address: null,
    streamId: null,
    connected: false
  };

  port.onMessage.addListener(async (message) => {
    console.log('[Background] WebSocket message:', message.type, wsId);

    switch (message.type) {
      case 'WS_OPEN': {
        const { address, url, protocols } = message;
        wsState.address = address;
        wsState.streamId = `ws-stream-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

        try {
          // Ensure we have a wormhole connection
          const wormhole = await ensureConnection(address);

          // Send WebSocket upgrade request through the wormhole
          const wsRequest = {
            type: 'websocket_open',
            streamId: wsState.streamId,
            url: url,
            protocols: protocols
          };

          await wormhole.send(JSON.stringify(wsRequest));

          // Wait for open acknowledgment with timeout
          const timeoutId = setTimeout(() => {
            if (!wsState.connected) {
              port.postMessage({
                event: 'error',
                message: 'WebSocket connection timeout'
              });
              port.postMessage({
                event: 'close',
                code: 1006,
                reason: 'Connection timeout',
                wasClean: false
              });
            }
          }, 10000);

          // Listen for response
          const responseData = await wormhole.receive(10000);
          clearTimeout(timeoutId);

          const response = JSON.parse(new TextDecoder().decode(responseData));

          if (response.type === 'websocket_open' && response.success) {
            wsState.connected = true;
            activeWebSocketStreams.set(wsId, wsState);

            port.postMessage({
              event: 'open',
              protocol: response.protocol || '',
              extensions: response.extensions || ''
            });

            // Start listening for messages from the wormhole
            listenForWebSocketMessages(wormhole, wsId, port, wsState);
          } else {
            port.postMessage({
              event: 'error',
              message: response.error || 'WebSocket connection refused'
            });
            port.postMessage({
              event: 'close',
              code: 1006,
              reason: response.error || 'Connection refused',
              wasClean: false
            });
          }
        } catch (error) {
          console.error('[Background] WebSocket open error:', error);
          port.postMessage({
            event: 'error',
            message: error.message
          });
          port.postMessage({
            event: 'close',
            code: 1006,
            reason: error.message,
            wasClean: false
          });
        }
        break;
      }

      case 'WS_SEND': {
        if (!wsState.connected || !wsState.address) {
          console.warn('[Background] WebSocket send but not connected');
          return;
        }

        try {
          const wormhole = activeConnections.get(wsState.address);
          if (!wormhole) {
            throw new Error('No active wormhole connection');
          }

          const wsMessage = {
            type: 'websocket_message',
            streamId: wsState.streamId,
            data: message.data
          };

          await wormhole.send(JSON.stringify(wsMessage));
        } catch (error) {
          console.error('[Background] WebSocket send error:', error);
          port.postMessage({
            event: 'error',
            message: error.message
          });
        }
        break;
      }

      case 'WS_CLOSE': {
        if (!wsState.address) {
          return;
        }

        try {
          const wormhole = activeConnections.get(wsState.address);
          if (wormhole) {
            const wsClose = {
              type: 'websocket_close',
              streamId: wsState.streamId,
              code: message.code || 1000,
              reason: message.reason || ''
            };
            await wormhole.send(JSON.stringify(wsClose));
          }
        } catch (error) {
          console.error('[Background] WebSocket close error:', error);
        }

        wsState.connected = false;
        activeWebSocketStreams.delete(wsId);

        port.postMessage({
          event: 'close',
          code: message.code || 1000,
          reason: message.reason || '',
          wasClean: true
        });
        break;
      }
    }
  });

  port.onDisconnect.addListener(() => {
    console.log('[Background] WebSocket port disconnected:', wsId);
    wsState.connected = false;
    activeWebSocketStreams.delete(wsId);
  });
});

/**
 * Listen for WebSocket messages from the wormhole and forward to port
 * Note: This is a simplified implementation. In a real scenario,
 * you'd need message multiplexing for multiple WebSockets over one wormhole.
 */
async function listenForWebSocketMessages(wormhole, wsId, port, wsState) {
  while (wsState.connected && wormhole.state === WormholeState.CONNECTED) {
    try {
      const data = await wormhole.receive(60000); // 60s timeout for heartbeat
      const message = JSON.parse(new TextDecoder().decode(data));

      // Check if this message is for our WebSocket stream
      if (message.streamId !== wsState.streamId) {
        continue; // Not for us
      }

      switch (message.type) {
        case 'websocket_message':
          port.postMessage({
            event: 'message',
            data: message.data
          });
          break;

        case 'websocket_close':
          wsState.connected = false;
          activeWebSocketStreams.delete(wsId);
          port.postMessage({
            event: 'close',
            code: message.code || 1000,
            reason: message.reason || '',
            wasClean: true
          });
          return;

        case 'websocket_error':
          port.postMessage({
            event: 'error',
            message: message.error || 'Unknown error'
          });
          break;
      }
    } catch (error) {
      if (!wsState.connected) {
        return; // Expected disconnect
      }
      console.error('[Background] WebSocket receive error:', error);
      port.postMessage({
        event: 'error',
        message: error.message
      });
    }
  }
}

/**
 * Initialize extension
 */
async function init() {
  console.log('Wormhole Browser extension starting (standalone mode)...');

  // Load saved addresses into known hosts
  try {
    const stored = await chrome.storage.local.get(['addresses']);
    if (stored.addresses) {
      for (const [address, code] of Object.entries(stored.addresses)) {
        knownHosts.set(address, { code, advertisement: null });
      }
    }
  } catch (e) {
    console.log('Failed to load saved addresses:', e.message);
  }

  updateIcon(false);

  console.log('Wormhole Browser extension initialized (standalone mode)');
}

// Start initialization
init();
