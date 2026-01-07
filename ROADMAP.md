# Critical Wormhole Tools - Roadmap

## Current Implementation (v0.1.0)

### Implemented Networking Tools

| Tool | Traditional Equivalent | Status | Description |
|------|----------------------|--------|-------------|
| `wh nc` | `netcat` / `nc` | ✅ Complete | Bidirectional pipe over wormhole |
| `wh listen` | `nc -l` / daemon | ✅ Complete | Multi-purpose listener (port forward, SSH, HTTP) |
| `wh ssh` | `ssh` | ✅ Complete | Interactive SSH shell over wormhole |
| `wh scp` | `scp` | ✅ Complete | Secure file copy over wormhole |
| `wh sftp` | `sftp` | ✅ Complete | Interactive SFTP session |
| `wh curl` | `curl` | ✅ Complete | HTTP requests through wormhole proxy |
| `wh wget` | `wget` | ✅ Complete | File downloads through wormhole proxy |

---

## Phase 2: Additional Network Tools (v0.2.0) ✅ COMPLETE

### Implemented Commands

| Tool | Traditional Equivalent | Status | Description |
|------|----------------------|--------|-------------|
| `wh ping` | `ping` | ✅ Complete | Round-trip latency measurement through wormhole |
| `wh rsync` | `rsync` | ✅ Complete | Efficient incremental file sync (checksum-based) |
| `wh proxy` | SOCKS5 proxy | ✅ Complete | Full SOCKS5 proxy through wormhole |
| `wh tunnel` | `ssh -L/-R` | ✅ Complete | Local port forwarding (SSH-style) |

### Future Network Tools (Lower Priority)

| Tool | Traditional Equivalent | Priority | Description |
|------|----------------------|----------|-------------|
| `wh telnet` | `telnet` | Medium | Raw TCP connection (for debugging) |
| `wh ftp` | `ftp` | Medium | FTP client through wormhole |
| `wh nmap` | `nmap` | Medium | Port scanning through wormhole proxy |
| `wh traceroute` | `traceroute` | Medium | Hop-by-hop latency analysis |
| `wh dns` | `dig` / `nslookup` | Medium | DNS queries through wormhole |
| `wh mount` | `sshfs` / NFS | Low | Mount remote filesystem via wormhole |
| `wh vnc` | VNC client | Low | VNC desktop sharing through wormhole |
| `wh rdp` | RDP client | Low | Windows Remote Desktop through wormhole |

### Usage Examples

#### `wh ping`
```bash
# Responder side
wh ping -l
# Listening on code: 7-guitar-sunset

# Client side
wh ping 7-guitar-sunset
# 64 bytes from peer: seq=0 time=45.23 ms
# 64 bytes from peer: seq=1 time=43.81 ms
# 64 bytes from peer: seq=2 time=44.12 ms
# 64 bytes from peer: seq=3 time=42.95 ms
#
# --- wormhole ping statistics ---
# 4 packets transmitted, 4 received, 0.0% packet loss
# rtt min/avg/max/stddev = 42.950/44.028/45.230/0.841 ms
```

#### `wh tunnel`
```bash
# Remote: Accept tunnel connections
wh tunnel -l
# Tunnel listening on code: 7-guitar-sunset

# Local: Forward local port 8080 to remote's localhost:80
wh tunnel -L 8080:localhost:80 7-guitar-sunset
# Forwarding localhost:8080 -> localhost:80
# Tunnel active, press Ctrl+C to stop

# Now http://localhost:8080 accesses remote's port 80
```

#### `wh proxy`
```bash
# Remote: Run as proxy server
wh proxy -l
# Proxy listening on code: 7-guitar-sunset

# Local: Start SOCKS5 proxy
wh proxy 7-guitar-sunset
# SOCKS5 proxy running on 127.0.0.1:1080

# Use with curl
curl --socks5 127.0.0.1:1080 https://example.com

# Or configure browser to use SOCKS5 proxy at 127.0.0.1:1080
```

#### `wh rsync`
```bash
# Remote: Listen to receive files
wh rsync -l ./dest
# Rsync listening on code: 7-guitar-sunset

# Local: Sync directory
wh rsync -r ./src 7-guitar-sunset:./dest
# Local files: 42
# Remote files: 38
# Files to send: 5
# Sending: new-file.txt
# Sending: modified-file.py
# Sent 5 files, 12345 bytes

# With delete (remove files not in source)
wh rsync -r --delete ./src 7-guitar-sunset:./dest
```

---

## Phase 3: Wormhole Name Service (v0.3.0) ✅ COMPLETE

### The Problem (SOLVED)
Current wormhole codes are ephemeral - they're generated fresh for each session and expire after use. This prevents use cases like:
- Hosting a website on a wormhole address
- Running a persistent service accessible via wormhole
- Bookmarking a wormhole address

### Implemented Solution: Wormhole Name Service (WNS)

WNS provides persistent, self-certifying addresses using Ed25519 keypairs. The address is derived from the public key hash (like Tor .onion addresses).

#### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Wormhole Name Service                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌─────────────────┐    ┌────────────────┐  │
│  │   WNS Node   │◄──►│   Kademlia DHT  │◄──►│   WNS Node     │  │
│  │   (Client)   │    │   (Distributed) │    │   (Server)     │  │
│  └──────────────┘    └─────────────────┘    └────────────────┘  │
│         │                    │                      │           │
│         │                    │                      │           │
│         │   Lookup:          │    Publish:          │           │
│         │   address→code     │    signed            │           │
│         │                    │    advertisement     │           │
│         └────────────────────┴──────────────────────┘           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

#### Address Formats

```
wh://a7b3c9d2e1f4g5h6i7j8k9l0m1.wns    # Full self-certifying address
wh://laptop.a7b3c9d2e1f4g5h6i7j8k9l0m1.wns  # Scoped name (publisher-controlled)
wh://my-laptop.wns                      # Global name (first-come-first-served)
laptop                                  # Local alias (petname)
7-guitar-sunset                         # Ephemeral code (legacy)
```

#### Implemented Commands

```bash
# Identity Management
wh identity create                      # Generate new identity
wh identity create --name "my-server"   # With local display name
wh identity list                        # List all identities
wh identity show <address>              # Show identity details
wh identity export <address>            # Export public key
wh identity delete <address>            # Delete identity

# Scoped Names (publisher-controlled)
wh identity set-name <address> laptop   # Set scoped name
# Server advertises as: wh://laptop.<address>.wns

# Global Names (first-come-first-served via DHT)
wh identity claim-name my-laptop <addr> # Claim a global name
wh identity list-names                  # List claimed names
wh identity release-name my-laptop      # Release a name

# Local Aliases (petnames)
wh alias add laptop wh://<address>.wns  # Add alias
wh alias add server wh://<addr>.wns --username admin  # With default user
wh alias list                           # List all aliases
wh alias remove laptop                  # Remove alias
wh alias resolve laptop                 # Resolve to address

# Persistent Server
wh serve --ssh                          # Start with auto identity
wh serve --ssh --identity <address>     # Use specific identity
```

#### Security Model

| Feature | Implementation |
|---------|----------------|
| Address derivation | `base32(sha256(ed25519_pubkey)[:16])` - 26 chars |
| Code advertisement | Signed with Ed25519, includes expiry timestamp |
| Trust model | TOFU (Trust-On-First-Use), like SSH |
| Key storage | `~/.wh/known_hosts/<address>.json` |
| Name claims | Signed, expire after 7 days if not renewed |

#### Data Storage

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

## Phase 4: Browser Integration (v0.4.0) 🚧 IN PROGRESS

### Wormhole Browser Extension

A Chrome/Firefox extension that allows browsing websites hosted on wormhole addresses.

#### Implemented Features

| Feature | Status | Description |
|---------|--------|-------------|
| Extension manifest | ✅ Complete | Chrome MV3 + Firefox WebExtensions |
| Background service worker | ✅ Complete | Handles proxy configuration |
| Popup UI | ✅ Complete | Status display, address navigation |
| `wh daemon` command | ✅ Complete | Local HTTP API server |
| PAC proxy configuration | ✅ Complete | Routes `wh://` URLs through daemon |
| Native messaging host | ✅ Complete | Bridge for tighter integration |

#### Pending Features

| Feature | Status | Description |
|---------|--------|-------------|
| Full HTTP proxy | 📋 Pending | Complete request proxying through wormhole |
| Chrome Web Store | 📋 Pending | Publish to Chrome Web Store |
| Firefox Add-ons | 📋 Pending | Publish to Firefox Add-ons |

#### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Browser                                   │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐  │
│  │  Extension  │◄──►│   HTTP API  │◄──►│   wh daemon         │  │
│  │  (popup.js) │    │   :9475     │    │   (wh daemon start) │  │
│  └─────────────┘    └─────────────┘    └─────────────────────┘  │
│        │                                         │              │
│        │         ┌─────────────┐                │              │
│        └────────►│  PAC Proxy  │◄───────────────┘              │
│                  │  Config     │                               │
│                  └─────────────┘                               │
│                        │                                       │
│                        ▼                                       │
│                  wh:// URLs routed                             │
│                  through wormhole                              │
└─────────────────────────────────────────────────────────────────┘
```

#### Usage

```bash
# Start the daemon
wh daemon start

# Check status
wh daemon status

# Load extension in browser (developer mode)
# Navigate to wh://address.wns
```

#### Daemon API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/status` | GET | Check daemon status |
| `/resolve` | POST | Resolve WNS address to ephemeral code |
| `/connect` | POST | Establish wormhole connection |
| `/browse/<url>` | GET | Proxy HTTP request through wormhole |

---

## Phase 5: Web Server Integration (v0.5.0)

### Overview

Enable popular web servers to serve content over wormhole addresses natively.

### Apache Module (`mod_wormhole`)

```apache
# httpd.conf
LoadModule wormhole_module modules/mod_wormhole.so

<VirtualHost *:80>
    ServerName mysite.wh
    WormholeEnable On
    WormholeName mysite
    WormholeKey /etc/apache2/wh-keys/mysite.key

    DocumentRoot /var/www/mysite
</VirtualHost>
```

#### Implementation

```c
// mod_wormhole.c
static int wormhole_handler(request_rec *r) {
    // Establish wormhole listener
    // Forward HTTP requests/responses
    // Handle connection lifecycle
}
```

### Nginx Module (`ngx_wormhole`)

```nginx
# nginx.conf
load_module modules/ngx_wormhole_module.so;

server {
    listen wormhole;
    wormhole_name mysite;
    wormhole_key /etc/nginx/wh-keys/mysite.key;

    location / {
        root /var/www/mysite;
        index index.html;
    }
}
```

### HAProxy Integration

```haproxy
# haproxy.cfg
frontend wormhole_front
    mode http
    bind wormhole@mysite.wh
    default_backend web_servers

backend web_servers
    mode http
    server web1 127.0.0.1:8080 check
```

### Caddy Plugin

```caddyfile
# Caddyfile
mysite.wh {
    wormhole {
        name mysite
        key /etc/caddy/wh-keys/mysite.key
    }

    root * /var/www/mysite
    file_server
}
```

### Traefik Provider

```yaml
# traefik.yml
providers:
  wormhole:
    names:
      - mysite
    keyPath: /etc/traefik/wh-keys/

http:
  routers:
    mysite:
      rule: "WormholeHost(`mysite.wh`)"
      service: web
```

### Squid Proxy Integration

```squid
# squid.conf
# Enable wormhole URL scheme
wormhole_enable on
wormhole_resolver wns.example.com

# Allow wormhole URLs
acl wormhole_urls url_regex ^wh://
http_access allow wormhole_urls

# Cache wormhole content
cache allow wormhole_urls
```

---

## Phase 6: Enterprise Features (v1.0.0)

### Authentication & Authorization

```bash
# Require authentication for wormhole connection
wh listen --ssh --auth-method=pubkey --authorized-keys=/etc/wh/authorized_keys

# LDAP/AD integration
wh listen --ssh --auth-method=ldap --ldap-server=ldap://ad.company.com
```

### Audit Logging

```bash
# Enable detailed audit logging
wh daemon start --audit-log=/var/log/wh/audit.log

# Log format: JSON for SIEM integration
# {"timestamp": "...", "event": "connection", "code": "...", "peer": "...", "action": "ssh"}
```

### Rate Limiting & Quotas

```yaml
# /etc/wh/policy.yml
rate_limits:
  connections_per_minute: 10
  bandwidth_mbps: 100

quotas:
  max_concurrent_connections: 50
  max_transfer_gb_per_day: 100
```

### Multi-Tenancy

```bash
# Namespace isolation for teams
wh --namespace=engineering listen --ssh
wh --namespace=engineering ssh team-server

# Different namespaces can use same codes without conflict
```

---

## Timeline

| Phase | Version | Target | Status |
|-------|---------|--------|--------|
| Core Tools | v0.1.0 | Q1 2024 | ✅ Complete |
| Additional Network Tools | v0.2.0 | Q2 2024 | ✅ Complete |
| Wormhole Name Service | v0.3.0 | Q3 2024 | ✅ Complete |
| Browser Extension | v0.4.0 | Q4 2024 | 🚧 In Progress |
| Web Server Integration | v0.5.0 | Q1 2025 | 📋 Design |
| Enterprise Features | v1.0.0 | Q2 2025 | 📋 Design |

---

## Contributing to the Roadmap

We welcome community input on prioritization and new feature ideas!

- **Discussions**: [GitHub Discussions](https://github.com/bshuler/critical-wormhole-tools/discussions)
- **Feature Requests**: [GitHub Issues](https://github.com/bshuler/critical-wormhole-tools/issues/new?template=feature_request.md)
- **RFC Process**: Major features go through RFC process in `/rfcs` directory

---

## Name & Branding Suggestions

### Project Name Options

| Name | CLI Command | Package Name | Notes |
|------|-------------|--------------|-------|
| **Critical Wormhole Tools** | `cwt` / `wh` | `critical-wormhole` | Professional, serious |
| Wormhole Tools | `wh` | `wormhole-tools` | Simple, direct |
| Wormhole Network | `whn` | `wormhole-network` | Emphasizes networking |
| Portal Tools | `pt` | `portal-tools` | Alternative metaphor |
| Tunnel Worm | `tw` | `tunnel-worm` | Playful |

### Branding Guidelines

- **Primary Color**: Indigo (#6366f1) - representing the wormhole portal
- **Secondary**: Purple gradient (#8b5cf6 → #a855f7) - space/sci-fi feel
- **Accent**: White - for contrast and readability
- **Logo**: Concentric circles suggesting a wormhole/portal with connection arrows

### Taglines

- "Connect securely. Share easily. No IP addresses required."
- "Your network, simplified."
- "From anywhere to anywhere, securely."
- "Network tools for the NAT-traversal era."
