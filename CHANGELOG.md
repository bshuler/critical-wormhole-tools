# Changelog

All notable changes to Critical Wormhole Tools will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

#### Network Tools (Lower Priority)
- `wh telnet` - Interactive telnet client over wormhole
  - Line mode and character mode support
  - Escape sequences handling
  - Configurable timeout

- `wh ftp` - FTP client over wormhole
  - Active and passive mode support
  - Binary and ASCII transfers
  - Interactive command shell

- `wh nmap` - Network scanning through wormhole proxy
  - Port scanning (`-p`)
  - Service detection (`-sV`)
  - Multiple host support
  - JSON output (`--json`)

- `wh traceroute` - Network path tracing via wormhole
  - Configurable max hops (`-m`)
  - Custom timeout (`-w`)
  - ICMP and UDP probe modes

- `wh dns` - DNS resolution through wormhole
  - Query types: A, AAAA, MX, TXT, CNAME, NS, SOA
  - Multiple resolver support (`@server`)
  - Reverse lookups (`-x`)

- `wh mount` - Mount remote filesystems via wormhole
  - FUSE-based mounting
  - Read-only and read-write modes
  - Automatic unmount on disconnect

- `wh vnc` - VNC client over wormhole
  - Password authentication
  - TightVNC and RealVNC compatible
  - Viewer integration

- `wh rdp` - Remote Desktop Protocol over wormhole
  - NLA authentication support
  - Credential forwarding
  - Dynamic resolution

#### Browser Extension
- Chrome/Firefox extension for wormhole browsing
  - Navigate to `wh://` and `.wns` URLs directly in browser
  - Automatic proxy configuration
  - Connection status indicator
  - Address resolution via Wormhole Name System

- Extension components:
  - Background service worker for proxy management
  - Popup UI for connection status
  - Content script for link interception
  - Options page for configuration

#### Daemon
- `wh daemon` - Background daemon for browser extension
  - HTTP API on port 9475
  - WNS resolution endpoint
  - Proxy request forwarding
  - Connection pooling

#### Web Server Integrations (Phase 5)
- Caddy plugin scaffold (`integrations/caddy/`)
  - Native Go module for Caddy v2
  - Caddyfile directive support
  - Daemon client integration
  - Unit tests with mock HTTP servers

- Documentation for reverse proxy configurations:
  - Nginx configuration examples
  - Apache mod_proxy setup
  - HAProxy backend configuration
  - Traefik middleware integration
  - Squid proxy configuration

#### Docker Support
- Multi-stage `Dockerfile` for optimized images
  - Non-root user for security
  - Health check included
  - Minimal runtime image

- `docker-compose.yml` with services:
  - `daemon` - Browser extension backend
  - `relay` - Self-hosted wormhole relay (profile)
  - `ssh-server` - SSH over wormhole (profile)
  - `file-server` - HTTP file serving (profile)

- GitHub Actions workflow for Docker CI/CD
  - Automatic builds on push to main
  - Multi-architecture builds (amd64, arm64) on release
  - GitHub Container Registry publishing

#### Documentation
- Comprehensive Docker deployment guide (`docs/docker.md`)
  - Docker Compose usage
  - Kubernetes deployment examples
  - Production configurations (Traefik, Nginx)
  - Troubleshooting guide

- Updated README with:
  - Docker installation instructions
  - Integration links
  - Browser extension setup

### Changed
- Improved test coverage for async operations
- Expanded ROADMAP with Phase 5 progress

### Fixed
- VNC/RDP async test fixtures for proper cleanup
- Browser extension service worker lifecycle handling

## [0.1.0] - 2024-01-XX

### Added

#### Core Infrastructure
- `WormholeManager` class for managing Magic Wormhole connections
- Twisted/asyncio bridge for seamless async operation
- Transport adapters for AsyncSSH integration
- Streaming protocol base classes

#### Network Tools
- `wh nc` - Netcat-style bidirectional pipe over wormhole
  - Listen mode (`wh nc -l`)
  - Connect mode (`wh nc <code>`)
  - Stdin/stdout piping

- `wh listen` - Multi-purpose listener daemon
  - Port forwarding mode (`--port`)
  - SSH server mode (`--ssh`)
  - HTTP proxy mode (`--http`)
  - Custom code support (`--code`)

- `wh ssh` - SSH client over wormhole
  - Interactive shell support
  - Command execution
  - Password authentication
  - PTY allocation

- `wh scp` - Secure file copy
  - Upload files to remote
  - Download files from remote
  - Recursive directory transfer (`-r`)
  - Progress display

- `wh sftp` - Interactive SFTP client
  - Directory listing (`ls`)
  - Directory navigation (`cd`, `lcd`, `pwd`, `lpwd`)
  - File transfer (`get`, `put`)
  - File management (`mkdir`, `rm`, `rmdir`)
  - Interactive and batch modes

- `wh curl` - HTTP requests through wormhole proxy
  - GET, POST, PUT, DELETE methods
  - Custom headers (`-H`)
  - Request body (`-d`, `--data-binary`)
  - Output to file (`-o`)
  - Verbose mode (`-v`)

- `wh wget` - File downloads through wormhole proxy
  - Auto-detect filename from URL
  - Custom output filename (`-O`)
  - Output to stdout (`-O -`)
  - Directory prefix (`-P`)
  - Quiet mode (`-q`)

#### Testing
- 74 unit and integration tests
- pytest configuration with asyncio support
- Test coverage reporting
- Real wormhole relay integration tests

#### Documentation
- Comprehensive README with badges
- ROADMAP with future plans
- CONTRIBUTING guide
- This CHANGELOG

#### Packaging
- PyPI package (`critical-wormhole-tools`)
- Homebrew formula template
- Chocolatey package template
- GitHub Actions CI/CD

### Technical Details

- Python 3.10+ required
- Uses Magic Wormhole's Dilation protocol for streaming
- AsyncSSH for SSH/SCP/SFTP implementation
- Click for CLI interface
- httpx for HTTP client functionality

---

## Version History

- **0.1.0** - Initial release with core network tools

[Unreleased]: https://github.com/bshuler/critical-wormhole-tools/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/bshuler/critical-wormhole-tools/releases/tag/v0.1.0
