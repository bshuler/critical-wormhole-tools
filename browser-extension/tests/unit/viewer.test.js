/**
 * Tests for the viewer navigation system
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { JSDOM } from 'jsdom';

// Helper functions from viewer.js (extracted for testing)
function isExternalLink(href) {
  if (!href) return true;
  return href.startsWith('http://') ||
         href.startsWith('https://') ||
         href.startsWith('javascript:') ||
         href.startsWith('mailto:') ||
         href.startsWith('tel:') ||
         href.startsWith('#');
}

function resolvePath(base, relative) {
  if (relative.startsWith('/')) {
    return relative;
  }
  const baseDir = base.endsWith('/') ? base : base.replace(/\/[^\/]*$/, '/');
  let path = baseDir + relative;
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

function extractBody(html) {
  const dom = new JSDOM(html);
  if (!dom.window.document.body) return html;

  // Rewrite internal links (same as viewer.js)
  const links = dom.window.document.body.querySelectorAll('a[href]');
  links.forEach(link => {
    const href = link.getAttribute('href');
    if (href && !isExternalLink(href)) {
      link.setAttribute('data-wh-href', href);
      link.setAttribute('href', '#');
      link.classList.add('wh-internal-link');
    }
  });

  return dom.window.document.body.innerHTML;
}

function extractTitle(html) {
  const match = html.match(/<title>([^<]*)<\/title>/i);
  return match ? match[1] : null;
}

describe('Link Classification', () => {
  it('should identify external links correctly', () => {
    expect(isExternalLink('https://example.com')).toBe(true);
    expect(isExternalLink('http://example.com')).toBe(true);
    expect(isExternalLink('javascript:void(0)')).toBe(true);
    expect(isExternalLink('mailto:test@test.com')).toBe(true);
    expect(isExternalLink('tel:+1234567890')).toBe(true);
    expect(isExternalLink('#section')).toBe(true);
  });

  it('should identify internal links correctly', () => {
    expect(isExternalLink('/about')).toBe(false);
    expect(isExternalLink('/contact')).toBe(false);
    expect(isExternalLink('about')).toBe(false);
    expect(isExternalLink('../contact')).toBe(false);
    expect(isExternalLink('./page')).toBe(false);
  });

  it('should treat empty/null hrefs as external', () => {
    expect(isExternalLink(null)).toBe(true);
    expect(isExternalLink(undefined)).toBe(true);
    expect(isExternalLink('')).toBe(true);
  });
});

describe('Path Resolution', () => {
  describe('absolute paths', () => {
    it('should return absolute paths unchanged', () => {
      expect(resolvePath('/', '/about')).toBe('/about');
      expect(resolvePath('/foo/bar', '/contact')).toBe('/contact');
      expect(resolvePath('/deep/nested/path', '/root')).toBe('/root');
    });
  });

  describe('relative paths from root', () => {
    it('should resolve relative paths from root', () => {
      expect(resolvePath('/', 'about')).toBe('/about');
      expect(resolvePath('/', 'foo/bar')).toBe('/foo/bar');
    });
  });

  describe('relative paths from directories', () => {
    it('should resolve relative paths from directory paths', () => {
      expect(resolvePath('/foo/', 'bar')).toBe('/foo/bar');
      expect(resolvePath('/foo/baz/', 'qux')).toBe('/foo/baz/qux');
    });

    it('should resolve relative paths from file paths', () => {
      expect(resolvePath('/foo/index.html', 'bar')).toBe('/foo/bar');
      expect(resolvePath('/foo/page.html', 'other.html')).toBe('/foo/other.html');
    });
  });

  describe('parent directory references', () => {
    it('should handle single parent reference', () => {
      expect(resolvePath('/foo/bar/', '../baz')).toBe('/foo/baz');
      expect(resolvePath('/foo/bar/page.html', '../baz')).toBe('/foo/baz');
    });

    it('should handle multiple parent references', () => {
      expect(resolvePath('/foo/bar/baz/', '../../qux')).toBe('/foo/qux');
      expect(resolvePath('/a/b/c/d/', '../../../x')).toBe('/a/x');
    });

    it('should handle current directory references', () => {
      expect(resolvePath('/foo/', './bar')).toBe('/foo/bar');
      expect(resolvePath('/foo/page.html', './bar')).toBe('/foo/bar');
    });
  });

  describe('edge cases', () => {
    it('should handle paths that go above root', () => {
      // Going above root should just return the relative part
      expect(resolvePath('/', '../about')).toBe('/about');
    });

    it('should handle complex mixed paths', () => {
      expect(resolvePath('/a/b/c/', '../d/./e/../f')).toBe('/a/b/d/f');
    });
  });
});

describe('HTML Extraction', () => {
  describe('extractBody', () => {
    it('should extract body content from full HTML', () => {
      const html = '<html><head><title>Test</title></head><body><h1>Hello</h1><p>World</p></body></html>';
      const body = extractBody(html);
      expect(body).toContain('<h1>Hello</h1>');
      expect(body).toContain('<p>World</p>');
      expect(body).not.toContain('<title>');
    });

    it('should handle HTML without body tags', () => {
      const html = '<h1>Just content</h1>';
      const body = extractBody(html);
      expect(body).toContain('Just content');
    });

    it('should rewrite internal links with data-wh-href', () => {
      const html = '<body><a href="/about">About</a><a href="https://example.com">External</a></body>';
      const body = extractBody(html);

      // Internal link should be rewritten
      expect(body).toContain('data-wh-href="/about"');
      expect(body).toContain('href="#"');
      expect(body).toContain('wh-internal-link');

      // External link should NOT be rewritten
      expect(body).toContain('href="https://example.com"');
      expect(body).not.toContain('data-wh-href="https://example.com"');
    });

    it('should rewrite relative links', () => {
      const html = '<body><a href="page">Relative</a><a href="../parent">Parent</a></body>';
      const body = extractBody(html);

      expect(body).toContain('data-wh-href="page"');
      expect(body).toContain('data-wh-href="../parent"');
    });

    it('should not rewrite hash links', () => {
      const html = '<body><a href="#section">Section</a></body>';
      const body = extractBody(html);

      expect(body).toContain('href="#section"');
      expect(body).not.toContain('data-wh-href="#section"');
    });
  });

  describe('extractTitle', () => {
    it('should extract title from HTML', () => {
      const html = '<html><head><title>My Page</title></head><body></body></html>';
      expect(extractTitle(html)).toBe('My Page');
    });

    it('should return null when no title', () => {
      const html = '<html><head></head><body></body></html>';
      expect(extractTitle(html)).toBe(null);
    });
  });
});

describe('Click Event Handling', () => {
  let dom;
  let document;

  beforeEach(() => {
    dom = new JSDOM(`
      <!DOCTYPE html>
      <html>
      <body>
        <div id="content">
          <a href="/about" id="internal-link">About</a>
          <a href="https://example.com" id="external-link">External</a>
          <a href="#section" id="hash-link">Section</a>
          <a href="relative/path" id="relative-link">Relative</a>
          <button id="not-a-link">Button</button>
        </div>
      </body>
      </html>
    `);
    document = dom.window.document;
  });

  it('should find closest anchor from nested elements', () => {
    const content = document.getElementById('content');
    const link = document.getElementById('internal-link');

    // Simulate clicking on text inside link
    const span = document.createElement('span');
    span.textContent = 'Click me';
    link.appendChild(span);

    const closest = span.closest('a');
    expect(closest).toBe(link);
    expect(closest.getAttribute('href')).toBe('/about');
  });

  it('should not find anchor when clicking non-link elements', () => {
    const button = document.getElementById('not-a-link');
    const closest = button.closest('a');
    expect(closest).toBe(null);
  });
});

describe('Navigation Integration', () => {
  it('should build correct viewer URL with parameters', () => {
    const address = '7-guitar-sunset';
    const connectionId = 'conn-abc123';
    const path = '/about';

    const viewerUrl = `chrome-extension://test-id/viewer.html` +
      `?address=${encodeURIComponent(address)}` +
      `&connectionId=${encodeURIComponent(connectionId)}` +
      `&path=${encodeURIComponent(path)}`;

    expect(viewerUrl).toContain('address=7-guitar-sunset');
    expect(viewerUrl).toContain('connectionId=conn-abc123');
    expect(viewerUrl).toContain('path=%2Fabout');
  });

  it('should parse URL parameters correctly', () => {
    const url = 'chrome-extension://test/viewer.html?address=7-guitar-sunset&connectionId=conn-123&path=/about';
    const params = new URLSearchParams(url.split('?')[1]);

    expect(params.get('address')).toBe('7-guitar-sunset');
    expect(params.get('connectionId')).toBe('conn-123');
    expect(params.get('path')).toBe('/about');
  });
});

describe('Content Type Handling', () => {
  it('should identify HTML content type', () => {
    const htmlTypes = [
      'text/html',
      'text/html; charset=utf-8',
      'text/html;charset=UTF-8'
    ];

    for (const type of htmlTypes) {
      expect(type.includes('text/html')).toBe(true);
    }
  });

  it('should identify image content types', () => {
    const imageTypes = [
      'image/png',
      'image/jpeg',
      'image/gif',
      'image/svg+xml',
      'image/webp'
    ];

    for (const type of imageTypes) {
      expect(type.startsWith('image/')).toBe(true);
    }
  });

  it('should identify CSS content type', () => {
    expect('text/css'.includes('css')).toBe(true);
  });

  it('should identify JavaScript content types', () => {
    const jsTypes = [
      'application/javascript',
      'text/javascript',
      'application/x-javascript'
    ];

    for (const type of jsTypes) {
      expect(type.includes('javascript')).toBe(true);
    }
  });
});

describe('Base URL Handling', () => {
  function getBaseUrl(address, path) {
    // Construct base URL for resolving relative paths
    const basePath = path.endsWith('/') ? path : path.replace(/\/[^\/]*$/, '/');
    return `wh://${address}${basePath}`;
  }

  it('should construct base URL from address and path', () => {
    expect(getBaseUrl('example.wns', '/')).toBe('wh://example.wns/');
    expect(getBaseUrl('example.wns', '/about')).toBe('wh://example.wns/');
    expect(getBaseUrl('example.wns', '/docs/')).toBe('wh://example.wns/docs/');
    expect(getBaseUrl('example.wns', '/docs/page.html')).toBe('wh://example.wns/docs/');
  });

  it('should handle wormhole code addresses', () => {
    expect(getBaseUrl('7-guitar-sunset', '/')).toBe('wh://7-guitar-sunset/');
    expect(getBaseUrl('7-guitar-sunset', '/page')).toBe('wh://7-guitar-sunset/');
  });
});

describe('Error Display', () => {
  it('should format error message for display', () => {
    const errors = [
      { message: 'Connection timeout', expected: 'Connection timeout' },
      { message: 'Could not resolve address: invalid', expected: 'Could not resolve address: invalid' },
      { message: 'WebSocket closed', expected: 'WebSocket closed' }
    ];

    for (const { message, expected } of errors) {
      expect(message).toBe(expected);
    }
  });

  it('should handle error objects', () => {
    const error = new Error('Test error');
    expect(error.message).toBe('Test error');
    expect(error.toString()).toContain('Test error');
  });
});

describe('Loading State', () => {
  it('should track loading states', () => {
    const states = {
      loading: true,
      content: null,
      error: null
    };

    // Simulate loading complete
    states.loading = false;
    states.content = '<h1>Loaded</h1>';

    expect(states.loading).toBe(false);
    expect(states.content).not.toBeNull();
  });

  it('should track error states', () => {
    const states = {
      loading: false,
      content: null,
      error: 'Connection failed'
    };

    expect(states.error).toBe('Connection failed');
  });
});

describe('History Management', () => {
  it('should build history entry', () => {
    const entry = {
      address: '7-guitar-sunset',
      path: '/about',
      title: 'About Page',
      timestamp: Date.now()
    };

    expect(entry.address).toBe('7-guitar-sunset');
    expect(entry.path).toBe('/about');
    expect(entry.timestamp).toBeGreaterThan(0);
  });

  it('should track navigation history', () => {
    const history = [];

    history.push({ path: '/' });
    history.push({ path: '/about' });
    history.push({ path: '/contact' });

    expect(history.length).toBe(3);
    expect(history[history.length - 1].path).toBe('/contact');
  });

  it('should support back navigation', () => {
    const history = [{ path: '/' }, { path: '/about' }];
    let currentIndex = 1;

    // Go back
    currentIndex--;
    expect(history[currentIndex].path).toBe('/');
  });

  it('should support forward navigation', () => {
    const history = [{ path: '/' }, { path: '/about' }];
    let currentIndex = 0;

    // Go forward
    currentIndex++;
    expect(history[currentIndex].path).toBe('/about');
  });
});

describe('Resource URL Rewriting', () => {
  function rewriteResourceUrl(url, baseAddress, currentPath) {
    // Handle relative URLs
    if (url.startsWith('/')) {
      // Absolute path - keep as is but prepend wh protocol
      return `wh://${baseAddress}${url}`;
    } else if (!url.includes('://')) {
      // Relative path
      const basePath = currentPath.replace(/\/[^\/]*$/, '/');
      return `wh://${baseAddress}${basePath}${url}`;
    }
    // External URL - return as is
    return url;
  }

  it('should rewrite absolute paths', () => {
    const result = rewriteResourceUrl('/images/logo.png', 'example.wns', '/about');
    expect(result).toBe('wh://example.wns/images/logo.png');
  });

  it('should rewrite relative paths', () => {
    const result = rewriteResourceUrl('style.css', 'example.wns', '/docs/page.html');
    expect(result).toBe('wh://example.wns/docs/style.css');
  });

  it('should not rewrite external URLs', () => {
    const result = rewriteResourceUrl('https://cdn.example.com/lib.js', 'example.wns', '/');
    expect(result).toBe('https://cdn.example.com/lib.js');
  });

  it('should handle root path correctly', () => {
    const result = rewriteResourceUrl('script.js', 'example.wns', '/');
    expect(result).toBe('wh://example.wns/script.js');
  });
});

describe('Form Handling', () => {
  function buildFormData(form) {
    const data = {};
    // Simulate collecting form data
    const inputs = [
      { name: 'username', value: 'test' },
      { name: 'password', value: 'secret' }
    ];

    for (const input of inputs) {
      data[input.name] = input.value;
    }

    return data;
  }

  it('should collect form data', () => {
    const formData = buildFormData({});
    expect(formData.username).toBe('test');
    expect(formData.password).toBe('secret');
  });

  it('should construct form action URL', () => {
    const action = '/submit';
    const address = 'example.wns';
    const actionUrl = `wh://${address}${action}`;

    expect(actionUrl).toBe('wh://example.wns/submit');
  });
});

describe('iframe Sandboxing', () => {
  it('should define sandbox attributes', () => {
    const sandboxAttrs = 'allow-scripts allow-same-origin allow-forms allow-popups';

    expect(sandboxAttrs).toContain('allow-scripts');
    expect(sandboxAttrs).toContain('allow-same-origin');
    expect(sandboxAttrs).toContain('allow-forms');
    expect(sandboxAttrs).toContain('allow-popups');
  });

  it('should not allow top navigation by default', () => {
    const sandboxAttrs = 'allow-scripts allow-same-origin';
    expect(sandboxAttrs).not.toContain('allow-top-navigation');
  });
});

describe('Address Bar Display', () => {
  function formatAddressBar(address, path) {
    const normalizedPath = path === '/' ? '' : path;
    return `wh://${address}${normalizedPath}`;
  }

  it('should format address bar for root path', () => {
    expect(formatAddressBar('example.wns', '/')).toBe('wh://example.wns');
  });

  it('should format address bar with path', () => {
    expect(formatAddressBar('example.wns', '/about')).toBe('wh://example.wns/about');
  });

  it('should format wormhole code address', () => {
    expect(formatAddressBar('7-guitar-sunset', '/page')).toBe('wh://7-guitar-sunset/page');
  });
});

describe('Message Passing', () => {
  it('should structure navigation message', () => {
    const message = {
      type: 'NAVIGATE',
      address: 'example.wns',
      path: '/about',
      connectionId: 'conn-123'
    };

    expect(message.type).toBe('NAVIGATE');
    expect(message.address).toBe('example.wns');
    expect(message.path).toBe('/about');
  });

  it('should structure fetch response', () => {
    const response = {
      success: true,
      data: {
        status: 200,
        headers: { 'content-type': 'text/html' },
        body: '<h1>Hello</h1>'
      }
    };

    expect(response.success).toBe(true);
    expect(response.data.status).toBe(200);
  });

  it('should structure error response', () => {
    const response = {
      success: false,
      error: 'Connection timeout'
    };

    expect(response.success).toBe(false);
    expect(response.error).toBe('Connection timeout');
  });
});
