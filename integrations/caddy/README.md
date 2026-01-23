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

The Caddy plugin includes comprehensive unit and integration tests:

```bash
# Run all tests
go test ./...

# Run only unit tests
go test -v -run Test[^Integration]

# Run only integration tests
go test -v -run TestIntegration

# Run with coverage
go test -cover ./...
```

#### Test Coverage

| Component | Test File | Coverage |
|-----------|-----------|----------|
| Address parsing | `wormhole_test.go` | Unit tests for WNS address parsing |
| Daemon client | `daemon_test.go` | Unit tests for HTTP API client |
| Integration | `integration_test.go` | End-to-end integration tests |

#### Integration Tests

The integration tests use mock HTTP servers to simulate the `wh daemon` API:

- **TestIntegration_MockDaemonServer**: Validates daemon client with mock server
- **TestIntegration_WormholeListener**: Tests listener's ability to accept connections
- **TestIntegration_WormholeConn_ReadWrite**: Tests read/write operations on connections
- **TestIntegration_WormholeConn_PartialRead**: Tests buffering of partial reads
- **TestIntegration_Deadline_Read**: Tests read deadline handling
- **TestIntegration_Deadline_Write**: Tests write deadline handling
- **TestIntegration_Connection_Lifecycle**: Tests full connection lifecycle
- **TestIntegration_MultipleConnections**: Tests concurrent connection handling

## Working Examples

### Example 1: Static File Server

Serve static files over wormhole address:

```bash
# 1. Start the wh daemon (required for all wormhole operations)
wh daemon start

# 2. Create a Caddyfile
cat > Caddyfile <<EOF
mysite.wh {
    wormhole {
        name mysite
    }

    root * /var/www/html
    file_server
}
EOF

# 3. Start Caddy
caddy run

# 4. Connect from another machine
wh curl wh://mysite.<address>.wns/
```

### Example 2: Reverse Proxy

Proxy requests to a backend service:

```bash
# Start backend service
python3 -m http.server 8080 &

# Create Caddyfile
cat > Caddyfile <<EOF
api.wh {
    wormhole {
        name api
        daemon http://127.0.0.1:9475
    }

    reverse_proxy localhost:8080
}
EOF

# Start Caddy
caddy run

# Access from remote
wh curl wh://api.<address>.wns/endpoint
```

### Example 3: Multiple Sites

Host multiple sites on different wormhole addresses:

```bash
cat > Caddyfile <<EOF
blog.wh {
    wormhole {
        name blog
    }
    root * /var/www/blog
    file_server
}

docs.wh {
    wormhole {
        name docs
    }
    root * /var/www/docs
    file_server
    templates
}

api.wh {
    wormhole {
        name api
    }
    reverse_proxy localhost:3000
}
EOF

caddy run
```

## Known Limitations

### 1. Daemon Dependency

The Caddy plugin requires the `wh daemon` to be running:

```bash
# Start daemon
wh daemon start

# Check status
wh daemon status

# View logs
wh daemon logs
```

**Workaround**: Set up the daemon as a systemd service to ensure it's always running.

### 2. Connection Timeout

Wormhole connections use a 30-second default timeout for read/write operations.

**Impact**: Long-running requests may timeout.

**Workaround**: Adjust timeouts in your application or use WebSockets for long-lived connections.

### 3. Binary Data Handling

The daemon API uses HTTP for data transfer, which may add overhead for binary data.

**Impact**: Slightly reduced performance for large binary transfers compared to direct wormhole connections.

**Workaround**: Use `wh scp` for large file transfers instead of HTTP.

### 4. TLS Termination

The plugin handles wormhole connections but doesn't currently integrate with Caddy's automatic HTTPS.

**Impact**: HTTPS must be handled separately if needed.

**Status**: Under investigation - wormhole already provides encryption, so this may not be necessary.

### 5. Load Balancing

Currently, each listener creates a single wormhole endpoint.

**Impact**: No built-in load balancing across multiple backend servers.

**Workaround**: Use multiple Caddy instances with different wormhole addresses and a custom load balancer.

## Troubleshooting

### Issue: "Failed to connect to daemon"

**Cause**: The `wh daemon` is not running or not accessible.

**Solution**:
```bash
# Check if daemon is running
wh daemon status

# Start daemon if not running
wh daemon start

# Check daemon logs
wh daemon logs

# Verify daemon URL in Caddyfile
wormhole {
    daemon http://127.0.0.1:9475  # Default URL
}
```

### Issue: "Listener failed to start"

**Cause**: The wormhole identity or network configuration is incorrect.

**Solution**:
```bash
# Create an identity if none exists
wh identity create --name my-server

# Use specific identity in Caddyfile
wormhole {
    identity /path/to/identity.key
}

# Check network connectivity to relay
curl -I https://relay.magic-wormhole.io/
```

### Issue: "Connection timeout"

**Cause**: The wormhole connection was interrupted or the peer disconnected.

**Solution**:
- Check network connectivity on both sides
- Verify the wormhole code is correct
- Ensure firewall isn't blocking WebSocket connections to relay server
- Try using a custom relay: `wh relay` on a server you control

### Issue: "Address already in use"

**Cause**: Another process is using the same wormhole address/name.

**Solution**:
```bash
# Use a different scoped name
wormhole {
    name mysite-prod  # Change this to be unique
}

# Or use a different identity
wh identity create --name caddy-server-2
wormhole {
    identity /path/to/new/identity.key
}
```

### Issue: "Tests fail with 'connection refused'"

**Cause**: Test is trying to connect to actual daemon instead of mock server.

**Solution**:
The integration tests use mock HTTP servers and should not require a running daemon. If tests fail:

```bash
# Ensure no environment variables override daemon URL
unset WH_DAEMON_URL

# Run tests in verbose mode to see details
go test -v -run TestIntegration

# Check for port conflicts
lsof -i :9475
```

### Debug Mode

Enable verbose logging for debugging:

```bash
# Set environment variable
export CADDY_DEBUG=1

# Run Caddy with debug logging
caddy run --config Caddyfile --adapter caddyfile --debug
```

### Getting Help

- **GitHub Issues**: Report bugs or request features
- **Discussions**: Ask questions about usage
- **Logs**: Always include Caddy logs and `wh daemon logs` when reporting issues

## Performance Considerations

### Benchmarks

Connection establishment time:
- Local network: ~50-100ms
- Internet (via relay): ~200-500ms

Throughput:
- Direct transit: ~50-100 MB/s
- Via relay: ~10-20 MB/s

Latency overhead:
- ~20-50ms additional latency compared to direct HTTP

### Optimization Tips

1. **Use direct transit relay when possible**: Configure peers to use direct connections
2. **Run your own relay**: Reduces latency compared to public relay
3. **Batch small requests**: HTTP overhead is significant for small requests
4. **Use connection pooling**: Keep connections alive for multiple requests
5. **Monitor daemon performance**: The daemon is a potential bottleneck

## Roadmap

- [x] Basic wormhole listener implementation
- [x] WNS identity integration
- [x] Caddyfile directive parsing
- [x] Integration with daemon API
- [x] Comprehensive integration tests
- [ ] Automatic code publication to DHT
- [ ] Connection metrics and logging
- [ ] TLS certificate integration
- [ ] Load balancing support
- [ ] WebSocket support
- [ ] HTTP/2 and HTTP/3 support

## License

Same license as the main wormhole-tools project.
