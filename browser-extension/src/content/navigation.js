/**
 * Content script for intercepting navigation within wormhole pages.
 *
 * Injected into pages served through the wormhole to handle link clicks
 * and form submissions, routing them back through the wormhole connection.
 */

(function() {
  // Get the wormhole address from the page's data attribute
  const whAddress = document.body.dataset.whAddress;
  const whConnectionId = document.body.dataset.whConnectionId;

  if (!whAddress) {
    console.log('[WH Navigation] No wormhole address found, skipping navigation interception');
    return;
  }

  console.log('[WH Navigation] Intercepting navigation for:', whAddress);

  /**
   * Handle link clicks
   */
  document.addEventListener('click', async (event) => {
    // Find the closest anchor element
    const link = event.target.closest('a');
    if (!link) return;

    const href = link.getAttribute('href');
    if (!href) return;

    // Skip external links, javascript:, mailto:, etc.
    if (href.startsWith('http://') || href.startsWith('https://') ||
        href.startsWith('javascript:') || href.startsWith('mailto:') ||
        href.startsWith('tel:') || href.startsWith('#')) {
      return;
    }

    // This is an internal link - intercept it
    event.preventDefault();
    event.stopPropagation();

    console.log('[WH Navigation] Intercepted link click:', href);

    // Resolve relative paths
    const currentPath = document.body.dataset.whPath || '/';
    const newPath = resolvePath(currentPath, href);

    // Show loading state
    showLoading();

    try {
      // Request the new page through the background script
      const response = await chrome.runtime.sendMessage({
        type: 'NAVIGATE',
        address: whAddress,
        connectionId: whConnectionId,
        path: newPath
      });

      if (response.success) {
        // Update the page content
        updatePage(response.data, newPath);
      } else {
        showError(response.error || 'Navigation failed');
      }
    } catch (error) {
      console.error('[WH Navigation] Error:', error);
      showError(error.message);
    }
  }, true);

  /**
   * Handle form submissions
   */
  document.addEventListener('submit', async (event) => {
    const form = event.target;
    const action = form.getAttribute('action') || document.body.dataset.whPath || '/';
    const method = (form.getAttribute('method') || 'GET').toUpperCase();

    // Skip external form submissions
    if (action.startsWith('http://') || action.startsWith('https://')) {
      return;
    }

    event.preventDefault();
    event.stopPropagation();

    console.log('[WH Navigation] Intercepted form submit:', method, action);

    // Collect form data
    const formData = new FormData(form);
    const data = {};
    for (const [key, value] of formData.entries()) {
      data[key] = value;
    }

    // Resolve path
    const currentPath = document.body.dataset.whPath || '/';
    const newPath = resolvePath(currentPath, action);

    showLoading();

    try {
      const response = await chrome.runtime.sendMessage({
        type: 'NAVIGATE',
        address: whAddress,
        connectionId: whConnectionId,
        path: newPath,
        method: method,
        body: data
      });

      if (response.success) {
        updatePage(response.data, newPath);
      } else {
        showError(response.error || 'Form submission failed');
      }
    } catch (error) {
      console.error('[WH Navigation] Error:', error);
      showError(error.message);
    }
  }, true);

  /**
   * Resolve a relative path against a base path
   */
  function resolvePath(base, relative) {
    if (relative.startsWith('/')) {
      return relative;
    }

    // Remove filename from base if present
    const baseDir = base.replace(/\/[^\/]*$/, '/');

    // Handle ../ and ./
    let path = baseDir + relative;

    // Normalize path (remove ../ and ./)
    const parts = path.split('/');
    const result = [];
    for (const part of parts) {
      if (part === '..') {
        result.pop();
      } else if (part !== '.' && part !== '') {
        result.push(part);
      }
    }

    return '/' + result.join('/');
  }

  /**
   * Show loading indicator
   */
  function showLoading() {
    let loader = document.getElementById('wh-loader');
    if (!loader) {
      loader = document.createElement('div');
      loader.id = 'wh-loader';
      loader.innerHTML = `
        <style>
          #wh-loader {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
            background: linear-gradient(90deg, #667eea, #764ba2);
            animation: wh-loading 1s ease-in-out infinite;
            z-index: 999999;
          }
          @keyframes wh-loading {
            0% { transform: translateX(-100%); }
            50% { transform: translateX(0%); }
            100% { transform: translateX(100%); }
          }
        </style>
      `;
      document.body.appendChild(loader);
    }
    loader.style.display = 'block';
  }

  /**
   * Hide loading indicator
   */
  function hideLoading() {
    const loader = document.getElementById('wh-loader');
    if (loader) {
      loader.style.display = 'none';
    }
  }

  /**
   * Show error message
   */
  function showError(message) {
    hideLoading();

    let error = document.getElementById('wh-error');
    if (!error) {
      error = document.createElement('div');
      error.id = 'wh-error';
      document.body.appendChild(error);
    }

    error.innerHTML = `
      <style>
        #wh-error {
          position: fixed;
          top: 20px;
          right: 20px;
          background: #f8d7da;
          color: #721c24;
          padding: 15px 20px;
          border-radius: 8px;
          box-shadow: 0 4px 12px rgba(0,0,0,0.15);
          z-index: 999999;
          animation: wh-fade-in 0.3s ease;
        }
        @keyframes wh-fade-in {
          from { opacity: 0; transform: translateY(-10px); }
          to { opacity: 1; transform: translateY(0); }
        }
      </style>
      <strong>Error:</strong> ${message}
    `;

    setTimeout(() => {
      error.remove();
    }, 5000);
  }

  /**
   * Update the page with new content
   */
  function updatePage(response, newPath) {
    hideLoading();

    if (response.status >= 400) {
      showError(`HTTP ${response.status}: ${response.statusText || 'Error'}`);
      return;
    }

    // Parse the HTML
    const parser = new DOMParser();
    const doc = parser.parseFromString(response.body, 'text/html');

    // Update the page content
    // Preserve wormhole data attributes
    const newBody = doc.body;
    newBody.dataset.whAddress = whAddress;
    newBody.dataset.whConnectionId = whConnectionId;
    newBody.dataset.whPath = newPath;

    // Replace body content
    document.body.innerHTML = newBody.innerHTML;
    document.body.dataset.whAddress = whAddress;
    document.body.dataset.whConnectionId = whConnectionId;
    document.body.dataset.whPath = newPath;

    // Update title if present
    const newTitle = doc.querySelector('title');
    if (newTitle) {
      document.title = newTitle.textContent;
    }

    // Update head styles/meta if needed
    const newStyles = doc.querySelectorAll('style, link[rel="stylesheet"]');
    const oldStyles = document.querySelectorAll('style:not(#wh-loader style):not(#wh-error style), link[rel="stylesheet"]');
    oldStyles.forEach(s => s.remove());
    newStyles.forEach(s => document.head.appendChild(s.cloneNode(true)));

    // Scroll to top
    window.scrollTo(0, 0);

    console.log('[WH Navigation] Page updated to:', newPath);
  }
})();
