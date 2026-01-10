# HAProxy Wormhole Integration

Load balance and proxy wormhole connections using HAProxy.

## Overview

HAProxy can be used to:
- Load balance multiple wormhole daemon instances
- Route requests to wormhole daemon based on path/headers
- Provide high availability for wormhole services

## Configuration

### Basic Setup

```haproxy
# /etc/haproxy/haproxy.cfg

global
    log /dev/log local0
    chroot /var/lib/haproxy
    stats socket /run/haproxy/admin.sock mode 660 level admin
    stats timeout 30s
    user haproxy
    group haproxy
    daemon

defaults
    log     global
    mode    http
    option  httplog
    option  dontlognull
    timeout connect 5000
    timeout client  50000
    timeout server  50000

# Frontend for incoming requests
frontend http_front
    bind *:80

    # ACL for wormhole requests
    acl is_wormhole path_beg /wh/
    acl is_wormhole_ws hdr(Upgrade) -i WebSocket path_beg /wh/ws/

    # Route wormhole requests to backend
    use_backend wormhole_backend if is_wormhole
    use_backend wormhole_ws_backend if is_wormhole_ws

    # Default backend for other requests
    default_backend web_backend

# Wormhole daemon backend
backend wormhole_backend
    mode http
    balance roundrobin
    option httpchk GET /status

    server wh1 127.0.0.1:9475 check
    server wh2 127.0.0.1:9476 check backup

# WebSocket backend for wormhole
backend wormhole_ws_backend
    mode http
    balance source
    option http-server-close

    server wh1 127.0.0.1:9475 check
    server wh2 127.0.0.1:9476 check backup

# Regular web backend
backend web_backend
    mode http
    balance roundrobin

    server web1 127.0.0.1:8080 check
```

### URL Rewriting

Strip `/wh/` prefix when proxying:

```haproxy
backend wormhole_backend
    mode http

    # Strip /wh/ prefix
    http-request set-path %[path,regsub(^/wh/,/)]

    server wh1 127.0.0.1:9475 check
```

### Health Checks

```haproxy
backend wormhole_backend
    mode http

    # Custom health check endpoint
    option httpchk GET /status
    http-check expect status 200

    server wh1 127.0.0.1:9475 check inter 5000 fall 3 rise 2
```

## High Availability Setup

### Active-Passive

```haproxy
backend wormhole_backend
    mode http

    # Primary server
    server wh_primary 127.0.0.1:9475 check

    # Backup server (only used if primary fails)
    server wh_backup 127.0.0.1:9476 check backup
```

### Active-Active with Session Persistence

```haproxy
backend wormhole_backend
    mode http
    balance source  # Same client always goes to same server
    hash-type consistent

    server wh1 127.0.0.1:9475 check weight 100
    server wh2 127.0.0.1:9476 check weight 100
```

## SSL/TLS Termination

```haproxy
frontend https_front
    bind *:443 ssl crt /etc/ssl/private/combined.pem

    acl is_wormhole path_beg /wh/
    use_backend wormhole_backend if is_wormhole
    default_backend web_backend

backend wormhole_backend
    mode http
    server wh1 127.0.0.1:9475 check
```

## Statistics Dashboard

```haproxy
# Enable stats page
listen stats
    bind *:8404
    stats enable
    stats uri /stats
    stats refresh 10s
    stats admin if LOCALHOST
```

Access at `http://localhost:8404/stats`

## Rate Limiting

```haproxy
frontend http_front
    bind *:80

    # Rate limit wormhole connections
    stick-table type ip size 100k expire 30s store http_req_rate(10s)
    http-request track-sc0 src
    http-request deny deny_status 429 if { sc_http_req_rate(0) gt 100 }

    acl is_wormhole path_beg /wh/
    use_backend wormhole_backend if is_wormhole
```

## Docker Compose Example

```yaml
version: '3'
services:
  haproxy:
    image: haproxy:latest
    ports:
      - "80:80"
      - "8404:8404"
    volumes:
      - ./haproxy.cfg:/usr/local/etc/haproxy/haproxy.cfg:ro
    depends_on:
      - wh-daemon-1
      - wh-daemon-2

  wh-daemon-1:
    image: wormhole-tools:latest
    command: daemon start --port 9475
    expose:
      - "9475"

  wh-daemon-2:
    image: wormhole-tools:latest
    command: daemon start --port 9475
    expose:
      - "9475"
```

## Troubleshooting

### Connection Timeouts

Increase timeouts for long-lived wormhole connections:

```haproxy
defaults
    timeout connect 10s
    timeout client  3600s   # 1 hour
    timeout server  3600s
    timeout tunnel  3600s   # For WebSocket tunnels
```

### Backend Health

Check backend status:

```bash
echo "show stat" | socat /run/haproxy/admin.sock stdio
```

### Debug Logging

```haproxy
global
    log /dev/log local0 debug

defaults
    log global
    option httplog
```

## See Also

- [Main Integration Guide](../README.md)
- [Nginx Integration](../nginx/README.md)
- [Traefik Integration](../traefik/README.md)
