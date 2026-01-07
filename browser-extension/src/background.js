/**
 * Wormhole Browser Extension - Background Service Worker
 *
 * Handles wh:// URL interception and routing through local wormhole daemon.
 */

const DAEMON_PORT = 9475;
const DAEMON_URL = `http://localhost:${DAEMON_PORT}`;

// Connection state
let daemonConnected = false;
let activeConnections = new Map();

/**
 * Check if the wh daemon is running
 */
async function checkDaemon() {
  try {
    const response = await fetch(`${DAEMON_URL}/status`, {
      method: 'GET',
      headers: { 'Accept': 'application/json' }
    });
    if (response.ok) {
      const data = await response.json();
      daemonConnected = true;
      updateIcon(true);
      return data;
    }
  } catch (e) {
    // Daemon not running
  }
  daemonConnected = false;
  updateIcon(false);
  return null;
}

/**
 * Update the extension icon based on connection state
 */
function updateIcon(connected) {
  const suffix = connected ? '' : '-disconnected';
  chrome.action.setIcon({
    path: {
      16: `icons/wormhole-16${suffix}.png`,
      32: `icons/wormhole-32${suffix}.png`,
      48: `icons/wormhole-48${suffix}.png`,
      128: `icons/wormhole-128${suffix}.png`
    }
  });
  chrome.action.setTitle({
    title: connected ? 'Wormhole Browser (Connected)' : 'Wormhole Browser (Daemon not running)'
  });
}

/**
 * Resolve a WNS address to an ephemeral wormhole code
 */
async function resolveAddress(wnsAddress) {
  try {
    const response = await fetch(`${DAEMON_URL}/resolve`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      },
      body: JSON.stringify({ address: wnsAddress })
    });
    if (response.ok) {
      return await response.json();
    }
  } catch (e) {
    console.error('Failed to resolve address:', e);
  }
  return null;
}

/**
 * Start a proxy connection to a wormhole address
 */
async function connectToAddress(wnsAddress) {
  try {
    const response = await fetch(`${DAEMON_URL}/connect`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      },
      body: JSON.stringify({ address: wnsAddress })
    });
    if (response.ok) {
      const data = await response.json();
      activeConnections.set(wnsAddress, data);
      return data;
    }
  } catch (e) {
    console.error('Failed to connect:', e);
  }
  return null;
}

/**
 * Configure PAC proxy for wh:// URLs
 */
function configurePacProxy() {
  const pacScript = `
    function FindProxyForURL(url, host) {
      // Route wh:// URLs through the local wormhole daemon proxy
      if (url.startsWith('wh://') || host.endsWith('.wns') || host.endsWith('.wh')) {
        return 'PROXY localhost:${DAEMON_PORT}';
      }
      // Direct connection for everything else
      return 'DIRECT';
    }
  `;

  chrome.proxy.settings.set({
    value: {
      mode: 'pac_script',
      pacScript: {
        data: pacScript
      }
    },
    scope: 'regular'
  }, () => {
    if (chrome.runtime.lastError) {
      console.error('Failed to set proxy:', chrome.runtime.lastError);
    } else {
      console.log('PAC proxy configured for wh:// URLs');
    }
  });
}

/**
 * Handle URL interception for wh:// scheme
 * Note: In MV3, we can't intercept arbitrary URL schemes directly,
 * so we use the proxy API to route traffic through the daemon.
 */
chrome.webNavigation?.onBeforeNavigate?.addListener((details) => {
  const url = details.url;

  // Check for wh:// URLs that got through (shouldn't happen with proxy)
  if (url.startsWith('wh://')) {
    // Extract the WNS address from the URL
    const wnsUrl = new URL(url.replace('wh://', 'http://'));
    const address = wnsUrl.hostname;

    console.log('Intercepted wh:// URL:', address);

    // Redirect to the daemon proxy
    chrome.tabs.update(details.tabId, {
      url: `http://localhost:${DAEMON_PORT}/browse/${encodeURIComponent(url)}`
    });
  }
});

/**
 * Handle messages from popup and content scripts
 */
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  switch (message.type) {
    case 'GET_STATUS':
      checkDaemon().then(status => {
        sendResponse({
          connected: daemonConnected,
          status: status,
          connections: Object.fromEntries(activeConnections)
        });
      });
      return true; // Async response

    case 'CONNECT':
      connectToAddress(message.address).then(result => {
        sendResponse({ success: !!result, data: result });
      });
      return true;

    case 'RESOLVE':
      resolveAddress(message.address).then(result => {
        sendResponse({ success: !!result, data: result });
      });
      return true;

    case 'REFRESH_DAEMON':
      checkDaemon().then(status => {
        sendResponse({ connected: daemonConnected, status });
      });
      return true;
  }
});

/**
 * Handle native messaging from wh daemon
 */
let nativePort = null;

function connectNativeMessaging() {
  try {
    nativePort = chrome.runtime.connectNative('com.criticalwormhole.daemon');

    nativePort.onMessage.addListener((message) => {
      console.log('Native message:', message);

      switch (message.type) {
        case 'CONNECTION_ESTABLISHED':
          activeConnections.set(message.address, message.data);
          break;
        case 'CONNECTION_CLOSED':
          activeConnections.delete(message.address);
          break;
        case 'STATUS_UPDATE':
          daemonConnected = message.running;
          updateIcon(daemonConnected);
          break;
      }
    });

    nativePort.onDisconnect.addListener(() => {
      console.log('Native messaging disconnected');
      nativePort = null;
      daemonConnected = false;
      updateIcon(false);

      // Retry connection after delay
      setTimeout(connectNativeMessaging, 5000);
    });
  } catch (e) {
    console.log('Native messaging not available, using HTTP fallback');
  }
}

/**
 * Initialize extension
 */
async function init() {
  console.log('Wormhole Browser extension starting...');

  // Check daemon status
  await checkDaemon();

  // Configure proxy
  configurePacProxy();

  // Try native messaging
  connectNativeMessaging();

  // Periodic daemon check
  setInterval(checkDaemon, 30000);

  console.log('Wormhole Browser extension initialized');
}

// Start initialization
init();
