/**
 * Hello World Wormhole Demo Script
 *
 * This script is loaded remotely through a Magic Wormhole connection.
 * It modifies the DOM to prove that external JavaScript execution works.
 */

// Update message to show content was served through wormhole
document.getElementById('message').textContent =
  'This page was served through a Magic Wormhole connection!';

// Update JS status to prove this file was loaded and executed
const jsStatus = document.getElementById('js-status');
jsStatus.textContent = 'JavaScript loaded successfully';
jsStatus.classList.add('loaded');

// Add dynamic timestamp to prove script execution timing
const timestamp = document.getElementById('timestamp');
const now = new Date();
timestamp.textContent = `Page loaded at: ${now.toLocaleTimeString()} on ${now.toLocaleDateString()}`;

// Add a custom attribute to the body for easy test verification
document.body.setAttribute('data-wormhole-js-loaded', 'true');

// Log to console for debugging
console.log('[Wormhole Demo] External JavaScript executed successfully');
console.log('[Wormhole Demo] Load time:', now.toISOString());
