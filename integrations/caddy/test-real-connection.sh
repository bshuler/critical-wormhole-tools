#!/bin/bash
# Test Caddy plugin with real wormhole connection

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_PORT=8888
CADDY_PORT=2019
HTTP_PID=""
LISTEN_PID=""
CADDY_PID=""

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

cleanup() {
    log_info "Cleaning up..."
    if [ -n "$HTTP_PID" ] && kill -0 "$HTTP_PID" 2>/dev/null; then
        kill "$HTTP_PID" 2>/dev/null || true
    fi
    if [ -n "$LISTEN_PID" ] && kill -0 "$LISTEN_PID" 2>/dev/null; then
        kill "$LISTEN_PID" 2>/dev/null || true
    fi
    if [ -n "$CADDY_PID" ] && kill -0 "$CADDY_PID" 2>/dev/null; then
        kill "$CADDY_PID" 2>/dev/null || true
    fi
}

trap cleanup EXIT INT TERM

echo "==================================================================="
echo "  Caddy Wormhole Plugin - Real Connection Integration Test"
echo "==================================================================="
echo ""

# Check prerequisites
log_info "Checking prerequisites..."

if ! command -v wh >/dev/null 2>&1; then
    log_error "wh CLI not found. Please install wormhole first."
    exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
    log_error "python3 not found. Please install Python 3."
    exit 1
fi

if [ ! -f "$SCRIPT_DIR/Caddyfile.test" ]; then
    log_error "Caddyfile.test not found at $SCRIPT_DIR/Caddyfile.test"
    exit 1
fi

# Start daemon if not running
log_info "Checking wormhole daemon status..."
if ! wh daemon status 2>/dev/null; then
    log_warn "Daemon not running. Starting wh daemon..."
    wh daemon start
    sleep 2

    # Verify it started
    if ! wh daemon status 2>/dev/null; then
        log_error "Failed to start wormhole daemon"
        exit 1
    fi
    log_info "Daemon started successfully"
else
    log_info "Daemon is already running"
fi

# Create a temporary directory for test content
TEST_DIR=$(mktemp -d)
echo "Hello from Wormhole via Caddy!" > "$TEST_DIR/index.html"
log_info "Created test content at $TEST_DIR/index.html"

# Start a test HTTP server
log_info "Starting test HTTP server on port $TEST_PORT..."
cd "$TEST_DIR"
python3 -m http.server $TEST_PORT >/dev/null 2>&1 &
HTTP_PID=$!
cd - >/dev/null
sleep 1

if ! kill -0 "$HTTP_PID" 2>/dev/null; then
    log_error "Failed to start HTTP server"
    exit 1
fi
log_info "HTTP server running (PID: $HTTP_PID)"

# Start wormhole listener and capture the code
log_info "Starting wormhole listener..."
WH_OUTPUT=$(mktemp)
wh listen --http --forward http://localhost:$TEST_PORT > "$WH_OUTPUT" 2>&1 &
LISTEN_PID=$!

# Wait for code to be generated
sleep 3

if ! kill -0 "$LISTEN_PID" 2>/dev/null; then
    log_error "Wormhole listener failed to start"
    cat "$WH_OUTPUT"
    rm -f "$WH_OUTPUT"
    rm -rf "$TEST_DIR"
    exit 1
fi

# Extract the wormhole code from output
WH_CODE=$(grep -oE '[0-9]+-[a-z]+-[a-z]+' "$WH_OUTPUT" | head -1)

if [ -z "$WH_CODE" ]; then
    log_warn "Could not extract wormhole code from output:"
    cat "$WH_OUTPUT"
    WH_CODE="<code-not-found>"
else
    log_info "Wormhole listener ready with code: $WH_CODE"
fi

rm -f "$WH_OUTPUT"

echo ""
echo "==================================================================="
echo "  Test Setup Complete"
echo "==================================================================="
echo ""
echo "Components running:"
echo "  - Test HTTP server: http://localhost:$TEST_PORT"
echo "  - Wormhole listener: $WH_CODE (forwarding to HTTP server)"
echo ""
echo "To test through Caddy:"
echo ""
echo "  1. Build Caddy with wormhole plugin:"
echo "     cd $SCRIPT_DIR"
echo "     xcaddy build --with github.com/wormhole-foundation/magic-wormhole-go/integrations/caddy=."
echo ""
echo "  2. Run Caddy with test config:"
echo "     ./caddy run --config Caddyfile.test"
echo ""
echo "  3. Test the connection:"
echo "     curl -H 'Host: $WH_CODE.wns' http://localhost:$CADDY_PORT/"
echo ""
echo "Expected output:"
echo "     Hello from Wormhole via Caddy!"
echo ""
echo "==================================================================="
echo ""

# Ask user if they want to continue with manual testing
read -p "Press Enter to continue with manual testing, or Ctrl+C to exit..."

echo ""
log_info "Test environment is ready. Components will remain running."
log_info "Press Ctrl+C to stop all services and clean up."

# Wait indefinitely until user stops
wait
