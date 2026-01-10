# Critical Wormhole Tools - Project Plan

> Last Updated: 2026-01-09
> Current Version: 0.4.0
> Current Phase: Phase 5 (Web Server Integration) - In Progress

---

## Project Overview

**Critical Wormhole Tools** (`wh` / `cwt`) provides secure network utilities using Magic Wormhole code-based addressing. Instead of IP addresses and port forwarding, users share human-readable codes like `7-guitar-sunset` to connect securely from anywhere.

### Key Technologies
- **Magic Wormhole** - PAKE-based key exchange, end-to-end encryption
- **AsyncSSH** - SSH/SCP/SFTP implementation
- **Twisted/asyncio** - Async networking
- **Ed25519** - WNS identity keypairs
- **Kademlia DHT** - Distributed name resolution

---

## Current State

### Test Status
- **Python Tests**: 745 passing
- **Browser Extension Tests**: 552 passing
- **Linting**: All checks pass (ruff)
- **Coverage**: ~44% overall

### Repository Stats
- **Main Branch**: `main`
- **Latest Commit**: `9bcaa00` (chore: Add GitHub templates and pre-commit configuration)

### CI/CD Workflows
| Workflow | Status | Description |
|----------|--------|-------------|
| `ci.yml` | Active | Python tests on Linux/macOS/Windows, Python 3.10-3.13 |
| `docker.yml` | Active | Docker image build, multi-arch on release |
| `browser-extension.yml` | Active | Extension tests and artifact build |
| `discovery-site.yml` | Active | Discovery site build and GitHub Pages deploy |
| `publish.yml` | Active | PyPI publish on release |

---

## Phase Completion Status

### ✅ Phase 1: Core Tools (v0.1.0) - COMPLETE
All core networking tools implemented:
- `wh nc` - Netcat-style bidirectional pipe
- `wh listen` - Multi-purpose listener (SSH, HTTP, port forward)
- `wh ssh` - SSH client over wormhole
- `wh scp` - Secure file copy
- `wh sftp` - Interactive SFTP client
- `wh curl` - HTTP requests through wormhole
- `wh wget` - File downloads through wormhole

### ✅ Phase 2: Additional Network Tools (v0.2.0) - COMPLETE
Extended network capabilities:
- `wh ping` - Latency measurement
- `wh rsync` - Incremental file sync
- `wh proxy` - SOCKS5 proxy
- `wh tunnel` - SSH-style port forwarding
- `wh telnet` - Raw TCP connection
- `wh ftp` - FTP client
- `wh nmap` - Port scanning
- `wh traceroute` - Hop-by-hop analysis
- `wh dns` - DNS queries
- `wh mount` - FUSE filesystem mounting
- `wh vnc` - VNC client
- `wh rdp` - RDP client

### ✅ Phase 3: Wormhole Name Service (v0.3.0) - COMPLETE
Persistent addressing system:
- WNS identities (Ed25519 keypairs)
- Self-certifying addresses (`wh://address.wns`)
- Scoped names (`wh://name.address.wns`)
- Global names via DHT (`wh://my-laptop.wns`)
- Local aliases (petnames)
- TOFU trust model
- Identity management CLI

### ✅ Phase 4: Browser Extension (v0.4.0) - COMPLETE
Browser integration for wormhole URLs:
- Chrome/Firefox extension (MV3)
- Background service worker
- Popup UI for status
- PAC proxy configuration
- `wh daemon` for HTTP API
- `wh relay` for self-hosted relay
- Native messaging host

**Pending**: Publish to Chrome Web Store and Firefox Add-ons

### 🚧 Phase 5: Web Server Integration (v0.5.0) - IN PROGRESS
Enable web servers to serve over wormhole:

| Integration | Type | Status | Notes |
|-------------|------|--------|-------|
| Caddy | Go Plugin | Complete | Listener uses daemon API for connections |
| Discovery Site | Static Site | Complete | Standalone wormhole browsing, GitHub Pages |
| Nginx | Config | Docs | Reverse proxy examples |
| Apache | Config | Docs | mod_proxy examples |
| HAProxy | Config | Docs | Load balancing examples |
| Traefik | Config | Docs | Traefik config docs |
| Squid | Config | Docs | Caching proxy examples |

**Discovery Site**: A standalone static website that provides wormhole browsing without requiring an extension or daemon. Bundles the complete protocol stack in JavaScript and deploys to GitHub Pages.

### 📋 Phase 6: Enterprise Features (v1.0.0) - DESIGN
Planned enterprise capabilities:
- Authentication & Authorization (LDAP/AD integration)
- Audit Logging (JSON for SIEM)
- Rate Limiting & Quotas
- Multi-Tenancy (namespace isolation)

---

## Outstanding TODOs in Code

No critical TODOs remain. The DHT now auto-discovers bootstrap nodes via:
1. **HTTP Bootstrap** - Fetches node list from configurable URLs (default: GitHub-hosted JSON)
2. **mDNS Discovery** - Finds nodes on local network automatically
3. **Static fallback** - Hardcoded nodes can be added as needed

To set up a bootstrap node list, create `bootstrap.json`:
```json
{"nodes": [{"host": "dht1.example.com", "port": 8469}]}
```

---

## Immediate Tasks

### Ready to Do
1. [x] Add `CODE_OF_CONDUCT.md` (skipped)
2. [ ] Publish browser extension to Chrome Web Store
3. [ ] Publish browser extension to Firefox Add-ons

### Next Sprint (Phase 5 Completion)
4. [x] Implement Caddy plugin wormhole connection logic
   - Added daemon listener API endpoints (/listen, /accept, /send, /recv)
   - Implemented WormholeListener.acceptLoop using daemon API
   - Implemented connection deadlines in WormholeConn
5. [ ] Test Caddy plugin with real wormhole connections
6. [x] Write Caddy integration tests (unit tests added)

### Backlog
7. [x] Set up public DHT bootstrap nodes (now uses public BitTorrent DHT - batteries included)
8. [x] Add default identity support (implemented with CLI commands)
9. [ ] Consider native Nginx module
10. [ ] Consider native Traefik plugin
11. [ ] Start Phase 6 design document

---

## Project Structure

```
critical-wormhole-tools/
├── src/wh/                    # Main Python package
│   ├── cli/                   # CLI commands (nc, ssh, scp, etc.)
│   ├── core/                  # Core wormhole management
│   ├── http/                  # HTTP client/server
│   ├── relay/                 # Built-in relay server
│   ├── ssh/                   # SSH client/server
│   ├── transfer/              # SCP/SFTP implementations
│   └── wns/                   # Wormhole Name Service
├── tests/                     # Python tests
│   ├── unit/                  # Unit tests (fast)
│   ├── functional/            # Functional tests
│   └── integration/           # Integration tests (network)
├── browser-extension/         # Chrome/Firefox extension
│   ├── src/                   # Extension source
│   └── tests/                 # Extension tests
├── discovery-site/            # Standalone wormhole browser
│   ├── src/                   # Site source (app.js, viewer.js, lib/)
│   └── dist/                  # Built static site
├── integrations/              # Web server integrations
│   ├── caddy/                 # Caddy Go plugin
│   ├── nginx/                 # Nginx config docs
│   ├── apache/                # Apache config docs
│   ├── haproxy/               # HAProxy config docs
│   ├── traefik/               # Traefik config docs
│   └── squid/                 # Squid config docs
├── docs/                      # Documentation
│   └── docker.md              # Docker deployment guide
├── .github/                   # GitHub configuration
│   ├── workflows/             # CI/CD workflows
│   ├── ISSUE_TEMPLATE/        # Issue templates
│   └── PULL_REQUEST_TEMPLATE.md
├── Dockerfile                 # Docker image
├── docker-compose.yml         # Docker Compose services
├── Makefile                   # Development commands
├── pyproject.toml             # Python project config
├── CHANGELOG.md               # Version history
├── CONTRIBUTING.md            # Contribution guide
├── SECURITY.md                # Security policy
├── ROADMAP.md                 # Feature roadmap
└── README.md                  # Project documentation
```

---

## Development Commands

```bash
# Setup
make install-dev          # Install with dev dependencies

# Testing
make test                 # Run all Python tests
make test-coverage        # Run with coverage report
make extension-test       # Run browser extension tests
make lint                 # Run linting

# Building
make build                # Build Python package
make extension-build      # Build browser extension
make docker-build         # Build Docker image

# Other
make clean                # Remove build artifacts
make help                 # Show all commands
```

---

## Key Files for Context

When resuming work, these files provide the most context:

| File | Purpose |
|------|---------|
| `PLAN.md` | This file - current state and tasks |
| `ROADMAP.md` | Feature roadmap and phase details |
| `CHANGELOG.md` | What's been implemented |
| `pyproject.toml` | Dependencies and config |
| `integrations/caddy/` | Active development area |

---

## Session History (Recent)

### 2026-01-10 Session (Discovery Site Implementation)
Accomplished:
- **Discovery Site (standalone wormhole browsing):**
  - Created `discovery-site/` directory with complete implementation
  - Copied `lib/` directory from browser extension (100% reusable)
  - Copied `sandbox.html` (1,905 lines, 100% reusable)
  - Created `package.json` with webpack, babel, vitest dependencies
  - Created `webpack.config.js` for standalone bundle
  - Created `app.js` core module (transformed from background.js)
    - Removed all chrome.* API calls
    - Uses localStorage adapter instead of chrome.storage
    - Exports: parseWormholeUrl, resolveAddress, ensureConnection, fetchOverWormhole, openWebSocket
  - Created `index.html` landing page with URL input, recent connections, active connections
  - Created `viewer.js` and `viewer.html` (adapted from extension)
  - Added GitHub Pages deployment workflow

Files Created:
- `discovery-site/package.json`
- `discovery-site/webpack.config.js`
- `discovery-site/src/app.js`
- `discovery-site/src/index.html`
- `discovery-site/src/viewer.js`
- `discovery-site/src/viewer.html`
- `discovery-site/src/lib/` (copied from extension)
- `discovery-site/src/sandbox.html` (copied from extension)
- `.github/workflows/discovery-site.yml`

### 2026-01-10 Session (BitTorrent DHT - Batteries Included)
Accomplished:
- **BitTorrent DHT Integration (batteries included P2P discovery):**
  - Replaced standalone kademlia library with public BitTorrent Mainline DHT
  - Uses public BitTorrent bootstrap nodes by default: router.bittorrent.com, dht.transmissionbt.com, router.utorrent.com
  - Implemented `SimpleDHTNode` class with full BEP 5 protocol support (bencode, UDP messaging)
  - Added `AdvertisementServer` for serving signed advertisements via TCP
  - DHT is used for peer discovery; actual data exchanged via direct connection
  - Security: cryptographic signatures prevent DHT nodes from forging advertisements

- **Configuration Options for Custom Bootstrap:**
  - `DHTConfig.use_public_bootstrap` - Enable/disable public nodes (default: True)
  - `DHTConfig.bootstrap_nodes` - Custom bootstrap nodes list
  - Environment variables: `WH_DHT_BOOTSTRAP_NODES`, `WH_DHT_USE_PUBLIC_BOOTSTRAP`
  - Can combine custom nodes with public nodes, or use exclusively private

- **Updated Tests:**
  - 52 new/updated unit tests for BitTorrent DHT implementation
  - Tests for bencode/bdecode, bootstrap configuration, namespace encryption

Files Modified:
- `src/wh/wns/dht.py` - Complete rewrite for BitTorrent DHT
- `tests/unit/test_dht_namespace.py` - Updated tests for new implementation
- `pyproject.toml` - Removed kademlia dependency
- `PLAN.md` - Updated status

### 2026-01-10 Session (Earlier - Default Identity)
Accomplished:
- **Default Identity Support:**
  - Added config storage in `~/.wh/config.json`
  - `set_default_identity()`, `clear_default_identity()`, `get_default_identity_address()` methods
  - CLI commands: `wh identity default`, `set-default`, `clear-default`
  - `wh identity list` shows default with asterisk
  - 7 new unit tests

Files Modified:
- `src/wh/wns/identity.py` - Default identity config methods
- `src/wh/wns/cli.py` - Default identity CLI commands
- `tests/unit/test_wns.py` - Default identity tests

### 2026-01-09 Session (Caddy Plugin Implementation)
Accomplished:
- Implemented daemon listener API endpoints:
  - POST /listen - Start wormhole listener, return code
  - GET /accept/{id} - Wait for incoming connection (long-poll)
  - POST /send/{id} - Send data through connection
  - POST /recv/{id} - Receive data from connection
  - DELETE /listener/{id} - Close listener
  - DELETE /connection/{id} - Close connection
- Extended Caddy DaemonClient with listener methods
- Implemented WormholeListener.acceptLoop using daemon API
- Implemented WormholeConn with proper deadline support
- Added timeoutError type implementing net.Error interface
- Added 13 new unit tests for listener functionality

Files Modified:
- `src/wh/cli/daemon.py` - Added listener endpoints and connection management
- `integrations/caddy/daemon.go` - Added listener API client methods
- `integrations/caddy/listener.go` - Implemented acceptLoop with daemon integration
- `tests/unit/test_daemon.py` - Added listener endpoint tests

### 2026-01-09 Session (Earlier)
Accomplished:
- Updated CHANGELOG with all recent features
- Fixed Caddy plugin net.Conn interface (time.Time deadlines)
- Fixed linting issues across codebase (unused imports, f-strings)
- Added browser extension CI workflow
- Bumped version to 0.4.0
- Added Makefile for development
- Added SECURITY.md
- Updated README with Makefile usage
- Added GitHub issue/PR templates
- Added pre-commit configuration

Commits:
- `8298bc6` docs: Update CHANGELOG with recent features
- `a352c06` fix(caddy): Fix net.Conn interface implementation
- `f15df64` chore: Fix unused imports and f-string issues
- `f77b34d` chore: Fix additional linting issues
- `ebb320d` ci: Add browser extension CI workflow and bump to 0.4.0
- `d71ec31` chore: Add Makefile and update CONTRIBUTING.md
- `2cb6f2f` docs: Add SECURITY.md
- `2fdc922` docs: Update README with Makefile usage
- `9bcaa00` chore: Add GitHub templates and pre-commit configuration

---

## Current Work: Discovery Site Browser Testing

### Goal
Set up proper browser testing for the discovery site to verify wormhole connections work correctly in a browser environment.

### Problem
Headless Chromium in Playwright has issues with WebSocket/WebRTC connections - the wormhole connections fail to establish in headless mode.

### Approach: Headed Mode with xvfb-run
Use `xvfb-run` to create a virtual X display, allowing Playwright to run in "headed" mode which may have better WebSocket/WebRTC support.

### Test Plan
1. [x] Verify `xvfb-run` is available in the environment
2. [x] Test headed browser mode with xvfb-run - **WORKS!**
3. [ ] Create integration test script that uses headed mode
4. [ ] Add proper fixtures for wormhole server testing
5. [ ] Document the testing approach

### Findings (2026-01-10)
**Headed mode with xvfb-run works!** The WebSocket connection to the relay server succeeds and data is exchanged. However, there's a timing issue:

1. **Dilation timeout is 30 seconds** - The browser tries to establish a dilated connection but fails after 30 seconds
2. **Connection falls back to undilated mode** - After dilation timeout, connection continues successfully
3. **Navigation to viewer happens at ~30s** - Right at the test timeout boundary
4. **"Crowded" error on viewer reload** - The viewer tries to re-establish connection and gets a "crowded" error

**Solutions needed:**
1. Reduce dilation timeout to 10 seconds (better UX)
2. Fix viewer to reuse existing connection instead of reconnecting
3. Increase test timeout to 60 seconds to accommodate dilation fallback

### Alternative Approaches (not needed now that headed mode works)
1. **Mock/local relay** - Remove external dependency by testing against local relay
2. **API-level tests** - Test wormhole connection logic directly without browser
3. **Real browser via Selenium Grid/BrowserStack** - Cloud browsers with full networking

### Files
- `tests/integration/test_discovery_site.py` - Playwright-based integration tests
- `discovery-site/tests/run_full_integration_test.py` - Full integration test script
- `discovery-site/Makefile` - Make targets for testing

---

## Notes for Future Sessions

1. **Caddy Plugin**: Implementation is complete. The Caddy listener uses the daemon API for wormhole connections. To test:
   - Start `wh daemon start`
   - Run Caddy with wormhole network listener
   - Connections will be handled through the daemon's /listen and /accept endpoints

2. **Browser Extension Publishing**: Extensions are built and tested. Need to create developer accounts on Chrome Web Store and Firefox Add-ons, then submit for review.

3. **DHT Bootstrap**: Now uses public BitTorrent DHT by default (batteries included). Users can:
   - Use public nodes out of the box (no configuration needed)
   - Add custom nodes via `DHTConfig.bootstrap_nodes` or env var `WH_DHT_BOOTSTRAP_NODES`
   - Disable public nodes via `DHTConfig.use_public_bootstrap=False` or env var `WH_DHT_USE_PUBLIC_BOOTSTRAP=false`
   - Run private DHT networks by specifying only custom nodes

4. **Test Coverage**: Currently at 44%. CLI commands have lower coverage as they require integration testing. Focus on core modules for unit test improvements.

5. **Phase 6 Design**: Enterprise features should be designed with backward compatibility in mind. Consider a separate `wh-enterprise` package or feature flags.

---

*This plan is a living document. Update it as work progresses.*
