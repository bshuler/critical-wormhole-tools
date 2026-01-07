/**
 * Hello World E2E Test
 *
 * Tests the complete flow:
 * 1. Start mock wormhole daemon server
 * 2. Load browser extension in Chrome
 * 3. Navigate to the daemon-served page
 * 4. Verify HTML is loaded
 * 5. Verify CSS is applied
 * 6. Verify external JS file is loaded and executed
 * 7. Verify DOM modifications from JS
 */

import { test, expect, chromium } from '@playwright/test';
import { createServer } from 'http';
import { readFileSync, existsSync, mkdtempSync, rmSync } from 'fs';
import { tmpdir } from 'os';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const extensionPath = path.resolve(__dirname, '../../dist');
const fixturesPath = path.resolve(__dirname, 'fixtures/hello-world');

const DAEMON_PORT = 9476; // Use different port to avoid conflicts

// Shared state
let server = null;
let browserContext = null;
let userDataDir = null;

/**
 * Create a mock daemon server that serves the hello world content
 */
function createMockDaemon(port) {
  return new Promise((resolve, reject) => {
    const httpServer = createServer((req, res) => {
      const url = new URL(req.url, `http://localhost:${port}`);
      const pathname = url.pathname;

      // CORS headers
      res.setHeader('Access-Control-Allow-Origin', '*');
      res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
      res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Accept');

      if (req.method === 'OPTIONS') {
        res.writeHead(204);
        res.end();
        return;
      }

      // Status endpoint
      if (pathname === '/status') {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ running: true, version: '0.4.0' }));
        return;
      }

      // Serve index.html
      if (pathname === '/' || pathname === '/index.html') {
        try {
          const content = readFileSync(path.join(fixturesPath, 'index.html'), 'utf-8');
          res.writeHead(200, { 'Content-Type': 'text/html' });
          res.end(content);
        } catch (e) {
          res.writeHead(500);
          res.end(`Error: ${e.message}`);
        }
        return;
      }

      // Serve CSS
      if (pathname === '/style.css') {
        try {
          const content = readFileSync(path.join(fixturesPath, 'style.css'), 'utf-8');
          res.writeHead(200, { 'Content-Type': 'text/css' });
          res.end(content);
        } catch (e) {
          res.writeHead(500);
          res.end(`Error: ${e.message}`);
        }
        return;
      }

      // Serve JS
      if (pathname === '/app.js') {
        try {
          const content = readFileSync(path.join(fixturesPath, 'app.js'), 'utf-8');
          res.writeHead(200, { 'Content-Type': 'application/javascript' });
          res.end(content);
        } catch (e) {
          res.writeHead(500);
          res.end(`Error: ${e.message}`);
        }
        return;
      }

      // 404
      res.writeHead(404);
      res.end('Not Found');
    });

    httpServer.on('error', reject);
    httpServer.listen(port, () => {
      console.log(`Mock daemon listening on port ${port}`);
      resolve(httpServer);
    });
  });
}

// Configure serial execution for this file
test.describe.configure({ mode: 'serial' });

test.describe('Hello World via Wormhole', () => {
  // Increase timeout for beforeAll since it launches browser with extension
  test.setTimeout(120000);

  test.beforeAll(async () => {
    // Verify extension exists
    if (!existsSync(extensionPath)) {
      throw new Error(`Extension not built. Run 'npm run build' first. Expected path: ${extensionPath}`);
    }
    console.log('Extension path:', extensionPath);

    // Start mock server
    console.log('Starting mock server...');
    server = await createMockDaemon(DAEMON_PORT);
    console.log('Mock server started');

    // Create temp directory for browser profile
    userDataDir = mkdtempSync(path.join(tmpdir(), 'playwright-ext-'));
    console.log('User data dir:', userDataDir);

    // Use headless mode by default, can be overridden with HEADFUL=1
    const headless = !process.env.HEADFUL;

    // Launch browser with extension using system Chrome
    console.log('Launching browser with extension...');
    browserContext = await chromium.launchPersistentContext(userDataDir, {
      channel: 'chrome', // Use system Chrome instead of Playwright Chromium
      headless: headless,
      args: [
        `--disable-extensions-except=${extensionPath}`,
        `--load-extension=${extensionPath}`,
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-gpu',
        '--disable-dev-shm-usage',
        '--disable-background-networking',
        '--disable-default-apps',
        '--disable-sync',
        '--no-first-run',
        // New headless mode supports extensions (Chrome 109+)
        ...(headless ? ['--headless=new'] : [])
      ],
      timeout: 60000
    });
    console.log('Browser launched');

    // Wait for extension to initialize
    await new Promise(r => setTimeout(r, 2000));
    console.log('Extension initialized');
  });

  test.afterAll(async () => {
    if (browserContext) {
      await browserContext.close();
      browserContext = null;
    }
    if (server) {
      server.close();
      server = null;
    }
    if (userDataDir) {
      try {
        rmSync(userDataDir, { recursive: true, force: true });
      } catch (e) {
        console.log('Failed to clean up user data dir:', e.message);
      }
      userDataDir = null;
    }
  });

  test('loads HTML page through mock daemon', async () => {
    const page = await browserContext.newPage();

    try {
      await page.goto(`http://localhost:${DAEMON_PORT}/`, { timeout: 10000 });
      await page.waitForLoadState('networkidle');

      // Verify the greeting text
      const greeting = page.locator('#greeting');
      await expect(greeting).toBeVisible();
      await expect(greeting).toHaveText('Hello from the Wormhole!');
    } finally {
      await page.close();
    }
  });

  test('loads external CSS stylesheet', async () => {
    const page = await browserContext.newPage();

    try {
      await page.goto(`http://localhost:${DAEMON_PORT}/`);
      await page.waitForLoadState('networkidle');

      // Check that CSS is applied
      const container = page.locator('.container');
      await expect(container).toBeVisible();

      // Verify CSS gradient is applied
      const bodyStyles = await page.evaluate(() => {
        return window.getComputedStyle(document.body).backgroundImage;
      });
      expect(bodyStyles).toContain('linear-gradient');
    } finally {
      await page.close();
    }
  });

  test('loads and executes external JavaScript file', async () => {
    const page = await browserContext.newPage();

    try {
      await page.goto(`http://localhost:${DAEMON_PORT}/`);
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(500);

      // Verify JS modified the DOM
      const message = page.locator('#message');
      await expect(message).toContainText('Magic Wormhole connection');

      const jsStatus = page.locator('#js-status');
      await expect(jsStatus).toHaveText('JavaScript loaded successfully');

      // Check CSS class added by JS
      const hasLoadedClass = await page.evaluate(() => {
        return document.getElementById('js-status').classList.contains('loaded');
      });
      expect(hasLoadedClass).toBe(true);

      // Check data attribute
      const dataAttr = await page.evaluate(() => {
        return document.body.getAttribute('data-wormhole-js-loaded');
      });
      expect(dataAttr).toBe('true');
    } finally {
      await page.close();
    }
  });

  test('timestamp is dynamically generated by JS', async () => {
    const page = await browserContext.newPage();

    try {
      await page.goto(`http://localhost:${DAEMON_PORT}/`);
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(500);

      const timestamp = page.locator('#timestamp');
      const timestampText = await timestamp.textContent();

      expect(timestampText).toContain('Page loaded at:');
      expect(timestampText).toMatch(/\d{1,2}:\d{2}/);
    } finally {
      await page.close();
    }
  });

  test('verifies complete page structure via DOM inspection', async () => {
    const page = await browserContext.newPage();

    try {
      await page.goto(`http://localhost:${DAEMON_PORT}/`);
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(500);

      const pageStructure = await page.evaluate(() => {
        return {
          title: document.title,
          hasStylesheet: !!document.querySelector('link[rel="stylesheet"]'),
          hasScript: !!document.querySelector('script[src="app.js"]'),
          greeting: document.getElementById('greeting')?.textContent,
          message: document.getElementById('message')?.textContent,
          jsStatus: document.getElementById('js-status')?.textContent,
          jsStatusClasses: Array.from(document.getElementById('js-status')?.classList || []),
          bodyDataAttr: document.body.getAttribute('data-wormhole-js-loaded'),
          containerExists: !!document.querySelector('.container')
        };
      });

      // Verify HTML structure
      expect(pageStructure.title).toBe('Hello Wormhole!');
      expect(pageStructure.hasStylesheet).toBe(true);
      expect(pageStructure.hasScript).toBe(true);
      expect(pageStructure.containerExists).toBe(true);

      // Verify JS execution results
      expect(pageStructure.greeting).toBe('Hello from the Wormhole!');
      expect(pageStructure.message).toContain('Magic Wormhole connection');
      expect(pageStructure.jsStatus).toBe('JavaScript loaded successfully');
      expect(pageStructure.jsStatusClasses).toContain('loaded');
      expect(pageStructure.bodyDataAttr).toBe('true');
    } finally {
      await page.close();
    }
  });

  test('console shows JS execution logs', async () => {
    const page = await browserContext.newPage();

    try {
      const consoleLogs = [];
      page.on('console', msg => consoleLogs.push(msg.text()));

      await page.goto(`http://localhost:${DAEMON_PORT}/`);
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(500);

      expect(consoleLogs.some(log => log.includes('[Wormhole Demo]'))).toBe(true);
      expect(consoleLogs.some(log => log.includes('External JavaScript executed'))).toBe(true);
    } finally {
      await page.close();
    }
  });

  test('CSS file is fetched from server', async () => {
    const page = await browserContext.newPage();

    try {
      const cssRequests = [];
      page.on('request', req => {
        if (req.url().includes('style.css')) cssRequests.push(req.url());
      });

      await page.goto(`http://localhost:${DAEMON_PORT}/`);
      await page.waitForLoadState('networkidle');

      expect(cssRequests.length).toBeGreaterThan(0);
    } finally {
      await page.close();
    }
  });

  test('JavaScript file is fetched from server', async () => {
    const page = await browserContext.newPage();

    try {
      const jsRequests = [];
      page.on('request', req => {
        if (req.url().includes('app.js')) jsRequests.push(req.url());
      });

      await page.goto(`http://localhost:${DAEMON_PORT}/`);
      await page.waitForLoadState('networkidle');

      expect(jsRequests.length).toBeGreaterThan(0);
    } finally {
      await page.close();
    }
  });

  test('all resources return 200 OK', async () => {
    const page = await browserContext.newPage();

    try {
      const responses = [];
      page.on('response', res => {
        responses.push({ url: res.url(), status: res.status() });
      });

      await page.goto(`http://localhost:${DAEMON_PORT}/`);
      await page.waitForLoadState('networkidle');

      const htmlResponse = responses.find(r => r.url.includes(`localhost:${DAEMON_PORT}/`) && !r.url.includes('.css') && !r.url.includes('.js'));
      const cssResponse = responses.find(r => r.url.includes('style.css'));
      const jsResponse = responses.find(r => r.url.includes('app.js'));

      expect(htmlResponse?.status).toBe(200);
      expect(cssResponse?.status).toBe(200);
      expect(jsResponse?.status).toBe(200);
    } finally {
      await page.close();
    }
  });
});
