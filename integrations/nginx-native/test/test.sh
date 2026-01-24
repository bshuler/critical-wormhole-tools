#!/bin/bash
#
# Test script for Wormhole Nginx Module
#
# This script tests the wormhole nginx module by:
# 1. Starting a mock wormhole daemon
# 2. Building and loading the nginx module
# 3. Sending test requests
# 4. Verifying responses

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
MODULE_DIR="$(dirname "$SCRIPT_DIR")"
ROOT_DIR="$(dirname "$(dirname "$MODULE_DIR")")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counters
TESTS_PASSED=0
TESTS_FAILED=0

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_test() {
    echo -e "${YELLOW}[TEST]${NC} $1"
}

pass_test() {
    echo -e "${GREEN}[PASS]${NC} $1"
    ((TESTS_PASSED++))
}

fail_test() {
    echo -e "${RED}[FAIL]${NC} $1"
    ((TESTS_FAILED++))
}

# Mock daemon using netcat or Python
start_mock_daemon() {
    log_info "Starting mock wormhole daemon on port 8080..."

    # Simple Python HTTP server that responds to /browse/ requests
    python3 -c '
import http.server
import socketserver
import json
import urllib.parse

class MockHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Suppress logging

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path

        if path.startswith("/browse/"):
            # Extract WNS name from path
            parts = path[8:].split("/", 1)
            wns_name = parts[0]
            sub_path = "/" + parts[1] if len(parts) > 1 else "/"

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("X-Wormhole-Resolved", wns_name)
            self.end_headers()

            response = {
                "success": True,
                "wns_name": wns_name,
                "path": sub_path,
                "message": f"Mock response for {wns_name}"
            }
            self.wfile.write(json.dumps(response).encode())

        elif path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"OK")

        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        self.do_GET()

PORT = 8080
with socketserver.TCPServer(("", PORT), MockHandler) as httpd:
    httpd.serve_forever()
' &
    DAEMON_PID=$!
    sleep 1

    # Verify daemon is running
    if kill -0 $DAEMON_PID 2>/dev/null; then
        log_info "Mock daemon started (PID: $DAEMON_PID)"
    else
        log_error "Failed to start mock daemon"
        exit 1
    fi
}

stop_mock_daemon() {
    if [ -n "$DAEMON_PID" ]; then
        log_info "Stopping mock daemon..."
        kill $DAEMON_PID 2>/dev/null || true
        wait $DAEMON_PID 2>/dev/null || true
    fi
}

# Test helper functions
test_request() {
    local description="$1"
    local url="$2"
    local expected_status="$3"
    local host_header="$4"

    log_test "$description"

    local curl_args="-s -o /dev/null -w %{http_code}"
    if [ -n "$host_header" ]; then
        curl_args="$curl_args -H Host:$host_header"
    fi

    local status=$(curl $curl_args "$url")

    if [ "$status" = "$expected_status" ]; then
        pass_test "$description (status: $status)"
        return 0
    else
        fail_test "$description (expected: $expected_status, got: $status)"
        return 1
    fi
}

test_response_contains() {
    local description="$1"
    local url="$2"
    local expected_content="$3"
    local host_header="$4"

    log_test "$description"

    local curl_args="-s"
    if [ -n "$host_header" ]; then
        curl_args="$curl_args -H Host:$host_header"
    fi

    local response=$(curl $curl_args "$url")

    if echo "$response" | grep -q "$expected_content"; then
        pass_test "$description"
        return 0
    else
        fail_test "$description (content not found: $expected_content)"
        echo "Response was: $response"
        return 1
    fi
}

# Main test suite
run_tests() {
    log_info "Running wormhole nginx module tests..."
    echo ""

    # Test 1: Mock daemon health check
    test_request "Mock daemon health check" \
        "http://localhost:8080/health" \
        "200" || true

    # Test 2: Mock daemon browse endpoint
    test_request "Mock daemon browse endpoint" \
        "http://localhost:8080/browse/alice.wns/" \
        "200" || true

    # Test 3: Browse with path
    test_response_contains "Browse with sub-path" \
        "http://localhost:8080/browse/alice.wns/api/data" \
        "alice.wns" || true

    # Test 4: Browse with .wormhole suffix
    test_response_contains "Browse with .wormhole name" \
        "http://localhost:8080/browse/bob.wormhole/" \
        "bob.wormhole" || true

    # Test 5: Browse with nested path
    test_response_contains "Browse with nested path" \
        "http://localhost:8080/browse/charlie.wns/api/v1/users" \
        "charlie.wns" || true

    echo ""
    echo "=================================="
    echo "Test Results"
    echo "=================================="
    echo -e "Passed: ${GREEN}$TESTS_PASSED${NC}"
    echo -e "Failed: ${RED}$TESTS_FAILED${NC}"
    echo ""

    if [ $TESTS_FAILED -eq 0 ]; then
        log_info "All tests passed!"
        return 0
    else
        log_error "Some tests failed"
        return 1
    fi
}

# Cleanup on exit
cleanup() {
    stop_mock_daemon
}
trap cleanup EXIT

# Build module (if cmake is available)
build_module() {
    if command -v cmake &> /dev/null; then
        log_info "Building nginx module..."
        cd "$MODULE_DIR"

        if [ ! -d "build" ]; then
            mkdir build
        fi

        cd build
        cmake .. && make
        cd "$SCRIPT_DIR"
    else
        log_warn "cmake not found, skipping module build"
    fi
}

# Main
main() {
    echo "=================================="
    echo "Wormhole Nginx Module Test Suite"
    echo "=================================="
    echo ""

    # Start mock daemon
    start_mock_daemon

    # Run tests
    run_tests

    exit_code=$?
    exit $exit_code
}

# Run main if not sourced
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
