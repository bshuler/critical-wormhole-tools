<p align="center">
  <img src="assets/logo.svg" alt="Critical Wormhole Tools" width="200">
</p>

<h1 align="center">Critical Wormhole Tools</h1>

<p align="center">
  <strong>Secure network utilities using Magic Wormhole code-based addressing</strong>
</p>

<p align="center">
  <a href="https://github.com/bshuler/critical-wormhole-tools/actions/workflows/ci.yml">
    <img src="https://github.com/bshuler/critical-wormhole-tools/actions/workflows/ci.yml/badge.svg" alt="CI Status">
  </a>
  <a href="https://codecov.io/gh/bshuler/critical-wormhole-tools">
    <img src="https://codecov.io/gh/bshuler/critical-wormhole-tools/branch/main/graph/badge.svg" alt="codecov">
  </a>
  <a href="https://pypi.org/project/critical-wormhole-tools/">
    <img src="https://img.shields.io/pypi/v/critical-wormhole-tools.svg" alt="PyPI version">
  </a>
  <a href="https://pypi.org/project/critical-wormhole-tools/">
    <img src="https://img.shields.io/pypi/pyversions/critical-wormhole-tools.svg" alt="Python versions">
  </a>
  <a href="https://github.com/bshuler/critical-wormhole-tools/blob/main/LICENSE">
    <img src="https://img.shields.io/github/license/bshuler/critical-wormhole-tools.svg" alt="License">
  </a>
</p>

<p align="center">
  <a href="https://pypi.org/project/critical-wormhole-tools/">
    <img src="https://img.shields.io/pypi/dm/critical-wormhole-tools.svg" alt="Downloads">
  </a>
  <a href="https://github.com/bshuler/critical-wormhole-tools/stargazers">
    <img src="https://img.shields.io/github/stars/bshuler/critical-wormhole-tools.svg" alt="GitHub stars">
  </a>
  <a href="https://github.com/bshuler/critical-wormhole-tools/network/members">
    <img src="https://img.shields.io/github/forks/bshuler/critical-wormhole-tools.svg" alt="GitHub forks">
  </a>
  <a href="https://github.com/bshuler/critical-wormhole-tools/issues">
    <img src="https://img.shields.io/github/issues/bshuler/critical-wormhole-tools.svg" alt="GitHub issues">
  </a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/platform-linux%20%7C%20macos%20%7C%20windows-blue" alt="Platform">
  <img src="https://img.shields.io/badge/security-end--to--end%20encrypted-green" alt="Security">
  <img src="https://img.shields.io/badge/NAT-traversal%20built--in-orange" alt="NAT Traversal">
</p>

---

## What is Critical Wormhole Tools?

**Critical Wormhole Tools** (`cwt` / `wh`) brings the power of [Magic Wormhole](https://magic-wormhole.readthedocs.io/) code-based addressing to everyday network utilities. Instead of dealing with IP addresses, port forwarding, and firewall rules, simply share a human-readable code like `7-guitar-sunset` and connect securely from anywhere in the world.

```
┌─────────────────┐                              ┌─────────────────┐
│   Your Machine  │                              │  Remote Machine │
│                 │      "7-guitar-sunset"       │                 │
│   wh ssh ───────┼──────────────────────────────┼─────── wh listen│
│                 │     End-to-End Encrypted     │        --ssh    │
└─────────────────┘      NAT Traversal Built-in  └─────────────────┘
```

### Key Features

- **No IP addresses** - Use memorable codes like `7-guitar-sunset`
- **No port forwarding** - Works through NAT and firewalls automatically
- **End-to-end encrypted** - PAKE-based key agreement, no trusted third parties
- **Cross-platform** - Works on Linux, macOS, and Windows
- **Familiar tools** - Same interface as netcat, ssh, scp, sftp, curl, wget

---

## Installation

### Using pip (Recommended)

```bash
pip install critical-wormhole-tools
```

### Using pipx (Isolated Environment)

```bash
pipx install critical-wormhole-tools
```

### Using Homebrew (macOS/Linux)

```bash
brew tap bshuler/critical-wormhole
brew install critical-wormhole
```

### Using Chocolatey (Windows)

```powershell
choco install critical-wormhole-tools
```

### From Source

```bash
git clone https://github.com/bshuler/critical-wormhole-tools.git
cd cwt
pip install -e ".[dev]"
```

---

## Quick Start

### 1. Netcat (`wh nc`)

**Machine A (Listen):**
```bash
wh nc -l
# Output: Listening on code: 7-guitar-sunset
```

**Machine B (Connect):**
```bash
echo "Hello through the wormhole!" | wh nc 7-guitar-sunset
```

### 2. SSH (`wh ssh`)

**Server (Listen):**
```bash
wh listen --ssh
# Output: Listening on code: 3-castle-thunder
# SSH server ready
```

**Client (Connect):**
```bash
wh ssh 3-castle-thunder
# You're now in a shell on the remote machine!
```

### 3. File Transfer (`wh scp`)

**Server:**
```bash
wh listen --ssh
# Output: Listening on code: 5-river-mountain
```

**Client - Download:**
```bash
wh scp 5-river-mountain:/path/to/remote/file.txt ./local/
```

**Client - Upload:**
```bash
wh scp ./local/file.txt 5-river-mountain:/path/to/remote/
```

### 4. Interactive SFTP (`wh sftp`)

```bash
wh sftp 5-river-mountain
sftp> ls
sftp> get documents/report.pdf
sftp> put ./data.csv /home/user/
sftp> quit
```

### 5. HTTP Requests (`wh curl`)

**Server (HTTP Proxy):**
```bash
wh listen --http
# Output: Listening on code: 2-ocean-breeze
```

**Client:**
```bash
wh curl --code 2-ocean-breeze https://api.example.com/data
wh curl --code 2-ocean-breeze -X POST -d '{"key":"value"}' https://api.example.com/
```

### 6. File Download (`wh wget`)

```bash
wh wget --code 2-ocean-breeze https://example.com/large-file.zip
```

---

## Commands Reference

| Command | Description | Example |
|---------|-------------|---------|
| `wh nc` | Netcat-style bidirectional pipe | `wh nc 7-guitar-sunset` |
| `wh nc -l` | Listen for incoming connections | `wh nc -l` |
| `wh listen` | Multi-purpose listener daemon | `wh listen --ssh` |
| `wh ssh` | SSH client over wormhole | `wh ssh 3-castle-thunder` |
| `wh scp` | Secure copy files | `wh scp code:/remote ./local` |
| `wh sftp` | Interactive SFTP session | `wh sftp 3-castle-thunder` |
| `wh curl` | HTTP requests through proxy | `wh curl --code X http://...` |
| `wh wget` | Download files via HTTP proxy | `wh wget --code X http://...` |

---

## How It Works

Critical Wormhole Tools uses [Magic Wormhole](https://magic-wormhole.readthedocs.io/)'s **Dilation** protocol:

1. **Code Exchange**: Both parties enter the same code (e.g., `7-guitar-sunset`)
2. **PAKE Handshake**: Password-Authenticated Key Exchange establishes shared secrets
3. **Direct Connection**: Attempts direct P2P connection with NAT traversal
4. **Relay Fallback**: If direct fails, uses relay server (data still encrypted)
5. **Streaming**: Dilated wormhole provides reliable, ordered, bidirectional streams

```
┌────────┐         ┌─────────────┐         ┌────────┐
│ Client │◄───────►│   Mailbox   │◄───────►│ Server │
│        │   Code  │   Server    │   Code  │        │
└───┬────┘         └─────────────┘         └────┬───┘
    │                                           │
    │              PAKE Key Exchange            │
    │◄─────────────────────────────────────────►│
    │                                           │
    │           Direct P2P (if possible)        │
    │◄═════════════════════════════════════════►│
    │          or via Transit Relay             │
    │         (still E2E encrypted)             │
    └───────────────────────────────────────────┘
```

---

## Security

- **PAKE (SPAKE2)**: No passwords transmitted, even to relay servers
- **NaCl encryption**: Industry-standard cryptographic primitives
- **Forward secrecy**: Each session uses unique keys
- **No account required**: Anonymous, decentralized by design
- **Verifier display**: Optional visual verification of connection

---

## Use Cases

### Remote Access Without VPN
Access your home server from anywhere without setting up port forwarding or dynamic DNS.

### Quick File Sharing
Share files between machines without uploading to cloud services.

### Pair Programming
Give a colleague SSH access to your development machine temporarily.

### IoT Device Access
Connect to devices behind carrier-grade NAT.

### Secure API Testing
Make HTTP requests to internal APIs through a trusted proxy.

---

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `WH_RELAY` | Mailbox relay URL | `ws://relay.magic-wormhole.io:4000/v1` |
| `WH_TRANSIT` | Transit relay | `tcp:transit.magic-wormhole.io:4001` |
| `WH_SSH_PASSWORD` | SSH password (avoid prompts) | - |

### Custom Relay

For privacy or performance, run your own relay:

```bash
# Use custom relay
wh --relay ws://my-relay.example.com:4000/v1 nc -l
```

---

## Development

### Setup

```bash
git clone https://github.com/bshuler/critical-wormhole-tools.git
cd cwt
pip install -e ".[dev]"
```

### Run Tests

```bash
# All tests
pytest

# Unit tests only (fast)
pytest tests/unit

# With coverage
pytest --cov=wh --cov-report=html
```

### Code Quality

```bash
# Linting
ruff check src tests

# Type checking
mypy src
```

---

## Roadmap

- [ ] **Permanent Addresses**: Static wormhole codes for persistent services
- [ ] **Browser Extension**: Browse wormhole-hosted sites in Chrome/Firefox
- [ ] **Web Server Integration**: Apache/Nginx/HAProxy wormhole modules
- [ ] **wh ping**: Network diagnostics through wormhole
- [ ] **wh rsync**: Efficient file synchronization
- [ ] **wh proxy**: SOCKS5 proxy through wormhole

See [ROADMAP.md](ROADMAP.md) for detailed plans.

---

## Contributing

Contributions are welcome! Please read our [Contributing Guide](CONTRIBUTING.md) first.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing`)
5. Open a Pull Request

---

## License

MIT License - see [LICENSE](LICENSE) for details.

---

## Acknowledgments

- [Magic Wormhole](https://github.com/magic-wormhole/magic-wormhole) - The amazing protocol this is built on
- [AsyncSSH](https://asyncssh.readthedocs.io/) - SSH implementation
- [Twisted](https://twisted.org/) - Async networking framework

---

<p align="center">
  <strong>Connect securely. Share easily. No IP addresses required.</strong>
</p>

<p align="center">
  <a href="https://github.com/bshuler/critical-wormhole-tools">GitHub</a> •
  <a href="https://pypi.org/project/critical-wormhole-tools/">PyPI</a> •
  <a href="https://github.com/bshuler/critical-wormhole-tools/issues">Issues</a> •
  <a href="https://github.com/bshuler/critical-wormhole-tools/discussions">Discussions</a>
</p>
