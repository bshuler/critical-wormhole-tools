# Work Plan: NPM Packages, Dilation Support, and Mobile Implementation

> Generated: 2026-01-24
> **Revised: 2026-01-24** - Added Phase A for publishable NPM packages
> Scope: Create publishable NPM packages from browser extension, fix dilation bugs, implement mobile app
> Estimated Effort: 5-7 days

---

## Context

### Original Request
Implement dilation for all tools which currently do not support it, plus:
1. React Native wormhole service needs real SPAKE2/relay implementation
2. Nginx module compilation/testing infrastructure
3. Screenshot capture (manual - documentation exists)
4. Phase 6 enterprise features (out of scope - 18 week project)
5. Mobile app testing with Expo (manual - requires physical device)

### Research Findings

**CRITICAL DISCOVERY: The browser extension contains NOVEL implementations that should be published as NPM packages:**

The browser extension's protocol libraries are NOT just copies of existing packages - they are original implementations that fill gaps in the JavaScript ecosystem:

| Package | What It Does | Why It's Novel |
|---------|--------------|----------------|
| `@wormhole-tools/spake2` | SPAKE2 symmetric mode over Ed25519 | Only modern browser-compatible SPAKE2 implementation |
| `@wormhole-tools/mailbox` | Magic Wormhole mailbox WebSocket client | No existing package for this |
| `@wormhole-tools/dilation` | WebRTC-based dilation + subchannel multiplexing | UNIQUE - no other implementation exists anywhere |
| `@wormhole-tools/protocol` | High-level wormhole API | Bundles all above for easy consumption |

**Source Files (Browser Extension):**

| File | Lines | Dependencies |
|------|-------|--------------|
| `/browser-extension/src/lib/crypto/spake2.js` | 369 | `@noble/ed25519`, `@noble/hashes` |
| `/browser-extension/src/lib/crypto/hkdf.js` | ~50 | `@noble/hashes` |
| `/browser-extension/src/lib/crypto/nacl.js` | ~150 | `@noble/ciphers` or tweetnacl |
| `/browser-extension/src/lib/crypto/hash.js` | ~30 | `@noble/hashes` |
| `/browser-extension/src/lib/crypto/ed25519.js` | ~100 | `@noble/ed25519` |
| `/browser-extension/src/lib/crypto/index.js` | ~20 | Re-exports |
| `/browser-extension/src/lib/protocol/mailbox.js` | 527 | None |
| `/browser-extension/src/lib/protocol/dilation.js` | 965 | spake2, hkdf, nacl |
| `/browser-extension/src/lib/protocol/transit.js` | ~300 | spake2 |
| `/browser-extension/src/lib/protocol/wormhole.js` | 610 | All above |

**Dilation Pattern (Python CLI):**
The correct pattern for dilation is seen in `ssh.py` (lines 98-99):
```python
await manager.create_and_set_code(code)
await manager.dilate()  # <-- REPLACES establish() - NOT added after it!
```

**CRITICAL FINDING:** `ssh.py` does NOT call `establish()` at all. The `dilate()` method REPLACES `establish()` - it handles both connection establishment AND dilation setup in one call.

**Components WITHOUT Dilation (BUG):**
| File | Issue |
|------|-------|
| `/src/wh/cli/ping.py` | Uses `establish()` then `connector_for/listener_for` without `dilate()` |
| `/src/wh/cli/rsync.py` | Uses `establish()` then `connector_for/listener_for` without `dilate()` |
| `/src/wh/cli/tunnel.py` | Uses `establish()` then `connector_for/listener_for` without `dilate()` |
| `/src/wh/cli/proxy.py` | Uses `establish()` then `connector_for/listener_for` without `dilate()` |
| `/src/wh/cli/telnet.py` | Uses `establish()` then `connector_for/listener_for` without `dilate()` |
| `/src/wh/cli/ftp.py` | Uses `establish()` then `connector_for/listener_for` without `dilate()` |
| `/src/wh/cli/nmap.py` | Uses `establish()` then `connector_for/listener_for` without `dilate()` |
| `/src/wh/cli/traceroute.py` | Uses `establish()` then `connector_for/listener_for` without `dilate()` |
| `/src/wh/cli/dns.py` | Uses `establish()` then `connector_for/listener_for` without `dilate()` |
| `/src/wh/cli/mount.py` | Uses `establish()` then `connector_for/listener_for` without `dilate()` |
| `/src/wh/cli/vnc.py` | Uses `establish()` then `connector_for/listener_for` without `dilate()` |
| `/src/wh/cli/rdp.py` | Uses `establish()` then `connector_for/listener_for` without `dilate()` |

---

## Work Objectives

### Core Objective
1. **Create publishable NPM packages** from browser extension code
2. **Fix all CLI tools** that incorrectly use `establish()` instead of `dilate()`
3. **Mobile app** imports from published packages instead of copying code

### Deliverables
1. **4 NPM packages** published to npm registry under `@wormhole-tools` scope
2. **Dilation fixes for 12 CLI tools** - All tools properly call `dilate()`
3. **Mobile app** using `@wormhole-tools/protocol` package
4. **Nginx module test infrastructure** - Docker-based compilation

### Definition of Done
- [ ] `@wormhole-tools/spake2` published with tests
- [ ] `@wormhole-tools/mailbox` published with tests
- [ ] `@wormhole-tools/dilation` published with tests
- [ ] `@wormhole-tools/protocol` published with tests
- [ ] All 12 affected CLI tools use `dilate()` instead of `establish()`
- [ ] Unit tests pass (`make test`)
- [ ] Mobile app connects using `@wormhole-tools/protocol`
- [ ] Nginx module compiles in Docker environment

---

## Must Have (Guardrails)

1. **DO** create proper npm packages with package.json, TypeScript definitions, tests
2. **DO** REPLACE `establish()` with `dilate()` in CLI tools - do NOT add after
3. **DO** add TypeScript type definitions (.d.ts) for all packages
4. **DO** reuse browser extension tests where applicable
5. **DO NOT** break existing working tools (ssh, scp, sftp, curl, wget)
6. **DO NOT** change the protocol names used by each tool
7. **DO NOT** modify browser extension source directly (extract, don't change)

---

## Must NOT Have (Exclusions)

1. Phase 6 enterprise features (separate 18-week project)
2. Screenshot capture (requires manual human action)
3. Mobile app testing with Expo (requires physical device/simulator)
4. Publishing browser extension to stores (separate process)

---

## Task Flow and Dependencies

```
PHASE A: NPM PACKAGES
[A1] Create monorepo structure
      |
      v
[A2] Extract @wormhole-tools/spake2 --+
      |                                |
      v                                | (Parallel)
[A3] Extract @wormhole-tools/mailbox --+
      |
      v
[A4] Extract @wormhole-tools/dilation (depends on A2)
      |
      v
[A5] Create @wormhole-tools/protocol bundle (depends on A2-A4)
      |
      v
[A6] Add TypeScript definitions
      |
      v
[A7] Add tests and publish

PHASE B: PYTHON CLI DILATION FIXES (can start in parallel with A4+)
[B1-B12] Fix all 12 CLI tools (ping, rsync, tunnel, proxy, telnet, ftp, nmap, traceroute, dns, mount, vnc, rdp)
      |
      v
[B13] Verify all tests pass

PHASE C: MOBILE APP (depends on A7)
[C1] Add @wormhole-tools/protocol to mobile
      |
      v
[C2] Add React Native polyfills
      |
      v
[C3] Update wormhole.js to use packages

PHASE D: NGINX (independent)
[D1] Docker infrastructure
      |
      v
[D2] CI/CD workflow
```

---

## Detailed Tasks

### PHASE A: Create Publishable NPM Packages

---

### Task A1: Create Monorepo Structure
**Location:** `/packages/`

**Required Structure:**
```
/packages/
  /spake2/
    package.json
    tsconfig.json
    src/
      index.js
    types/
      index.d.ts
    tests/
  /mailbox/
    package.json
    ...
  /dilation/
    package.json
    ...
  /protocol/
    package.json
    ...
```

**Root Configuration:**
```json
// /packages/package.json (workspace root)
{
  "name": "@wormhole-tools/monorepo",
  "private": true,
  "workspaces": ["packages/*"]
}
```

**Acceptance Criteria:**
- [ ] `/packages/` directory created
- [ ] Workspace root package.json configured
- [ ] Common tsconfig.json for all packages

---

### Task A2: Extract `@wormhole-tools/spake2`
**Source:** `/browser-extension/src/lib/crypto/spake2.js` (369 lines)

**Package Files:**
```
/packages/spake2/
  package.json
  src/
    index.js        <- from spake2.js
    hkdf.js         <- from crypto/hkdf.js (dependency)
  types/
    index.d.ts      <- TypeScript definitions
  README.md
```

**package.json:**
```json
{
  "name": "@wormhole-tools/spake2",
  "version": "0.1.0",
  "description": "SPAKE2 Password-Authenticated Key Exchange for browsers",
  "main": "src/index.js",
  "types": "types/index.d.ts",
  "exports": {
    ".": {
      "import": "./src/index.js",
      "types": "./types/index.d.ts"
    }
  },
  "dependencies": {
    "@noble/ed25519": "^2.0.0",
    "@noble/hashes": "^1.3.0"
  },
  "keywords": ["spake2", "pake", "key-exchange", "cryptography", "magic-wormhole"]
}
```

**TypeScript Definitions (types/index.d.ts):**
```typescript
export class SPAKE2_Symmetric {
  constructor(password: Uint8Array, idSymmetric?: Uint8Array);
  start(): Uint8Array;
  finish(inboundMessage: Uint8Array): Uint8Array;
}

export function createSPAKE2(password: string, appId?: string): SPAKE2_Symmetric;

// Legacy exports
export class SymmetricSPAKE2 {
  constructor(appId: string, passwordHash: Uint8Array, side: string);
  start(): Promise<Uint8Array>;
  finish(peerMessage: Uint8Array): Promise<Uint8Array>;
}
```

**Acceptance Criteria:**
- [ ] Package structure created
- [ ] Code extracted from browser extension (no modifications needed)
- [ ] TypeScript definitions added
- [ ] `npm pack` succeeds
- [ ] Works with `@noble/ed25519` and `@noble/hashes`

---

### Task A3: Extract `@wormhole-tools/mailbox`
**Source:** `/browser-extension/src/lib/protocol/mailbox.js` (527 lines)

**Package Files:**
```
/packages/mailbox/
  package.json
  src/
    index.js        <- from mailbox.js
  types/
    index.d.ts
  README.md
```

**package.json:**
```json
{
  "name": "@wormhole-tools/mailbox",
  "version": "0.1.0",
  "description": "Magic Wormhole mailbox WebSocket client",
  "main": "src/index.js",
  "types": "types/index.d.ts",
  "keywords": ["magic-wormhole", "mailbox", "websocket", "rendezvous"]
}
```

**TypeScript Definitions:**
```typescript
export const MessageType: {
  BIND: string;
  ALLOCATE: string;
  CLAIM: string;
  OPEN: string;
  ADD: string;
  RELEASE: string;
  CLOSE: string;
  PING: string;
  WELCOME: string;
  ALLOCATED: string;
  CLAIMED: string;
  MESSAGE: string;
  RELEASED: string;
  CLOSED: string;
  ACK: string;
  PONG: string;
  ERROR: string;
};

export const DEFAULT_RELAY: string;

export class MailboxClient {
  constructor(relayUrl?: string, appId?: string);
  static generateSide(): string;
  connect(): Promise<object>;
  allocate(): Promise<string>;
  claim(nameplate: string): Promise<object>;
  open(mailbox?: string): Promise<void>;
  addMessage(phase: string, body: string | object | Uint8Array): Promise<void>;
  onMessage(handler: (phase: string, body: string | Uint8Array, side: string) => void): () => void;
  waitForPhase(phase: string, timeout?: number): Promise<string>;
  waitForPhaseWithSide(phase: string, timeout?: number): Promise<{body: string | Uint8Array, side: string}>;
  release(): Promise<void>;
  close(): Promise<void>;
}

export function parseCode(code: string): { nameplate: string; password: string };
export function generateCode(nameplate: string, numWords?: number): string;
```

**Acceptance Criteria:**
- [ ] Package structure created
- [ ] Code extracted (no dependencies needed!)
- [ ] TypeScript definitions added
- [ ] Works standalone with browser WebSocket

---

### Task A4: Extract `@wormhole-tools/dilation`
**Source:** `/browser-extension/src/lib/protocol/dilation.js` (965 lines)

**Dependencies:** `@wormhole-tools/spake2` (for crypto helpers)

**Package Files:**
```
/packages/dilation/
  package.json
  src/
    index.js        <- from dilation.js
    nacl.js         <- from crypto/nacl.js (encryption)
    hkdf.js         <- from crypto/hkdf.js (key derivation)
  types/
    index.d.ts
  README.md
```

**package.json:**
```json
{
  "name": "@wormhole-tools/dilation",
  "version": "0.1.0",
  "description": "Magic Wormhole dilation protocol with WebRTC subchannels",
  "main": "src/index.js",
  "types": "types/index.d.ts",
  "dependencies": {
    "@noble/ciphers": "^0.4.0",
    "@noble/hashes": "^1.3.0"
  },
  "peerDependencies": {
    "@wormhole-tools/mailbox": "^0.1.0"
  },
  "keywords": ["magic-wormhole", "dilation", "webrtc", "subchannel", "multiplexing"]
}
```

**Acceptance Criteria:**
- [ ] Package structure created
- [ ] Crypto helpers (nacl.js, hkdf.js) included
- [ ] TypeScript definitions for DilationManager, Subchannel, etc.
- [ ] Works with browser WebRTC APIs

---

### Task A5: Create `@wormhole-tools/protocol` Bundle
**Source:** `/browser-extension/src/lib/protocol/wormhole.js` (610 lines)

**This package bundles everything for easy consumption.**

**Package Files:**
```
/packages/protocol/
  package.json
  src/
    index.js        <- from wormhole.js (high-level API)
    transit.js      <- from transit.js
  types/
    index.d.ts
  README.md
```

**package.json:**
```json
{
  "name": "@wormhole-tools/protocol",
  "version": "0.1.0",
  "description": "Complete Magic Wormhole protocol implementation for browsers",
  "main": "src/index.js",
  "types": "types/index.d.ts",
  "dependencies": {
    "@wormhole-tools/spake2": "^0.1.0",
    "@wormhole-tools/mailbox": "^0.1.0",
    "@wormhole-tools/dilation": "^0.1.0"
  },
  "keywords": ["magic-wormhole", "secure-transfer", "webrtc", "p2p"]
}
```

**TypeScript Definitions:**
```typescript
export const WormholeState: {
  DISCONNECTED: string;
  ALLOCATING: string;
  WAITING: string;
  EXCHANGING: string;
  CONNECTED: string;
  DILATING: string;
  DILATED: string;
  FAILED: string;
  CLOSED: string;
};

export class Wormhole {
  constructor(options?: { relayUrl?: string; appId?: string });
  allocate(numWords?: number): Promise<string>;
  connect(code: string): Promise<void>;
  waitForPeer(): Promise<void>;
  send(data: Uint8Array | string): Promise<void>;
  receive(timeout?: number): Promise<Uint8Array>;
  dilate(): Promise<{ connect: (protocol: string) => SubchannelConnector; listen: (protocol: string) => SubchannelListener }>;
  close(): Promise<void>;

  code: string | null;
  verifier: string | null;
  state: string;
  isDilated: boolean;

  onStateChange: ((newState: string, oldState: string) => void) | null;
  onMessage: ((data: Uint8Array) => void) | null;
  onError: ((error: Error) => void) | null;
}

export function createWormhole(options?: object): Promise<Wormhole>;
export function connectWormhole(code: string, options?: object): Promise<Wormhole>;

// Re-export everything
export * from '@wormhole-tools/spake2';
export * from '@wormhole-tools/mailbox';
export * from '@wormhole-tools/dilation';
```

**Acceptance Criteria:**
- [ ] High-level Wormhole class works
- [ ] All sub-packages re-exported
- [ ] Compatible with browser extension (drop-in replacement)

---

### Task A6: Add TypeScript Definitions
**Scope:** All packages

**Acceptance Criteria:**
- [ ] All exported classes/functions have TypeScript definitions
- [ ] Types are accurate and match implementation
- [ ] `npm run typecheck` passes (if configured)

---

### Task A7: Add Tests and Publish
**Scope:** All packages

**Test Sources (reuse from browser extension):**
- `/browser-extension/tests/` - Existing tests

**CI Workflow (.github/workflows/npm-packages.yml):**
```yaml
name: NPM Packages
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
      - run: npm ci
        working-directory: packages
      - run: npm test
        working-directory: packages

  publish:
    if: github.ref == 'refs/heads/main'
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          registry-url: 'https://registry.npmjs.org'
      - run: npm ci && npm publish --workspaces --access public
        working-directory: packages
        env:
          NODE_AUTH_TOKEN: ${{ secrets.NPM_TOKEN }}
```

**Acceptance Criteria:**
- [ ] Tests pass for all packages
- [ ] CI workflow configured
- [ ] (Optional) Published to npm under `@wormhole-tools` scope

---

### PHASE B: Fix Python CLI Dilation

---

### Task B1: Fix `wh ping` Dilation Bug
**File:** `/Users/bshuler/code/wormhole_netcat_ssh_scp_sftp_copy_curl_wget/src/wh/cli/ping.py`

**Required Change:**
REPLACE `await manager.establish()` with `await manager.dilate()` on lines 321 and 336.

**Acceptance Criteria:**
- [ ] Line 321: `establish()` replaced with `dilate()` (listen mode)
- [ ] Line 336: `establish()` replaced with `dilate()` (client mode)
- [ ] `wh ping -l` works (generates code, waits for peer)
- [ ] `wh ping <code>` works (connects and measures latency)

---

### Tasks B2-B12: Fix Remaining Tools

| Task | Tool | File |
|------|------|------|
| B2 | rsync | `/src/wh/cli/rsync.py` |
| B3 | tunnel | `/src/wh/cli/tunnel.py` |
| B4 | proxy | `/src/wh/cli/proxy.py` |
| B5 | telnet | `/src/wh/cli/telnet.py` |
| B6 | ftp | `/src/wh/cli/ftp.py` |
| B7 | nmap | `/src/wh/cli/nmap.py` |
| B8 | traceroute | `/src/wh/cli/traceroute.py` |
| B9 | dns | `/src/wh/cli/dns.py` |
| B10 | mount | `/src/wh/cli/mount.py` |
| B11 | vnc | `/src/wh/cli/vnc.py` |
| B12 | rdp | `/src/wh/cli/rdp.py` |

**Pattern for ALL:** REPLACE `await manager.establish()` with `await manager.dilate()` in BOTH listen and client modes.

---

### Task B13: Verify All Tests Pass
**Command:** `make test`

**Acceptance Criteria:**
- [ ] All 791 Python tests pass
- [ ] No regressions in core functionality
- [ ] `make lint` passes

---

### PHASE C: Mobile App Uses Published Packages

---

### Task C1: Add `@wormhole-tools/protocol` to Mobile
**File:** `/mobile/package.json`

**Add Dependencies:**
```json
{
  "dependencies": {
    "@wormhole-tools/protocol": "^0.1.0"
  }
}
```

**Acceptance Criteria:**
- [ ] Package added to dependencies
- [ ] `npm install` succeeds

---

### Task C2: Add React Native Polyfills
**File:** `/mobile/package.json` and `/mobile/index.js`

**Required Polyfills:**
```json
{
  "dependencies": {
    "react-native-get-random-values": "^1.11.0",
    "react-native-webrtc": "^118.0.0"
  }
}
```

**In `/mobile/index.js` (BEFORE other imports):**
```javascript
import 'react-native-get-random-values';
```

**Acceptance Criteria:**
- [ ] `react-native-get-random-values` installed (already present at line 26)
- [ ] `react-native-webrtc` installed
- [ ] Polyfills imported at app entry point

---

### Task C3: Update Wormhole Service to Use Packages
**File:** `/mobile/src/services/wormhole.js`

**Replace placeholder with real implementation:**
```javascript
import { Wormhole, WormholeState } from '@wormhole-tools/protocol';

// Note: react-native-webrtc provides RTCPeerConnection globally
// The @wormhole-tools/dilation package will use it automatically

class WormholeService {
  async connect(code) {
    const wormhole = new Wormhole({
      relayUrl: 'wss://relay.magic-wormhole.io/v1',
      appId: 'wh.tools/v1'
    });

    await wormhole.connect(code);
    await wormhole.dilate();  // Enable WebRTC dilation

    return wormhole;
  }

  // ... rest of service
}
```

**Acceptance Criteria:**
- [ ] Placeholder implementation removed
- [ ] Real `@wormhole-tools/protocol` imported
- [ ] `connect(code)` establishes real connection
- [ ] Dilation works (WebRTC via `react-native-webrtc`)
- [ ] Works with Python CLI tools as peer

---

### PHASE D: Nginx Module Test Infrastructure

---

### Task D1: Nginx Module Docker Infrastructure
**Location:** `/integrations/nginx-native/`

**Create Dockerfile:**
```dockerfile
FROM nginx:1.25 AS builder
RUN apt-get update && apt-get install -y \
    build-essential \
    libpcre3-dev \
    zlib1g-dev \
    libssl-dev

COPY . /src
WORKDIR /src
RUN ./configure.sh && make

FROM nginx:1.25
COPY --from=builder /src/ngx_http_wormhole_module.so /etc/nginx/modules/
COPY nginx.conf /etc/nginx/nginx.conf
```

**Acceptance Criteria:**
- [ ] Dockerfile created
- [ ] `docker build` succeeds
- [ ] Module loads in nginx

---

### Task D2: Nginx CI/CD Workflow
**File:** `.github/workflows/nginx-module.yml`

```yaml
name: Nginx Module
on: [push, pull_request]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build module
        run: docker build -t nginx-wormhole integrations/nginx-native
      - name: Test module loads
        run: docker run --rm nginx-wormhole nginx -t
```

**Acceptance Criteria:**
- [ ] CI workflow created
- [ ] Runs on PR
- [ ] Module compilation verified

---

## Risk Identification and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| NPM scope `@wormhole-tools` unavailable | Low | Medium | Check availability first, use alternative if needed |
| Dilation fix breaks existing tools | Low | High | Only replace `establish()` with `dilate()` |
| Mobile WebRTC incompatible | Medium | Medium | Use well-tested `react-native-webrtc` |
| Nginx module won't compile | Medium | Low | Docker isolation, separate workflow |

---

## Commit Strategy

```
Phase A:
1. feat(packages): Create monorepo structure for NPM packages
2. feat(spake2): Extract @wormhole-tools/spake2 package
3. feat(mailbox): Extract @wormhole-tools/mailbox package
4. feat(dilation): Extract @wormhole-tools/dilation package
5. feat(protocol): Create @wormhole-tools/protocol bundle
6. feat(packages): Add TypeScript definitions
7. ci(packages): Add test and publish workflow

Phase B:
8. fix(cli): Add dilation support to ping command
9. fix(cli): Add dilation support to rsync, tunnel, proxy commands
10. fix(cli): Add dilation support to remaining tools (8 tools)
11. test: Verify all CLI tests pass

Phase C:
12. feat(mobile): Integrate @wormhole-tools/protocol package
13. feat(mobile): Add React Native WebRTC polyfills

Phase D:
14. ci(nginx): Add Docker-based module compilation testing
```

---

## Success Criteria

1. **NPM packages published** - All 4 packages available on npm
2. **All 12 CLI tools work with dilation** - Manual testing shows connection success
3. **Test suite passes** - `make test` shows 791+ tests passing
4. **Mobile app connects** - React Native app uses published packages
5. **Nginx module compiles** - Docker build succeeds in CI

---

## Notes

- **CRITICAL**: The fix pattern is to REPLACE `establish()` with `dilate()`, NOT add `dilate()` after `establish()`
- The browser extension code is production-quality and battle-tested
- TypeScript definitions enable great IDE support for consumers
- The `@wormhole-tools/dilation` package is UNIQUE - no other JS implementation of Magic Wormhole dilation exists
- Mobile implementation becomes trivial once packages are published - just `npm install @wormhole-tools/protocol`
