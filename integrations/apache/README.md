# Apache Wormhole Integration

Serve content over wormhole addresses using Apache HTTP Server.

## Methods

### 1. Reverse Proxy (Recommended for now)

Use Apache's mod_proxy to forward wormhole requests to `wh daemon`:

```bash
# Start the wormhole daemon
wh daemon start

# Configure Apache to proxy wormhole requests
```

#### Prerequisites

Enable required modules:

```bash
sudo a2enmod proxy
sudo a2enmod proxy_http
sudo a2enmod proxy_wstunnel
```

#### Configuration

```apache
# /etc/apache2/sites-available/wormhole.conf

<VirtualHost *:80>
    ServerName localhost

    # Enable proxy
    ProxyRequests Off
    ProxyPreserveHost On

    # Proxy wormhole requests to daemon
    ProxyPass /wh/ http://127.0.0.1:9475/
    ProxyPassReverse /wh/ http://127.0.0.1:9475/

    # WebSocket support
    RewriteEngine On
    RewriteCond %{HTTP:Upgrade} =websocket [NC]
    RewriteRule /wh/ws/(.*) ws://127.0.0.1:9475/ws/$1 [P,L]

    # Serve local content
    DocumentRoot /var/www/mysite
    <Directory /var/www/mysite>
        Options Indexes FollowSymLinks
        AllowOverride All
        Require all granted
    </Directory>

    ErrorLog ${APACHE_LOG_DIR}/wormhole_error.log
    CustomLog ${APACHE_LOG_DIR}/wormhole_access.log combined
</VirtualHost>
```

### 2. Native Module (Planned)

A native Apache module (`mod_wormhole`) is planned for future releases.

#### Planned Configuration

```apache
# Future native module configuration
LoadModule wormhole_module modules/mod_wormhole.so

<VirtualHost *:80>
    ServerName mysite.wh

    WormholeEnable On
    WormholeIdentity /etc/apache2/wh-keys/mysite.key
    WormholeName mysite

    DocumentRoot /var/www/mysite
</VirtualHost>
```

## Setup Guide

### Step 1: Install Apache Modules

```bash
# Debian/Ubuntu
sudo apt-get install apache2
sudo a2enmod proxy proxy_http proxy_wstunnel rewrite

# RHEL/CentOS
sudo yum install httpd
```

### Step 2: Start Wormhole Daemon

```bash
wh daemon start
```

### Step 3: Configure Apache

Create `/etc/apache2/sites-available/wormhole.conf`:

```apache
<VirtualHost *:80>
    ServerName localhost

    ProxyRequests Off
    ProxyPreserveHost On

    # Standard HTTP proxy
    ProxyPass /wh/ http://127.0.0.1:9475/
    ProxyPassReverse /wh/ http://127.0.0.1:9475/

    # Timeout for long connections
    ProxyTimeout 300

    DocumentRoot /var/www/html
</VirtualHost>
```

Enable and restart:

```bash
sudo a2ensite wormhole
sudo systemctl restart apache2
```

### Step 4: Test

```bash
curl http://localhost/wh/status
```

## SSL/TLS Configuration

For HTTPS support:

```apache
<VirtualHost *:443>
    ServerName example.com

    SSLEngine on
    SSLCertificateFile /etc/ssl/certs/example.crt
    SSLCertificateKeyFile /etc/ssl/private/example.key

    # Proxy to wormhole daemon
    SSLProxyEngine on
    ProxyPass /wh/ http://127.0.0.1:9475/
    ProxyPassReverse /wh/ http://127.0.0.1:9475/
</VirtualHost>
```

## Virtual Hosts for Wormhole Sites

Create separate virtual hosts for different wormhole-served sites:

```apache
# Site 1
<VirtualHost *:80>
    ServerName site1.example.com
    ProxyPass / http://127.0.0.1:9475/browse/wh://site1.wns/
    ProxyPassReverse / http://127.0.0.1:9475/browse/wh://site1.wns/
</VirtualHost>

# Site 2
<VirtualHost *:80>
    ServerName site2.example.com
    ProxyPass / http://127.0.0.1:9475/browse/wh://site2.wns/
    ProxyPassReverse / http://127.0.0.1:9475/browse/wh://site2.wns/
</VirtualHost>
```

## Troubleshooting

### 503 Service Unavailable

Check if daemon is running:

```bash
wh daemon status
```

### Proxy Errors

Enable verbose logging:

```apache
LogLevel proxy:debug
```

### WebSocket Issues

Ensure mod_proxy_wstunnel is enabled:

```bash
sudo a2enmod proxy_wstunnel
```

## Performance Tuning

```apache
# Increase connection pool
<Proxy http://127.0.0.1:9475/>
    ProxySet keepalive=On
    ProxySet connectiontimeout=5
    ProxySet timeout=300
</Proxy>

# Enable compression
<IfModule mod_deflate.c>
    AddOutputFilterByType DEFLATE text/html text/plain text/xml text/css application/json
</IfModule>
```

## See Also

- [Main Integration Guide](../README.md)
- [Nginx Integration](../nginx/README.md)
- [Wormhole Daemon Documentation](../../docs/daemon.md)
