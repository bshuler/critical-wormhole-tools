/**
 * Wormhole Browser Extension - Settings Page
 *
 * Manages relay configuration, security settings, and daemon options.
 */

// Default settings
const DEFAULT_SETTINGS = {
  relays: [
    {
      name: 'public',
      mailboxUrl: 'ws://relay.magic-wormhole.io:4000/v1',
      transitUrl: 'tcp:transit.magic-wormhole.io:4001',
      description: 'Official Magic Wormhole relay',
      isDefault: true
    }
  ],
  codeLength: 2,
  daemonPort: 9475,
  debugMode: false,
  autoConnect: false
};

// Current settings (loaded from storage)
let settings = { ...DEFAULT_SETTINGS };
let editingRelayIndex = -1;

// DOM elements
const relayList = document.getElementById('relayList');
const addRelayBtn = document.getElementById('addRelayBtn');
const relayModal = document.getElementById('relayModal');
const modalTitle = document.getElementById('modalTitle');
const closeModalBtn = document.getElementById('closeModalBtn');
const cancelRelayBtn = document.getElementById('cancelRelayBtn');
const saveRelayBtn = document.getElementById('saveRelayBtn');

const relayNameInput = document.getElementById('relayName');
const relayMailboxInput = document.getElementById('relayMailbox');
const relayTransitInput = document.getElementById('relayTransit');
const relayDescriptionInput = document.getElementById('relayDescription');
const relayDefaultInput = document.getElementById('relayDefault');

const codeLengthSelect = document.getElementById('codeLength');
const daemonPortInput = document.getElementById('daemonPort');
const debugModeInput = document.getElementById('debugMode');
const autoConnectInput = document.getElementById('autoConnect');

const advancedToggle = document.getElementById('advancedToggle');
const advancedContent = document.getElementById('advancedContent');

const resetBtn = document.getElementById('resetBtn');
const exportBtn = document.getElementById('exportBtn');
const importBtn = document.getElementById('importBtn');
const syncFromCliBtn = document.getElementById('syncFromCliBtn');

/**
 * Load settings from chrome.storage
 */
async function loadSettings() {
  try {
    const result = await chrome.storage.sync.get('settings');
    if (result.settings) {
      settings = { ...DEFAULT_SETTINGS, ...result.settings };
    }
    renderSettings();
  } catch (e) {
    console.error('Failed to load settings:', e);
    showNotification('Failed to load settings', true);
  }
}

/**
 * Save settings to chrome.storage
 */
async function saveSettings() {
  try {
    await chrome.storage.sync.set({ settings });
    showNotification('Settings saved');

    // Notify background script of settings change
    chrome.runtime.sendMessage({ type: 'SETTINGS_UPDATED', settings });
  } catch (e) {
    console.error('Failed to save settings:', e);
    showNotification('Failed to save settings', true);
  }
}

/**
 * Render all settings in the UI
 */
function renderSettings() {
  renderRelayList();
  codeLengthSelect.value = settings.codeLength;
  daemonPortInput.value = settings.daemonPort;
  debugModeInput.checked = settings.debugMode;
  autoConnectInput.checked = settings.autoConnect;
}

/**
 * Render the relay list
 */
function renderRelayList() {
  if (!settings.relays || settings.relays.length === 0) {
    relayList.innerHTML = `
      <div class="empty-state">
        <p>No relays configured. Add one to get started.</p>
      </div>
    `;
    return;
  }

  relayList.innerHTML = settings.relays.map((relay, index) => `
    <div class="relay-item${relay.isDefault ? ' default' : ''}" data-index="${index}">
      <div class="relay-info">
        <div class="relay-name">
          ${escapeHtml(relay.name)}
          ${relay.isDefault ? '<span class="default-badge">default</span>' : ''}
        </div>
        <div class="relay-urls">
          ${escapeHtml(relay.mailboxUrl)}
        </div>
        ${relay.description ? `<div class="relay-description">${escapeHtml(relay.description)}</div>` : ''}
      </div>
      <div class="relay-actions">
        ${!relay.isDefault ? `<button class="set-default" title="Set as default">&#9733;</button>` : ''}
        <button class="edit" title="Edit">&#9998;</button>
        ${relay.name !== 'public' ? `<button class="delete" title="Delete">&#128465;</button>` : ''}
      </div>
    </div>
  `).join('');

  // Add event listeners
  relayList.querySelectorAll('.relay-item').forEach(item => {
    const index = parseInt(item.dataset.index);

    const setDefaultBtn = item.querySelector('.set-default');
    if (setDefaultBtn) {
      setDefaultBtn.addEventListener('click', () => setDefaultRelay(index));
    }

    const editBtn = item.querySelector('.edit');
    if (editBtn) {
      editBtn.addEventListener('click', () => openEditRelayModal(index));
    }

    const deleteBtn = item.querySelector('.delete');
    if (deleteBtn) {
      deleteBtn.addEventListener('click', () => deleteRelay(index));
    }
  });
}

/**
 * Open modal to add a new relay
 */
function openAddRelayModal() {
  editingRelayIndex = -1;
  modalTitle.textContent = 'Add Relay';
  relayNameInput.value = '';
  relayMailboxInput.value = '';
  relayTransitInput.value = '';
  relayDescriptionInput.value = '';
  relayDefaultInput.checked = false;
  relayModal.style.display = 'flex';
}

/**
 * Open modal to edit an existing relay
 */
function openEditRelayModal(index) {
  editingRelayIndex = index;
  const relay = settings.relays[index];
  modalTitle.textContent = 'Edit Relay';
  relayNameInput.value = relay.name;
  relayMailboxInput.value = relay.mailboxUrl;
  relayTransitInput.value = relay.transitUrl;
  relayDescriptionInput.value = relay.description || '';
  relayDefaultInput.checked = relay.isDefault;
  relayModal.style.display = 'flex';
}

/**
 * Close the relay modal
 */
function closeRelayModal() {
  relayModal.style.display = 'none';
  editingRelayIndex = -1;
}

/**
 * Save relay from modal form
 */
function saveRelay() {
  const name = relayNameInput.value.trim();
  const mailboxUrl = relayMailboxInput.value.trim();
  const transitUrl = relayTransitInput.value.trim();
  const description = relayDescriptionInput.value.trim();
  const isDefault = relayDefaultInput.checked;

  // Validation
  if (!name) {
    showNotification('Name is required', true);
    return;
  }
  if (!mailboxUrl) {
    showNotification('Mailbox URL is required', true);
    return;
  }
  if (!transitUrl) {
    showNotification('Transit URL is required', true);
    return;
  }

  // Check for duplicate names (when adding or renaming)
  const existingIndex = settings.relays.findIndex(r => r.name.toLowerCase() === name.toLowerCase());
  if (existingIndex !== -1 && existingIndex !== editingRelayIndex) {
    showNotification('A relay with this name already exists', true);
    return;
  }

  const relay = {
    name,
    mailboxUrl,
    transitUrl,
    description,
    isDefault
  };

  // If setting as default, unset others
  if (isDefault) {
    settings.relays.forEach(r => r.isDefault = false);
  }

  if (editingRelayIndex === -1) {
    // Adding new relay
    settings.relays.push(relay);
  } else {
    // Editing existing relay
    settings.relays[editingRelayIndex] = relay;
  }

  // Ensure at least one relay is default
  if (!settings.relays.some(r => r.isDefault)) {
    settings.relays[0].isDefault = true;
  }

  closeRelayModal();
  saveSettings();
  renderRelayList();
}

/**
 * Delete a relay
 */
function deleteRelay(index) {
  const relay = settings.relays[index];

  if (relay.name === 'public') {
    showNotification('Cannot delete the public relay', true);
    return;
  }

  if (!confirm(`Delete relay "${relay.name}"?`)) {
    return;
  }

  const wasDefault = relay.isDefault;
  settings.relays.splice(index, 1);

  // If deleted relay was default, set first one as default
  if (wasDefault && settings.relays.length > 0) {
    settings.relays[0].isDefault = true;
  }

  saveSettings();
  renderRelayList();
}

/**
 * Set a relay as the default
 */
function setDefaultRelay(index) {
  settings.relays.forEach((r, i) => {
    r.isDefault = (i === index);
  });
  saveSettings();
  renderRelayList();
}

/**
 * Toggle advanced section
 */
function toggleAdvanced() {
  const isExpanded = advancedContent.style.display !== 'none';
  advancedContent.style.display = isExpanded ? 'none' : 'block';
  advancedToggle.classList.toggle('expanded', !isExpanded);
}

/**
 * Reset to default settings
 */
function resetToDefaults() {
  if (!confirm('Reset all settings to defaults? This cannot be undone.')) {
    return;
  }

  settings = { ...DEFAULT_SETTINGS };
  saveSettings();
  renderSettings();
  showNotification('Settings reset to defaults');
}

/**
 * Export settings to JSON file
 */
function exportSettings() {
  const blob = new Blob([JSON.stringify(settings, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'wormhole-settings.json';
  a.click();
  URL.revokeObjectURL(url);
  showNotification('Settings exported');
}

/**
 * Import settings from JSON file
 */
function importSettings() {
  const input = document.createElement('input');
  input.type = 'file';
  input.accept = '.json';
  input.onchange = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    try {
      const text = await file.text();
      const imported = JSON.parse(text);

      // Validate imported settings
      if (!imported.relays || !Array.isArray(imported.relays)) {
        throw new Error('Invalid settings file');
      }

      settings = { ...DEFAULT_SETTINGS, ...imported };
      saveSettings();
      renderSettings();
      showNotification('Settings imported');
    } catch (err) {
      console.error('Import failed:', err);
      showNotification('Failed to import settings: ' + err.message, true);
    }
  };
  input.click();
}

/**
 * Sync relays from CLI configuration via daemon
 */
async function syncFromCli() {
  const daemonPort = settings.daemonPort || 9475;

  try {
    syncFromCliBtn.disabled = true;
    syncFromCliBtn.textContent = 'Syncing...';

    const response = await fetch(`http://localhost:${daemonPort}/config/relays`);

    if (!response.ok) {
      throw new Error(`Daemon returned ${response.status}`);
    }

    const data = await response.json();

    if (!data.relays || !Array.isArray(data.relays)) {
      throw new Error('Invalid response from daemon');
    }

    // Merge CLI relays with existing relays
    // CLI relays take precedence for matching names
    const existingByName = new Map(settings.relays.map(r => [r.name, r]));

    // Add/update CLI relays
    for (const cliRelay of data.relays) {
      existingByName.set(cliRelay.name, {
        name: cliRelay.name,
        mailboxUrl: cliRelay.mailboxUrl,
        transitUrl: cliRelay.transitUrl,
        description: cliRelay.description || '',
        isDefault: cliRelay.isDefault
      });
    }

    // Convert back to array
    settings.relays = Array.from(existingByName.values());

    // Ensure at least one relay is default
    if (!settings.relays.some(r => r.isDefault) && settings.relays.length > 0) {
      settings.relays[0].isDefault = true;
    }

    saveSettings();
    renderRelayList();
    showNotification(`Synced ${data.relays.length} relay(s) from CLI config`);

  } catch (err) {
    console.error('Sync from CLI failed:', err);
    if (err.message.includes('Failed to fetch')) {
      showNotification('Daemon not running. Start with: wh daemon start', true);
    } else {
      showNotification('Failed to sync: ' + err.message, true);
    }
  } finally {
    syncFromCliBtn.disabled = false;
    syncFromCliBtn.textContent = 'Sync from CLI';
  }
}

/**
 * Show a notification
 */
function showNotification(message, isError = false) {
  const notification = document.createElement('div');
  notification.className = 'notification' + (isError ? ' error' : '');
  notification.textContent = message;
  document.body.appendChild(notification);

  setTimeout(() => {
    notification.remove();
  }, 3000);
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

/**
 * Handle setting changes
 */
function handleSettingChange(key, value) {
  settings[key] = value;
  saveSettings();
}

// Event listeners
addRelayBtn.addEventListener('click', openAddRelayModal);
closeModalBtn.addEventListener('click', closeRelayModal);
cancelRelayBtn.addEventListener('click', closeRelayModal);
saveRelayBtn.addEventListener('click', saveRelay);

codeLengthSelect.addEventListener('change', () => handleSettingChange('codeLength', parseInt(codeLengthSelect.value)));
daemonPortInput.addEventListener('change', () => handleSettingChange('daemonPort', parseInt(daemonPortInput.value)));
debugModeInput.addEventListener('change', () => handleSettingChange('debugMode', debugModeInput.checked));
autoConnectInput.addEventListener('change', () => handleSettingChange('autoConnect', autoConnectInput.checked));

advancedToggle.addEventListener('click', toggleAdvanced);
resetBtn.addEventListener('click', resetToDefaults);
exportBtn.addEventListener('click', exportSettings);
importBtn.addEventListener('click', importSettings);
syncFromCliBtn.addEventListener('click', syncFromCli);

// Close modal on backdrop click
relayModal.addEventListener('click', (e) => {
  if (e.target === relayModal) {
    closeRelayModal();
  }
});

// Close modal on Escape key
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape' && relayModal.style.display !== 'none') {
    closeRelayModal();
  }
});

// Initialize
loadSettings();
