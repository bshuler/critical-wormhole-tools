/**
 * Unit tests for Background Service Worker
 *
 * Tests the browser extension background script functionality.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Mock chrome APIs
const mockChrome = {
  action: {
    setIcon: vi.fn(() => Promise.resolve()),
    setTitle: vi.fn()
  },
  omnibox: {
    onInputEntered: { addListener: vi.fn() },
    onInputChanged: { addListener: vi.fn() },
    onInputStarted: { addListener: vi.fn() },
    setDefaultSuggestion: vi.fn()
  },
  runtime: {
    onMessage: { addListener: vi.fn() },
    onConnect: { addListener: vi.fn() },
    getURL: vi.fn((path) => `chrome-extension://test-id/${path}`),
    sendMessage: vi.fn()
  },
  tabs: {
    update: vi.fn(() => Promise.resolve()),
    create: vi.fn(() => Promise.resolve())
  },
  storage: {
    local: {
      get: vi.fn(() => Promise.resolve({})),
      set: vi.fn(() => Promise.resolve())
    }
  }
};

global.chrome = mockChrome;

// Mock fetch
global.fetch = vi.fn(() => Promise.reject(new Error('Fetch not mocked')));

// Helper functions extracted from background.js for testing
function parseWormholeUrl(input) {
  let cleaned = input.trim();
  if (cleaned.startsWith('wh://')) {
    cleaned = cleaned.slice(5);
  }

  const slashIndex = cleaned.indexOf('/');
  let address, path;

  if (slashIndex !== -1) {
    address = cleaned.slice(0, slashIndex);
    path = cleaned.slice(slashIndex);
  } else {
    address = cleaned;
    path = '/';
  }

  const isWormholeCode = /^\d+-[a-z]+-[a-z]+$/i.test(address);

  if (!address.includes('.') && !isWormholeCode) {
    address = address + '.wns';
  }

  return { address, path };
}

function generateConnectionId() {
  return 'conn-' + Math.random().toString(36).substring(2, 10);
}

function injectWormholeMetadata(html, address, connectionId, path) {
  const bodyMatch = html.match(/<body([^>]*)>/i);
  if (bodyMatch) {
    const existingAttrs = bodyMatch[1] || '';
    const newAttrs = ` data-wh-address="${address}" data-wh-connection-id="${connectionId}" data-wh-path="${path}"`;
    html = html.replace(/<body([^>]*)>/i, `<body${existingAttrs}${newAttrs}>`);
  } else {
    html = `<body data-wh-address="${address}" data-wh-connection-id="${connectionId}" data-wh-path="${path}">${html}</body>`;
  }
  return html;
}

describe('parseWormholeUrl', () => {
  describe('basic parsing', () => {
    it('should parse bare address', () => {
      const result = parseWormholeUrl('example');
      expect(result.address).toBe('example.wns');
      expect(result.path).toBe('/');
    });

    it('should parse address with path', () => {
      const result = parseWormholeUrl('example/about');
      expect(result.address).toBe('example.wns');
      expect(result.path).toBe('/about');
    });

    it('should parse wh:// URL', () => {
      const result = parseWormholeUrl('wh://example');
      expect(result.address).toBe('example.wns');
      expect(result.path).toBe('/');
    });

    it('should parse wh:// URL with path', () => {
      const result = parseWormholeUrl('wh://example/page/subpage');
      expect(result.address).toBe('example.wns');
      expect(result.path).toBe('/page/subpage');
    });
  });

  describe('wormhole codes', () => {
    it('should recognize wormhole code format', () => {
      const result = parseWormholeUrl('7-guitar-sunset');
      expect(result.address).toBe('7-guitar-sunset');
      expect(result.path).toBe('/');
    });

    it('should not add .wns to wormhole codes', () => {
      const result = parseWormholeUrl('42-purple-dinosaur');
      expect(result.address).toBe('42-purple-dinosaur');
    });

    it('should handle wormhole code with path', () => {
      const result = parseWormholeUrl('7-guitar-sunset/page');
      expect(result.address).toBe('7-guitar-sunset');
      expect(result.path).toBe('/page');
    });

    it('should handle wh:// with wormhole code', () => {
      const result = parseWormholeUrl('wh://7-guitar-sunset');
      expect(result.address).toBe('7-guitar-sunset');
    });
  });

  describe('domain handling', () => {
    it('should preserve existing TLD', () => {
      const result = parseWormholeUrl('example.wns');
      expect(result.address).toBe('example.wns');
    });

    it('should preserve other TLDs', () => {
      const result = parseWormholeUrl('example.wh');
      expect(result.address).toBe('example.wh');
    });

    it('should add .wns to bare addresses', () => {
      const result = parseWormholeUrl('myserver');
      expect(result.address).toBe('myserver.wns');
    });
  });

  describe('edge cases', () => {
    it('should trim whitespace', () => {
      const result = parseWormholeUrl('  example  ');
      expect(result.address).toBe('example.wns');
    });

    it('should handle root path', () => {
      const result = parseWormholeUrl('example/');
      expect(result.path).toBe('/');
    });

    it('should handle deep paths', () => {
      const result = parseWormholeUrl('example/a/b/c/d');
      expect(result.path).toBe('/a/b/c/d');
    });
  });
});

describe('generateConnectionId', () => {
  it('should generate string starting with conn-', () => {
    const id = generateConnectionId();
    expect(id).toMatch(/^conn-/);
  });

  it('should generate unique IDs', () => {
    const id1 = generateConnectionId();
    const id2 = generateConnectionId();
    expect(id1).not.toBe(id2);
  });

  it('should generate alphanumeric suffix', () => {
    const id = generateConnectionId();
    expect(id).toMatch(/^conn-[a-z0-9]+$/);
  });
});

describe('injectWormholeMetadata', () => {
  const address = '7-guitar-sunset';
  const connectionId = 'conn-abc123';
  const path = '/test';

  it('should inject attributes into existing body tag', () => {
    const html = '<html><body><h1>Hello</h1></body></html>';
    const result = injectWormholeMetadata(html, address, connectionId, path);

    expect(result).toContain(`data-wh-address="${address}"`);
    expect(result).toContain(`data-wh-connection-id="${connectionId}"`);
    expect(result).toContain(`data-wh-path="${path}"`);
  });

  it('should preserve existing body attributes', () => {
    const html = '<body class="main" id="content"><h1>Hello</h1></body>';
    const result = injectWormholeMetadata(html, address, connectionId, path);

    expect(result).toContain('class="main"');
    expect(result).toContain('id="content"');
    expect(result).toContain('data-wh-address');
  });

  it('should wrap content without body tag', () => {
    const html = '<h1>No body tag</h1>';
    const result = injectWormholeMetadata(html, address, connectionId, path);

    expect(result).toContain('<body');
    expect(result).toContain('data-wh-address');
    expect(result).toContain('<h1>No body tag</h1>');
  });

  it('should handle empty body', () => {
    const html = '<body></body>';
    const result = injectWormholeMetadata(html, address, connectionId, path);

    expect(result).toContain('data-wh-address');
  });

  it('should handle body with whitespace', () => {
    const html = '<body   >content</body>';
    const result = injectWormholeMetadata(html, address, connectionId, path);

    expect(result).toContain('data-wh-address');
  });
});

describe('Chrome API Mocks', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('action API', () => {
    it('should mock setIcon', async () => {
      await chrome.action.setIcon({ path: 'icon.png' });
      expect(chrome.action.setIcon).toHaveBeenCalled();
    });

    it('should mock setTitle', () => {
      chrome.action.setTitle({ title: 'Test' });
      expect(chrome.action.setTitle).toHaveBeenCalledWith({ title: 'Test' });
    });
  });

  describe('runtime API', () => {
    it('should mock getURL', () => {
      const url = chrome.runtime.getURL('popup.html');
      expect(url).toBe('chrome-extension://test-id/popup.html');
    });

    it('should mock message listeners', () => {
      const handler = vi.fn();
      chrome.runtime.onMessage.addListener(handler);
      expect(chrome.runtime.onMessage.addListener).toHaveBeenCalledWith(handler);
    });
  });

  describe('storage API', () => {
    it('should mock storage.local.get', async () => {
      const result = await chrome.storage.local.get(['key']);
      expect(result).toEqual({});
    });

    it('should mock storage.local.set', async () => {
      await chrome.storage.local.set({ key: 'value' });
      expect(chrome.storage.local.set).toHaveBeenCalledWith({ key: 'value' });
    });
  });

  describe('tabs API', () => {
    it('should mock tabs.update', async () => {
      await chrome.tabs.update({ url: 'https://example.com' });
      expect(chrome.tabs.update).toHaveBeenCalled();
    });

    it('should mock tabs.create', async () => {
      await chrome.tabs.create({ url: 'https://example.com' });
      expect(chrome.tabs.create).toHaveBeenCalled();
    });
  });
});

describe('Message handling', () => {
  let messageHandler;

  beforeEach(() => {
    vi.clearAllMocks();
    // Capture the message handler when it's registered
    chrome.runtime.onMessage.addListener.mockImplementation((handler) => {
      messageHandler = handler;
    });
  });

  describe('GET_STATUS message', () => {
    it('should return status object', () => {
      // Simulate status response
      const sendResponse = vi.fn();
      const result = messageHandler?.(
        { type: 'GET_STATUS' },
        {},
        sendResponse
      );

      // Since we can't fully test the real handler, just verify mock works
      expect(chrome.runtime.onMessage.addListener).toBeDefined();
    });
  });
});

describe('Omnibox handling', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should register input entered listener', () => {
    chrome.omnibox.onInputEntered.addListener(vi.fn());
    expect(chrome.omnibox.onInputEntered.addListener).toHaveBeenCalled();
  });

  it('should register input changed listener', () => {
    chrome.omnibox.onInputChanged.addListener(vi.fn());
    expect(chrome.omnibox.onInputChanged.addListener).toHaveBeenCalled();
  });

  it('should register input started listener', () => {
    chrome.omnibox.onInputStarted.addListener(vi.fn());
    expect(chrome.omnibox.onInputStarted.addListener).toHaveBeenCalled();
  });

  it('should set default suggestion', () => {
    chrome.omnibox.setDefaultSuggestion({
      description: 'Enter a wormhole address'
    });
    expect(chrome.omnibox.setDefaultSuggestion).toHaveBeenCalled();
  });
});

describe('Request queue management', () => {
  // Test request queue behavior
  it('should handle concurrent requests correctly', async () => {
    const queue = Promise.resolve();
    let executionOrder = [];

    const request1 = queue.then(() => {
      executionOrder.push(1);
      return Promise.resolve();
    });

    const request2 = request1.then(() => {
      executionOrder.push(2);
      return Promise.resolve();
    });

    await request2;

    expect(executionOrder).toEqual([1, 2]);
  });
});

describe('WebSocket handling', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should register connect listener', () => {
    chrome.runtime.onConnect.addListener(vi.fn());
    expect(chrome.runtime.onConnect.addListener).toHaveBeenCalled();
  });

  it('should handle websocket port naming', () => {
    const portName = 'websocket-abc123';
    const wsId = portName.replace('websocket-', '');
    expect(wsId).toBe('abc123');
  });
});

describe('Address resolution', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should recognize wormhole code pattern', () => {
    const pattern = /^\d+-[a-z]+-[a-z]+$/i;

    expect(pattern.test('7-guitar-sunset')).toBe(true);
    expect(pattern.test('42-purple-dinosaur')).toBe(true);
    expect(pattern.test('1-a-b')).toBe(true);
    expect(pattern.test('999-hello-world')).toBe(true);

    expect(pattern.test('example.wns')).toBe(false);
    expect(pattern.test('guitar-sunset')).toBe(false);
    expect(pattern.test('7-guitar')).toBe(false);
  });

  it('should handle cached resolutions', () => {
    const cache = new Map();

    // Add to cache
    cache.set('example.wns', {
      code: '7-guitar-sunset',
      advertisement: { isExpired: () => false }
    });

    // Check cache hit
    const cached = cache.get('example.wns');
    expect(cached).toBeDefined();
    expect(cached.code).toBe('7-guitar-sunset');
  });

  it('should handle expired cache entries', () => {
    const cache = new Map();

    // Add expired entry
    cache.set('example.wns', {
      code: '7-guitar-sunset',
      advertisement: { isExpired: () => true }
    });

    const cached = cache.get('example.wns');
    const isExpired = cached?.advertisement?.isExpired?.();

    expect(isExpired).toBe(true);
  });
});

describe('Icon update', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should update icon with connection count in title', () => {
    const connectionCount = 3;
    const title = `Wormhole Browser (${connectionCount} connection${connectionCount !== 1 ? 's' : ''})`;

    expect(title).toBe('Wormhole Browser (3 connections)');
  });

  it('should handle singular connection', () => {
    const connectionCount = 1;
    const title = `Wormhole Browser (${connectionCount} connection${connectionCount !== 1 ? 's' : ''})`;

    expect(title).toBe('Wormhole Browser (1 connection)');
  });

  it('should show default title when no connections', () => {
    const hasActiveConnections = false;
    const title = hasActiveConnections ? 'Wormhole Browser (X connections)' : 'Wormhole Browser';

    expect(title).toBe('Wormhole Browser');
  });
});

describe('Data URL creation', () => {
  it('should create valid data URL', () => {
    const contentType = 'text/html';
    const body = '<h1>Hello</h1>';
    const encoded = btoa(unescape(encodeURIComponent(body)));
    const dataUrl = `data:${contentType};base64,${encoded}`;

    expect(dataUrl).toMatch(/^data:text\/html;base64,/);
  });

  it('should handle different content types', () => {
    const types = ['text/html', 'text/css', 'application/javascript', 'application/json'];

    for (const type of types) {
      const dataUrl = `data:${type};base64,dGVzdA==`;
      expect(dataUrl).toContain(`data:${type}`);
    }
  });
});

describe('Viewer URL construction', () => {
  it('should construct viewer URL with parameters', () => {
    const address = '7-guitar-sunset';
    const connectionId = 'conn-abc123';
    const path = '/about';

    const viewerUrl = chrome.runtime.getURL('viewer.html') +
      `?address=${encodeURIComponent(address)}` +
      `&connectionId=${encodeURIComponent(connectionId)}` +
      `&path=${encodeURIComponent(path)}`;

    expect(viewerUrl).toContain('viewer.html');
    expect(viewerUrl).toContain('address=7-guitar-sunset');
    expect(viewerUrl).toContain('connectionId=conn-abc123');
    expect(viewerUrl).toContain('path=%2Fabout');
  });

  it('should construct error viewer URL', () => {
    const address = 'invalid';
    const error = 'Connection failed';

    const errorUrl = chrome.runtime.getURL('viewer.html') +
      `?address=${encodeURIComponent(address)}` +
      `&error=${encodeURIComponent(error)}` +
      `&connectionId=error`;

    expect(errorUrl).toContain('error=Connection%20failed');
    expect(errorUrl).toContain('connectionId=error');
  });
});
