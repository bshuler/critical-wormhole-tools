# Deployment Guide

This guide covers all deployment options for Critical Wormhole Tools.

## Table of Contents

1. [Quick Start](#quick-start)
2. [PyPI Installation](#pypi-installation)
3. [Docker Deployment](#docker-deployment)
4. [System Requirements](#system-requirements)
5. [Configuration Options](#configuration-options)
6. [Environment Variables](#environment-variables)
7. [Production Deployment](#production-deployment)
8. [Troubleshooting](#troubleshooting)

---

## Quick Start

### Install via pip

```bash
pip install critical-wormhole-tools
```

### Verify installation

```bash
wh --version
wh --help
```

### Run your first command

```bash
# On one machine
wh nc -l
# Output: Listening on code: 7-guitar-sunset

# On another machine
echo "Hello!" | wh nc 7-guitar-sunset
```

---

## PyPI Installation

### Standard Installation

```bash
# Install latest stable release
pip install critical-wormhole-tools

# Install specific version
pip install critical-wormhole-tools==0.4.0

# Upgrade to latest
pip install --upgrade critical-wormhole-tools
```

### Installation with Optional Dependencies

```bash
# Enterprise features (LDAP, audit logging, rate limiting)
pip install "critical-wormhole-tools[enterprise]"

# Browser extension dependencies
pip install "critical-wormhole-tools[browser]"

# Development dependencies
pip install "critical-wormhole-tools[dev]"

# All optional dependencies
pip install "critical-wormhole-tools[all]"
```

### Using pipx (Isolated Environment)

```bash
# Install in isolated environment
pipx install critical-wormhole-tools

# Install with extras
pipx install "critical-wormhole-tools[enterprise]"

# Upgrade
pipx upgrade critical-wormhole-tools
```

### Using Homebrew (macOS/Linux)

```bash
# Add tap
brew tap bshuler/critical-wormhole

# Install
brew install critical-wormhole

# Upgrade
brew upgrade critical-wormhole
```

### Using Chocolatey (Windows)

```powershell
# Install
choco install critical-wormhole-tools

# Upgrade
choco upgrade critical-wormhole-tools
```

### From Source

```bash
git clone https://github.com/bshuler/critical-wormhole-tools.git
cd critical-wormhole-tools

# Install in editable mode
pip install -e ".[dev]"

# Or build and install
python -m build
pip install dist/critical_wormhole_tools-*.whl
```

---

## Docker Deployment

### Pull Pre-built Image

```bash
# Pull from GitHub Container Registry
docker pull ghcr.io/bshuler/critical-wormhole-tools:latest

# Pull specific version
docker pull ghcr.io/bshuler/critical-wormhole-tools:0.4.0
```

### Run Commands

```bash
# Run any wh command
docker run --rm ghcr.io/bshuler/critical-wormhole-tools nc -l

# Interactive mode
docker run -it --rm ghcr.io/bshuler/critical-wormhole-tools sftp 7-guitar-sunset

# With persistent data
docker run -v ~/.wh:/home/wormhole/.wh \
  ghcr.io/bshuler/critical-wormhole-tools identity list
```

### Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  daemon:
    image: ghcr.io/bshuler/critical-wormhole-tools:latest
    command: daemon start
    ports:
      - "9475:9475"
    volumes:
      - wh-data:/home/wormhole/.wh
    restart: unless-stopped

  relay:
    image: ghcr.io/bshuler/critical-wormhole-tools:latest
    command: relay serve -p 4000 -t 4001
    ports:
      - "4000:4000"
      - "4001:4001"
    restart: unless-stopped
    profiles: ["relay"]

volumes:
  wh-data:
```

Run services:

```bash
# Start daemon only
docker-compose up -d daemon

# Start daemon and relay
docker-compose --profile relay up -d

# Check logs
docker-compose logs -f daemon

# Stop all
docker-compose down
```

See [docker.md](docker.md) for comprehensive Docker documentation.

---

## System Requirements

### Minimum Requirements

- **Python**: 3.10 or higher
- **Operating System**: Linux, macOS, or Windows
- **Memory**: 256 MB RAM
- **Disk Space**: 100 MB for installation
- **Network**: Internet connection for relay servers

### Recommended Requirements

- **Python**: 3.11 or 3.12
- **Memory**: 512 MB RAM
- **Disk Space**: 500 MB (for WNS data, logs, cache)

### Python Version Compatibility

| Python Version | Status | Notes |
|----------------|--------|-------|
| 3.10 | ✅ Supported | Minimum version |
| 3.11 | ✅ Supported | Recommended |
| 3.12 | ✅ Supported | Latest stable |
| 3.13 | ✅ Supported | Experimental features |

### Platform Support

| Platform | Status | Notes |
|----------|--------|-------|
| Linux (x86_64) | ✅ Full Support | Primary platform |
| Linux (ARM64) | ✅ Full Support | Raspberry Pi, etc. |
| macOS (Intel) | ✅ Full Support | macOS 10.15+ |
| macOS (Apple Silicon) | ✅ Full Support | M1/M2/M3 |
| Windows 10/11 | ✅ Full Support | WSL2 recommended |
| FreeBSD | ⚠️ Experimental | Community supported |

### Dependencies

Core dependencies (installed automatically):

- `magic-wormhole >= 0.12.0` - Core wormhole protocol
- `asyncssh >= 2.13.0` - SSH/SCP/SFTP implementation
- `twisted >= 22.0.0` - Async networking
- `click >= 8.0.0` - CLI framework
- `cryptography >= 41.0.0` - Cryptographic primitives

Optional dependencies:

- `python-ldap` - LDAP authentication (enterprise)
- `zeroconf` - mDNS relay discovery
- `fusepy` - Filesystem mounting (`wh mount`)

---

## Configuration Options

### Data Directory

All configuration, identities, and state are stored in `~/.wh/`:

```
~/.wh/
├── config.json         # Global configuration
├── relays.yaml         # Multi-relay configuration
├── aliases.json        # Local alias mappings
├── identity/           # WNS identities (Ed25519 keypairs)
│   └── <address>/
│       ├── private.key
│       └── public.key
├── known_hosts/        # Cached public keys (TOFU)
│   └── <address>.json
├── advertise/          # Published advertisements
│   └── <address>.json
└── names/              # Claimed global names
    └── <name>.json
```

### Global Configuration

Edit `~/.wh/config.json`:

```json
{
  "default_relay": "public",
  "default_identity": "abc123...",
  "code_length": 2,
  "verify_mode": "text",
  "log_level": "INFO"
}
```

### Multi-Relay Configuration

Configure multiple relays in `~/.wh/relays.yaml`:

```yaml
relays:
  public:
    mailbox: wss://relay.magic-wormhole.io/v1
    transit: tcp:transit.magic-wormhole.io:4001
    description: Public relay

  work:
    mailbox: wss://work-relay.example.com/v1
    transit: tcp:work-relay.example.com:4001
    description: Company relay

  home:
    mailbox: ws://192.168.1.10:4000/v1
    transit: tcp:192.168.1.10:4001
    description: Home network relay

default: public
```

Manage relays:

```bash
# List configured relays
wh relay list

# Add a relay
wh relay add myrelay ws://relay.example.com/v1 tcp:relay.example.com:4001

# Set default
wh relay set-default myrelay

# Use specific relay
wh --relay work nc -l
```

### Code Length Configuration

Longer codes provide more security against brute-force guessing:

```bash
# Default: 2 words (~23 bits entropy)
wh nc -l
# Output: 7-guitar-sunset

# 4 words (~39 bits entropy)
wh -c 4 nc -l
# Output: 7-guitar-sunset-castle-thunder

# Set default in config.json
echo '{"code_length": 4}' > ~/.wh/config.json
```

| Code Length | Entropy | Attack Resistance |
|-------------|---------|-------------------|
| 2 words | 23 bits | Casual attacker |
| 3 words | 31 bits | Determined attacker |
| 4 words | 39 bits | High security |
| 6 words | 55 bits | Maximum security |

---

## Environment Variables

### Core Variables

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `WH_RELAY` | Mailbox relay URL or name | `public` | `wss://relay.example.com/v1` |
| `WH_TRANSIT` | Transit relay endpoint | Auto-detected | `tcp:transit.example.com:4001` |
| `WH_CODE_LENGTH` | Number of words in codes | `2` | `4` |
| `WH_DATA_DIR` | Data directory path | `~/.wh` | `/var/lib/wh` |
| `WH_LOG_LEVEL` | Logging verbosity | `INFO` | `DEBUG` |

### WNS Variables

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `WH_DEFAULT_IDENTITY` | Default WNS identity address | None | `abc123...` |
| `WH_NAMESPACE` | Namespace for multi-tenancy | `default` | `engineering` |
| `WH_DHT_BOOTSTRAP_NODES` | Custom DHT bootstrap nodes | Public BitTorrent DHT | `router.example.com:6881` |
| `WH_DHT_USE_PUBLIC_BOOTSTRAP` | Use public BitTorrent DHT | `true` | `false` |

### SSH Variables

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `WH_SSH_PASSWORD` | SSH password (avoid prompts) | None | `secretpassword` |
| `WH_SSH_PORT` | Local SSH server port | `22` | `2222` |
| `WH_SSH_KNOWN_HOSTS` | Custom known_hosts file | `~/.wh/known_hosts/` | `/etc/wh/known_hosts` |

### Enterprise Variables

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `WH_AUTH_METHOD` | Authentication method | `none` | `ldap` |
| `WH_LDAP_SERVER` | LDAP server URL | None | `ldap://ad.company.com` |
| `WH_LDAP_BASE_DN` | LDAP base DN | None | `dc=company,dc=com` |
| `WH_AUDIT_LOG` | Audit log file path | None | `/var/log/wh/audit.log` |
| `WH_POLICY_FILE` | Rate limiting policy file | None | `/etc/wh/policy.yml` |

### Daemon Variables

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `WH_DAEMON_PORT` | HTTP API port | `9475` | `8080` |
| `WH_DAEMON_HOST` | Bind address | `127.0.0.1` | `0.0.0.0` |
| `WH_DAEMON_CORS` | Enable CORS | `false` | `true` |

### Example Configuration

```bash
# ~/.bashrc or ~/.zshrc

# Use custom relay
export WH_RELAY=wss://company-relay.example.com/v1
export WH_TRANSIT=tcp:company-relay.example.com:4001

# Longer codes for security
export WH_CODE_LENGTH=4

# Custom data directory
export WH_DATA_DIR=/var/lib/wormhole

# Enable debug logging
export WH_LOG_LEVEL=DEBUG

# Set default identity
export WH_DEFAULT_IDENTITY=abc123def456

# Use namespace
export WH_NAMESPACE=engineering
```

---

## Production Deployment

### Systemd Service (Linux)

Create `/etc/systemd/system/wh-daemon.service`:

```ini
[Unit]
Description=Wormhole Daemon
After=network.target

[Service]
Type=simple
User=wormhole
Group=wormhole
WorkingDirectory=/var/lib/wormhole
Environment="WH_DATA_DIR=/var/lib/wormhole/.wh"
Environment="WH_DAEMON_HOST=0.0.0.0"
ExecStart=/usr/local/bin/wh daemon start
Restart=on-failure
RestartSec=10s

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
# Create user
sudo useradd -r -s /bin/false wormhole
sudo mkdir -p /var/lib/wormhole/.wh
sudo chown -R wormhole:wormhole /var/lib/wormhole

# Enable service
sudo systemctl enable wh-daemon
sudo systemctl start wh-daemon

# Check status
sudo systemctl status wh-daemon

# View logs
sudo journalctl -u wh-daemon -f
```

### Relay Server Deployment

Deploy a self-hosted relay for your organization:

```bash
# Create systemd service for relay
cat > /etc/systemd/system/wh-relay.service <<EOF
[Unit]
Description=Wormhole Relay Server
After=network.target

[Service]
Type=simple
User=wormhole
ExecStart=/usr/local/bin/wh relay serve -p 4000 -t 4001
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

# Enable and start
sudo systemctl enable wh-relay
sudo systemctl start wh-relay
```

### Nginx Reverse Proxy

Proxy the daemon through Nginx with TLS:

```nginx
upstream wh_daemon {
    server 127.0.0.1:9475;
}

server {
    listen 443 ssl http2;
    server_name wh.example.com;

    ssl_certificate /etc/letsencrypt/live/wh.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/wh.example.com/privkey.pem;

    location / {
        proxy_pass http://wh_daemon;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Kubernetes Deployment

Create `wh-deployment.yaml`:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: wh-config
data:
  WH_RELAY: "wss://relay.magic-wormhole.io/v1"
  WH_CODE_LENGTH: "4"
  WH_LOG_LEVEL: "INFO"

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: wh-daemon
  labels:
    app: wh-daemon
spec:
  replicas: 1
  selector:
    matchLabels:
      app: wh-daemon
  template:
    metadata:
      labels:
        app: wh-daemon
    spec:
      containers:
      - name: daemon
        image: ghcr.io/bshuler/critical-wormhole-tools:latest
        args: ["daemon", "start"]
        ports:
        - containerPort: 9475
          name: http
        envFrom:
        - configMapRef:
            name: wh-config
        volumeMounts:
        - name: wh-data
          mountPath: /home/wormhole/.wh
        livenessProbe:
          httpGet:
            path: /status
            port: 9475
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /status
            port: 9475
          initialDelaySeconds: 5
          periodSeconds: 10
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "500m"
      volumes:
      - name: wh-data
        persistentVolumeClaim:
          claimName: wh-data

---
apiVersion: v1
kind: Service
metadata:
  name: wh-daemon
spec:
  selector:
    app: wh-daemon
  ports:
  - port: 9475
    targetPort: 9475
  type: ClusterIP

---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: wh-data
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 1Gi
```

Deploy:

```bash
kubectl apply -f wh-deployment.yaml
kubectl get pods -l app=wh-daemon
kubectl logs -l app=wh-daemon -f
```

### High Availability Setup

Run multiple daemon instances behind a load balancer:

```yaml
# docker-compose.yml for HA
version: '3.8'

services:
  daemon1:
    image: ghcr.io/bshuler/critical-wormhole-tools:latest
    command: daemon start
    environment:
      WH_DAEMON_HOST: 0.0.0.0
    volumes:
      - wh-data1:/home/wormhole/.wh
    networks:
      - wh-net

  daemon2:
    image: ghcr.io/bshuler/critical-wormhole-tools:latest
    command: daemon start
    environment:
      WH_DAEMON_HOST: 0.0.0.0
    volumes:
      - wh-data2:/home/wormhole/.wh
    networks:
      - wh-net

  haproxy:
    image: haproxy:latest
    ports:
      - "9475:9475"
    volumes:
      - ./haproxy.cfg:/usr/local/etc/haproxy/haproxy.cfg:ro
    networks:
      - wh-net
    depends_on:
      - daemon1
      - daemon2

volumes:
  wh-data1:
  wh-data2:

networks:
  wh-net:
```

---

## Troubleshooting

### Installation Issues

**Problem**: `pip install` fails with dependency errors

```bash
# Solution 1: Upgrade pip
pip install --upgrade pip setuptools wheel

# Solution 2: Install build dependencies (Debian/Ubuntu)
sudo apt-get install python3-dev build-essential libffi-dev libssl-dev

# Solution 3: Install build dependencies (macOS)
xcode-select --install

# Solution 4: Install build dependencies (Windows)
# Install Microsoft C++ Build Tools from visualstudio.microsoft.com
```

**Problem**: Command not found after installation

```bash
# Solution: Check PATH
which wh

# If not found, add pip bin directory to PATH
export PATH="$HOME/.local/bin:$PATH"  # Linux/macOS
# or
export PATH="$PATH:$(python -m site --user-base)/bin"
```

### Connection Issues

**Problem**: Wormhole connection times out

```bash
# Check relay connectivity
curl -I https://relay.magic-wormhole.io/v1/welcome

# Test with verbose logging
WH_LOG_LEVEL=DEBUG wh nc -l

# Try custom relay
wh --relay wss://relay.magic-wormhole.io/v1 nc -l
```

**Problem**: Firewall blocking connections

```bash
# Required ports for default public relay:
# - TCP 443 (HTTPS) for mailbox WebSocket
# - TCP/UDP 4001 for transit relay

# Check firewall rules
sudo iptables -L -n | grep -E '443|4001'  # Linux
sudo pfctl -sr | grep -E '443|4001'        # macOS
netsh advfirewall firewall show rule name=all | findstr "4001"  # Windows

# Allow required ports (example for Linux)
sudo iptables -A OUTPUT -p tcp --dport 443 -j ACCEPT
sudo iptables -A OUTPUT -p tcp --dport 4001 -j ACCEPT
```

### Permission Issues

**Problem**: Permission denied accessing `~/.wh/`

```bash
# Fix ownership
chmod 700 ~/.wh
chmod 600 ~/.wh/identity/*/private.key
```

**Problem**: Docker container permission errors

```bash
# Fix volume permissions
chown -R 1000:1000 /path/to/wh-data

# Or run as root (not recommended)
docker run --user root ...
```

### Performance Issues

**Problem**: Slow file transfers

```bash
# Enable compression
wh scp -C remote:/large/file ./

# Use multiple connections for rsync
wh rsync --parallel=4 ./dir/ remote:/dest/

# Monitor bandwidth
WH_LOG_LEVEL=DEBUG wh scp remote:/file ./
```

**Problem**: High memory usage

```bash
# Limit concurrent connections (daemon)
wh daemon start --max-connections=10

# Reduce DHT cache size
wh daemon start --dht-cache-size=100
```

### Diagnostic Commands

```bash
# Check installation
wh --version
wh --help

# Test basic functionality
wh nc -l &
PID=$!
echo "test" | wh nc $(wh nc -l)
kill $PID

# Check configuration
cat ~/.wh/config.json
wh relay list
wh identity list

# View logs
# macOS/Linux
tail -f ~/.wh/logs/wh.log

# Windows
type %USERPROFILE%\.wh\logs\wh.log

# System logs (if running as service)
sudo journalctl -u wh-daemon -f  # systemd
sudo tail -f /var/log/wh-daemon.log  # syslog
```

### Getting Help

- **Documentation**: https://github.com/bshuler/critical-wormhole-tools
- **Issues**: https://github.com/bshuler/critical-wormhole-tools/issues
- **Discussions**: https://github.com/bshuler/critical-wormhole-tools/discussions
- **Email**: support@critical-wormhole-tools.example.com

---

## Security Best Practices

### 1. Use Longer Codes in Production

```bash
export WH_CODE_LENGTH=4  # Minimum for production
```

### 2. Run Self-Hosted Relay

```bash
# Don't rely on public relay for sensitive data
wh relay serve -p 4000 -t 4001
```

### 3. Enable Authentication

```bash
wh listen --ssh --auth-method=pubkey --authorized-keys=~/.ssh/authorized_keys
```

### 4. Enable Audit Logging

```bash
wh listen --ssh --audit-log=/var/log/wh/audit.log
```

### 5. Use TOFU Verification

```bash
# On first connection, verify the fingerprint out-of-band
wh ssh wh://newserver.wns
# WARNING: Unknown host. Fingerprint: abc123...
# Verify this matches the server's published fingerprint
```

### 6. Rotate WNS Identities

```bash
# Create new identity periodically
wh identity create --name "server-2026"
wh serve --ssh --identity <new-address>

# Announce transition to clients
# Update aliases after migration
```

### 7. Secure Configuration Files

```bash
chmod 700 ~/.wh
chmod 600 ~/.wh/config.json
chmod 600 ~/.wh/identity/*/private.key
```

### 8. Use Environment Variables for Secrets

```bash
# Don't hardcode passwords in scripts
export WH_SSH_PASSWORD=$(pass show wh/ssh-password)
wh ssh admin@server
```

---

## Next Steps

1. **Basic Usage**: See [README.md](../README.md) for command examples
2. **Docker**: See [docker.md](docker.md) for containerized deployment
3. **Enterprise**: See [docs/enterprise/](enterprise/) for advanced features
4. **Web Servers**: See [integrations/](../integrations/) for Caddy, Nginx, Apache, etc.
5. **Browser Extension**: See [browser-extension/README.md](../browser-extension/README.md)
