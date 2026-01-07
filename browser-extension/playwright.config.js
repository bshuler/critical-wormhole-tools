import { defineConfig, devices } from '@playwright/test';
import path from 'path';

const extensionPath = path.join(import.meta.dirname, 'dist');

export default defineConfig({
  testDir: './tests/e2e',

  // Run tests serially to avoid port conflicts with mock servers
  fullyParallel: false,
  workers: 1,

  // Fail build on test.only
  forbidOnly: !!process.env.CI,

  // Retries
  retries: process.env.CI ? 2 : 0,

  // Timeout for each test
  timeout: 60000,

  // Reporter
  reporter: [
    ['list'],
    ['html', { outputFolder: 'playwright-report' }]
  ],

  // Shared settings
  use: {
    // Collect trace on failure
    trace: 'on-first-retry',

    // Screenshot on failure
    screenshot: 'only-on-failure',

    // Video on failure
    video: 'on-first-retry'
  },

  // Project definitions - Only Chromium for extensions
  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        // Load extension in Chrome
        launchOptions: {
          args: [
            `--disable-extensions-except=${extensionPath}`,
            `--load-extension=${extensionPath}`,
            '--no-sandbox'
          ]
        }
      }
    }
  ],

  // Web server for test fixtures
  webServer: {
    command: 'npm run build',
    cwd: import.meta.dirname,
    reuseExistingServer: !process.env.CI
  }
});
