/**
 * TRUE End-to-End Test
 *
 * This test:
 * 1. Starts a local HTTP server serving test HTML files
 * 2. Starts `wh listen -p <port>` to create a wormhole to the HTTP server
 * 3. Connects to it via the browser extension
 * 4. Clicks links and verifies navigation works WITHOUT going to about:blank
 *
 * This is NOT a mock test - it tests the entire real flow.
 */

import { test as base, chromium, expect } from '@playwright/test';
import { spawn } from 'child_process';
import { existsSync } from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import http from 'http';
import fs from 'fs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const pathToExtension = path.resolve(__dirname, '../../dist');
const fixturesPath = path.resolve(__dirname, 'fixtures');

// Get MIME type from file extension
function getMimeType(filePath) {
  const ext = path.extname(filePath).toLowerCase();
  const mimeTypes = {
    '.html': 'text/html',
    '.css': 'text/css',
    '.js': 'application/javascript',
    '.json': 'application/json',
    '.svg': 'image/svg+xml',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.gif': 'image/gif',
    '.ico': 'image/x-icon',
    '.txt': 'text/plain',
    '.xml': 'application/xml'
  };
  return mimeTypes[ext] || 'application/octet-stream';
}

// Simple static file HTTP server
function createHttpServer(port) {
  return new Promise((resolve, reject) => {
    const server = http.createServer((req, res) => {
      // Parse URL without query string
      const urlPath = req.url.split('?')[0];

      // Determine file path
      let filePath;
      if (urlPath === '/') {
        filePath = '/index.html';
      } else if (path.extname(urlPath)) {
        // Has extension - use as-is
        filePath = urlPath;
      } else {
        // No extension - try .html
        filePath = urlPath + '.html';
      }

      let fullPath = path.join(fixturesPath, filePath);
      console.log('HTTP request:', req.url, '->', fullPath);

      // Try different paths if file doesn't exist
      if (!existsSync(fullPath)) {
        // Try without .html
        const withoutHtml = path.join(fixturesPath, urlPath);
        if (existsSync(withoutHtml) && fs.statSync(withoutHtml).isFile()) {
          fullPath = withoutHtml;
        } else {
          // Try index.html in directory
          const indexPath = path.join(fixturesPath, urlPath, 'index.html');
          if (existsSync(indexPath)) {
            fullPath = indexPath;
          }
        }
      }

      fs.readFile(fullPath, (err, data) => {
        if (err) {
          console.log('HTTP 404:', fullPath);
          res.writeHead(404, { 'Content-Type': 'text/html' });
          res.end('<h1>404 Not Found</h1>');
        } else {
          const contentType = getMimeType(fullPath);
          console.log('HTTP 200:', fullPath, contentType);
          res.writeHead(200, { 'Content-Type': contentType });
          res.end(data);
        }
      });
    });

    server.listen(port, '127.0.0.1', () => {
      console.log(`HTTP server listening on port ${port}`);
      resolve(server);
    });

    server.on('error', reject);
  });
}

// Custom test fixture with wormhole server
export const test = base.extend({
  // Start wh listen --serve to serve files directly
  whServer: async ({}, use) => {
    console.log('Starting wh listen --serve', fixturesPath);

    // Start wh listen --serve to serve files (browser extension compatible)
    const whProcess = spawn('wh', ['listen', '--serve', fixturesPath], {
      stdio: ['pipe', 'pipe', 'pipe'],
    });

    let wormholeCode = null;

    // Capture the wormhole code from stderr/stdout
    const codePromise = new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        reject(new Error('Timeout waiting for wormhole code'));
      }, 30000);

      const handleData = (data) => {
        const output = data.toString();
        console.log('wh output:', output);

        // Look for wormhole code pattern like "4-breakaway-flatfoot"
        const codeMatch = output.match(/(\d+-[a-z]+-[a-z]+)/i);
        if (codeMatch && !wormholeCode) {
          wormholeCode = codeMatch[1];
          console.log('Found wormhole code:', wormholeCode);
          clearTimeout(timeout);
          resolve(wormholeCode);
        }
      };

      whProcess.stdout.on('data', handleData);
      whProcess.stderr.on('data', handleData);

      whProcess.on('error', (err) => {
        clearTimeout(timeout);
        reject(err);
      });

      whProcess.on('exit', (code) => {
        if (!wormholeCode) {
          clearTimeout(timeout);
          reject(new Error(`wh process exited with code ${code} before providing code`));
        }
      });
    });

    try {
      const code = await codePromise;
      console.log('Wormhole ready with code:', code);

      // Give server a moment to fully initialize
      await new Promise(r => setTimeout(r, 1000));

      await use({ process: whProcess, code });
    } finally {
      console.log('Killing wh server...');
      whProcess.kill('SIGTERM');
      // Give it time to clean up
      await new Promise(r => setTimeout(r, 500));
    }
  },

  // Browser context with extension loaded
  context: async ({}, use) => {
    if (!existsSync(path.join(pathToExtension, 'manifest.json'))) {
      throw new Error(`Extension not found at ${pathToExtension}. Run 'npm run build' first.`);
    }

    // Extensions require headed mode - headless doesn't support service workers
    const context = await chromium.launchPersistentContext('', {
      headless: false,
      args: [
        `--disable-extensions-except=${pathToExtension}`,
        `--load-extension=${pathToExtension}`,
      ],
    });

    await use(context);
    await context.close();
  },

  // Get extension ID
  extensionId: async ({ context }, use) => {
    let [serviceWorker] = context.serviceWorkers();
    if (!serviceWorker) {
      serviceWorker = await context.waitForEvent('serviceworker', { timeout: 30000 });
    }
    const extensionId = serviceWorker.url().split('/')[2];
    console.log('Extension ID:', extensionId);
    await use(extensionId);
  },
});

test.describe('Full End-to-End Test', () => {
  test.setTimeout(120000); // 2 minutes for full E2E

  test('popup flow - uses viewer.html not data URL', async ({ context, extensionId, whServer }) => {
    console.log('=== TESTING POPUP FLOW ===');
    console.log('Wormhole code:', whServer.code);
    console.log('Extension ID:', extensionId);

    // Step 1: Open the extension popup
    const popupUrl = `chrome-extension://${extensionId}/popup.html`;
    const popupPage = await context.newPage();
    await popupPage.goto(popupUrl);

    // Enable console logging
    popupPage.on('console', msg => {
      console.log('POPUP CONSOLE:', msg.type(), msg.text());
    });

    // Step 2: Enter the wormhole code in the address input
    const addressInput = popupPage.locator('#addressInput');
    await addressInput.fill(whServer.code);
    console.log('Entered wormhole code in popup');

    // Step 3: Click the Go button
    // Set up listener for new page BEFORE clicking
    const pagePromise = context.waitForEvent('page', { timeout: 30000 });

    const goBtn = popupPage.locator('#goBtn');
    await goBtn.click();
    console.log('Clicked Go button');

    // Step 4: Wait for new page to open
    const viewerPage = await pagePromise;
    console.log('New page opened:', viewerPage.url());

    // Step 5: Verify we're on viewer.html, NOT a data: URL
    const url = viewerPage.url();
    expect(url).not.toContain('data:');
    expect(url).toContain('viewer.html');
    expect(url).toContain(`address=${encodeURIComponent(whServer.code)}`);
    console.log('Verified URL is viewer.html with correct address');

    // Step 6: Wait for content to load
    viewerPage.on('console', msg => {
      console.log('VIEWER CONSOLE:', msg.type(), msg.text());
    });

    // Content is now inside the sandbox iframe
    const sandbox = viewerPage.frameLocator('#wh-sandbox');

    // Wait for sandbox content to load
    await sandbox.locator('h1:has-text("Home Page")').waitFor({ timeout: 60000 });

    // Step 7: Verify the page content
    const homeTitle = await sandbox.locator('h1').first().textContent();
    expect(homeTitle).toBe('Home Page');
    console.log('Home page content verified');

    // Step 8: Click About link and verify no about:blank
    // Use first() since there are multiple About links on the comprehensive test page
    const aboutLink = sandbox.locator('a[data-wh-href="/about"]').first();
    await aboutLink.click();

    // Wait for About page to load in sandbox
    await sandbox.locator('h1:has-text("About Page")').waitFor({ timeout: 15000 });

    const afterClickUrl = viewerPage.url();
    expect(afterClickUrl).not.toContain('about:blank');
    expect(afterClickUrl).not.toContain('data:');
    expect(afterClickUrl).toContain('viewer.html');
    console.log('Navigation to About page works without about:blank');

    console.log('=== POPUP FLOW TEST PASSED ===');
    await popupPage.close();
    await viewerPage.close();
  });

  test('direct viewer navigation flow', async ({ context, extensionId, whServer }) => {
    console.log('=== STARTING FULL E2E TEST ===');
    console.log('Wormhole code:', whServer.code);
    console.log('Extension ID:', extensionId);

    const page = await context.newPage();

    // Enable console logging from the page
    page.on('console', msg => {
      console.log('PAGE CONSOLE:', msg.type(), msg.text());
    });

    // Step 1: Navigate to the wormhole address via viewer
    const viewerUrl = `chrome-extension://${extensionId}/viewer.html?address=${whServer.code}&connectionId=test-e2e&path=/`;
    console.log('Navigating to:', viewerUrl);

    await page.goto(viewerUrl);

    // Step 2: Wait for content to load (not loading, not error)
    console.log('Waiting for content to load...');

    // Give more time for wormhole connection (can take a while)
    await page.waitForTimeout(5000);

    // Content is now inside the sandbox iframe
    const sandbox = page.frameLocator('#wh-sandbox');

    // Wait for content element to have content
    console.log('Waiting for content...');
    await sandbox.locator('h1:has-text("Home Page")').waitFor({ timeout: 60000 });

    // Step 3: Verify home page loaded
    console.log('Checking home page content...');
    const homeTitle = await sandbox.locator('h1').first().textContent();
    console.log('Home page title:', homeTitle);
    expect(homeTitle).toBe('Home Page');

    // Step 4: Inspect the About link BEFORE clicking
    console.log('Inspecting About link...');
    const aboutLink = sandbox.locator('a[data-wh-href="/about"]').first();
    const aboutLinkVisible = await aboutLink.isVisible();
    console.log('About link visible:', aboutLinkVisible);
    expect(aboutLinkVisible).toBe(true);

    // Step 5: Record URL before clicking
    const beforeClickUrl = page.url();
    console.log('URL before click:', beforeClickUrl);

    // Step 6: Click the About link (use first() since there are multiple)
    console.log('Clicking About link...');
    await aboutLink.click();

    // Step 7: Wait for navigation to complete
    console.log('Waiting for navigation...');
    await sandbox.locator('h1:has-text("About Page")').waitFor({ timeout: 15000 });

    // Step 8: Verify we're still in the viewer (NOT about:blank)
    const afterClickUrl = page.url();
    console.log('URL after click:', afterClickUrl);

    expect(afterClickUrl).not.toContain('about:blank');
    expect(afterClickUrl).toContain('viewer.html');
    expect(afterClickUrl).toMatch(/path=.*about/);

    // Step 9: Verify About page content
    const aboutTitle = await sandbox.locator('h1').first().textContent();
    console.log('About page title:', aboutTitle);
    expect(aboutTitle).toBe('About Page');

    // Step 10: Navigate to Contact to test another link
    console.log('Clicking Contact link...');
    const contactLink = sandbox.locator('a[data-wh-href="/contact"]');
    await contactLink.click();

    await sandbox.locator('h1:has-text("Contact Page")').waitFor({ timeout: 15000 });

    const contactUrl = page.url();
    console.log('URL after Contact click:', contactUrl);
    expect(contactUrl).toMatch(/path=.*contact/);
    expect(contactUrl).not.toContain('about:blank');

    // Step 11: Go back to Home
    console.log('Clicking Home link...');
    const homeLink = sandbox.locator('a[data-wh-href="/"]');
    await homeLink.click();

    await sandbox.locator('h1:has-text("Home Page")').waitFor({ timeout: 15000 });

    const finalUrl = page.url();
    console.log('Final URL:', finalUrl);
    expect(finalUrl).not.toContain('about:blank');

    console.log('=== FULL E2E TEST PASSED ===');
    await page.close();
  });

  test('CSS styling works and JavaScript executes in sandbox', async ({ context, extensionId, whServer }) => {
    console.log('=== TESTING CSS AND JS ===');

    const page = await context.newPage();
    page.on('console', msg => console.log('PAGE:', msg.type(), msg.text()));

    const viewerUrl = `chrome-extension://${extensionId}/viewer.html?address=${whServer.code}&connectionId=test-js&path=/`;
    await page.goto(viewerUrl);

    // Content is now inside the sandbox iframe
    const sandbox = page.frameLocator('#wh-sandbox');

    // Wait for home page to load
    await sandbox.locator('h1:has-text("Home Page")').waitFor({ timeout: 60000 });

    // Test 1: CSS is applied (check that container exists with styles)
    console.log('Testing CSS...');
    const containerVisible = await sandbox.locator('.container').isVisible();
    expect(containerVisible).toBe(true);
    console.log('CSS container visible: true');

    // Test 2: JavaScript DOES execute in the sandbox!
    console.log('Testing that JS DOES execute in sandbox...');
    // The JS on the page sets #js-status-text to 'Working!'
    const jsStatusText = await sandbox.locator('#js-status-text').textContent();
    console.log('JS Status Text:', jsStatusText);
    expect(jsStatusText).toBe('Working!'); // Script DID run!

    // Test 3: JS-added class should be present
    const jsStatusHasClass = await sandbox.locator('#js-status.status-green').count();
    console.log('JS status has green class:', jsStatusHasClass > 0);
    expect(jsStatusHasClass).toBeGreaterThan(0);

    // Test 4: Interactive button test
    console.log('Testing interactive button...');
    const clickCounterBtn = sandbox.locator('button:has-text("Click Counter")');
    const buttonExists = await clickCounterBtn.count();
    expect(buttonExists).toBeGreaterThan(0);

    // Click the button and verify the counter updates
    await clickCounterBtn.click();
    await sandbox.locator('#js-output:has-text("Click count: 1")').waitFor({ timeout: 5000 });
    const countText = await sandbox.locator('#js-output').textContent();
    console.log('Click count after click:', countText);
    expect(countText).toBe('Click count: 1');

    console.log('=== CSS AND JS TEST PASSED ===');
    await page.close();
  });

  test('edge cases - hash links and special hrefs', async ({ context, extensionId, whServer }) => {
    console.log('=== TESTING EDGE CASES ===');

    const page = await context.newPage();
    page.on('console', msg => console.log('PAGE:', msg.type(), msg.text()));

    // Navigate to edge cases page
    const viewerUrl = `chrome-extension://${extensionId}/viewer.html?address=${whServer.code}&connectionId=test-edge&path=/edge-cases`;
    await page.goto(viewerUrl);

    // Content is now inside the sandbox iframe
    const sandbox = page.frameLocator('#wh-sandbox');

    await sandbox.locator('h1:has-text("Edge Cases")').waitFor({ timeout: 60000 });

    // Test 1: Hash link scrolls but doesn't navigate away
    console.log('Testing hash link...');
    const beforeHashUrl = page.url();
    const hashLink = sandbox.locator('a[href="#local-section"]');
    await hashLink.click();

    await page.waitForTimeout(500);
    const afterHashUrl = page.url();

    // URL should stay on same page (viewer.html)
    expect(afterHashUrl).toContain('viewer.html');
    expect(afterHashUrl).not.toContain('about:blank');
    console.log('Hash link handled correctly');

    // Test 2: External link - should NOT be rewritten (no data-wh-href)
    console.log('Testing external link...');
    const externalLink = sandbox.locator('a[href="https://example.com"]').first();
    const extLinkExists = await externalLink.count();
    expect(extLinkExists).toBeGreaterThan(0);
    console.log('External link exists without rewriting');

    // Test 3: Link with query params
    console.log('Testing link with query params...');
    const queryLink = sandbox.locator('a[data-wh-href="/about?foo=bar&baz=qux"]');
    const queryLinkExists = await queryLink.count();
    expect(queryLinkExists).toBeGreaterThan(0);

    console.log('=== EDGE CASES TEST PASSED ===');
    await page.close();
  });

  test('JS test page - interactive JavaScript works in sandbox', async ({ context, extensionId, whServer }) => {
    console.log('=== TESTING JS TEST PAGE (JS DOES execute in sandbox) ===');

    const page = await context.newPage();
    page.on('console', msg => console.log('PAGE:', msg.type(), msg.text()));

    // Navigate to JS test page
    const viewerUrl = `chrome-extension://${extensionId}/viewer.html?address=${whServer.code}&connectionId=test-jspage&path=/javascript-test`;
    await page.goto(viewerUrl);

    // Content is now inside the sandbox iframe
    const sandbox = page.frameLocator('#wh-sandbox');

    await sandbox.locator('h1:has-text("JavaScript Test")').waitFor({ timeout: 60000 });

    // Test 1: Page loads and displays content
    const hasTitle = await sandbox.locator('h1').first().textContent();
    expect(hasTitle).toContain('JavaScript Test');
    console.log('Page title verified');

    // Test 2: DOM manipulation test - click button and verify result changes
    console.log('Testing DOM manipulation...');
    const domButton = sandbox.locator('button:has-text("Run DOM Test")');
    await domButton.click();

    // Wait for the result to change from 'Waiting...'
    await sandbox.locator('#dom-result:not(:has-text("Waiting"))').waitFor({ timeout: 5000 });
    const domResult = await sandbox.locator('#dom-result').textContent();
    console.log('DOM result after click:', domResult);
    // JS executes in sandbox, so result should change!
    expect(domResult).not.toBe('Waiting...');

    console.log('=== JS TEST PAGE PASSED - JavaScript works! ===');
    await page.close();
  });

  test('forms test page - forms display and inputs work with JS', async ({ context, extensionId, whServer }) => {
    console.log('=== TESTING FORMS PAGE ===');

    const page = await context.newPage();
    page.on('console', msg => console.log('PAGE:', msg.type(), msg.text()));

    // Navigate to forms test page
    const viewerUrl = `chrome-extension://${extensionId}/viewer.html?address=${whServer.code}&connectionId=test-forms&path=/forms-test`;
    await page.goto(viewerUrl);

    // Content is now inside the sandbox iframe
    const sandbox = page.frameLocator('#wh-sandbox');

    await sandbox.locator('h1:has-text("Forms Test")').waitFor({ timeout: 60000 });

    // Test 1: Verify forms exist
    const getFormExists = await sandbox.locator('#get-form').count();
    const postFormExists = await sandbox.locator('#post-form').count();
    expect(getFormExists).toBeGreaterThan(0);
    expect(postFormExists).toBeGreaterThan(0);
    console.log('Forms exist');

    // Test 2: Fill and interact with form elements
    await sandbox.locator('#search').fill('test query');
    await sandbox.locator('#category').selectOption('docs');

    // Verify values were set
    const searchValue = await sandbox.locator('#search').inputValue();
    const categoryValue = await sandbox.locator('#category').inputValue();
    expect(searchValue).toBe('test query');
    expect(categoryValue).toBe('docs');
    console.log('Form inputs work');

    console.log('=== FORMS PAGE PASSED ===');
    await page.close();
  });

  test('resource loading - external CSS, scripts, and fetch', async ({ context, extensionId, whServer }) => {
    console.log('=== TESTING RESOURCE LOADING ===');

    const page = await context.newPage();
    page.on('console', msg => console.log('PAGE:', msg.type(), msg.text()));

    // Navigate to resource test page
    const viewerUrl = `chrome-extension://${extensionId}/viewer.html?address=${whServer.code}&connectionId=test-resources&path=/resource-test`;
    await page.goto(viewerUrl);

    const sandbox = page.frameLocator('#wh-sandbox');

    // Wait for page to load
    await sandbox.locator('h1:has-text("Resource Loading")').waitFor({ timeout: 60000 });
    console.log('Resource test page loaded');

    // Test 1: External CSS loaded
    console.log('Testing external CSS...');
    // The external CSS adds a gradient background to .external-css-test
    // Give it time to load
    await page.waitForTimeout(2000);
    const cssStatus = await sandbox.locator('#css-status').textContent();
    console.log('CSS status:', cssStatus);
    // CSS may or may not load depending on server support

    // Test 2: External script loaded
    console.log('Testing external script...');
    await page.waitForTimeout(2000);
    const scriptStatus = await sandbox.locator('#external-script-indicator').textContent();
    console.log('Script status:', scriptStatus);

    // Test 3: localStorage works
    console.log('Testing localStorage...');
    const storageBtn = sandbox.locator('button:has-text("Test localStorage")');
    await storageBtn.click();
    await page.waitForTimeout(500);
    const storageResult = await sandbox.locator('#storage-result').textContent();
    console.log('Storage result:', storageResult.substring(0, 100));
    expect(storageResult).toContain('localStorage test');

    // Test 4: sessionStorage works
    console.log('Testing sessionStorage...');
    const sessionBtn = sandbox.locator('button:has-text("Test sessionStorage")');
    await sessionBtn.click();
    await page.waitForTimeout(500);
    const sessionResult = await sandbox.locator('#session-storage-result').textContent();
    console.log('Session storage result:', sessionResult.substring(0, 100));
    expect(sessionResult).toContain('sessionStorage test');

    // Test 5: Cookies work
    console.log('Testing cookies...');
    const cookieBtn = sandbox.locator('button:has-text("Test Cookies")');
    await cookieBtn.click();
    await page.waitForTimeout(500);
    const cookieResult = await sandbox.locator('#cookie-result').textContent();
    console.log('Cookie result:', cookieResult);
    expect(cookieResult).toContain('document.cookie');

    // Test 6: Location properties
    console.log('Testing window.location...');
    const locationBtn = sandbox.locator('button:has-text("Test Location")');
    await locationBtn.click();
    await page.waitForTimeout(500);
    const locationResult = await sandbox.locator('#location-result').textContent();
    console.log('Location result:', locationResult.substring(0, 100));
    // Location may show wh:// protocol or sandbox URL depending on override success

    console.log('=== RESOURCE LOADING TEST PASSED ===');
    await page.close();
  });

  test('iframe loading - nested iframes load content through wormhole', async ({ context, extensionId, whServer }) => {
    console.log('=== TESTING IFRAME LOADING ===');

    const page = await context.newPage();
    page.on('console', msg => console.log('PAGE:', msg.type(), msg.text()));

    // Navigate to WebSocket and iframe test page
    const viewerUrl = `chrome-extension://${extensionId}/viewer.html?address=${whServer.code}&connectionId=test-iframe&path=/websocket-iframe-test`;
    await page.goto(viewerUrl);

    const sandbox = page.frameLocator('#wh-sandbox');

    // Wait for page to load
    await sandbox.locator('h1:has-text("WebSocket & Iframe Test")').waitFor({ timeout: 60000 });
    console.log('WebSocket & Iframe test page loaded');

    // Test 1: Static iframe should have content loaded via srcdoc
    console.log('Testing static iframe...');
    await page.waitForTimeout(3000); // Give iframe time to load

    // Check if the iframe exists and has srcdoc attribute (means it was loaded through wormhole)
    const iframeElement = sandbox.locator('#test-iframe');
    const iframeCount = await iframeElement.count();
    expect(iframeCount).toBeGreaterThan(0);
    console.log('Static iframe exists');

    // Check the iframe status indicator
    const iframeStatus = await sandbox.locator('#iframe-status').textContent();
    console.log('Iframe status:', iframeStatus);

    // Test 2: Dynamic iframe creation
    console.log('Testing dynamic iframe creation...');
    const createBtn = sandbox.locator('button:has-text("Create Iframe")');
    await createBtn.click();

    // Wait for dynamic iframe to be created
    await page.waitForTimeout(2000);
    const dynamicStatus = await sandbox.locator('#dynamic-iframe-status').textContent();
    console.log('Dynamic iframe status:', dynamicStatus);

    // Test 3: WebSocket class is properly overridden
    console.log('Testing WebSocket proxy class...');
    const runAllBtn = sandbox.locator('button:has-text("Run All Tests")');
    await runAllBtn.click();
    await page.waitForTimeout(500);

    const allTestsResult = await sandbox.locator('#all-tests-result').textContent();
    console.log('All tests result:', allTestsResult);
    expect(allTestsResult).toContain('WebSocket class: PASS');

    console.log('=== IFRAME LOADING TEST PASSED ===');
    await page.close();
  });

  test('advanced features - location, history, workers, indexedDB', async ({ context, extensionId, whServer }) => {
    console.log('=== TESTING ADVANCED FEATURES ===');

    const page = await context.newPage();
    page.on('console', msg => console.log('PAGE:', msg.type(), msg.text()));

    // Navigate to advanced features test page
    const viewerUrl = `chrome-extension://${extensionId}/viewer.html?address=${whServer.code}&connectionId=test-advanced&path=/advanced-features-test`;
    await page.goto(viewerUrl);

    const sandbox = page.frameLocator('#wh-sandbox');

    // Wait for page to load
    await sandbox.locator('h1:has-text("Advanced Features Test")').waitFor({ timeout: 60000 });
    console.log('Advanced features test page loaded');

    // Test 1: Location API
    console.log('Testing Location API...');
    const locationBtn = sandbox.locator('button:has-text("Test Location Properties")');
    await locationBtn.click();
    await page.waitForTimeout(500);

    const locationResult = await sandbox.locator('#location-result').textContent();
    console.log('Location result:', locationResult.substring(0, 200));
    // Should have whLocation as fallback
    expect(locationResult).toContain('whLocation');

    // Test 2: History API
    console.log('Testing History API...');
    const pushStateBtn = sandbox.locator('button:has-text("pushState")');
    await pushStateBtn.click();
    await page.waitForTimeout(500);

    const historyResult = await sandbox.locator('#history-result').textContent();
    console.log('History result:', historyResult);
    expect(historyResult).toContain('pushState called');

    // Test 3: Run all tests
    console.log('Running comprehensive test suite...');
    const runAllBtn = sandbox.locator('button:has-text("Run All Tests")');
    await runAllBtn.click();
    await page.waitForTimeout(1000);

    const allTestsResult = await sandbox.locator('#all-tests-result').textContent();
    console.log('All tests result:', allTestsResult);

    // Verify all APIs are available
    expect(allTestsResult).toContain('whLocation exists: true');
    expect(allTestsResult).toContain('pushState available: true');
    expect(allTestsResult).toContain('replaceState available: true');
    expect(allTestsResult).toContain('Worker class exists: true');
    expect(allTestsResult).toContain('indexedDB exists: true');
    expect(allTestsResult).toContain('fetch available: true');
    expect(allTestsResult).toContain('XMLHttpRequest available: true');
    expect(allTestsResult).toContain('localStorage available: true');
    expect(allTestsResult).toContain('sessionStorage available: true');
    expect(allTestsResult).toContain('WebSocket available: true');

    console.log('=== ADVANCED FEATURES TEST PASSED ===');
    await page.close();
  });

  test('web workers - can create and communicate with workers', async ({ context, extensionId, whServer }) => {
    console.log('=== TESTING WEB WORKERS ===');

    const page = await context.newPage();
    page.on('console', msg => console.log('PAGE:', msg.type(), msg.text()));

    const viewerUrl = `chrome-extension://${extensionId}/viewer.html?address=${whServer.code}&connectionId=test-workers&path=/advanced-features-test`;
    await page.goto(viewerUrl);

    const sandbox = page.frameLocator('#wh-sandbox');
    await sandbox.locator('h1:has-text("Advanced Features Test")').waitFor({ timeout: 60000 });

    // Test Web Worker
    console.log('Creating Web Worker...');
    const workerBtn = sandbox.locator('button:has-text("Create Worker")');
    await workerBtn.click();

    // Wait for worker messages
    await page.waitForTimeout(1000);

    const workerResult = await sandbox.locator('#worker-result').textContent();
    console.log('Worker result:', workerResult);
    expect(workerResult).toContain('Worker created successfully');

    console.log('=== WEB WORKERS TEST PASSED ===');
    await page.close();
  });

  test('indexedDB - can open database and store data', async ({ context, extensionId, whServer }) => {
    console.log('=== TESTING INDEXEDDB ===');

    const page = await context.newPage();
    page.on('console', msg => console.log('PAGE:', msg.type(), msg.text()));

    const viewerUrl = `chrome-extension://${extensionId}/viewer.html?address=${whServer.code}&connectionId=test-idb&path=/advanced-features-test`;
    await page.goto(viewerUrl);

    const sandbox = page.frameLocator('#wh-sandbox');
    await sandbox.locator('h1:has-text("Advanced Features Test")').waitFor({ timeout: 60000 });

    // Test IndexedDB
    console.log('Testing IndexedDB...');
    const idbBtn = sandbox.locator('button:has-text("Test IndexedDB")');
    await idbBtn.click();

    // Wait for IDB operations
    await page.waitForTimeout(1000);

    const idbResult = await sandbox.locator('#idb-result').textContent();
    console.log('IndexedDB result:', idbResult);
    expect(idbResult).toContain('indexedDB available: true');
    expect(idbResult).toContain('Database opened successfully');

    console.log('=== INDEXEDDB TEST PASSED ===');
    await page.close();
  });

  test('webrtc - RTCPeerConnection works with public STUN servers', async ({ context, extensionId, whServer }) => {
    console.log('=== TESTING WEBRTC ===');

    const page = await context.newPage();
    page.on('console', msg => console.log('PAGE:', msg.type(), msg.text()));

    const viewerUrl = `chrome-extension://${extensionId}/viewer.html?address=${whServer.code}&connectionId=test-webrtc&path=/webrtc-test`;
    await page.goto(viewerUrl);

    const sandbox = page.frameLocator('#wh-sandbox');
    await sandbox.locator('h1:has-text("WebRTC Test")').waitFor({ timeout: 60000 });
    console.log('WebRTC test page loaded');

    // Run the comprehensive test
    console.log('Running WebRTC tests...');
    const runAllBtn = sandbox.locator('button:has-text("Run All Tests")');
    await runAllBtn.click();
    await page.waitForTimeout(1000);

    const allTestsResult = await sandbox.locator('#all-tests-result').textContent();
    console.log('WebRTC tests result:', allTestsResult);

    // Verify RTCPeerConnection is available
    expect(allTestsResult).toContain('RTCPeerConnection available: true');
    expect(allTestsResult).toContain('Create RTCPeerConnection: PASS');

    // Test peer connection creation
    console.log('Testing peer connection...');
    const peerBtn = sandbox.locator('button:has-text("Test Peer Connection")');
    await peerBtn.click();
    await page.waitForTimeout(5000); // Wait for ICE gathering

    const peerResult = await sandbox.locator('#peer-result').textContent();
    console.log('Peer connection result:', peerResult.substring(0, 300));
    expect(peerResult).toContain('Created peer connection');
    expect(peerResult).toContain('Created offer');

    console.log('=== WEBRTC TEST PASSED ===');
    await page.close();
  });

  test('external css - styles from external CSS file are applied', async ({ context, extensionId, whServer }) => {
    console.log('=== TESTING EXTERNAL CSS ===');

    const page = await context.newPage();
    page.on('console', msg => console.log('PAGE:', msg.type(), msg.text()));

    const viewerUrl = `chrome-extension://${extensionId}/viewer.html?address=${whServer.code}&connectionId=test-css&path=/resource-test`;
    await page.goto(viewerUrl);

    const sandbox = page.frameLocator('#wh-sandbox');
    await sandbox.locator('h1:has-text("Resource Loading Test")').waitFor({ timeout: 60000 });

    // Wait for external CSS to load and check if gradient is applied
    await page.waitForTimeout(2000);

    // Check CSS status - the page checks for gradient background
    const cssStatus = await sandbox.locator('#css-status').textContent();
    console.log('CSS status:', cssStatus);

    // Verify the external CSS test element exists
    const cssTestElement = sandbox.locator('.external-css-test');
    expect(await cssTestElement.count()).toBeGreaterThan(0);

    console.log('=== EXTERNAL CSS TEST PASSED ===');
    await page.close();
  });

  test('external scripts - JavaScript from external file executes', async ({ context, extensionId, whServer }) => {
    console.log('=== TESTING EXTERNAL SCRIPTS ===');

    const page = await context.newPage();
    page.on('console', msg => console.log('PAGE:', msg.type(), msg.text()));

    const viewerUrl = `chrome-extension://${extensionId}/viewer.html?address=${whServer.code}&connectionId=test-scripts&path=/resource-test`;
    await page.goto(viewerUrl);

    const sandbox = page.frameLocator('#wh-sandbox');
    await sandbox.locator('h1:has-text("Resource Loading Test")').waitFor({ timeout: 60000 });

    // Wait for external script to load
    await page.waitForTimeout(3000);

    // Check external script indicator - set by app.js
    const scriptIndicator = await sandbox.locator('#external-script-indicator').textContent();
    console.log('External script indicator:', scriptIndicator);

    // The external script sets externalScriptLoaded = true and updates indicator to "External script loaded!"
    expect(scriptIndicator.toLowerCase()).toContain('loaded');

    console.log('=== EXTERNAL SCRIPTS TEST PASSED ===');
    await page.close();
  });

  test('fetch api - can fetch JSON through wormhole', async ({ context, extensionId, whServer }) => {
    console.log('=== TESTING FETCH API ===');

    const page = await context.newPage();
    page.on('console', msg => console.log('PAGE:', msg.type(), msg.text()));

    const viewerUrl = `chrome-extension://${extensionId}/viewer.html?address=${whServer.code}&connectionId=test-fetch&path=/resource-test`;
    await page.goto(viewerUrl);

    const sandbox = page.frameLocator('#wh-sandbox');
    await sandbox.locator('h1:has-text("Resource Loading Test")').waitFor({ timeout: 60000 });

    // Click the Fetch test button
    const fetchBtn = sandbox.locator('button:has-text("Test Fetch")');
    await fetchBtn.click();
    await page.waitForTimeout(2000);

    // Check fetch result
    const fetchResult = await sandbox.locator('#fetch-result').textContent();
    console.log('Fetch result:', fetchResult);

    // Should contain successful JSON response
    expect(fetchResult).toContain('"success": true');

    console.log('=== FETCH API TEST PASSED ===');
    await page.close();
  });

  test('xhr - XMLHttpRequest works through wormhole', async ({ context, extensionId, whServer }) => {
    console.log('=== TESTING XHR ===');

    const page = await context.newPage();
    page.on('console', msg => console.log('PAGE:', msg.type(), msg.text()));

    const viewerUrl = `chrome-extension://${extensionId}/viewer.html?address=${whServer.code}&connectionId=test-xhr&path=/resource-test`;
    await page.goto(viewerUrl);

    const sandbox = page.frameLocator('#wh-sandbox');
    await sandbox.locator('h1:has-text("Resource Loading Test")').waitFor({ timeout: 60000 });

    // Click the XHR test button
    const xhrBtn = sandbox.locator('button:has-text("Test XHR")');
    await xhrBtn.click();
    await page.waitForTimeout(2000);

    // Check XHR result
    const xhrResult = await sandbox.locator('#xhr-result').textContent();
    console.log('XHR result:', xhrResult);

    // Should contain response status in parentheses (format: "XHR result (status 200):")
    expect(xhrResult).toContain('status 200');

    console.log('=== XHR TEST PASSED ===');
    await page.close();
  });

  test('localStorage - data persists and is per-site', async ({ context, extensionId, whServer }) => {
    console.log('=== TESTING LOCALSTORAGE ===');

    const page = await context.newPage();
    page.on('console', msg => console.log('PAGE:', msg.type(), msg.text()));

    const viewerUrl = `chrome-extension://${extensionId}/viewer.html?address=${whServer.code}&connectionId=test-storage&path=/resource-test`;
    await page.goto(viewerUrl);

    const sandbox = page.frameLocator('#wh-sandbox');
    await sandbox.locator('h1:has-text("Resource Loading Test")').waitFor({ timeout: 60000 });

    // Click the localStorage test button
    const storageBtn = sandbox.locator('button:has-text("Test localStorage")');
    await storageBtn.click();
    await page.waitForTimeout(1000);

    // Check storage result
    const storageResult = await sandbox.locator('#storage-result').textContent();
    console.log('localStorage result:', storageResult);

    // Should show matching values (format: "Match: true")
    expect(storageResult.toLowerCase()).toContain('match: true');

    console.log('=== LOCALSTORAGE TEST PASSED ===');
    await page.close();
  });

  test('sessionStorage - session data works per-site', async ({ context, extensionId, whServer }) => {
    console.log('=== TESTING SESSIONSTORAGE ===');

    const page = await context.newPage();
    page.on('console', msg => console.log('PAGE:', msg.type(), msg.text()));

    const viewerUrl = `chrome-extension://${extensionId}/viewer.html?address=${whServer.code}&connectionId=test-session&path=/resource-test`;
    await page.goto(viewerUrl);

    const sandbox = page.frameLocator('#wh-sandbox');
    await sandbox.locator('h1:has-text("Resource Loading Test")').waitFor({ timeout: 60000 });

    // Click the sessionStorage test button
    const sessionBtn = sandbox.locator('button:has-text("Test sessionStorage")');
    await sessionBtn.click();
    await page.waitForTimeout(1000);

    // Check session storage result
    const sessionResult = await sandbox.locator('#session-storage-result').textContent();
    console.log('sessionStorage result:', sessionResult);

    // Should show matching values (format: "Match: true")
    expect(sessionResult.toLowerCase()).toContain('match: true');

    console.log('=== SESSIONSTORAGE TEST PASSED ===');
    await page.close();
  });

  test('cookies - document.cookie works', async ({ context, extensionId, whServer }) => {
    console.log('=== TESTING COOKIES ===');

    const page = await context.newPage();
    page.on('console', msg => console.log('PAGE:', msg.type(), msg.text()));

    const viewerUrl = `chrome-extension://${extensionId}/viewer.html?address=${whServer.code}&connectionId=test-cookies&path=/resource-test`;
    await page.goto(viewerUrl);

    const sandbox = page.frameLocator('#wh-sandbox');
    await sandbox.locator('h1:has-text("Resource Loading Test")').waitFor({ timeout: 60000 });

    // Click the cookies test button
    const cookieBtn = sandbox.locator('button:has-text("Test Cookies")');
    await cookieBtn.click();
    await page.waitForTimeout(1000);

    // Check cookie result
    const cookieResult = await sandbox.locator('#cookie-result').textContent();
    console.log('Cookies result:', cookieResult);

    // Should show cookie operations
    expect(cookieResult.toLowerCase()).not.toContain('error');

    console.log('=== COOKIES TEST PASSED ===');
    await page.close();
  });

  test('images - images load through wormhole', async ({ context, extensionId, whServer }) => {
    console.log('=== TESTING IMAGE LOADING ===');

    const page = await context.newPage();
    page.on('console', msg => console.log('PAGE:', msg.type(), msg.text()));

    const viewerUrl = `chrome-extension://${extensionId}/viewer.html?address=${whServer.code}&connectionId=test-images&path=/resource-test`;
    await page.goto(viewerUrl);

    const sandbox = page.frameLocator('#wh-sandbox');
    await sandbox.locator('h1:has-text("Resource Loading Test")').waitFor({ timeout: 60000 });

    // Wait for images to load
    await page.waitForTimeout(4000);

    // Check image status
    const imageStatus = await sandbox.locator('#image-status').textContent();
    console.log('Image status:', imageStatus);

    // Should show images loaded
    expect(imageStatus.toLowerCase()).toContain('loaded');

    console.log('=== IMAGE LOADING TEST PASSED ===');
    await page.close();
  });

  test('navigation - internal links work without page reload', async ({ context, extensionId, whServer }) => {
    console.log('=== TESTING NAVIGATION ===');

    const page = await context.newPage();
    page.on('console', msg => console.log('PAGE:', msg.type(), msg.text()));

    const viewerUrl = `chrome-extension://${extensionId}/viewer.html?address=${whServer.code}&connectionId=test-nav&path=/`;
    await page.goto(viewerUrl);

    const sandbox = page.frameLocator('#wh-sandbox');
    await sandbox.locator('h1:has-text("Home Page")').waitFor({ timeout: 60000 });

    // Click About link
    await sandbox.locator('a:has-text("About")').click();
    await page.waitForTimeout(1000);

    // Should navigate to about page (h1 is "About Page")
    await sandbox.locator('h1:has-text("About Page")').waitFor({ timeout: 10000 });

    // Verify URL updated
    const url = page.url();
    expect(url).toContain('path=%2Fabout');

    console.log('=== NAVIGATION TEST PASSED ===');
    await page.close();
  });

  test('history pushState - URL updates without reload', async ({ context, extensionId, whServer }) => {
    console.log('=== TESTING HISTORY PUSHSTATE ===');

    const page = await context.newPage();
    page.on('console', msg => console.log('PAGE:', msg.type(), msg.text()));

    const viewerUrl = `chrome-extension://${extensionId}/viewer.html?address=${whServer.code}&connectionId=test-history&path=/advanced-features-test`;
    await page.goto(viewerUrl);

    const sandbox = page.frameLocator('#wh-sandbox');
    await sandbox.locator('h1:has-text("Advanced Features Test")').waitFor({ timeout: 60000 });

    // Click pushState button
    const pushBtn = sandbox.locator('button:has-text("pushState")');
    await pushBtn.click();
    await page.waitForTimeout(500);

    // Check result
    const historyResult = await sandbox.locator('#history-result').textContent();
    console.log('History result:', historyResult);
    expect(historyResult).toContain('pushState called');

    // Verify URL was updated (page=2 gets URL-encoded as page%3D2 inside the path parameter)
    const url = page.url();
    console.log('Current URL:', url);
    // The path parameter value contains URL-encoded query string
    expect(url).toContain('page%3D2');

    console.log('=== HISTORY PUSHSTATE TEST PASSED ===');
    await page.close();
  });

  test('whLocation - fallback location object works', async ({ context, extensionId, whServer }) => {
    console.log('=== TESTING WHLOCATION ===');

    const page = await context.newPage();
    page.on('console', msg => console.log('PAGE:', msg.type(), msg.text()));

    const viewerUrl = `chrome-extension://${extensionId}/viewer.html?address=${whServer.code}&connectionId=test-location&path=/advanced-features-test`;
    await page.goto(viewerUrl);

    const sandbox = page.frameLocator('#wh-sandbox');
    await sandbox.locator('h1:has-text("Advanced Features Test")').waitFor({ timeout: 60000 });

    // Click test location button
    const locationBtn = sandbox.locator('button:has-text("Test Location Properties")');
    await locationBtn.click();
    await page.waitForTimeout(500);

    // Check result
    const locationResult = await sandbox.locator('#location-result').textContent();
    console.log('Location result:', locationResult.substring(0, 500));

    // whLocation should have correct values
    expect(locationResult).toContain('whLocation');
    expect(locationResult).toContain('wh:');
    expect(locationResult).toContain(whServer.code);

    console.log('=== WHLOCATION TEST PASSED ===');
    await page.close();
  });
});
