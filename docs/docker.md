# Docker Deployment Guide

This guide covers running Wormhole Tools in Docker containers.

## Quick Start

### Pull the Image

```bash
docker pull ghcr.io/bshuler/critical-wormhole-tools:latest
```

### Run Commands

```bash
# Run any wh command
docker run --rm ghcr.io/bshuler/critical-wormhole-tools nc -l
docker run --rm ghcr.io/bshuler/critical-wormhole-tools ssh --help

# Interactive mode
docker run -it --rm ghcr.io/bshuler/critical-wormhole-tools sftp 7-guitar-sunset
```

## Docker Compose Services

The included `docker-compose.yml` provides several pre-configured services.

### Daemon (Browser Extension Backend)

```bash
# Start the daemon
docker-compose up -d daemon

# Check logs
docker-compose logs -f daemon

# Access the API
curl http://localhost:9475/status
```

### Self-Hosted Relay

Run your own wormhole relay server:

```bash
# Start relay services
docker-compose --profile relay up -d

# Your relay is now available at:
# - Mailbox: ws://localhost:4000/v1
# - Transit: tcp://localhost:4001
```

Configure clients to use your relay:

```bash
export WH_RELAY=ws://your-server:4000/v1
export WH_TRANSIT=tcp:your-server:4001
wh nc -l
```

### SSH Server

Expose SSH access through wormhole:

```bash
# Start SSH server
docker-compose --profile ssh up -d

# Connect from anywhere
wh ssh <code-from-logs>
```

### File Server

Serve files over wormhole:

```bash
# Set the directory to serve
export FILE_SERVER_PATH=/path/to/files

# Start file server
docker-compose --profile files up -d

# Access from browser extension or wh curl
wh curl wh://<address>.wns/
```

## Building the Image

### Standard Build

```bash
docker build -t wormhole-tools .
```

### Multi-Architecture Build

```bash
# Set up buildx
docker buildx create --name multiarch --use

# Build for multiple architectures
docker buildx build --platform linux/amd64,linux/arm64 \
  -t wormhole-tools:latest --push .
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `WH_RELAY` | `wss://relay.magic-wormhole.io/v1` | Mailbox relay URL |
| `WH_TRANSIT` | `tcp:transit.magic-wormhole.io:4001` | Transit relay URL |
| `WH_RELAY_HOST` | `127.0.0.1` | Host for relay server to bind |

## Volumes

### Persistent Data

```yaml
volumes:
  wh-data:/home/wormhole/.wh  # WNS identities and config
```

### SSH Keys

```yaml
volumes:
  ssh-keys:/home/wormhole/.ssh:ro  # SSH authorized_keys
```

## Networking

### Exposed Ports

| Port | Service | Description |
|------|---------|-------------|
| 9475 | Daemon | HTTP API for browser extension |
| 4000 | Relay | WebSocket mailbox server |
| 4001 | Relay | TCP transit relay |

### Custom Networks

```yaml
networks:
  wormhole:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
```

## Production Deployment

### With Traefik

```yaml
version: '3.8'
services:
  daemon:
    image: ghcr.io/bshuler/critical-wormhole-tools:latest
    command: daemon start
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.wh.rule=Host(`wh.example.com`)"
      - "traefik.http.services.wh.loadbalancer.server.port=9475"
```

### With Nginx

```nginx
upstream wormhole {
    server wh-daemon:9475;
}

server {
    listen 443 ssl;
    server_name wh.example.com;

    location / {
        proxy_pass http://wormhole;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### Health Checks

The image includes a health check:

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wh daemon status || exit 1
```

## Kubernetes Deployment

### Basic Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: wormhole-daemon
spec:
  replicas: 1
  selector:
    matchLabels:
      app: wormhole-daemon
  template:
    metadata:
      labels:
        app: wormhole-daemon
    spec:
      containers:
        - name: daemon
          image: ghcr.io/bshuler/critical-wormhole-tools:latest
          args: ["daemon", "start"]
          ports:
            - containerPort: 9475
          livenessProbe:
            httpGet:
              path: /status
              port: 9475
            initialDelaySeconds: 10
            periodSeconds: 30
---
apiVersion: v1
kind: Service
metadata:
  name: wormhole-daemon
spec:
  selector:
    app: wormhole-daemon
  ports:
    - port: 9475
      targetPort: 9475
```

### With Persistent Volume

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: wormhole-data
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 1Gi
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: wormhole-daemon
spec:
  template:
    spec:
      containers:
        - name: daemon
          volumeMounts:
            - name: data
              mountPath: /home/wormhole/.wh
      volumes:
        - name: data
          persistentVolumeClaim:
            claimName: wormhole-data
```

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker logs wh-daemon

# Run interactively to debug
docker run -it --rm --entrypoint /bin/bash wormhole-tools
```

### Connection Issues

```bash
# Test relay connectivity from container
docker run --rm wormhole-tools nc -l
# If this hangs, check firewall/relay settings
```

### Permission Denied

The container runs as non-root user `wormhole` (UID 1000). Ensure mounted volumes have correct permissions:

```bash
chown -R 1000:1000 /path/to/mounted/volume
```

## Security Considerations

1. **Non-root user**: Container runs as `wormhole` user
2. **Read-only mounts**: Use `:ro` for sensitive data
3. **Network isolation**: Use custom Docker networks
4. **Secret management**: Use Docker secrets for sensitive config

```yaml
secrets:
  wns_identity:
    file: ./identity.key

services:
  daemon:
    secrets:
      - wns_identity
```
