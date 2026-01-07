import { defineConfig } from 'vitest/config';
import path from 'path';

export default defineConfig({
  test: {
    // Global test settings
    globals: true,
    environment: 'happy-dom',

    // Include patterns
    include: ['tests/**/*.test.js'],

    // Exclude patterns
    exclude: ['tests/e2e/**', 'node_modules'],

    // Coverage configuration
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      include: ['src/**/*.js'],
      exclude: ['src/**/*.test.js']
    },

    // Setup files
    setupFiles: ['./tests/setup.js'],

    // Reporter configuration
    reporters: ['verbose'],

    // Mock configuration
    mockReset: true,
    restoreMocks: true,

    // Timeout
    testTimeout: 10000
  },

  // Resolve aliases
  resolve: {
    alias: {
      '@lib': path.resolve(import.meta.dirname, './src/lib'),
      '@crypto': path.resolve(import.meta.dirname, './src/lib/crypto'),
      '@protocol': path.resolve(import.meta.dirname, './src/lib/protocol'),
      '@wns': path.resolve(import.meta.dirname, './src/lib/wns')
    }
  }
});
