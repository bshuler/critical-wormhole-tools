# Nginx Wormhole Integration

Serve content over wormhole addresses using Nginx.

## Methods

### 1. Reverse Proxy (Recommended for now)

The simplest approach is to use Nginx as a reverse proxy to `wh daemon`:

```bash
# Start the wormhole daemon
wh daemon start

# Configure Nginx to proxy wormhole requests
```

#### Configuration

```nginx
# /etc/nginx/sites-available/wormhole

upstream wormhole_daemon {
    server 127.0.0.1:9475;
    keepalive 32;
}

server {
    listen 8080;
    server_name localhost;

    # Proxy all /wh/ requests to the wormhole daemon
    location /wh/ {
        proxy_pass http://wormhole_daemon/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeout settings for long-lived connections
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 3600s;
    }

    # Serve local content as a wormhole site
    location / {
        root /var/www/mysite;
        index index.html;
    }
}
```

### 2. Native Module (Planned)

A native Nginx module (`ngx_http_wormhole_module`) is planned for future releases.

#### Planned Features

- Direct wormhole protocol handling
- No separate daemon required
- Native configuration syntax:

```nginx
# Future native module configuration
server {
    listen wormhole;

    wormhole_enable on;
    wormhole_identity /etc/nginx/wh-keys/mysite.key;
    wormhole_name mysite;

    location / {
        root /var/www/mysite;
        index index.html;
    }
}
```

## Reverse Proxy Setup

### Step 1: Start the Wormhole Daemon

```bash
# Start daemon
wh daemon start

# Or with specific options
wh daemon start --port 9475 --verbose
```

### Step 2: Configure Nginx

Create `/etc/nginx/sites-available/wormhole`:

```nginx
server {
    listen 80;
    server_name _;

    location /wh/ {
        proxy_pass http://127.0.0.1:9475/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

Enable the site:

```bash
sudo ln -s /etc/nginx/sites-available/wormhole /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### Step 3: Serve Content

Use `wh serve` or `wh listen` to serve content:

```bash
# Serve files from a directory
wh listen --serve /var/www/mysite

# Or use the daemon's browse endpoint
curl http://localhost:9475/browse/wh://myaddress.wns/
```

## WebSocket Support

For applications requiring WebSocket connections through wormhole:

```nginx
map $http_upgrade $connection_upgrade {
    default upgrade;
    ''      close;
}

server {
    listen 80;

    location /wh/ws/ {
        proxy_pass http://127.0.0.1:9475/ws/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $connection_upgrade;
        proxy_read_timeout 86400s;
    }
}
```

## Load Balancing (Multiple Daemons)

For high availability:

```nginx
upstream wormhole_cluster {
    server 127.0.0.1:9475;
    server 127.0.0.1:9476;
    server 127.0.0.1:9477;

    keepalive 64;
}

server {
    listen 80;

    location /wh/ {
        proxy_pass http://wormhole_cluster/;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
    }
}
```

## Troubleshooting

### Connection Refused

```bash
# Check if daemon is running
wh daemon status

# Start if not running
wh daemon start
```

### WebSocket Errors

Ensure `proxy_http_version 1.1` and proper upgrade headers are set.

### Timeouts

Increase proxy timeouts for long-running connections:

```nginx
proxy_read_timeout 3600s;
proxy_send_timeout 60s;
```

## See Also

- [Main Integration Guide](../README.md)
- [Wormhole Daemon Documentation](../../docs/daemon.md)
- [Browser Extension](../../browser-extension/README.md)
