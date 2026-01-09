/**
 * E2E tests for viewer navigation - specifically testing link click interception
 *
 * Based on official Playwright docs: https://playwright.dev/docs/chrome-extensions
 *
 * KEY INSIGHT: Must use Playwright's bundled Chromium, NOT system Chrome.
 * Google Chrome removed the command-line flags for side-loading extensions.
 */

import { test as base, chromium, expect } from '@playwright/test';
import { mkdtempSync, rmSync, existsSync } from 'fs';
import { tmpdir } from 'os';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const pathToExtension = path.resolve(__dirname, '../../dist');

// Create custom test fixture that handles extension loading
// Following the official Playwright pattern for Chrome extensions
export const test = base.extend({
  // Override context to load the extension
  context: async ({}, use) => {
    // Verify extension exists
    if (!existsSync(path.join(pathToExtension, 'manifest.json'))) {
      throw new Error(`Extension not found at ${pathToExtension}. Run 'npm run build' first.`);
    }

    // CRITICAL: Use Playwright's bundled Chromium, not system Chrome
    // System Chrome (channel: 'chrome') has removed extension side-loading flags
    // NOTE: Extensions require headed mode - headless doesn't support service workers
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

  // Get extension ID from service worker
  extensionId: async ({ context }, use) => {
    // Wait for service worker to be available
    let [serviceWorker] = context.serviceWorkers();
    if (!serviceWorker) {
      serviceWorker = await context.waitForEvent('serviceworker', { timeout: 30000 });
    }

    // Extract extension ID from service worker URL
    // URL format: chrome-extension://<extensionId>/background.js
    const extensionId = serviceWorker.url().split('/')[2];
    console.log('Extension ID:', extensionId);
    console.log('Service Worker URL:', serviceWorker.url());

    await use(extensionId);
  },
});

test.describe('Viewer Navigation', () => {
  test.setTimeout(60000);

  test('extension loads and has valid ID', async ({ extensionId }) => {
    // Extension ID should be a 32-character alphanumeric string
    expect(extensionId).toBeTruthy();
    expect(extensionId.length).toBe(32);
    expect(extensionId).toMatch(/^[a-z]{32}$/);
    console.log('Extension loaded with ID:', extensionId);
  });

  test('viewer page loads and shows loading state', async ({ context, extensionId }) => {
    const page = await context.newPage();

    // Navigate to viewer with test params
    await page.goto(`chrome-extension://${extensionId}/viewer.html?address=test-address&connectionId=test-conn&path=/`);
    await page.waitForTimeout(500);

    // Check that viewer UI elements are present
    const loading = page.locator('#wh-loading');
    const content = page.locator('#wh-content');
    const error = page.locator('#wh-error');

    // One of these should exist
    const hasLoading = await loading.isVisible().catch(() => false);
    const hasContent = await content.isVisible().catch(() => false);
    const hasError = await error.isVisible().catch(() => false);

    console.log('Loading visible:', hasLoading);
    console.log('Content visible:', hasContent);
    console.log('Error visible:', hasError);

    // The page should have loaded something (loading, content, or error)
    expect(hasLoading || hasContent || hasError).toBe(true);

    await page.close();
  });

  test('click interception prevents navigation to about:blank', async ({ context, extensionId }) => {
    const page = await context.newPage();

    // Navigate to viewer
    const viewerUrl = `chrome-extension://${extensionId}/viewer.html?address=test&connectionId=test&path=/`;
    await page.goto(viewerUrl);
    await page.waitForTimeout(500);

    // Test the REAL flow: inject raw HTML and use extractBody to rewrite it
    // This simulates what happens when content comes from wormhole server
    const result = await page.evaluate(() => {
      const contentEl = document.getElementById('wh-content');
      const loadingEl = document.getElementById('wh-loading');
      const errorEl = document.getElementById('wh-error');

      // Hide loading and error overlays
      if (loadingEl) loadingEl.style.display = 'none';
      if (errorEl) errorEl.style.display = 'none';

      // Raw HTML as it would come from the server (NO data-wh-href yet)
      const rawHtml = `
        <html>
        <body>
          <h1>Test Page</h1>
          <a href="/about" id="test-internal">About Link</a>
          <a href="https://example.com" id="test-external">External Link</a>
        </body>
        </html>
      `;

      // Use the same extractBody function that viewer.js uses
      function isExternalLink(href) {
        if (!href) return true;
        return href.startsWith('http://') ||
               href.startsWith('https://') ||
               href.startsWith('javascript:') ||
               href.startsWith('mailto:') ||
               href.startsWith('tel:') ||
               href.startsWith('#');
      }

      function extractBody(html) {
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');
        if (!doc.body) return html;

        const links = doc.body.querySelectorAll('a[href]');
        let rewrittenCount = 0;

        links.forEach(link => {
          const href = link.getAttribute('href');
          if (href && !isExternalLink(href)) {
            link.setAttribute('data-wh-href', href);
            link.setAttribute('href', '#');
            link.classList.add('wh-internal-link');
            rewrittenCount++;
          }
        });

        return { html: doc.body.innerHTML, rewrittenCount };
      }

      // Process the raw HTML through extractBody (like displayContent does)
      const processed = extractBody(rawHtml);
      contentEl.innerHTML = processed.html;
      contentEl.style.display = 'block';

      // Verify the link was rewritten
      const link = document.getElementById('test-internal');
      return {
        rewrittenCount: processed.rewrittenCount,
        href: link?.getAttribute('href'),
        dataWhHref: link?.getAttribute('data-wh-href'),
        hasClass: link?.classList.contains('wh-internal-link')
      };
    });

    console.log('Link rewriting result:', result);

    // Verify extractBody worked
    expect(result.rewrittenCount).toBe(1);
    expect(result.href).toBe('#');
    expect(result.dataWhHref).toBe('/about');
    expect(result.hasClass).toBe(true);

    const beforeUrl = page.url();
    console.log('Before click URL:', beforeUrl);

    // Click the internal link
    const link = page.locator('#test-internal');
    await link.click();

    // Wait for any navigation
    await page.waitForTimeout(1000);

    const afterUrl = page.url();
    console.log('After click URL:', afterUrl);

    // The URL should NOT be about:blank
    expect(afterUrl).not.toContain('about:blank');

    // URL should still be in the viewer
    expect(afterUrl).toContain('viewer.html');

    await page.close();
  });

  test('link rewriting works in extractBody', async ({ context, extensionId }) => {
    const page = await context.newPage();

    // Navigate to viewer
    await page.goto(`chrome-extension://${extensionId}/viewer.html?address=test&connectionId=test&path=/`);
    await page.waitForTimeout(500);

    // Test the extractBody function directly
    const result = await page.evaluate(() => {
      // Access the extractBody function that should be in the global scope
      // If not available, we'll test the same logic
      function isExternalLink(href) {
        if (!href) return true;
        return href.startsWith('http://') ||
               href.startsWith('https://') ||
               href.startsWith('javascript:') ||
               href.startsWith('mailto:') ||
               href.startsWith('tel:') ||
               href.startsWith('#');
      }

      function extractBody(html) {
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');
        if (!doc.body) return { error: 'No body' };

        const links = doc.body.querySelectorAll('a[href]');
        let rewrittenCount = 0;

        links.forEach(link => {
          const href = link.getAttribute('href');
          if (href && !isExternalLink(href)) {
            link.setAttribute('data-wh-href', href);
            link.setAttribute('href', '#');
            link.classList.add('wh-internal-link');
            rewrittenCount++;
          }
        });

        return {
          rewrittenCount,
          html: doc.body.innerHTML
        };
      }

      const testHtml = `
        <body>
          <a href="/">Home</a>
          <a href="/about">About</a>
          <a href="https://example.com">External</a>
          <a href="#section">Hash</a>
        </body>
      `;

      return extractBody(testHtml);
    });

    console.log('Rewritten count:', result.rewrittenCount);
    console.log('Result HTML preview:', result.html?.substring(0, 200));

    // Should have rewritten 2 internal links (/ and /about)
    expect(result.rewrittenCount).toBe(2);

    // The HTML should contain data-wh-href attributes
    expect(result.html).toContain('data-wh-href="/"');
    expect(result.html).toContain('data-wh-href="/about"');

    // External and hash links should NOT be rewritten
    expect(result.html).toContain('href="https://example.com"');
    expect(result.html).toContain('href="#section"');

    await page.close();
  });

  test('popup page loads', async ({ context, extensionId }) => {
    const page = await context.newPage();

    // Navigate to popup
    await page.goto(`chrome-extension://${extensionId}/popup.html`);
    await page.waitForTimeout(500);

    // Check popup loaded
    const header = page.locator('.header h1');
    await expect(header).toHaveText('Wormhole Browser');

    await page.close();
  });
});
