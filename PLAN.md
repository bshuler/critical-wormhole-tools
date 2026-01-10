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
| Caddy | Go Plugin | Scaffold | Core structure done, needs wormhole logic |
| Nginx | Config | Docs | Reverse proxy examples |
| Apache | Config | Docs | mod_proxy examples |
| HAProxy | Config | Docs | Load balancing examples |
| Traefik | Config | Docs | Docker/K8s examples |
| Squid | Config | Docs | Caching proxy examples |

### 📋 Phase 6: Enterprise Features (v1.0.0) - DESIGN
Planned enterprise capabilities:
- Authentication & Authorization (LDAP/AD integration)
- Audit Logging (JSON for SIEM)
- Rate Limiting & Quotas
- Multi-Tenancy (namespace isolation)

---

## Outstanding TODOs in Code

| Priority | File | Line | Description |
|----------|------|------|-------------|
| Medium | `src/wh/wns/dht.py` | 45 | Set up public bootstrap nodes for DHT |
| Low | `src/wh/wns/identity.py` | 315 | Add support for marking identity as default |
| High | `integrations/caddy/listener.go` | 120 | Implement wormhole connection acceptance |
| Medium | `integrations/caddy/listener.go` | 221-233 | Implement connection deadlines |

---

## Immediate Tasks

### Ready to Do
1. [ ] Add `CODE_OF_CONDUCT.md`
2. [ ] Publish browser extension to Chrome Web Store
3. [ ] Publish browser extension to Firefox Add-ons

### Next Sprint (Phase 5 Completion)
4. [ ] Implement Caddy plugin wormhole connection logic
   - Connect to wh daemon HTTP API
   - Handle wormhole address resolution
   - Proxy HTTP requests through wormhole
5. [ ] Test Caddy plugin with real wormhole connections
6. [ ] Write Caddy integration tests

### Backlog
7. [ ] Set up public DHT bootstrap nodes
8. [ ] Add default identity support
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

### 2026-01-09 Session
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

## Notes for Future Sessions

1. **Caddy Plugin**: The scaffold is complete but needs actual wormhole protocol integration. The `DaemonClient` in `daemon.go` can communicate with `wh daemon` - use this for connection handling rather than reimplementing the protocol in Go.

2. **Browser Extension Publishing**: Extensions are built and tested. Need to create developer accounts on Chrome Web Store and Firefox Add-ons, then submit for review.

3. **DHT Bootstrap**: The WNS DHT implementation exists but needs public bootstrap nodes. Consider hosting these on reliable infrastructure.

4. **Test Coverage**: Currently at 44%. CLI commands have lower coverage as they require integration testing. Focus on core modules for unit test improvements.

5. **Phase 6 Design**: Enterprise features should be designed with backward compatibility in mind. Consider a separate `wh-enterprise` package or feature flags.

---

*This plan is a living document. Update it as work progresses.*
