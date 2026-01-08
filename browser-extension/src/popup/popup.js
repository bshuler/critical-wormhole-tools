/**
 * Wormhole Browser Extension - Popup Script
 * Standalone mode - no daemon required
 */

// DOM elements
const statusIndicator = document.getElementById('statusIndicator');
const statusValue = document.getElementById('statusValue');
const daemonWarning = document.getElementById('daemonWarning');
const refreshBtn = document.getElementById('refreshBtn');
const addressInput = document.getElementById('addressInput');
const goBtn = document.getElementById('goBtn');
const connectionsList = document.getElementById('connectionsList');

/**
 * Update UI with status
 */
function updateStatus(status) {
  // In standalone mode, we're always "ready"
  statusIndicator.classList.add('connected');
  statusValue.textContent = 'Ready (Standalone)';
  daemonWarning.style.display = 'none';
  goBtn.disabled = false;

  // Show connection count if any
  if (status.connections && Object.keys(status.connections).length > 0) {
    statusValue.textContent = `${Object.keys(status.connections).length} Active Connection(s)`;
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
        <div style="font-size: 11px; color: #888; margin-top: 4px;">
          Type "wh" in the URL bar to connect
        </div>
      </li>
    `;
    return;
  }

  connectionsList.innerHTML = Object.entries(connections).map(([address, data]) => `
    <li class="connection">
      <div class="icon">&#127744;</div>
      <div class="info">
        <div class="address" title="${address}">${formatAddress(address)}</div>
        <div class="code">${data.code || data.state || 'connected'}</div>
      </div>
      <button class="disconnect-btn" data-address="${address}" title="Disconnect">&#10005;</button>
    </li>
  `).join('');

  // Add disconnect handlers
  document.querySelectorAll('.disconnect-btn').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.stopPropagation();
      const address = btn.dataset.address;
      await chrome.runtime.sendMessage({ type: 'DISCONNECT', address });
      refreshStatus();
    });
  });
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
 * Refresh status
 */
async function refreshStatus() {
  statusValue.textContent = 'Checking...';

  try {
    const response = await chrome.runtime.sendMessage({ type: 'GET_STATUS' });
    updateStatus(response);
    updateConnections(response.connections);
  } catch (e) {
    console.error('Failed to get status:', e);
    // Still show ready in standalone mode
    statusIndicator.classList.add('connected');
    statusValue.textContent = 'Ready (Standalone)';
    daemonWarning.style.display = 'none';
    goBtn.disabled = false;
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
  if (!address.startsWith('wh://')) {
    // Check if it's a wormhole code (e.g., 7-guitar-sunset)
    if (/^\d+-[a-z]+-[a-z]+$/i.test(address)) {
      // It's a code, use as-is
    } else if (!address.includes('.')) {
      // Add .wns suffix if no TLD
      address = address + '.wns';
    }
  }

  // Show connecting state
  goBtn.disabled = true;
  goBtn.textContent = 'Connecting...';

  try {
    // Generate connection ID for navigation tracking
    const connectionId = 'conn-' + Math.random().toString(36).substring(2, 10);

    // Navigate to the viewer page - let it handle the connection
    const viewerUrl = chrome.runtime.getURL('viewer.html') +
      `?address=${encodeURIComponent(address)}` +
      `&connectionId=${encodeURIComponent(connectionId)}` +
      `&path=/`;

    // Open in new tab
    chrome.tabs.create({ url: viewerUrl });

    // Add to recent addresses
    await addRecentAddress(address);

    // Clear input
    addressInput.value = '';

    // Refresh to show connection (will appear once viewer connects)
    refreshStatus();
  } catch (e) {
    console.error('Failed to connect:', e);
    alert(`Connection failed: ${e.message}`);
  } finally {
    goBtn.disabled = false;
    goBtn.textContent = 'Go';
  }
}

/**
 * Add address to recent list
 */
async function addRecentAddress(address) {
  try {
    const stored = await chrome.storage.local.get(['recentAddresses']);
    let recent = stored.recentAddresses || [];

    // Remove if already exists
    recent = recent.filter(a => a !== address);

    // Add to front
    recent.unshift(address);

    // Keep only last 10
    recent = recent.slice(0, 10);

    await chrome.storage.local.set({ recentAddresses: recent });
  } catch (e) {
    console.error('Failed to save recent address:', e);
  }
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
 * Open settings page
 */
function openSettings() {
  chrome.runtime.openOptionsPage();
}

/**
 * Show saved addresses
 */
async function showSavedAddresses() {
  try {
    const response = await chrome.runtime.sendMessage({ type: 'GET_SAVED_ADDRESSES' });
    if (response.success && Object.keys(response.addresses).length > 0) {
      const dropdown = document.createElement('div');
      dropdown.className = 'saved-addresses-dropdown';
      dropdown.innerHTML = `
        <div class="dropdown-header">Saved Addresses</div>
        ${Object.entries(response.addresses).map(([addr, code]) => `
          <div class="dropdown-item" data-address="${addr}">
            <span class="addr">${formatAddress(addr)}</span>
            <span class="code">${code}</span>
          </div>
        `).join('')}
      `;

      // Position and show dropdown
      const inputRect = addressInput.getBoundingClientRect();
      dropdown.style.position = 'absolute';
      dropdown.style.top = `${inputRect.bottom + 2}px`;
      dropdown.style.left = `${inputRect.left}px`;
      dropdown.style.width = `${inputRect.width}px`;

      document.body.appendChild(dropdown);

      // Handle clicks
      dropdown.querySelectorAll('.dropdown-item').forEach(item => {
        item.addEventListener('click', () => {
          addressInput.value = item.dataset.address;
          dropdown.remove();
        });
      });

      // Remove on click outside
      setTimeout(() => {
        document.addEventListener('click', function handler(e) {
          if (!dropdown.contains(e.target)) {
            dropdown.remove();
            document.removeEventListener('click', handler);
          }
        });
      }, 0);
    }
  } catch (e) {
    console.error('Failed to get saved addresses:', e);
  }
}

/**
 * Event listeners
 */
refreshBtn.addEventListener('click', refreshStatus);
goBtn.addEventListener('click', navigateToAddress);
document.getElementById('settingsLink')?.addEventListener('click', (e) => {
  e.preventDefault();
  openSettings();
});

// Show saved addresses on input focus
addressInput.addEventListener('focus', () => {
  if (!addressInput.value) {
    showSavedAddresses();
  }
});

/**
 * Initialize popup
 */
refreshStatus();

// Refresh every 5 seconds while popup is open
setInterval(refreshStatus, 5000);
