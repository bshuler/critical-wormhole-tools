# Squid Wormhole Integration

Configure Squid proxy to handle wormhole URLs.

## Overview

Squid can be configured to:
- Intercept `wh://` URL requests
- Forward them to the wormhole daemon
- Cache wormhole content for improved performance

## Basic Configuration

### squid.conf

```squid
# /etc/squid/squid.conf

# Standard Squid configuration
http_port 3128

# Define wormhole daemon as parent proxy
cache_peer 127.0.0.1 parent 9475 0 no-query originserver name=wormhole

# ACL for wormhole URLs (custom URL rewrite needed)
acl wormhole_sites dstdom_regex \.wns$

# Route wormhole requests to daemon
cache_peer_access wormhole allow wormhole_sites
cache_peer_access wormhole deny all

# Allow wormhole sites
http_access allow wormhole_sites

# Standard access rules
acl localnet src 10.0.0.0/8
acl localnet src 172.16.0.0/12
acl localnet src 192.168.0.0/16

http_access allow localnet
http_access deny all
```

## URL Rewrite Program

Squid doesn't natively understand `wh://` URLs, so we need a URL rewriter:

### wh-rewriter.py

```python
#!/usr/bin/env python3
"""
Squid URL rewriter for wormhole URLs.

Converts wh://address.wns/path to http://localhost:9475/browse/wh://address.wns/path
"""

import sys

DAEMON_URL = "http://127.0.0.1:9475"

def main():
    # Squid sends URLs in format: URL client_ip/- ident method
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        parts = line.split()
        url = parts[0] if parts else ""

        # Check if it's a wormhole URL
        if url.startswith("wh://"):
            # Rewrite to daemon browse endpoint
            new_url = f"{DAEMON_URL}/browse/{url}"
            print(new_url)
        else:
            # Pass through unchanged
            print(url)

        sys.stdout.flush()

if __name__ == "__main__":
    main()
```

### squid.conf with URL rewriter

```squid
# URL rewriter for wh:// URLs
url_rewrite_program /usr/local/bin/wh-rewriter.py
url_rewrite_children 5 startup=1 idle=1 concurrency=50

# Only rewrite wormhole URLs
acl wormhole_url url_regex ^wh://
url_rewrite_access allow wormhole_url
url_rewrite_access deny all
```

## Caching Configuration

Cache wormhole content for better performance:

```squid
# Cache settings
cache_dir ufs /var/spool/squid 1000 16 256

# Cache wormhole responses
refresh_pattern -i \.wns/  1440 20% 10080 reload-into-ims

# Memory cache
cache_mem 256 MB
maximum_object_size_in_memory 512 KB

# Disk cache
maximum_object_size 100 MB
minimum_object_size 0 KB
```

## SSL/HTTPS Interception

For HTTPS wormhole URLs (if needed):

```squid
# SSL bump configuration
http_port 3128 ssl-bump \
  cert=/etc/squid/ssl/squid.pem \
  key=/etc/squid/ssl/squid.key \
  generate-host-certificates=on

# SSL bump ACLs
acl step1 at_step SslBump1
ssl_bump peek step1
ssl_bump bump all

# SSL certificate directory
sslcrtd_program /usr/lib/squid/security_file_certgen -s /var/lib/squid/ssl_db -M 4MB
```

## Transparent Proxy Setup

Intercept wormhole traffic without client configuration:

```squid
# Transparent proxy port
http_port 3129 intercept

# Redirect rules (iptables)
# iptables -t nat -A PREROUTING -p tcp --dport 80 -j REDIRECT --to-port 3129
```

## Access Control

```squid
# Time-based access
acl business_hours time MTWHF 09:00-17:00
http_access allow wormhole_sites business_hours

# Bandwidth limits
delay_pools 1
delay_class 1 2
delay_access 1 allow wormhole_sites
delay_parameters 1 64000/64000 8000/8000  # 64KB/s class, 8KB/s individual
```

## Authentication

```squid
# Basic authentication
auth_param basic program /usr/lib/squid/basic_ncsa_auth /etc/squid/passwd
auth_param basic realm Wormhole Proxy

acl authenticated proxy_auth REQUIRED
http_access allow wormhole_sites authenticated
```

## Logging

```squid
# Access log format
logformat wormhole %ts.%03tu %>a %Ss/%03>Hs %<st %rm %ru %un %Sh/%<a %mt

# Log wormhole requests separately
access_log /var/log/squid/wormhole.log wormhole wormhole_sites
```

## Systemd Service

```ini
# /etc/systemd/system/squid-wormhole.service
[Unit]
Description=Squid Wormhole Proxy
After=network.target wh-daemon.service

[Service]
Type=forking
ExecStart=/usr/sbin/squid -f /etc/squid/squid.conf
ExecReload=/bin/kill -HUP $MAINPID
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

## Client Configuration

### Environment Variables

```bash
export http_proxy=http://localhost:3128
export https_proxy=http://localhost:3128
export wh_proxy=http://localhost:3128

# Test
curl -x http://localhost:3128 wh://mysite.wns/
```

### Browser Configuration

Configure browser to use `localhost:3128` as HTTP/HTTPS proxy.

### PAC File

```javascript
// proxy.pac
function FindProxyForURL(url, host) {
    if (url.startsWith("wh://") || host.endsWith(".wns")) {
        return "PROXY localhost:3128";
    }
    return "DIRECT";
}
```

## Docker Setup

```dockerfile
# Dockerfile
FROM ubuntu:22.04

RUN apt-get update && apt-get install -y squid python3

COPY squid.conf /etc/squid/squid.conf
COPY wh-rewriter.py /usr/local/bin/

EXPOSE 3128

CMD ["squid", "-N", "-f", "/etc/squid/squid.conf"]
```

```yaml
# docker-compose.yml
version: '3'
services:
  squid:
    build: .
    ports:
      - "3128:3128"
    depends_on:
      - wormhole-daemon

  wormhole-daemon:
    image: wormhole-tools:latest
    command: daemon start
```

## Troubleshooting

### Debug Mode

```squid
debug_options ALL,1 33,2 28,9
```

### Cache Status

```bash
squidclient mgr:info
squidclient mgr:objects
```

### Test URL Rewriter

```bash
echo "wh://test.wns/ 192.168.1.1/- - GET" | /usr/local/bin/wh-rewriter.py
```

### Clear Cache

```bash
squid -k shutdown
rm -rf /var/spool/squid/*
squid -z
squid
```

## See Also

- [Main Integration Guide](../README.md)
- [Browser Extension](../../browser-extension/README.md)
- [PAC File Documentation](../../docs/pac-file.md)
