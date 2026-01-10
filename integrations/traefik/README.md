# Traefik Wormhole Integration

Use Traefik as a reverse proxy and load balancer for wormhole services.

## Overview

Traefik provides:
- Automatic service discovery
- Built-in Let's Encrypt support
- Docker and Kubernetes integration
- Dynamic configuration reload

## Quick Start with Docker

### docker-compose.yml

```yaml
version: '3'

services:
  traefik:
    image: traefik:v2.10
    command:
      - "--api.insecure=true"
      - "--providers.docker=true"
      - "--providers.docker.exposedbydefault=false"
      - "--entrypoints.web.address=:80"
    ports:
      - "80:80"
      - "8080:8080"  # Traefik dashboard
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro

  wormhole-daemon:
    image: wormhole-tools:latest
    command: daemon start --port 9475
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.wormhole.rule=PathPrefix(`/wh/`)"
      - "traefik.http.routers.wormhole.entrypoints=web"
      - "traefik.http.services.wormhole.loadbalancer.server.port=9475"
      - "traefik.http.middlewares.wh-strip.stripprefix.prefixes=/wh"
      - "traefik.http.routers.wormhole.middlewares=wh-strip"
```

## Static Configuration

### traefik.yml

```yaml
# /etc/traefik/traefik.yml

api:
  dashboard: true
  insecure: true

entryPoints:
  web:
    address: ":80"
  websecure:
    address: ":443"

providers:
  file:
    directory: /etc/traefik/dynamic/
    watch: true
```

### Dynamic Configuration

```yaml
# /etc/traefik/dynamic/wormhole.yml

http:
  routers:
    wormhole:
      rule: "PathPrefix(`/wh/`)"
      service: wormhole-daemon
      middlewares:
        - strip-wh-prefix

    wormhole-ws:
      rule: "PathPrefix(`/wh/ws/`)"
      service: wormhole-daemon

  services:
    wormhole-daemon:
      loadBalancer:
        servers:
          - url: "http://127.0.0.1:9475"
        healthCheck:
          path: /status
          interval: 10s

  middlewares:
    strip-wh-prefix:
      stripPrefix:
        prefixes:
          - "/wh"
```

## Host-Based Routing

Route different wormhole addresses to different backends:

```yaml
http:
  routers:
    site1:
      rule: "Host(`site1.example.com`)"
      service: wormhole-site1

    site2:
      rule: "Host(`site2.example.com`)"
      service: wormhole-site2

  services:
    wormhole-site1:
      loadBalancer:
        servers:
          - url: "http://127.0.0.1:9475/browse/wh://site1.wns/"

    wormhole-site2:
      loadBalancer:
        servers:
          - url: "http://127.0.0.1:9475/browse/wh://site2.wns/"
```

## TLS with Let's Encrypt

```yaml
# traefik.yml
certificatesResolvers:
  letsencrypt:
    acme:
      email: your-email@example.com
      storage: /letsencrypt/acme.json
      httpChallenge:
        entryPoint: web

# dynamic/wormhole.yml
http:
  routers:
    wormhole-secure:
      rule: "PathPrefix(`/wh/`)"
      service: wormhole-daemon
      entryPoints:
        - websecure
      tls:
        certResolver: letsencrypt
```

## Load Balancing Multiple Daemons

```yaml
http:
  services:
    wormhole-daemon:
      loadBalancer:
        servers:
          - url: "http://daemon1:9475"
          - url: "http://daemon2:9475"
          - url: "http://daemon3:9475"
        healthCheck:
          path: /status
          interval: 10s
          timeout: 3s
        sticky:
          cookie:
            name: wormhole_sticky
            secure: true
            httpOnly: true
```

## Kubernetes Integration

### IngressRoute

```yaml
apiVersion: traefik.containo.us/v1alpha1
kind: IngressRoute
metadata:
  name: wormhole
spec:
  entryPoints:
    - web
  routes:
    - match: PathPrefix(`/wh/`)
      kind: Rule
      services:
        - name: wormhole-daemon
          port: 9475
      middlewares:
        - name: strip-wh-prefix

---
apiVersion: traefik.containo.us/v1alpha1
kind: Middleware
metadata:
  name: strip-wh-prefix
spec:
  stripPrefix:
    prefixes:
      - /wh
```

### Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: wormhole-daemon
spec:
  replicas: 3
  selector:
    matchLabels:
      app: wormhole-daemon
  template:
    metadata:
      labels:
        app: wormhole-daemon
    spec:
      containers:
        - name: wormhole-daemon
          image: wormhole-tools:latest
          args: ["daemon", "start", "--port", "9475"]
          ports:
            - containerPort: 9475
          livenessProbe:
            httpGet:
              path: /status
              port: 9475
            initialDelaySeconds: 10
            periodSeconds: 5

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

## Rate Limiting

```yaml
http:
  middlewares:
    wormhole-ratelimit:
      rateLimit:
        average: 100
        burst: 50
        period: 1s

  routers:
    wormhole:
      rule: "PathPrefix(`/wh/`)"
      middlewares:
        - wormhole-ratelimit
      service: wormhole-daemon
```

## Authentication

Basic auth for wormhole endpoints:

```yaml
http:
  middlewares:
    wormhole-auth:
      basicAuth:
        users:
          - "admin:$apr1$xxx..."  # htpasswd generated

  routers:
    wormhole:
      rule: "PathPrefix(`/wh/`)"
      middlewares:
        - wormhole-auth
      service: wormhole-daemon
```

## Monitoring

```yaml
metrics:
  prometheus:
    buckets:
      - 0.1
      - 0.3
      - 1.2
      - 5.0

accessLog:
  filePath: /var/log/traefik/access.log
  format: json
  filters:
    statusCodes:
      - "400-599"
```

## Troubleshooting

### Debug Mode

```yaml
log:
  level: DEBUG
```

### Access Logs

```yaml
accessLog:
  filePath: /var/log/traefik/access.log
  bufferingSize: 100
```

### Dashboard

Access at `http://localhost:8080/dashboard/`

## See Also

- [Main Integration Guide](../README.md)
- [HAProxy Integration](../haproxy/README.md)
- [Kubernetes Deployment](../../docs/kubernetes.md)
