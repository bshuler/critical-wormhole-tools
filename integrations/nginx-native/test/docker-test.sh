#!/bin/bash
# Test script for nginx wormhole module using Docker
#
# This script should be run on a system with Docker installed (e.g., hp1 or hp2)
# Usage: ./docker-test.sh [--no-cache]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODULE_DIR="$(dirname "$SCRIPT_DIR")"
NO_CACHE=""

if [ "$1" = "--no-cache" ]; then
    NO_CACHE="--no-cache"
fi

echo "Building nginx wormhole module..."
docker build $NO_CACHE -t nginx-wormhole "$MODULE_DIR"

echo ""
echo "Testing module loads..."
docker run --rm nginx-wormhole nginx -t

echo ""
echo "Testing module configuration..."
if docker run --rm nginx-wormhole nginx -T | grep -q 'wormhole_enable'; then
    echo "✓ wormhole_enable directive found"
else
    echo "✗ wormhole_enable directive not found"
    exit 1
fi

if docker run --rm nginx-wormhole nginx -T | grep -q 'wormhole_daemon'; then
    echo "✓ wormhole_daemon directive found"
else
    echo "✗ wormhole_daemon directive not found"
    exit 1
fi

echo ""
echo "Verifying module is loaded..."
if docker run --rm nginx-wormhole test -f /etc/nginx/modules/ngx_http_wormhole_module.so; then
    echo "✓ Module shared object exists"
else
    echo "✗ Module shared object not found"
    exit 1
fi

echo ""
echo "Testing nginx starts successfully..."
CONTAINER_ID=$(docker run -d --name nginx-test nginx-wormhole)
sleep 2

if docker exec nginx-test nginx -s reload; then
    echo "✓ Nginx reload successful"
else
    echo "✗ Nginx reload failed"
    docker stop nginx-test
    docker rm nginx-test
    exit 1
fi

docker stop nginx-test
docker rm nginx-test

echo ""
echo "All tests passed!"
