/**
 * Wormhole Browser Extension - Popup Script
 */

const DAEMON_PORT = 9475;

// DOM elements
const statusIndicator = document.getElementById('statusIndicator');
const statusValue = document.getElementById('statusValue');
const daemonWarning = document.getElementById('daemonWarning');
const refreshBtn = document.getElementById('refreshBtn');
const addressInput = document.getElementById('addressInput');
const goBtn = document.getElementById('goBtn');
const connectionsList = document.getElementById('connectionsList');

/**
 * Update UI with daemon status
 */
function updateStatus(connected, status) {
  if (connected) {
    statusIndicator.classList.add('connected');
    statusValue.textContent = 'Connected';
    daemonWarning.style.display = 'none';
    goBtn.disabled = false;
  } else {
    statusIndicator.classList.remove('connected');
    statusValue.textContent = 'Not Running';
    daemonWarning.style.display = 'block';
    goBtn.disabled = true;
  }
}

/**
 * Update connections list
 */
function updateConnections(connections) {
  if (!connections || Object.keys(connections).length === 0) {
    connectionsList.innerHTML = `
      <li class="empty-state">
        <div class="icon">&#128268;</div>
        <div>No active connections</div>
      </li>
    `;
    return;
  }

  connectionsList.innerHTML = Object.entries(connections).map(([address, data]) => `
    <li class="connection">
      <div class="icon">&#127744;</div>
      <div class="info">
        <div class="address" title="${address}">${formatAddress(address)}</div>
        <div class="code">${data.code || 'connecting...'}</div>
      </div>
    </li>
  `).join('');
}

/**
 * Format a WNS address for display
 */
function formatAddress(address) {
  // Shorten long addresses
  if (address.length > 30) {
    return address.substring(0, 12) + '...' + address.substring(address.length - 8);
  }
  return address;
}

/**
 * Refresh daemon status
 */
async function refreshStatus() {
  statusValue.textContent = 'Checking...';

  try {
    const response = await chrome.runtime.sendMessage({ type: 'GET_STATUS' });
    updateStatus(response.connected, response.status);
    updateConnections(response.connections);
  } catch (e) {
    console.error('Failed to get status:', e);
    updateStatus(false, null);
  }
}

/**
 * Navigate to a wormhole address
 */
async function navigateToAddress() {
  let address = addressInput.value.trim();

  if (!address) {
    return;
  }

  // Normalize address format
  if (!address.startsWith('wh://') && !address.includes('.')) {
    // Assume it's an alias, try to resolve it
    try {
      const response = await chrome.runtime.sendMessage({
        type: 'RESOLVE',
        address: address
      });

      if (response.success && response.data.address) {
        address = response.data.address;
      }
    } catch (e) {
      console.error('Failed to resolve alias:', e);
    }
  }

  // Ensure wh:// prefix
  if (!address.startsWith('wh://')) {
    address = 'wh://' + address;
  }

  // Ensure .wns suffix if missing
  if (!address.includes('.wns') && !address.includes('.wh')) {
    const url = new URL(address.replace('wh://', 'http://'));
    if (!url.hostname.includes('.')) {
      address = address.replace(url.hostname, url.hostname + '.wns');
    }
  }

  // Navigate via daemon proxy
  const proxyUrl = `http://localhost:${DAEMON_PORT}/browse/${encodeURIComponent(address)}`;

  chrome.tabs.create({ url: proxyUrl });

  // Clear input
  addressInput.value = '';
}

/**
 * Handle Enter key in address input
 */
addressInput.addEventListener('keypress', (e) => {
  if (e.key === 'Enter') {
    navigateToAddress();
  }
});

/**
 * Event listeners
 */
refreshBtn.addEventListener('click', refreshStatus);
goBtn.addEventListener('click', navigateToAddress);

/**
 * Initialize popup
 */
refreshStatus();

// Refresh every 5 seconds while popup is open
setInterval(refreshStatus, 5000);
