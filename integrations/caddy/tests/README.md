# Caddy Wormhole Plugin Tests

This directory contains test infrastructure for the Caddy Wormhole plugin.

## Test Files

### Unit Tests
- **`../daemon_test.go`** - Tests for daemon client API
- **`../wormhole_test.go`** - Tests for wormhole module and handler
- **`../integration_test.go`** - Integration tests with mock daemon

Run unit tests:
```bash
go test -v ./...
```

### Real Connection Tests

#### test-real-connection.sh
Interactive test script that sets up a complete test environment:

1. Starts wormhole daemon (if not running)
2. Starts a test HTTP server on port 8888
3. Creates a wormhole listener forwarding to the test server
4. Provides instructions for manual Caddy testing

**Usage:**
```bash
cd /path/to/integrations/caddy
./test-real-connection.sh
```

The script will keep all services running until you press Ctrl+C.

**Test flow:**
1. Run the script to set up the environment
2. In another terminal, build and run Caddy:
   ```bash
   xcaddy build --with github.com/wormhole-foundation/magic-wormhole-go/integrations/caddy=.
   ./caddy run --config Caddyfile.test
   ```
3. Test the connection:
   ```bash
   curl -H 'Host: <code>.wns' http://localhost:2019/
   ```

Expected output:
```
Hello from Wormhole via Caddy!
```

#### Caddyfile.test
Test configuration for Caddy with the wormhole plugin.

**Features:**
- Debug logging enabled
- Wormhole routing on port 2019
- Fallback response for requests without wormhole code

**Configuration:**
```caddyfile
:2019 {
    route {
        wormhole {
            daemon_url http://localhost:8765
            debug true
        }
    }
}
```

### Integration Test (Go)

**`TestIntegration_RealWormholeConnection`** in `integration_test.go`:

This test verifies connectivity to a real wormhole daemon but does not complete the full connection flow (which requires two sides).

**Run with:**
```bash
# Skipped by default
go test -v -run TestIntegration_RealWormholeConnection

# Or in short mode (will skip)
go test -short -v -run TestIntegration_RealWormholeConnection
```

The test will:
1. Check if daemon is running (skip if not)
2. Create a real wormhole listener
3. Display the wormhole code and manual test instructions
4. Clean up the listener

## Test Prerequisites

### Required Tools
- **wh** - Wormhole CLI tool
- **go** - Go compiler (1.21+)
- **xcaddy** - Caddy builder with plugin support
- **python3** - For test HTTP server

### Install Prerequisites

1. Install wormhole CLI:
   ```bash
   # See main project README
   ```

2. Install xcaddy:
   ```bash
   go install github.com/caddyserver/xcaddy/cmd/xcaddy@latest
   ```

3. Start wormhole daemon:
   ```bash
   wh daemon start
   ```

## Test Coverage

Current test coverage includes:

**Unit Tests (13 tests):**
- Daemon client API (status, listen, accept, send/recv, close)
- Connection lifecycle
- Deadline handling (read, write, both)
- Partial reads and buffering
- Multiple concurrent connections
- Error handling

**Integration Tests:**
- Mock daemon server interactions
- Listener accept loop
- Connection read/write operations
- Full connection lifecycle
- Real daemon connectivity (manual)

**Manual Tests:**
- Real wormhole connection through Caddy
- End-to-end HTTP proxying via wormhole
- WNS (Wormhole Name Service) resolution

## Debugging Tests

### Enable Debug Logging

Set `debug true` in Caddyfile.test or use environment variables:

```bash
# Caddy debug mode
./caddy run --config Caddyfile.test --debug

# Wormhole daemon debug
wh daemon start --debug
```

### Common Issues

**Problem:** Daemon not running
```bash
# Check status
wh daemon status

# Start daemon
wh daemon start
```

**Problem:** Port already in use
```bash
# Check what's using port 2019
lsof -i :2019

# Or use a different port in Caddyfile.test
```

**Problem:** Connection timeout
- Verify daemon is running: `wh daemon status`
- Check firewall settings
- Verify relay server connectivity

## CI/CD Integration

Unit tests can run in CI without daemon:
```bash
go test -v -short ./...
```

Real connection tests require manual execution due to:
- Need for running daemon
- Network connectivity requirements
- Two-sided connection requirement
