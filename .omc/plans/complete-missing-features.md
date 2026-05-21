# Complete Missing Features - Work Plan

> Created: 2026-01-24
> Codebase: Critical Wormhole Tools v0.4.0
> Current Phase: Phase 5 (Web Server Integration)

---

## Executive Summary

This plan addresses all identified missing features across three phases:
- **Phase A (Quick Wins)**: 3 tasks, ~2-4 hours total
- **Phase B (Medium Effort)**: 3 tasks, ~2-3 days total
- **Phase C (High Effort)**: 3 tasks, ~1-2 weeks total

---

## Phase A: Quick Wins (2-4 hours)

### A1. Browser Extension Screenshots

**Objective**: Create 2-4 promotional screenshots for Chrome Web Store and Firefox Add-ons submission.

**Current State**:
- Extension is complete at `/browser-extension/`
- Manifest at `/browser-extension/manifest.json` (MV3, version 0.4.0)
- Icons exist in `/browser-extension/icons/` (PNG: 16, 32, 48, 128)
- Popup UI at `/browser-extension/src/popup/popup.html`

**Deliverables**:
1. `screenshots/popup-connected.png` - Popup showing active connection
2. `screenshots/viewer-page.png` - Viewer displaying wh:// content
3. `screenshots/settings-page.png` - Settings/configuration screen
4. `screenshots/address-bar.png` - Omnibox "wh" keyword in action

**Implementation Steps**:
```
1. Load extension in Chrome/Firefox
2. Start wh daemon and create a test listener
3. Navigate to test content via wh://
4. Capture screenshots at:
   - 1280x800 for Chrome Web Store (primary)
   - 1280x720 for Firefox Add-ons
5. Save to /browser-extension/screenshots/
```

**File Paths**:
- Create: `/browser-extension/screenshots/` directory
- Create: `/browser-extension/screenshots/README.md` with submission checklist

**Acceptance Criteria**:
- [ ] 4 screenshots at correct dimensions
- [ ] Screenshots show extension in action (not mocked)
- [ ] Chrome Web Store requirements met (promotional tile optional)
- [ ] Firefox Add-ons requirements met

**Verification**:
- Manual review of screenshot quality
- Verify dimensions with `file` or image tool

---

### A2. Reduce Discovery Site Dilation Timeout

**Objective**: Reduce dilation timeout from 30s to 10s for better UX when peer doesn't support WebRTC dilation.

**Current State**:
- Dilation timeout hardcoded at 30000ms (30s)
- Located in `/browser-extension/src/lib/protocol/dilation.js` line 198-203
- Same file copied to `/discovery-site/src/lib/protocol/dilation.js`

**Root Cause**:
The browser uses WebRTC for dilation, but Python magic-wormhole uses TCP-based transports. They're incompatible, so dilation always times out when connecting to Python peers.

**Deliverables**:
- Reduce timeout to 10000ms (10s)
- Make timeout configurable via constant

**Implementation Steps**:
```javascript
// In dilation.js, around line 198:
// BEFORE:
setTimeout(() => {
  if (this.state !== DilationState.CONNECTED) {
    this.setState(DilationState.FAILED);
    reject(new Error('Dilation timeout'));
  }
}, 30000);

// AFTER:
const DILATION_TIMEOUT_MS = 10000;  // Configurable constant

setTimeout(() => {
  if (this.state !== DilationState.CONNECTED) {
    console.log('[Dilation] Timeout after', DILATION_TIMEOUT_MS, 'ms - peer may not support WebRTC');
    this.setState(DilationState.FAILED);
    reject(new Error('Dilation timeout - peer may not support WebRTC dilation'));
  }
}, DILATION_TIMEOUT_MS);
```

**File Paths**:
- Modify: `/browser-extension/src/lib/protocol/dilation.js`
- Modify: `/discovery-site/src/lib/protocol/dilation.js`

**Acceptance Criteria**:
- [ ] Dilation timeout is 10s in both browser-extension and discovery-site
- [ ] Timeout constant is named and documented
- [ ] Error message explains why timeout occurred
- [ ] Existing tests pass (vitest)

**Verification**:
```bash
cd browser-extension && npm test
cd discovery-site && npm test  # If tests exist
```

---

### A3. Create Phase 6 Enterprise Design Document

**Objective**: Consolidate and complete Phase 6 (Enterprise Features) design documentation.

**Current State**:
- Partial docs exist at `/docs/enterprise/`:
  - `authentication.md` - Describes auth methods (pubkey, password, LDAP)
  - `audit-logging.md` - Audit logging design
  - `rate-limiting.md` - Rate limiting design
  - `multi-tenancy.md` - Namespace isolation design
- PLAN.md mentions Phase 6 but lacks detail
- No unified design document

**Deliverables**:
- `/docs/enterprise/PHASE6_DESIGN.md` - Comprehensive design document

**Document Structure**:
```markdown
# Phase 6: Enterprise Features Design

## Overview
- Target version: v1.0.0
- Scope: Enterprise-grade security, audit, and multi-tenant features

## Features

### 1. Authentication & Authorization
- Summary of auth methods (reference authentication.md)
- Role-Based Access Control (RBAC) design
- Integration points with WNS identities

### 2. Audit Logging
- JSON-structured logging for SIEM integration
- Log rotation and retention policies
- Sensitive data handling

### 3. Rate Limiting & Quotas
- Per-identity rate limits
- Connection quotas
- Bandwidth throttling

### 4. Multi-Tenancy
- Namespace isolation
- Identity scoping
- Shared vs. isolated relays

## Implementation Phases
1. Core auth (LDAP, SSO)
2. Audit infrastructure
3. Rate limiting
4. Multi-tenancy

## API Changes
- New CLI flags
- Configuration schema
- Daemon API endpoints

## Migration Path
- Backward compatibility requirements
- Upgrade procedures
```

**File Paths**:
- Create: `/docs/enterprise/PHASE6_DESIGN.md`
- Modify: `/PLAN.md` to reference new design doc

**Acceptance Criteria**:
- [ ] Design document covers all 4 enterprise feature areas
- [ ] Implementation phases clearly defined
- [ ] API changes documented
- [ ] References existing docs where appropriate

**Verification**:
- Manual review for completeness
- Cross-reference with existing enterprise docs

---

## Phase B: Medium Effort (2-3 days)

### B1. Implement Traefik Native Plugin

**Objective**: Complete the Traefik middleware plugin to enable native wh:// URL resolution.

**Current State**:
- Scaffold exists at `/integrations/traefik-native/`
- `wormhole.go` has structure but `ServeHTTP` returns 501 Not Implemented
- `go.mod` properly configured
- README has comprehensive documentation

**Code Analysis** (from `/integrations/traefik-native/wormhole.go`):
- `WormholeMiddleware` struct defined with config
- `CreateConfig()` returns sensible defaults
- `New()` creates middleware instance
- `ServeHTTP()` has TODO stubs for resolution and proxying
- `isWormholeRequest()` always returns false
- `resolveWNS()` and `proxyToPeer()` are stubs

**Deliverables**:
1. Working `ServeHTTP()` that intercepts wh:// requests
2. `isWormholeRequest()` properly detecting wormhole hosts
3. `resolveWNS()` calling daemon API for resolution
4. `proxyToPeer()` forwarding requests through wormhole
5. Connection caching with go-cache
6. Unit tests for all components

**Implementation Steps**:

```go
// 1. Fix isWormholeRequest to detect wormhole hosts
func (w *WormholeMiddleware) isWormholeRequest(host string) bool {
    // Check for wh:// prefix in Host header
    if strings.HasPrefix(host, "wh://") {
        return true
    }
    // Check for .wns TLD suffix
    if strings.HasSuffix(host, ".wns") {
        return true
    }
    // Check for known WNS patterns (e.g., hash.tld)
    if wnsPattern.MatchString(host) {
        return true
    }
    return false
}

// 2. Implement resolveWNS with daemon API call
func (w *WormholeMiddleware) resolveWNS(ctx context.Context, name string) (string, error) {
    // Check cache first
    if w.cache != nil {
        if cached, found := w.cache.Get(name); found {
            return cached.(string), nil
        }
    }

    // Call daemon API: POST /resolve
    reqBody := map[string]string{"address": name}
    jsonBody, _ := json.Marshal(reqBody)

    req, _ := http.NewRequestWithContext(ctx, "POST",
        w.daemonURL+"/resolve", bytes.NewReader(jsonBody))
    req.Header.Set("Content-Type", "application/json")

    resp, err := http.DefaultClient.Do(req)
    if err != nil {
        return "", fmt.Errorf("daemon unreachable: %w", err)
    }
    defer resp.Body.Close()

    var result struct {
        Code    string `json:"code"`
        Address string `json:"address"`
        Error   string `json:"error"`
    }
    json.NewDecoder(resp.Body).Decode(&result)

    if result.Error != "" {
        return "", errors.New(result.Error)
    }

    // Cache the result
    if w.cache != nil {
        w.cache.Set(name, result.Code, cache.DefaultExpiration)
    }

    return result.Code, nil
}

// 3. Implement proxyToPeer
func (w *WormholeMiddleware) proxyToPeer(rw http.ResponseWriter, req *http.Request, wnsName string) {
    ctx, cancel := context.WithTimeout(req.Context(), w.timeout)
    defer cancel()

    // Build browse URL for daemon proxy
    browseURL := fmt.Sprintf("%s/browse/%s%s",
        w.daemonURL,
        url.PathEscape(wnsName),
        req.URL.Path)

    proxyReq, _ := http.NewRequestWithContext(ctx, req.Method, browseURL, req.Body)

    // Copy headers
    for k, v := range req.Header {
        proxyReq.Header[k] = v
    }
    proxyReq.Header.Set("X-Wormhole-Original-Host", req.Host)

    resp, err := http.DefaultClient.Do(proxyReq)
    if err != nil {
        http.Error(rw, "Gateway Error: "+err.Error(), http.StatusBadGateway)
        return
    }
    defer resp.Body.Close()

    // Copy response headers
    for k, v := range resp.Header {
        rw.Header()[k] = v
    }
    rw.WriteHeader(resp.StatusCode)
    io.Copy(rw, resp.Body)
}

// 4. Update ServeHTTP
func (w *WormholeMiddleware) ServeHTTP(rw http.ResponseWriter, req *http.Request) {
    host := req.Host
    if host == "" {
        host = req.Header.Get("Host")
    }

    if !w.isWormholeRequest(host) {
        w.next.ServeHTTP(rw, req)
        return
    }

    // Extract WNS name from host
    wnsName := extractWNSName(host)

    if w.debug {
        log.Printf("[wormhole] Resolving: %s", wnsName)
    }

    // Resolve and proxy
    w.proxyToPeer(rw, req, wnsName)
}
```

**File Paths**:
- Modify: `/integrations/traefik-native/wormhole.go`
- Create: `/integrations/traefik-native/wormhole_test.go`
- Modify: `/integrations/traefik-native/go.mod` (add http test deps)

**Dependencies** (reference Caddy daemon.go patterns):
- Copy daemon client patterns from `/integrations/caddy/daemon.go`
- Reuse `DaemonClient` struct or create similar

**Acceptance Criteria**:
- [ ] isWormholeRequest correctly identifies wh:// and .wns hosts
- [ ] resolveWNS calls daemon API and caches results
- [ ] proxyToPeer forwards requests and streams responses
- [ ] Error handling returns appropriate HTTP status codes
- [ ] Debug logging works when enabled
- [ ] Unit tests cover happy path and error cases
- [ ] Integration test with real daemon (manual or CI)

**Verification**:
```bash
cd integrations/traefik-native
go mod tidy
go test -v ./...
go build .  # Verify compiles
```

---

### B2. Test Caddy with Real Wormhole Connection

**Objective**: Verify Caddy plugin works end-to-end with real wormhole connections.

**Current State**:
- Caddy plugin at `/integrations/caddy/` is implemented
- Unit tests pass (13 tests)
- Integration test file exists at `/integrations/caddy/integration_test.go`
- Daemon API implemented in `/src/wh/cli/daemon.py`
- Performance tests at `/integrations/caddy/tests/performance/`

**Gap**:
PLAN.md indicates "Test Caddy plugin with real wormhole connections" is still TODO.

**Deliverables**:
1. Automated integration test that starts daemon, Caddy, and tests connection
2. Documentation of manual testing procedure
3. Verification that wormhole HTTP proxy works

**Implementation Steps**:

```go
// In integration_test.go, add real connection test:
// +build integration

func TestRealWormholeConnection(t *testing.T) {
    // Skip if daemon not available
    if !isDaemonRunning() {
        t.Skip("wh daemon not running")
    }

    // 1. Start a test HTTP server
    testServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        w.Write([]byte("Hello from wormhole!"))
    }))
    defer testServer.Close()

    // 2. Start wh listen to expose test server
    // wh listen --http --forward testServer.URL
    cmd := exec.Command("wh", "listen", "--http", "--forward", testServer.URL)
    // Parse code from output

    // 3. Configure Caddy with wormhole listener
    // 4. Make request through Caddy
    // 5. Verify response
}
```

**Alternative Manual Test Script**:
```bash
#!/bin/bash
# /integrations/caddy/test-real-connection.sh

# Terminal 1: Start daemon
wh daemon start

# Terminal 2: Start test server
python -m http.server 8000

# Terminal 3: Expose via wormhole
wh listen --http --forward http://localhost:8000
# Note the code, e.g., "7-guitar-sunset"

# Terminal 4: Build and run Caddy with plugin
cd integrations/caddy
make build
./caddy run --config Caddyfile.test

# Terminal 5: Test through Caddy
curl -H "Host: 7-guitar-sunset.wns" http://localhost:2019/
```

**File Paths**:
- Modify: `/integrations/caddy/integration_test.go`
- Create: `/integrations/caddy/test-real-connection.sh`
- Create: `/integrations/caddy/Caddyfile.test`

**Acceptance Criteria**:
- [ ] Integration test passes with real wormhole connection
- [ ] Manual test script documented and works
- [ ] HTTP GET/POST through wormhole verified
- [ ] Connection reuse works (multiple requests same connection)
- [ ] Error handling for connection failures

**Verification**:
```bash
cd integrations/caddy
./test-real-connection.sh  # Manual
go test -tags=integration -v ./...  # Automated
```

---

### B3. Fix Viewer Reconnection Issue

**Objective**: When viewer reloads or navigates, reuse existing connection instead of reconnecting.

**Current State**:
- Discovery site viewer at `/discovery-site/src/viewer.js`
- On reload, calls `ensureConnection()` which may reconnect
- Gets "crowded" error when trying to reuse wormhole code
- App.js maintains `activeConnections` Map

**Root Cause Analysis**:
From `/discovery-site/src/app.js`:
```javascript
// ensureConnection() always checks activeConnections first
let wormhole = activeConnections.get(address);
if (wormhole && (wormhole.state === WormholeState.CONNECTED || ...)) {
    return wormhole;  // Should reuse
}
```

The issue: On page reload, `activeConnections` is cleared (page state lost).

**Solution Options**:
1. **Persist connection state in SessionStorage** - Reconnect with same code
2. **Use SharedWorker** - Share connection across tabs
3. **Service Worker persistence** - Keep connection in background

**Recommended Approach**: Option 1 (simplest, most reliable)

**Deliverables**:
1. Persist connection metadata to SessionStorage on connect
2. On page load, check SessionStorage for existing connection
3. If found, attempt to reuse or gracefully reconnect
4. Handle "crowded" error by waiting and retrying

**Implementation**:

```javascript
// In app.js, add session persistence:

const SESSION_KEY = 'wh-active-connections';

function saveConnectionToSession(address, wormhole) {
    const sessions = JSON.parse(sessionStorage.getItem(SESSION_KEY) || '{}');
    sessions[address] = {
        code: wormhole.code,
        connectedAt: Date.now(),
        state: wormhole.state
    };
    sessionStorage.setItem(SESSION_KEY, JSON.stringify(sessions));
}

function getConnectionFromSession(address) {
    const sessions = JSON.parse(sessionStorage.getItem(SESSION_KEY) || '{}');
    return sessions[address] || null;
}

function clearConnectionFromSession(address) {
    const sessions = JSON.parse(sessionStorage.getItem(SESSION_KEY) || '{}');
    delete sessions[address];
    sessionStorage.setItem(SESSION_KEY, JSON.stringify(sessions));
}

// Modify ensureConnection:
export async function ensureConnection(address, useDilation = CONFIG.useDilation) {
    // Check memory cache
    let wormhole = activeConnections.get(address);
    if (wormhole && isConnected(wormhole)) {
        return wormhole;
    }

    // Check session storage for previous connection
    const sessionData = getConnectionFromSession(address);
    if (sessionData) {
        console.log('Found previous connection in session:', sessionData.code);
        // Page was reloaded - connection still exists on server
        // Try to reconnect with same code
        try {
            wormhole = await connectWithCode(sessionData.code, address);
            activeConnections.set(address, wormhole);
            saveConnectionToSession(address, wormhole);
            return wormhole;
        } catch (e) {
            if (e.message.includes('crowded')) {
                // Code still in use - wait and retry
                console.log('Connection crowded, waiting...');
                await sleep(2000);
                // Connection may have closed, try fresh
            }
            clearConnectionFromSession(address);
        }
    }

    // Normal connection flow...
}
```

**File Paths**:
- Modify: `/discovery-site/src/app.js`
- Modify: `/discovery-site/src/viewer.js` (clear session on explicit disconnect)
- Add tests if test framework exists

**Acceptance Criteria**:
- [ ] Page reload reuses existing connection when possible
- [ ] "Crowded" error handled gracefully with retry
- [ ] Session storage cleared on explicit disconnect
- [ ] Fresh connection established if session data stale
- [ ] Multiple tabs to same address handled correctly

**Verification**:
- Manual test: Connect to wormhole, reload page, verify no error
- Manual test: Open two tabs to same address, verify behavior
- Browser DevTools: Check SessionStorage for connection data

---

## Phase C: High Effort (1-2 weeks)

### C1. Implement Nginx Native C Module

**Objective**: Complete the Nginx native module for wh:// URL resolution.

**Current State**:
- Scaffold at `/integrations/nginx-native/ngx_http_wormhole_module.c`
- Module structure defined (config, directives, context)
- Handler registered but returns `NGX_DECLINED`
- CMakeLists.txt and config file present
- README with comprehensive documentation

**Code Analysis** (215 lines currently):
- Configuration struct with all needed fields
- 6 configuration directives defined
- Handler stub that logs but doesn't process
- Missing: HTTP client for daemon API, connection handling, proxy logic

**Estimated Implementation Size**: ~500 lines total

**Implementation Architecture**:
```
ngx_http_wormhole_module.c
├── Configuration (existing)
├── Directives (existing)
├── HTTP Client (NEW)
│   ├── ngx_http_wormhole_resolve()
│   └── ngx_http_wormhole_proxy()
├── Request Handler (enhance)
├── Upstream (NEW)
│   └── ngx_http_wormhole_upstream
└── Caching (NEW)
    └── ngx_http_wormhole_cache
```

**Implementation Steps**:

```c
// 1. Add HTTP subrequest for daemon API
static ngx_int_t
ngx_http_wormhole_resolve(ngx_http_request_t *r, ngx_str_t *name, ngx_str_t *code)
{
    ngx_http_wormhole_loc_conf_t *conf;
    ngx_http_upstream_t *u;

    conf = ngx_http_get_module_loc_conf(r, ngx_http_wormhole_module);

    // Create subrequest to daemon /resolve endpoint
    ngx_str_t uri;
    ngx_str_set(&uri, "/resolve");

    // POST body: {"address": "<name>"}
    ngx_chain_t *body = create_resolve_body(r, name);

    // Execute subrequest to daemon
    ngx_http_subrequest(r, &uri, NULL, &sr, NULL,
                        NGX_HTTP_SUBREQUEST_IN_MEMORY);

    // Parse response for code
    return NGX_OK;
}

// 2. Add upstream for proxying
static ngx_int_t
ngx_http_wormhole_proxy(ngx_http_request_t *r, ngx_str_t *wns_name)
{
    ngx_http_wormhole_loc_conf_t *conf;
    conf = ngx_http_get_module_loc_conf(r, ngx_http_wormhole_module);

    // Use daemon's /browse/<address>/ endpoint
    // Construct upstream URL
    ngx_str_t browse_uri;
    create_browse_uri(r, wns_name, &browse_uri);

    // Forward request via proxy_pass-like mechanism
    return ngx_http_internal_redirect(r, &browse_uri, &r->args);
}

// 3. Enhance handler
static ngx_int_t
ngx_http_wormhole_handler(ngx_http_request_t *r)
{
    ngx_http_wormhole_loc_conf_t *conf;
    ngx_str_t wns_name;

    conf = ngx_http_get_module_loc_conf(r, ngx_http_wormhole_module);

    if (!conf->enable) {
        return NGX_DECLINED;
    }

    // Check if request is for wh:// URL
    if (!is_wormhole_request(r, &wns_name)) {
        return NGX_DECLINED;
    }

    ngx_log_error(NGX_LOG_INFO, r->connection->log, 0,
                  "wormhole: handling request for %V", &wns_name);

    // Proxy to daemon
    return ngx_http_wormhole_proxy(r, &wns_name);
}

// 4. Add request detection
static ngx_int_t
is_wormhole_request(ngx_http_request_t *r, ngx_str_t *name)
{
    // Check Host header for wh:// or .wns suffix
    if (r->headers_in.host == NULL) {
        return 0;
    }

    u_char *host = r->headers_in.host->value.data;
    size_t len = r->headers_in.host->value.len;

    // Check wh:// prefix
    if (len > 5 && ngx_strncmp(host, "wh://", 5) == 0) {
        name->data = host + 5;
        name->len = len - 5;
        return 1;
    }

    // Check .wns suffix
    if (len > 4 && ngx_strncmp(host + len - 4, ".wns", 4) == 0) {
        name->data = host;
        name->len = len;
        return 1;
    }

    return 0;
}
```

**File Paths**:
- Modify: `/integrations/nginx-native/ngx_http_wormhole_module.c`
- Modify: `/integrations/nginx-native/CMakeLists.txt` (if deps needed)
- Create: `/integrations/nginx-native/test/nginx.conf` (test config)
- Create: `/integrations/nginx-native/test/test.sh` (test script)

**Testing Requirements**:
- Build against Nginx 1.24+
- Test with local daemon
- Verify resolution and proxy work
- Load test for memory leaks

**Acceptance Criteria**:
- [ ] Module compiles as dynamic and static
- [ ] wh:// and .wns hosts detected
- [ ] Daemon API called for resolution
- [ ] Requests proxied through daemon /browse endpoint
- [ ] Error handling returns appropriate status codes
- [ ] Works with Nginx's async model
- [ ] No memory leaks (valgrind verified)

**Verification**:
```bash
cd integrations/nginx-native
# Build with Nginx
./configure --add-dynamic-module=$(pwd)
make modules

# Test
sudo nginx -t -c $(pwd)/test/nginx.conf
./test/test.sh
```

---

### C2. Port Wormhole Protocol to React Native Mobile App

**Objective**: Implement working wormhole protocol in the mobile app.

**Current State**:
- Scaffold at `/mobile/`
- React Native + Expo setup complete
- 4 screens: Home, Browser, Identities, Settings
- HomeScreen has wormhole code input with placeholder logic
- BrowserScreen has WNS URL input with placeholder logic
- README documents architecture

**Missing**:
- Actual wormhole protocol implementation
- Crypto library integration
- Connection state management
- Native module for performance (optional)

**Architecture Decision**: Pure JavaScript Implementation (Phase 1)
- Reuse `/browser-extension/src/lib/` protocol code
- Use `react-native-get-random-values` for crypto
- Use `libsodium-wrappers-sumo` for nacl

**Implementation Steps**:

```javascript
// 1. Create mobile-compatible wormhole service
// /mobile/src/services/wormhole.js

import 'react-native-get-random-values';
import { Wormhole, connectWormhole, WormholeState } from '../lib/protocol/wormhole';

class WormholeService {
    constructor() {
        this.connections = new Map();
    }

    async connect(code) {
        const wormhole = await connectWormhole(code, {
            relayUrl: DEFAULT_RELAY,
            appId: 'wh.tools/mobile/v1'
        });

        this.connections.set(code, wormhole);
        return wormhole;
    }

    async sendMessage(code, message) {
        const wh = this.connections.get(code);
        if (!wh) throw new Error('Not connected');
        await wh.send(message);
    }

    async receiveMessage(code, timeout = 30000) {
        const wh = this.connections.get(code);
        if (!wh) throw new Error('Not connected');
        return await wh.receive(timeout);
    }

    disconnect(code) {
        const wh = this.connections.get(code);
        if (wh) {
            wh.close();
            this.connections.delete(code);
        }
    }
}

export const wormholeService = new WormholeService();
```

```javascript
// 2. Create mobile-compatible storage adapter
// /mobile/src/services/storage.js

import AsyncStorage from '@react-native-async-storage/async-storage';

export const storage = {
    async get(keys) {
        const result = {};
        for (const key of Array.isArray(keys) ? keys : [keys]) {
            const value = await AsyncStorage.getItem(`wh-${key}`);
            if (value) result[key] = JSON.parse(value);
        }
        return result;
    },

    async set(data) {
        for (const [key, value] of Object.entries(data)) {
            await AsyncStorage.setItem(`wh-${key}`, JSON.stringify(value));
        }
    },

    async remove(keys) {
        for (const key of Array.isArray(keys) ? keys : [keys]) {
            await AsyncStorage.removeItem(`wh-${key}`);
        }
    }
};
```

```javascript
// 3. Update HomeScreen to use real wormhole
// /mobile/src/screens/HomeScreen.js

import { wormholeService } from '../services/wormhole';

const handleConnect = async () => {
    if (!code.trim()) {
        Alert.alert('Error', 'Please enter a wormhole code');
        return;
    }

    setConnecting(true);
    try {
        const wormhole = await wormholeService.connect(code.trim());

        // Listen for state changes
        wormhole.onStateChange = (newState) => {
            if (newState === 'closed') {
                Alert.alert('Disconnected', 'Connection closed');
            }
        };

        Alert.alert('Connected!',
            `Successfully connected with code: ${code}`,
            [{ text: 'Open Browser', onPress: () => navigation.navigate('Browser') }]
        );
        setCode('');
    } catch (error) {
        Alert.alert('Connection Failed', error.message);
    } finally {
        setConnecting(false);
    }
};
```

**Directory Structure**:
```
/mobile/src/
├── lib/                    # Copy from browser-extension/src/lib/
│   ├── crypto/
│   │   ├── index.js
│   │   ├── nacl.js        # Use libsodium-wrappers-sumo
│   │   ├── spake2.js
│   │   └── hkdf.js
│   ├── protocol/
│   │   ├── wormhole.js
│   │   ├── mailbox.js
│   │   └── dilation.js    # WebRTC may not work on mobile
│   └── wns/
│       ├── identity.js
│       └── advertisement.js
├── services/
│   ├── wormhole.js        # NEW: Mobile wormhole service
│   └── storage.js         # NEW: AsyncStorage adapter
├── hooks/
│   └── useWormhole.js     # NEW: React hook for wormhole state
└── screens/
    ├── HomeScreen.js      # UPDATE: Use wormholeService
    └── BrowserScreen.js   # UPDATE: Use wormholeService
```

**File Paths to Create/Modify**:
- Copy: `/browser-extension/src/lib/` to `/mobile/src/lib/`
- Create: `/mobile/src/services/wormhole.js`
- Create: `/mobile/src/services/storage.js`
- Create: `/mobile/src/hooks/useWormhole.js`
- Modify: `/mobile/src/screens/HomeScreen.js`
- Modify: `/mobile/src/screens/BrowserScreen.js`
- Modify: `/mobile/package.json` (add dependencies)

**Dependencies to Add**:
```json
{
  "dependencies": {
    "react-native-get-random-values": "^1.10.0",
    "libsodium-wrappers-sumo": "^0.7.13",
    "@react-native-async-storage/async-storage": "^1.21.0",
    "react-native-url-polyfill": "^2.0.0"
  }
}
```

**Acceptance Criteria**:
- [ ] Wormhole connection establishes from mobile app
- [ ] Messages can be sent and received
- [ ] Connection state properly tracked and displayed
- [ ] Works on iOS Simulator
- [ ] Works on Android Emulator
- [ ] Crypto operations perform acceptably (<100ms for key exchange)
- [ ] App doesn't crash on network errors

**Verification**:
```bash
cd mobile
npm install
npm start
# Test on Expo Go or simulator
```

---

### C3. Add Mobile QR Scanning and Push Notifications

**Objective**: Add QR code scanning for wormhole codes and push notifications for incoming connections.

**Current State**:
- HomeScreen has `handleScanQR()` placeholder
- README mentions future enhancements including push notifications
- No QR or notification code implemented

**Deliverables**:
1. QR Scanner screen/modal using camera
2. QR code generation for sharing codes
3. Push notification setup (Expo Push)
4. Background connection listening

**Implementation Steps**:

**Part 1: QR Scanner**
```javascript
// /mobile/src/screens/QRScannerScreen.js

import { BarCodeScanner } from 'expo-barcode-scanner';
import { useState, useEffect } from 'react';

export default function QRScannerScreen({ navigation }) {
    const [hasPermission, setHasPermission] = useState(null);
    const [scanned, setScanned] = useState(false);

    useEffect(() => {
        (async () => {
            const { status } = await BarCodeScanner.requestPermissionsAsync();
            setHasPermission(status === 'granted');
        })();
    }, []);

    const handleBarCodeScanned = ({ type, data }) => {
        setScanned(true);

        // Parse wormhole code from QR
        // Expected format: "wh://7-guitar-sunset" or just "7-guitar-sunset"
        let code = data;
        if (data.startsWith('wh://')) {
            code = data.slice(5);
        }

        navigation.navigate('Connect', { scannedCode: code });
    };

    return (
        <View style={styles.container}>
            <BarCodeScanner
                onBarCodeScanned={scanned ? undefined : handleBarCodeScanned}
                style={StyleSheet.absoluteFillObject}
            />
            <View style={styles.overlay}>
                <View style={styles.scanArea} />
                <Text style={styles.hint}>Point camera at wormhole QR code</Text>
            </View>
        </View>
    );
}
```

**Part 2: QR Code Generation**
```javascript
// /mobile/src/components/QRCodeDisplay.js

import QRCode from 'react-native-qrcode-svg';

export default function QRCodeDisplay({ code, size = 200 }) {
    const qrValue = `wh://${code}`;

    return (
        <View style={styles.container}>
            <QRCode
                value={qrValue}
                size={size}
                color="#2D3748"
                backgroundColor="#fff"
            />
            <Text style={styles.code}>{code}</Text>
            <TouchableOpacity onPress={() => Clipboard.setString(code)}>
                <Text style={styles.copy}>Tap to copy</Text>
            </TouchableOpacity>
        </View>
    );
}
```

**Part 3: Push Notifications**
```javascript
// /mobile/src/services/notifications.js

import * as Notifications from 'expo-notifications';
import * as Device from 'expo-device';

Notifications.setNotificationHandler({
    handleNotification: async () => ({
        shouldShowAlert: true,
        shouldPlaySound: true,
        shouldSetBadge: true,
    }),
});

export async function registerForPushNotifications() {
    if (!Device.isDevice) {
        console.log('Push notifications not available on simulator');
        return null;
    }

    const { status: existingStatus } = await Notifications.getPermissionsAsync();
    let finalStatus = existingStatus;

    if (existingStatus !== 'granted') {
        const { status } = await Notifications.requestPermissionsAsync();
        finalStatus = status;
    }

    if (finalStatus !== 'granted') {
        return null;
    }

    const token = await Notifications.getExpoPushTokenAsync();
    return token.data;
}

export async function sendLocalNotification(title, body) {
    await Notifications.scheduleNotificationAsync({
        content: {
            title,
            body,
            sound: true,
        },
        trigger: null,  // Immediate
    });
}

// Called when incoming connection received
export function notifyIncomingConnection(code, peerInfo) {
    sendLocalNotification(
        'Incoming Wormhole Connection',
        `Peer requesting connection with code: ${code}`
    );
}
```

**Part 4: Background Listening**
```javascript
// /mobile/src/services/backgroundListener.js

import * as TaskManager from 'expo-task-manager';
import * as BackgroundFetch from 'expo-background-fetch';
import { wormholeService } from './wormhole';
import { notifyIncomingConnection } from './notifications';

const BACKGROUND_LISTEN_TASK = 'wormhole-background-listen';

TaskManager.defineTask(BACKGROUND_LISTEN_TASK, async () => {
    try {
        // Check for pending connections on any active listeners
        const pending = await wormholeService.checkPendingConnections();

        if (pending.length > 0) {
            for (const conn of pending) {
                notifyIncomingConnection(conn.code, conn.peerInfo);
            }
        }

        return BackgroundFetch.BackgroundFetchResult.NewData;
    } catch (error) {
        return BackgroundFetch.BackgroundFetchResult.Failed;
    }
});

export async function startBackgroundListener() {
    await BackgroundFetch.registerTaskAsync(BACKGROUND_LISTEN_TASK, {
        minimumInterval: 60,  // seconds
        stopOnTerminate: false,
        startOnBoot: true,
    });
}
```

**File Paths**:
- Create: `/mobile/src/screens/QRScannerScreen.js`
- Create: `/mobile/src/components/QRCodeDisplay.js`
- Create: `/mobile/src/services/notifications.js`
- Create: `/mobile/src/services/backgroundListener.js`
- Modify: `/mobile/src/App.js` (add QR screen to navigation)
- Modify: `/mobile/src/screens/HomeScreen.js` (integrate QR scanning)
- Modify: `/mobile/package.json` (add dependencies)

**Dependencies to Add**:
```json
{
  "dependencies": {
    "expo-barcode-scanner": "~12.5.0",
    "react-native-qrcode-svg": "^6.2.0",
    "expo-notifications": "~0.20.0",
    "expo-device": "~5.4.0",
    "expo-task-manager": "~11.3.0",
    "expo-background-fetch": "~11.3.0"
  }
}
```

**Acceptance Criteria**:
- [ ] Camera permission requested on first QR scan attempt
- [ ] QR codes with wormhole codes are scanned and parsed
- [ ] Generated QR codes can be scanned by another phone
- [ ] Push notifications appear for incoming connections
- [ ] Background listener works when app minimized (iOS limited)
- [ ] Works on both iOS and Android

**Verification**:
- Manual test: Scan QR code containing wormhole code
- Manual test: Generate QR, scan with second device
- Manual test: Put app in background, trigger notification
- Test on real devices (simulators have camera limitations)

---

## Dependencies and Prerequisites

### Phase A Prerequisites
- Browser extension loaded in dev mode
- wh daemon running
- Test wormhole listener available

### Phase B Prerequisites
- Go 1.21+ installed
- wh daemon with full API
- Docker for Caddy testing (optional)
- Real wormhole relay access

### Phase C Prerequisites
- Nginx source code (for module build)
- Xcode (for iOS)
- Android Studio (for Android)
- Expo account (for push notifications)
- Physical devices for testing

---

## Risk Identification

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Dilation never works with Python peers | High | Medium | Document limitation, fast fallback |
| Nginx async I/O complexity | Medium | High | Use simple synchronous subrequest first |
| React Native crypto performance | Medium | Medium | Profile early, consider native module |
| Mobile background limitations (iOS) | High | Medium | Document iOS restrictions, favor foreground |
| Traefik plugin API changes | Low | High | Pin to stable Traefik version |

---

## Commit Strategy

### Phase A Commits
1. `feat(browser-extension): Add store submission screenshots`
2. `fix(discovery-site): Reduce dilation timeout to 10s`
3. `docs(enterprise): Add Phase 6 design document`

### Phase B Commits
1. `feat(traefik): Implement native wormhole middleware`
2. `test(caddy): Add real wormhole integration tests`
3. `fix(discovery-site): Persist connections across page reloads`

### Phase C Commits
1. `feat(nginx): Implement native wormhole module`
2. `feat(mobile): Add wormhole protocol implementation`
3. `feat(mobile): Add QR scanning and push notifications`

---

## Success Criteria

### Phase A Complete When:
- [ ] 4 browser extension screenshots ready for store submission
- [ ] Dilation timeout is 10s in all JS code
- [ ] Phase 6 design document exists and is comprehensive

### Phase B Complete When:
- [ ] Traefik plugin resolves and proxies wh:// URLs
- [ ] Caddy integration test passes with real wormhole
- [ ] Discovery site viewer handles page reloads gracefully

### Phase C Complete When:
- [ ] Nginx module compiles and handles wh:// URLs
- [ ] Mobile app connects via wormhole protocol
- [ ] Mobile app scans QR codes and shows notifications

---

## Next Steps

After plan approval:
1. Run `/start-work` to begin implementation
2. Start with Phase A (quick wins) for immediate progress
3. Parallelize Phase B tasks if multiple developers available
4. Plan Phase C timeline based on resource availability

---

*Generated by Prometheus - Strategic Planning Consultant*
