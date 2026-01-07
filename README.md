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
- **Persistent addresses** - WNS identities like `wh://laptop.wns` that never change
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

## Wormhole Name Service (WNS)

Regular wormhole codes like `7-guitar-sunset` are single-use—they're consumed when you connect. **WNS** provides persistent, self-certifying addresses that never change, even when the underlying wormhole code refreshes.

```
┌─────────────────┐                              ┌─────────────────┐
│   Your Machine  │                              │  Remote Machine │
│                 │    "wh://a7b3c9d2e1f4.wns"   │                 │
│   wh ssh ───────┼──────────────────────────────┼─────── wh serve │
│                 │   Persistent Identity        │        --ssh    │
└─────────────────┘   Auto-refreshing Codes      └─────────────────┘
```

### How WNS Works

1. **Generate an identity** - Creates an Ed25519 keypair; the address is derived from the public key
2. **Start a persistent server** - Automatically generates and publishes ephemeral codes
3. **Clients look up the address** - Discover the current code via DHT, verify the signature
4. **Connect using the code** - Same PAKE security as regular wormhole connections

### Creating an Identity

```bash
# Generate a new WNS identity
wh identity create
# Output: Created identity: wh://a7b3c9d2e1f4g5h6i7j8k9l0m1.wns

# Generate with a local name
wh identity create --name "my-server"

# List all identities
wh identity list

# Show details for an identity
wh identity show a7b3c9d2e1f4g5h6i7j8k9l0m1

# Export public key (for sharing)
wh identity export a7b3c9d2e1f4g5h6i7j8k9l0m1
```

### Starting a Persistent Server

```bash
# Start SSH server with WNS identity
wh serve --ssh
# Output:
# Using identity: wh://a7b3c9d2e1f4g5h6i7j8k9l0m1.wns
# Publishing to DHT: 7-guitar-sunset
# [Client connected]
# [Client disconnected]
# Publishing to DHT: 3-castle-thunder  ← New code, same address!

# With a specific identity
wh serve --ssh --identity a7b3c9d2e1f4g5h6i7j8k9l0m1
```

### Connecting to a WNS Address

All client commands accept WNS addresses:

```bash
# SSH
wh ssh wh://a7b3c9d2e1f4g5h6i7j8k9l0m1.wns

# SCP
wh scp wh://a7b3c9d2e1f4g5h6i7j8k9l0m1.wns:/path/file ./local/

# SFTP
wh sftp wh://a7b3c9d2e1f4g5h6i7j8k9l0m1.wns

# With username
wh ssh admin@wh://a7b3c9d2e1f4g5h6i7j8k9l0m1.wns
```

### Naming Your Addresses

WNS supports three types of human-readable names:

#### 1. Local Aliases (Petnames)

SSH-config style aliases stored on your machine:

```bash
# Add an alias
wh alias add laptop wh://a7b3c9d2e1f4g5h6i7j8k9l0m1.wns

# Add with default username
wh alias add work-server wh://xyz789.wns --username admin

# Now use the alias instead of the full address
wh ssh laptop
wh scp laptop:/file ./

# List all aliases
wh alias list

# Remove an alias
wh alias remove laptop
```

#### 2. Scoped Names (Publisher-Controlled)

Names controlled by the identity owner, namespaced to prevent collisions:

```bash
# Set a scoped name for your identity
wh identity set-name a7b3c9d2e1f4g5h6i7j8k9l0m1 laptop

# The server now advertises as:
# wh://laptop.a7b3c9d2e1f4g5h6i7j8k9l0m1.wns

# Clients can connect using either:
wh ssh wh://laptop.a7b3c9d2e1f4g5h6i7j8k9l0m1.wns
wh ssh wh://a7b3c9d2e1f4g5h6i7j8k9l0m1.wns
```

#### 3. Global Names (First-Come-First-Served)

Short, memorable names registered in the DHT:

```bash
# Claim a global name (links to your identity)
wh identity claim-name my-laptop a7b3c9d2e1f4g5h6i7j8k9l0m1

# Now anyone can connect via:
wh ssh wh://my-laptop.wns

# List your claimed names
wh identity list-names

# Release a name
wh identity release-name my-laptop
```

**Global Name Rules:**
- First-come-first-served (no central authority)
- Claims expire after 7 days if not renewed
- Reserved names: `wh`, `wns`, `admin`, `root`, `localhost`, etc.
- Cannot start with a digit followed by a dash (avoids confusion with wormhole codes)

### Name Resolution Order

When you connect, names are resolved in this order:

1. **Local aliases** - Check `~/.wh/aliases.json`
2. **Global names** - Look up in DHT (for `wh://name.wns` format)
3. **Scoped names** - Parse `name.address.wns` format
4. **Full addresses** - Use directly

### Trust Model (TOFU)

WNS uses Trust-On-First-Use, similar to SSH:

```bash
# First connection - public key is saved
wh ssh wh://a7b3c9d2e1f4.wns
# Output: Adding a7b3c9d2e1f4 to known hosts (TOFU)

# Subsequent connections - key is verified
wh ssh wh://a7b3c9d2e1f4.wns
# If key changed: WARNING: Public key mismatch! Possible impersonation attack.
```

Known hosts are stored in `~/.wh/known_hosts/`.

---

## Commands Reference

### Core Commands

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

### Network Tools

| Command | Description | Example |
|---------|-------------|---------|
| `wh ping` | Measure wormhole latency | `wh ping 7-guitar-sunset` |
| `wh ping -l` | Listen for ping requests | `wh ping -l` |
| `wh tunnel` | SSH-style port forwarding | `wh tunnel -L 8080:localhost:80 CODE` |
| `wh tunnel -l` | Accept tunnel connections | `wh tunnel -l` |
| `wh proxy` | SOCKS5 proxy client | `wh proxy 7-guitar-sunset` |
| `wh proxy -l` | SOCKS5 proxy server | `wh proxy -l` |
| `wh rsync` | Incremental file sync | `wh rsync -r ./src CODE:./dest` |
| `wh rsync -l` | Receive rsync files | `wh rsync -l ./dest` |

### WNS Commands

| Command | Description | Example |
|---------|-------------|---------|
| `wh identity create` | Generate new WNS identity | `wh identity create --name server` |
| `wh identity list` | List all identities | `wh identity list` |
| `wh identity show` | Show identity details | `wh identity show abc123` |
| `wh identity export` | Export public key | `wh identity export abc123` |
| `wh identity delete` | Delete an identity | `wh identity delete abc123` |
| `wh identity set-name` | Set scoped name | `wh identity set-name abc123 laptop` |
| `wh identity claim-name` | Claim global name | `wh identity claim-name my-laptop abc123` |
| `wh identity list-names` | List claimed names | `wh identity list-names` |
| `wh identity release-name` | Release global name | `wh identity release-name my-laptop` |
| `wh serve` | Persistent server with identity | `wh serve --ssh` |
| `wh alias add` | Add local alias | `wh alias add laptop wh://abc.wns` |
| `wh alias remove` | Remove alias | `wh alias remove laptop` |
| `wh alias list` | List all aliases | `wh alias list` |
| `wh alias resolve` | Resolve alias to address | `wh alias resolve laptop` |

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

### Data Directory

WNS stores data in `~/.wh/`:

```
~/.wh/
├── identity/           # WNS identities (keypairs)
│   └── <address>/
│       ├── private.key
│       └── public.key
├── known_hosts/        # Cached public keys (TOFU)
│   └── <address>.json
├── advertise/          # Published advertisements
│   └── <address>.json
├── names/              # Claimed global names
│   └── <name>.json
└── aliases.json        # Local alias mappings
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

- [x] **Wormhole Name Service (WNS)**: Persistent addresses with DHT discovery
- [x] **Local Aliases**: SSH-config style petnames for addresses
- [x] **Global Names**: First-come-first-served name registry
- [x] **wh ping**: Network diagnostics through wormhole
- [x] **wh tunnel**: SSH-style port forwarding
- [x] **wh proxy**: SOCKS5 proxy through wormhole
- [x] **wh rsync**: Efficient file synchronization
- [ ] **Browser Extension**: Browse wormhole-hosted sites in Chrome/Firefox
- [ ] **Web Server Integration**: Apache/Nginx/HAProxy wormhole modules

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
