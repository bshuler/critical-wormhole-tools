// External JavaScript file for testing

console.log('[External Script] app.js loaded!');

// Mark that external script loaded
window.externalScriptLoaded = true;

// Update indicator
const indicator = document.getElementById('external-script-indicator');
if (indicator) {
  indicator.textContent = 'External script loaded!';
  indicator.style.color = '#2ecc71';
}

// Test fetch API
async function testFetchApi() {
  const resultEl = document.getElementById('fetch-result');
  if (!resultEl) return;

  resultEl.textContent = 'Fetching /api/data.json...';

  try {
    const response = await fetch('/api/data.json');
    const data = await response.json();
    resultEl.textContent = 'Fetch result:\n' + JSON.stringify(data, null, 2);
    console.log('[External Script] Fetch successful:', data);
  } catch (error) {
    resultEl.textContent = 'Fetch error: ' + error.message;
    console.error('[External Script] Fetch error:', error);
  }
}

// Test localStorage
function testLocalStorage() {
  const resultEl = document.getElementById('storage-result');
  if (!resultEl) return;

  // Save a value
  const testValue = 'test-value-' + Date.now();
  localStorage.setItem('wh-test-key', testValue);

  // Read it back
  const readValue = localStorage.getItem('wh-test-key');

  // Display all storage
  const allKeys = [];
  for (let i = 0; i < localStorage.length; i++) {
    const key = localStorage.key(i);
    allKeys.push(key + ': ' + localStorage.getItem(key));
  }

  resultEl.textContent = 'localStorage test:\n' +
    'Set: wh-test-key = ' + testValue + '\n' +
    'Get: ' + readValue + '\n' +
    'Match: ' + (testValue === readValue) + '\n' +
    'All keys:\n' + allKeys.join('\n');

  console.log('[External Script] localStorage test complete');
}

// Test sessionStorage
function testSessionStorage() {
  const resultEl = document.getElementById('session-storage-result');
  if (!resultEl) return;

  const testValue = 'session-value-' + Date.now();
  sessionStorage.setItem('wh-session-key', testValue);
  const readValue = sessionStorage.getItem('wh-session-key');

  resultEl.textContent = 'sessionStorage test:\n' +
    'Set: wh-session-key = ' + testValue + '\n' +
    'Get: ' + readValue + '\n' +
    'Match: ' + (testValue === readValue);

  console.log('[External Script] sessionStorage test complete');
}

// Test cookies
function testCookies() {
  const resultEl = document.getElementById('cookie-result');
  if (!resultEl) return;

  // Set a cookie
  document.cookie = 'wh-test-cookie=cookie-value-' + Date.now();

  // Read cookies
  resultEl.textContent = 'document.cookie:\n' + document.cookie;

  console.log('[External Script] Cookie test complete');
}

// Test window.location
function testLocation() {
  const resultEl = document.getElementById('location-result');
  if (!resultEl) return;

  resultEl.textContent = 'window.location properties:\n' +
    'href: ' + window.location.href + '\n' +
    'pathname: ' + window.location.pathname + '\n' +
    'host: ' + window.location.host + '\n' +
    'hostname: ' + window.location.hostname + '\n' +
    'origin: ' + window.location.origin + '\n' +
    'protocol: ' + window.location.protocol;

  console.log('[External Script] Location test complete');
}

// Test XHR
function testXHR() {
  const resultEl = document.getElementById('xhr-result');
  if (!resultEl) return;

  resultEl.textContent = 'Making XHR request...';

  const xhr = new XMLHttpRequest();
  xhr.open('GET', '/api/data.json');
  xhr.onload = function() {
    resultEl.textContent = 'XHR result (status ' + xhr.status + '):\n' + xhr.responseText;
    console.log('[External Script] XHR successful');
  };
  xhr.onerror = function(e) {
    resultEl.textContent = 'XHR error: ' + e;
    console.error('[External Script] XHR error:', e);
  };
  xhr.send();
}

// Expose functions globally
window.testFetchApi = testFetchApi;
window.testLocalStorage = testLocalStorage;
window.testSessionStorage = testSessionStorage;
window.testCookies = testCookies;
window.testLocation = testLocation;
window.testXHR = testXHR;

console.log('[External Script] All functions registered');
