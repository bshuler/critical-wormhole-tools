# Web Server Integrations

This directory contains integration configurations and plugins for popular web servers
to serve content over wormhole addresses natively.

## Overview

There are two ways to integrate wormhole with web servers:

### 1. Reverse Proxy Method (Simple)

Use your existing web server as a reverse proxy to `wh daemon`:

```bash
# Start the wormhole daemon
wh daemon start

# Configure your web server to proxy wh:// URLs to localhost:9475
```

This works with any web server that supports reverse proxying.

### 2. Native Module Method (Advanced)

For tighter integration, native modules/plugins are available for some web servers.
These provide:
- Direct wormhole protocol handling
- No separate daemon required
- Better performance
- Native configuration syntax

## Available Integrations

| Web Server | Type | Status | Description |
|------------|------|--------|-------------|
| [Caddy](./caddy/) | Go Plugin | Scaffold | Native Caddy module with Caddyfile support |
| [Nginx](./nginx/) | Config | Docs | Reverse proxy configuration examples |
| [Apache](./apache/) | Config | Docs | mod_proxy configuration examples |
| [HAProxy](./haproxy/) | Config | Docs | Load balancing configuration examples |
| [Traefik](./traefik/) | Config | Docs | Docker/Kubernetes configuration examples |
| [Squid](./squid/) | Config | Docs | Caching proxy configuration examples |

## Quick Start with Reverse Proxy

### Caddy (Reverse Proxy)

```caddyfile
# Caddyfile
:8080 {
    reverse_proxy /wh/* localhost:9475
}
```

### Nginx (Reverse Proxy)

```nginx
# nginx.conf
location /wh/ {
    proxy_pass http://127.0.0.1:9475/;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
}
```

### Apache (Reverse Proxy)

```apache
# httpd.conf
ProxyPass /wh/ http://127.0.0.1:9475/
ProxyPassReverse /wh/ http://127.0.0.1:9475/
```

### HAProxy (Reverse Proxy)

```haproxy
# haproxy.cfg
frontend http_front
    bind *:8080
    acl is_wormhole path_beg /wh/
    use_backend wormhole_backend if is_wormhole

backend wormhole_backend
    server wh_daemon 127.0.0.1:9475
```

## Requirements

- `wh daemon` must be running (for reverse proxy method)
- Web server with proxy capabilities
- For native modules: appropriate build tools (Go, C compiler, etc.)

## Usage with WNS Addresses

Once configured, your web server can serve content at wormhole addresses:

```bash
# Start your web server with wormhole integration
# Then connect from anywhere:

wh curl wh://mysite.wns/page.html
# Or use the browser extension to navigate to wh://mysite.wns
```
