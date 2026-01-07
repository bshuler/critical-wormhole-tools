# Changelog

All notable changes to Critical Wormhole Tools will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Nothing yet

### Changed
- Nothing yet

### Fixed
- Nothing yet

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
