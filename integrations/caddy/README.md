# Caddy Wormhole Plugin

A Caddy module that enables serving websites over wormhole addresses.

## Overview

This plugin allows Caddy to:
- Listen on wormhole addresses (e.g., `wh://mysite.wns`)
- Serve HTTP content over the wormhole protocol
- Automatically manage WNS identity and code publication

## Installation

### Using xcaddy (Recommended)

```bash
xcaddy build --with github.com/your-org/caddy-wormhole
```

### From Source

```bash
cd integrations/caddy
go build -o caddy-wormhole ./cmd/caddy
```

## Configuration

### Caddyfile Syntax

```caddyfile
# Basic wormhole site
mysite.wh {
    wormhole {
        identity /path/to/identity.key  # Optional: use specific identity
        name mysite                      # Optional: scoped name
    }

    root * /var/www/mysite
    file_server
}

# Multiple wormhole sites
api.wh {
    wormhole
    reverse_proxy localhost:3000
}

static.wh {
    wormhole {
        name static
    }
    file_server browse
}
```

### JSON Configuration

```json
{
  "apps": {
    "http": {
      "servers": {
        "wormhole": {
          "listen": ["wormhole://"],
          "routes": [{
            "match": [{"host": ["mysite.wh"]}],
            "handle": [{
              "handler": "wormhole",
              "identity": "/path/to/identity.key"
            }, {
              "handler": "file_server",
              "root": "/var/www/mysite"
            }]
          }]
        }
      }
    }
  }
}
```

## Usage

### Start Caddy with Wormhole

```bash
# Using Caddyfile
caddy run --config Caddyfile

# Your site is now available at wh://[address].wns
```

### Connect to Wormhole Site

```bash
# Using wh curl
wh curl wh://mysite.wns/

# Using browser extension
# Navigate to wh://mysite.wns in your browser
```

## Architecture

```
                    ┌─────────────────────────────────────┐
                    │           Caddy Server              │
                    │                                     │
                    │  ┌─────────────┐  ┌─────────────┐  │
                    │  │  Wormhole   │  │   HTTP      │  │
Internet ────────────►│   Module    │──►│  Handler    │  │
                    │  │             │  │             │  │
                    │  └─────────────┘  └─────────────┘  │
                    │         │                          │
                    └─────────│──────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │  Magic Wormhole │
                    │     Relay       │
                    └─────────────────┘
```

## Module Structure

```
caddy/
├── README.md           # This file
├── go.mod              # Go module definition
├── go.sum              # Go dependencies
├── wormhole.go         # Main Caddy module
├── listener.go         # Wormhole listener implementation
├── caddyfile.go        # Caddyfile parser
└── cmd/
    └── caddy/
        └── main.go     # Custom Caddy build entry point
```

## Development

### Prerequisites

- Go 1.21+
- xcaddy (for building custom Caddy)

### Building

```bash
# Install xcaddy
go install github.com/caddyserver/xcaddy/cmd/xcaddy@latest

# Build with wormhole module
xcaddy build --with github.com/your-org/caddy-wormhole=./

# Or build directly
go build -o caddy ./cmd/caddy
```

### Testing

```bash
go test ./...
```

## Roadmap

- [ ] Basic wormhole listener implementation
- [ ] WNS identity integration
- [ ] Caddyfile directive parsing
- [ ] Automatic code publication to DHT
- [ ] Connection metrics and logging
- [ ] TLS certificate integration
- [ ] Load balancing support

## License

Same license as the main wormhole-tools project.
