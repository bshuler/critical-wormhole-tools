# Nginx Native Wormhole Module

Native Nginx module for integrating Wormhole Name System (WNS) directly into Nginx.

## Overview

This module allows Nginx to natively resolve and proxy `wh://` URLs without requiring external tools or reverse proxies. It communicates with the `wh` daemon API to resolve WNS names and establish peer connections.

## Features

- Native `wh://` URL resolution
- Automatic peer discovery via DHT
- Identity-based authentication
- Connection pooling and caching
- Minimal configuration required

## Architecture

```
Client Request (wh://example.tld)
         ↓
    Nginx Module
         ↓
    wh Daemon API (HTTP)
         ↓
    DHT Resolution
         ↓
    Peer Connection
         ↓
    Proxy Response
```

## Building

### Docker Build (Recommended)

```bash
docker build -t nginx-wormhole .
docker run -d -p 80:80 nginx-wormhole
```

### Manual Build with nginx source

```bash
# Download nginx source (version must match your installation)
wget http://nginx.org/download/nginx-1.25.5.tar.gz
tar -xzf nginx-1.25.5.tar.gz
cd nginx-1.25.5

# Configure with the wormhole module
./configure \
    --add-dynamic-module=/path/to/nginx-native \
    --with-compat

# Build the module
make modules

# Copy the module to nginx modules directory
cp objs/ngx_http_wormhole_module.so /etc/nginx/modules/
```

### Compile Statically

```bash
# Configure Nginx with static module
./configure --add-module=/path/to/nginx-native

# Build and install
make
sudo make install
```

## Configuration

### Load Module (Dynamic)

```nginx
load_module modules/ngx_http_wormhole_module.so;
```

### Basic Usage

```nginx
http {
    server {
        listen 80;
        server_name localhost;

        location / {
            wormhole_enable on;
            wormhole_daemon http://localhost:8080;
        }
    }
}
```

### Advanced Configuration

```nginx
http {
    # Global wormhole settings
    wormhole_daemon http://localhost:8080;
    wormhole_timeout 30s;
    wormhole_connect_timeout 10s;
    wormhole_cache_size 100m;
    wormhole_cache_time 5m;

    server {
        listen 443 ssl;
        server_name wormhole-gateway.example.com;

        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;

        location / {
            wormhole_enable on;

            # Use specific identity
            wormhole_identity "default";

            # Custom relay server
            wormhole_relay wss://relay.example.com:4000;

            # Pass through headers
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        }
    }
}
```

## Directives

### wormhole_enable

- **Syntax:** `wormhole_enable on | off;`
- **Default:** `off`
- **Context:** `http`, `server`, `location`

Enable wormhole resolution for this context.

### wormhole_daemon

- **Syntax:** `wormhole_daemon <url>;`
- **Default:** `http://localhost:8080`
- **Context:** `http`, `server`, `location`

URL of the `wh` daemon API.

### wormhole_identity

- **Syntax:** `wormhole_identity <name>;`
- **Default:** `default`
- **Context:** `http`, `server`, `location`

Identity to use for outgoing connections.

### wormhole_relay

- **Syntax:** `wormhole_relay <url>;`
- **Default:** (uses daemon default)
- **Context:** `http`, `server`, `location`

Override default relay server.

### wormhole_timeout

- **Syntax:** `wormhole_timeout <time>;`
- **Default:** `30s`
- **Context:** `http`, `server`, `location`

Timeout for wormhole connections.

### wormhole_connect_timeout

- **Syntax:** `wormhole_connect_timeout <time>;`
- **Default:** `10s`
- **Context:** `http`, `server`, `location`

Timeout for establishing peer connections.

### wormhole_cache_size

- **Syntax:** `wormhole_cache_size <size>;`
- **Default:** `100m`
- **Context:** `http`

Size of the DHT resolution cache.

### wormhole_cache_time

- **Syntax:** `wormhole_cache_time <time>;`
- **Default:** `5m`
- **Context:** `http`, `server`, `location`

How long to cache DHT resolutions.

## Implementation Details

### Module Structure

```c
ngx_http_wormhole_module.c
├── Configuration directives
├── Module context and handlers
├── Daemon API client
├── Connection pool
└── Response proxy logic
```

### Request Flow

1. Client requests `wh://example.tld/path`
2. Nginx intercepts request in wormhole handler
3. Module queries wh daemon API for DHT resolution
4. Daemon returns peer connection details
5. Module establishes connection to peer
6. Response is proxied back to client
7. Connection optionally cached for reuse

### Performance Optimizations

- Connection pooling for frequently accessed peers
- DHT resolution caching (configurable TTL)
- Asynchronous I/O for daemon API calls
- Lazy connection establishment

## Testing

### Docker Testing (Recommended)

Run tests on a system with Docker (e.g., hp1 or hp2):

```bash
# Run all tests
./test/docker-test.sh

# Force rebuild
./test/docker-test.sh --no-cache
```

### Manual Testing

```bash
# Start wh daemon
wh daemon start

# Start Nginx with module
sudo nginx -c /path/to/nginx.conf

# Test wormhole resolution
curl -H "Host: wh://example.tld" http://localhost/

# Verify module loads
nginx -t

# Check configuration
nginx -T | grep wormhole
```

## CI/CD

GitHub Actions workflow automatically builds and tests the module on every push to `integrations/nginx-native/`.

See `.github/workflows/nginx-module.yml` for details.

## Troubleshooting

### Module not loading

Check Nginx error log:
```bash
sudo tail -f /var/log/nginx/error.log
```

Verify module compilation:
```bash
nginx -V 2>&1 | grep wormhole
```

### Daemon connection errors

Verify daemon is running:
```bash
wh daemon status
```

Test daemon API:
```bash
curl http://localhost:8080/health
```

### Resolution failures

Enable debug logging:
```nginx
error_log /var/log/nginx/error.log debug;
```

Check daemon logs:
```bash
wh daemon logs
```

## Security Considerations

- Module validates all daemon API responses
- Connection establishment uses identity-based auth
- No private keys stored in Nginx config
- Relay connections use TLS
- DHT responses are verified

## Future Enhancements

- [ ] HTTP/2 support for peer connections
- [ ] WebSocket proxying
- [ ] Custom error pages for resolution failures
- [ ] Metrics and monitoring integration
- [ ] Load balancing across multiple peers
- [ ] Circuit breaker for failing peers

## License

MIT
