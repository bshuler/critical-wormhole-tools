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

## Phase 2: Additional Network Tools (v0.2.0)

### Suggested New Commands

| Tool | Traditional Equivalent | Priority | Description |
|------|----------------------|----------|-------------|
| `wh ping` | `ping` | High | Round-trip latency measurement through wormhole |
| `wh rsync` | `rsync` | High | Efficient incremental file sync |
| `wh proxy` | SOCKS5 proxy | High | Full SOCKS5 proxy through wormhole |
| `wh tunnel` | `ssh -L/-R` | High | Local/remote port forwarding |
| `wh telnet` | `telnet` | Medium | Raw TCP connection (for debugging) |
| `wh ftp` | `ftp` | Medium | FTP client through wormhole |
| `wh nmap` | `nmap` | Medium | Port scanning through wormhole proxy |
| `wh traceroute` | `traceroute` | Medium | Hop-by-hop latency analysis |
| `wh dns` | `dig` / `nslookup` | Medium | DNS queries through wormhole |
| `wh mount` | `sshfs` / NFS | Low | Mount remote filesystem via wormhole |
| `wh vnc` | VNC client | Low | VNC desktop sharing through wormhole |
| `wh rdp` | RDP client | Low | Windows Remote Desktop through wormhole |

### Implementation Details

#### `wh ping`
```bash
# Measure wormhole connection latency
wh ping 7-guitar-sunset
# PING 7-guitar-sunset: 64 bytes icmp_seq=1 time=45.2 ms
# PING 7-guitar-sunset: 64 bytes icmp_seq=2 time=43.8 ms
```

#### `wh rsync`
```bash
# Efficient sync with delta compression
wh rsync -avz ./local/ 7-guitar-sunset:/remote/
wh rsync -avz 7-guitar-sunset:/remote/ ./local/
```

#### `wh proxy`
```bash
# Start SOCKS5 proxy
wh listen --socks5
# Configure browser: SOCKS5 proxy via wormhole code

# Client connects and uses proxy
wh proxy 7-guitar-sunset --port 1080
# Now localhost:1080 is a SOCKS5 proxy through the wormhole
```

#### `wh tunnel`
```bash
# Local port forwarding (access remote service locally)
wh tunnel -L 8080:localhost:80 7-guitar-sunset
# Now localhost:8080 connects to remote's localhost:80

# Remote port forwarding (expose local service remotely)
wh tunnel -R 8080:localhost:3000 7-guitar-sunset
# Remote's localhost:8080 now connects to your localhost:3000
```

---

## Phase 3: Permanent Wormhole Addressing (v0.3.0)

### The Problem
Current wormhole codes are ephemeral - they're generated fresh for each session and expire after use. This prevents use cases like:
- Hosting a website on a wormhole address
- Running a persistent service accessible via wormhole
- Bookmarking a wormhole address

### Proposed Solution: Wormhole Name Service (WNS)

#### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Wormhole Name Service                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌─────────────────┐    ┌────────────────┐  │
│  │   WNS Node   │◄──►│   WNS Registry  │◄──►│   WNS Node     │  │
│  │   (DHT)      │    │   (Distributed) │    │   (DHT)        │  │
│  └──────────────┘    └─────────────────┘    └────────────────┘  │
│         ▲                                           ▲           │
│         │                                           │           │
│         │          ┌─────────────────┐              │           │
│         └──────────│   WNS Client    │──────────────┘           │
│                    └─────────────────┘                          │
│                            │                                    │
│                            ▼                                    │
│                    ┌─────────────────┐                          │
│                    │   wh://name     │                          │
│                    │   Resolution    │                          │
│                    └─────────────────┘                          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

#### Naming Scheme

```
wh://mysite.wh              # Human-readable name (requires registration)
wh://abc123def456.onion.wh  # Self-certifying address (Tor-like)
wh://7-guitar-sunset        # Ephemeral code (current behavior)
```

#### Registration Flow

```bash
# Register a permanent wormhole name
wh register mysite
# Generates keypair, registers with WNS
# Output: Registered wh://mysite.wh (expires: 2025-01-01)

# Renew registration
wh renew mysite

# Transfer ownership
wh transfer mysite --to <public-key>
```

#### Self-Certifying Addresses

For users who don't want to rely on any registry:

```bash
# Generate permanent self-certifying address
wh keygen
# Output: Your permanent address: wh://a7b3c9d2e1f4.self.wh
# Private key saved to ~/.wh/keys/a7b3c9d2e1f4.key

# Anyone can connect to you using this address
# The address IS the public key (like Tor .onion addresses)
```

### Persistent Listener Daemon

```bash
# Run as a system service
wh daemon start --name mysite
# Keeps wormhole connection alive
# Auto-reconnects on failure
# Registers with WNS

# Systemd service file generated automatically
sudo systemctl enable wh-mysite
sudo systemctl start wh-mysite
```

---

## Phase 4: Browser Integration (v0.4.0)

### Wormhole Browser Extension

A Chrome/Firefox extension that allows browsing websites hosted on wormhole addresses.

#### Features

1. **URL Bar Integration**: Navigate to `wh://mysite.wh` directly
2. **Automatic Proxy**: Routes `wh://` URLs through local wormhole proxy
3. **Connection Status**: Shows connection state in toolbar
4. **Bookmarks**: Save wormhole sites like regular bookmarks

#### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Browser                                   │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐  │
│  │  Extension  │◄──►│   Native    │◄──►│   wh daemon         │  │
│  │  (JS/WASM)  │    │   Messaging │    │   (Local service)   │  │
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

#### User Experience

```
1. Install extension from Chrome Web Store / Firefox Add-ons
2. Extension prompts to install native helper (wh daemon)
3. Navigate to wh://mysite.wh
4. Extension resolves name, establishes wormhole, proxies HTTP
5. Website loads in browser!
```

#### Technical Implementation

```javascript
// background.js - Service Worker
chrome.webRequest.onBeforeRequest.addListener(
  (details) => {
    if (details.url.startsWith('wh://')) {
      // Route through local wormhole proxy
      return { redirectUrl: `http://localhost:${WH_PROXY_PORT}/${details.url}` };
    }
  },
  { urls: ['wh://*/*'] },
  ['blocking']
);
```

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
| Additional Network Tools | v0.2.0 | Q2 2024 | 🔄 Planning |
| Permanent Addressing | v0.3.0 | Q3 2024 | 📋 Design |
| Browser Extension | v0.4.0 | Q4 2024 | 📋 Design |
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
