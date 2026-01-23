# Traefik Native Wormhole Plugin

Native Traefik middleware plugin for integrating Wormhole Name System (WNS) directly into Traefik.

## Overview

This plugin allows Traefik to natively resolve and route `wh://` URLs without requiring external tools or sidecars. It communicates with the `wh` daemon API to resolve WNS names and establish peer connections.

## Features

- Native `wh://` URL resolution
- Automatic peer discovery via DHT
- Identity-based authentication
- Dynamic routing based on WNS names
- Connection pooling and caching
- Works with both static and dynamic configuration

## Architecture

```
Client Request (wh://example.tld)
         ↓
    Traefik Router
         ↓
    Wormhole Middleware
         ↓
    wh Daemon API (HTTP)
         ↓
    DHT Resolution
         ↓
    Peer Connection
         ↓
    Proxy Response
```

## Installation

### Using Traefik Pilot (Recommended)

```yaml
# traefik.yml
experimental:
  plugins:
    wormhole:
      moduleName: github.com/yourusername/traefik-wormhole-plugin
      version: v0.1.0
```

### Local Development

```bash
# Clone to Traefik plugins directory
git clone https://github.com/yourusername/traefik-wormhole-plugin.git \
  ~/.local/share/traefik/plugins-local/src/github.com/yourusername/traefik-wormhole-plugin

# Reference in traefik.yml
experimental:
  localPlugins:
    wormhole:
      moduleName: github.com/yourusername/traefik-wormhole-plugin
```

## Configuration

### Static Configuration

```yaml
# traefik.yml
experimental:
  plugins:
    wormhole:
      moduleName: github.com/yourusername/traefik-wormhole-plugin
      version: v0.1.0

# Optional: Configure daemon endpoint globally
providers:
  plugin:
    wormhole:
      daemonURL: http://localhost:8080
      identity: default
      timeout: 30s
```

### Dynamic Configuration (File Provider)

```yaml
# dynamic.yml
http:
  middlewares:
    wormhole-resolver:
      plugin:
        wormhole:
          daemonURL: http://localhost:8080
          identity: default
          relayURL: wss://relay.magic-wormhole.io:4000
          timeout: 30s
          connectTimeout: 10s
          cacheEnabled: true
          cacheTTL: 5m

  routers:
    wormhole-router:
      rule: "HostRegexp(`{subdomain:[a-z0-9-]+}.tld`)"
      service: wormhole-service
      middlewares:
        - wormhole-resolver

  services:
    wormhole-service:
      loadBalancer:
        servers:
          - url: http://localhost:9999  # Placeholder, overridden by middleware
```

### Dynamic Configuration (Docker Labels)

```yaml
# docker-compose.yml
services:
  myapp:
    image: myapp:latest
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.myapp.rule=Host(`wh://myapp.tld`)"
      - "traefik.http.routers.myapp.middlewares=wormhole-resolver"
      - "traefik.http.middlewares.wormhole-resolver.plugin.wormhole.identity=myapp"
```

## Plugin Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `daemonURL` | string | `http://localhost:8080` | URL of wh daemon API |
| `identity` | string | `default` | Identity to use for connections |
| `relayURL` | string | (daemon default) | Override relay server URL |
| `timeout` | duration | `30s` | Request timeout |
| `connectTimeout` | duration | `10s` | Connection establishment timeout |
| `cacheEnabled` | bool | `true` | Enable DHT resolution caching |
| `cacheTTL` | duration | `5m` | Cache time-to-live |
| `maxConnections` | int | `100` | Max concurrent peer connections |
| `debug` | bool | `false` | Enable debug logging |

## Usage Examples

### Basic WNS Routing

```yaml
http:
  middlewares:
    wormhole:
      plugin:
        wormhole: {}

  routers:
    wns-gateway:
      rule: "HostRegexp(`^wh://.+$`)"
      service: dummy
      middlewares:
        - wormhole

  services:
    dummy:
      loadBalancer:
        servers:
          - url: http://localhost:1  # Overridden by middleware
```

### Multi-Identity Setup

```yaml
http:
  middlewares:
    wormhole-alice:
      plugin:
        wormhole:
          identity: alice

    wormhole-bob:
      plugin:
        wormhole:
          identity: bob

  routers:
    alice-router:
      rule: "Host(`alice.example.com`)"
      middlewares:
        - wormhole-alice

    bob-router:
      rule: "Host(`bob.example.com`)"
      middlewares:
        - wormhole-bob
```

### With TLS Termination

```yaml
http:
  routers:
    wormhole-secure:
      rule: "HostRegexp(`{name:[a-z0-9-]+}.tld`)"
      entryPoints:
        - websecure
      tls:
        certResolver: letsencrypt
      middlewares:
        - wormhole-resolver
```

## Implementation Details

### Middleware Flow

1. Client request arrives at Traefik
2. Wormhole middleware intercepts request
3. Host header parsed for WNS name
4. Daemon API called for DHT resolution
5. Peer connection established (or reused from pool)
6. Request forwarded to peer
7. Response streamed back to client

### Connection Pooling

The plugin maintains a connection pool for frequently accessed peers:

- Connections are keyed by WNS name
- Idle connections are kept alive for `cacheTTL`
- Pool size limited by `maxConnections`
- Automatic cleanup of stale connections

### Error Handling

- Resolution failures return 502 Bad Gateway
- Connection timeouts return 504 Gateway Timeout
- Daemon unavailable returns 503 Service Unavailable
- All errors logged with request context

## Development

### Prerequisites

- Go 1.21+
- Traefik 2.10+
- wh daemon running

### Building

```bash
go mod tidy
go build -o traefik-wormhole-plugin
```

### Testing

```bash
# Unit tests
go test ./...

# Integration tests (requires wh daemon)
go test -tags=integration ./...
```

### Local Testing with Traefik

```bash
# Start wh daemon
wh daemon start

# Start Traefik with plugin
traefik --configFile=traefik.yml

# Test resolution
curl -H "Host: wh://example.tld" http://localhost/
```

## Monitoring

### Metrics

The plugin exposes the following Prometheus metrics:

- `wormhole_requests_total` - Total requests processed
- `wormhole_resolutions_total` - DHT resolutions attempted
- `wormhole_resolution_duration_seconds` - Resolution time
- `wormhole_connections_active` - Active peer connections
- `wormhole_cache_hits_total` - Cache hit count
- `wormhole_cache_misses_total` - Cache miss count
- `wormhole_errors_total` - Errors by type

### Health Checks

```bash
# Check plugin status
curl http://localhost:8080/api/http/middlewares/wormhole@file

# Check daemon connectivity
curl http://localhost:8080/health
```

## Troubleshooting

### Plugin not loading

Check Traefik logs:
```bash
traefik --log.level=DEBUG
```

Verify plugin installation:
```bash
ls ~/.local/share/traefik/plugins-local/src/
```

### Resolution failures

Enable debug mode:
```yaml
plugin:
  wormhole:
    debug: true
```

Check daemon status:
```bash
wh daemon status
wh daemon logs
```

### Performance issues

Adjust connection pool:
```yaml
plugin:
  wormhole:
    maxConnections: 200
    cacheTTL: 10m
```

## Security Considerations

- Plugin validates all daemon API responses
- Peer connections use identity-based authentication
- No private keys stored in Traefik config
- Relay connections use TLS
- DHT responses are cryptographically verified
- Request headers sanitized before forwarding

## Future Enhancements

- [ ] HTTP/2 and gRPC support
- [ ] WebSocket proxying
- [ ] Circuit breaker integration
- [ ] Distributed tracing (OpenTelemetry)
- [ ] Rate limiting per WNS name
- [ ] Custom error pages
- [ ] Automatic failover to backup peers

## Contributing

Contributions welcome! Please see CONTRIBUTING.md.

## License

MIT
