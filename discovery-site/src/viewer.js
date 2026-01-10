/**
 * Wormhole Viewer - Displays content fetched through wormhole connections
 *
 * Standalone version for Discovery Site (no browser extension required)
 *
 * Features:
 * - Sandboxed iframe for script execution
 * - Resource proxying (images, CSS, scripts)
 * - Per-site storage (localStorage, sessionStorage)
 * - Cookie management
 */

import {
  fetchOverWormhole,
  ensureConnection,
  openWebSocket,
  generateConnectionId
} from './app.js';

// Get URL parameters
const params = new URLSearchParams(window.location.search);
const address = params.get('address');
const connectionId = params.get('connectionId');
let currentPath = params.get('path') || '/';

// DOM elements
const loadingEl = document.getElementById('wh-loading');
const loadingAddressEl = document.getElementById('wh-loading-address');
const errorEl = document.getElementById('wh-error');
const errorMessageEl = document.getElementById('wh-error-message');
const sandboxEl = document.getElementById('wh-sandbox');
const navLoadingEl = document.getElementById('wh-nav-loading');

// Track sandbox ready state
let sandboxReady = false;
let pendingContent = null;

// Per-site storage (keyed by wormhole address)
const siteStorage = {
  local: {},
  session: {}
};

// Per-site cookies
let siteCookies = {};

// Active WebSocket connections (id -> ws)
const activeWebSockets = new Map();

// Storage adapter using localStorage
const storage = {
  async get(key) {
    const value = localStorage.getItem(`wh-${key}`);
    if (value) {
      try {
        return JSON.parse(value);
      } catch {
        return value;
      }
    }
    return null;
  },
  async set(key, value) {
    localStorage.setItem(`wh-${key}`, JSON.stringify(value));
  }
};

/**
 * Load storage for this site from localStorage
 */
async function loadSiteStorage() {
  try {
    const storageKey = `storage-${address}`;
    const data = await storage.get(storageKey);
    if (data) {
      siteStorage.local = data.local || {};
      // Session storage is not persisted, starts fresh
    }
    console.log('[Viewer] Loaded storage for', address);
  } catch (e) {
    console.warn('[Viewer] Could not load storage:', e);
  }
}

/**
 * Save storage for this site to localStorage
 */
async function saveSiteStorage() {
  try {
    const storageKey = `storage-${address}`;
    await storage.set(storageKey, {
      local: siteStorage.local,
      lastAccess: Date.now()
    });
  } catch (e) {
    console.warn('[Viewer] Could not save storage:', e);
  }
}

/**
 * Load cookies for this site
 */
async function loadSiteCookies() {
  try {
    const cookieKey = `cookies-${address}`;
    const data = await storage.get(cookieKey);
    if (data) {
      siteCookies = data || {};
    }
    console.log('[Viewer] Loaded cookies for', address);
  } catch (e) {
    console.warn('[Viewer] Could not load cookies:', e);
  }
}

/**
 * Save cookies for this site
 */
async function saveSiteCookies() {
  try {
    const cookieKey = `cookies-${address}`;
    await storage.set(cookieKey, siteCookies);
  } catch (e) {
    console.warn('[Viewer] Could not save cookies:', e);
  }
}

/**
 * Show loading state
 */
function showLoading(isNavigation = false) {
  if (isNavigation) {
    navLoadingEl.style.display = 'block';
  } else {
    loadingEl.style.display = 'flex';
    loadingAddressEl.textContent = address;
  }
}

/**
 * Hide loading state
 */
function hideLoading() {
  loadingEl.style.display = 'none';
  navLoadingEl.style.display = 'none';
}

/**
 * Show error state
 */
function showError(message) {
  hideLoading();
  sandboxEl.classList.remove('active');
  errorEl.style.display = 'block';
  errorMessageEl.textContent = message;
}

/**
 * Fetch a resource through the wormhole
 */
async function fetchResource(path, options = {}) {
  try {
    const response = await fetchOverWormhole(address, path, {
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
  } catch (error) {
    console.error('[Viewer] Resource fetch error:', path, error);
    throw error;
  }
}

/**
 * Convert data to base64 data URL
 * Data URLs work across origin boundaries unlike blob URLs
 */
function createDataUrl(data, contentType) {
  // If already a data URL
  if (typeof data === 'string' && data.startsWith('data:')) {
    return data;
  }

  // Try to convert to base64 data URL
  try {
    // If it's already base64
    const base64 = btoa(data);
    return `data:${contentType};base64,${base64}`;
  } catch (e) {
    // If data contains non-Latin1 characters, use encodeURIComponent
    try {
      return `data:${contentType};base64,${btoa(unescape(encodeURIComponent(data)))}`;
    } catch (e2) {
      // Last resort - return as-is if it's already a valid URL
      console.warn('[Viewer] Could not create data URL:', e2);
      return data;
    }
  }
}

/**
 * Display content in the sandbox iframe
 */
function displayContent(html, path) {
  hideLoading();
  errorEl.style.display = 'none';

  // Update current path
  currentPath = path;

  // Update URL without reload
  try {
    const newUrl = new URL(window.location);
    newUrl.searchParams.set('path', path);
    window.history.pushState({ path }, '', newUrl);
    console.log('[Viewer] Updated URL to:', newUrl.toString());
  } catch (e) {
    console.warn('[Viewer] Could not update URL:', e.message);
  }

  // Show the sandbox
  sandboxEl.classList.add('active');

  // Send content to sandbox with storage and cookies
  const message = {
    type: 'RENDER',
    html: html,
    path: path,
    address: address,
    storage: siteStorage,
    cookies: siteCookies
  };

  if (sandboxReady) {
    sandboxEl.contentWindow.postMessage(message, '*');
    console.log('[Viewer] Sent content to sandbox for path:', path);
  } else {
    // Queue content until sandbox is ready
    pendingContent = message;
    console.log('[Viewer] Sandbox not ready, queuing content for path:', path);
  }
}

/**
 * Navigate to a new path through the wormhole
 */
async function navigateTo(path, method = 'GET', body = null) {
  console.log('[Viewer] Navigating to:', path);
  showLoading(true);

  try {
    const response = await fetchResource(path, { method, body });
    displayContent(response.body, path);
  } catch (error) {
    console.error('[Viewer] Navigation error:', error);
    showError(error.message);
  }
}

/**
 * Handle WebSocket open request from sandbox
 */
async function handleWebSocketOpen(data) {
  const { id, url, protocols } = data;
  console.log('[Viewer] WebSocket open request:', id, url);

  try {
    // Open WebSocket through wormhole
    const ws = await openWebSocket(address, url, protocols);

    // Store the WebSocket
    activeWebSockets.set(id, ws);

    // Listen for events
    ws.onopen = () => {
      sandboxEl.contentWindow.postMessage({
        type: 'WS_EVENT',
        id: id,
        event: 'open',
        protocol: ws.protocol,
        extensions: ws.extensions
      }, '*');
    };

    ws.onmessage = (event) => {
      sandboxEl.contentWindow.postMessage({
        type: 'WS_EVENT',
        id: id,
        event: 'message',
        data: event.data
      }, '*');
    };

    ws.onerror = (event) => {
      sandboxEl.contentWindow.postMessage({
        type: 'WS_EVENT',
        id: id,
        event: 'error',
        message: 'WebSocket error'
      }, '*');
    };

    ws.onclose = (event) => {
      activeWebSockets.delete(id);
      sandboxEl.contentWindow.postMessage({
        type: 'WS_EVENT',
        id: id,
        event: 'close',
        code: event.code,
        reason: event.reason,
        wasClean: event.wasClean
      }, '*');
    };

  } catch (error) {
    console.error('[Viewer] WebSocket open error:', error);
    sandboxEl.contentWindow.postMessage({
      type: 'WS_EVENT',
      id: id,
      event: 'error',
      message: error.message
    }, '*');
  }
}

/**
 * Handle WebSocket send from sandbox
 */
function handleWebSocketSend(data) {
  const { id, data: messageData } = data;
  const ws = activeWebSockets.get(id);

  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(messageData);
  } else {
    console.warn('[Viewer] WebSocket send to unknown or closed ID:', id);
  }
}

/**
 * Handle WebSocket close from sandbox
 */
function handleWebSocketClose(data) {
  const { id, code, reason } = data;
  const ws = activeWebSockets.get(id);

  if (ws) {
    ws.close(code, reason);
    activeWebSockets.delete(id);
  }
}

/**
 * Handle resource request from sandbox
 */
async function handleResourceRequest(data) {
  const { id, path, method, headers, body, responseType } = data;
  console.log('[Viewer] Resource request:', path, responseType);

  try {
    const response = await fetchResource(path, { method, headers, body });

    let responseData;
    if (responseType === 'blob') {
      // Convert to data URL for binary content (works across origins)
      responseData = createDataUrl(response.body, response.contentType);
      sandboxEl.contentWindow.postMessage({
        type: 'RESOURCE_RESPONSE',
        id: id,
        blobUrl: responseData,  // Actually a data URL now
        responseType: 'blob'
      }, '*');
    } else if (responseType === 'full') {
      // Send full response with headers
      sandboxEl.contentWindow.postMessage({
        type: 'RESOURCE_RESPONSE',
        id: id,
        data: {
          body: response.body,
          status: response.status,
          statusText: response.statusText,
          headers: response.headers
        },
        responseType: 'full'
      }, '*');
    } else {
      // Text response
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

/**
 * Handle IndexedDB operations (per-site storage)
 */
async function handleIndexedDBOperation(data) {
  const storageKey = `idb-${address}`;

  try {
    // Load current IDB data
    let idbData = await storage.get(storageKey) || {};

    switch (data.type) {
      case 'IDB_PUT':
        if (!idbData[data.database]) idbData[data.database] = {};
        if (!idbData[data.database][data.store]) idbData[data.database][data.store] = {};
        idbData[data.database][data.store][data.key] = data.value;
        break;

      case 'IDB_DELETE_ITEM':
        if (idbData[data.database]?.[data.store]) {
          delete idbData[data.database][data.store][data.key];
        }
        break;

      case 'IDB_CLEAR':
        if (idbData[data.database]) {
          idbData[data.database][data.store] = {};
        }
        break;

      case 'IDB_DELETE':
        delete idbData[data.database];
        break;
    }

    // Save updated IDB data
    await storage.set(storageKey, idbData);
  } catch (e) {
    console.warn('[Viewer] IndexedDB operation failed:', e);
  }
}

/**
 * Handle messages from the sandbox iframe
 */
window.addEventListener('message', async (event) => {
  // Only accept messages from our sandbox
  if (event.source !== sandboxEl.contentWindow) {
    return;
  }

  const { type, ...data } = event.data;

  switch (type) {
    case 'SANDBOX_READY':
      sandboxReady = true;
      console.log('[Viewer] Sandbox is ready');
      // Send any pending content
      if (pendingContent) {
        sandboxEl.contentWindow.postMessage(pendingContent, '*');
        console.log('[Viewer] Sent queued content to sandbox');
        pendingContent = null;
      }
      break;

    case 'NAVIGATE':
      navigateTo(data.path);
      break;

    case 'FORM_SUBMIT':
      navigateTo(data.path, data.method, data.data);
      break;

    case 'EXTERNAL_LINK':
      window.open(data.url, '_blank');
      break;

    case 'TITLE_CHANGE':
      document.title = data.title + ' - Wormhole';
      break;

    case 'CONTENT_LOADED':
      console.log('[Viewer] Content loaded in sandbox for path:', data.path);
      sandboxEl.contentWindow.scrollTo(0, 0);
      break;

    case 'RESOURCE_REQUEST':
      handleResourceRequest(data);
      break;

    case 'STORAGE_SET':
      if (data.storageType === 'local') {
        siteStorage.local[data.key] = data.value;
        saveSiteStorage();
      } else {
        siteStorage.session[data.key] = data.value;
      }
      break;

    case 'STORAGE_REMOVE':
      if (data.storageType === 'local') {
        delete siteStorage.local[data.key];
        saveSiteStorage();
      } else {
        delete siteStorage.session[data.key];
      }
      break;

    case 'STORAGE_CLEAR':
      if (data.storageType === 'local') {
        siteStorage.local = {};
        saveSiteStorage();
      } else {
        siteStorage.session = {};
      }
      break;

    case 'COOKIE_SET':
      // Parse and store cookie
      const cookieParts = data.cookie.split(';')[0].split('=');
      if (cookieParts.length >= 2) {
        siteCookies[cookieParts[0].trim()] = cookieParts.slice(1).join('=').trim();
        saveSiteCookies();
      }
      break;

    case 'WS_OPEN':
      handleWebSocketOpen(data);
      break;

    case 'WS_SEND':
      handleWebSocketSend(data);
      break;

    case 'WS_CLOSE':
      handleWebSocketClose(data);
      break;

    case 'WH_IFRAME_REQUEST':
      // Forward iframe resource requests
      handleResourceRequest({
        id: data.id,
        path: data.url,
        method: data.method || 'GET',
        responseType: 'full'
      });
      break;

    case 'WINDOW_OPEN':
      // Open a new viewer tab for wormhole URLs
      const newViewerUrl = `viewer.html` +
        `?address=${encodeURIComponent(data.address)}` +
        `&connectionId=${encodeURIComponent(connectionId + '-child')}` +
        `&path=${encodeURIComponent(data.path || '/')}`;

      if (data.target === '_self') {
        window.location.href = newViewerUrl;
      } else {
        window.open(newViewerUrl, data.target || '_blank', data.features || '');
      }
      console.log('[Viewer] Opening new window:', data.address, data.path);
      break;

    case 'NAVIGATE_ADDRESS':
      // Navigate to a different wormhole address
      const redirectUrl = `viewer.html` +
        `?address=${encodeURIComponent(data.address)}` +
        `&connectionId=${encodeURIComponent('conn-' + Date.now())}` +
        `&path=${encodeURIComponent(data.path || '/')}`;
      window.location.href = redirectUrl;
      break;

    case 'HISTORY_PUSH':
      // Update browser URL for pushState
      try {
        const pushUrl = new URL(window.location);
        pushUrl.searchParams.set('path', data.path);
        window.history.pushState({ path: data.path, state: data.state }, data.title || '', pushUrl);
        currentPath = data.path;
      } catch (e) {
        console.warn('[Viewer] Could not update URL for pushState:', e);
      }
      break;

    case 'HISTORY_REPLACE':
      // Update browser URL for replaceState
      try {
        const replaceUrl = new URL(window.location);
        replaceUrl.searchParams.set('path', data.path);
        window.history.replaceState({ path: data.path, state: data.state }, data.title || '', replaceUrl);
        currentPath = data.path;
      } catch (e) {
        console.warn('[Viewer] Could not update URL for replaceState:', e);
      }
      break;

    case 'IDB_OPEN':
    case 'IDB_DELETE':
    case 'IDB_PUT':
    case 'IDB_DELETE_ITEM':
    case 'IDB_CLEAR':
      // IndexedDB operations - store per-site
      handleIndexedDBOperation(data);
      break;
  }
});

/**
 * Handle browser back/forward buttons
 */
window.addEventListener('popstate', (event) => {
  if (event.state && event.state.path) {
    navigateTo(event.state.path);
  }
});

/**
 * Initial load
 */
async function init() {
  // Check for error parameter (from failed connection)
  const errorParam = params.get('error');
  if (errorParam) {
    showError(`Connection to ${address || 'unknown'} failed: ${errorParam}`);
    return;
  }

  if (!address) {
    showError('No wormhole address specified');
    return;
  }

  // Load per-site storage and cookies
  await Promise.all([
    loadSiteStorage(),
    loadSiteCookies()
  ]);

  showLoading();

  try {
    // Ensure connection is established
    await ensureConnection(address);

    const response = await fetchResource(currentPath);
    displayContent(response.body, currentPath);
  } catch (error) {
    console.error('[Viewer] Initial load error:', error);
    showError(error.message);
  }
}

// Start
init();
