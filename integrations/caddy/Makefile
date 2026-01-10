# Makefile for Caddy Wormhole Plugin

.PHONY: all build test clean install deps xcaddy

# Variables
BINARY_NAME=caddy-wormhole
GO=go
XCADDY=xcaddy

# Default target
all: deps test build

# Install dependencies
deps:
	$(GO) mod tidy

# Run tests
test:
	$(GO) test -v ./...

# Run tests with coverage
test-coverage:
	$(GO) test -v -coverprofile=coverage.out ./...
	$(GO) tool cover -html=coverage.out -o coverage.html

# Build the plugin (requires xcaddy)
build: deps
	$(XCADDY) build --with github.com/bshuler/wormhole-tools/integrations/caddy=./

# Build without xcaddy (for testing compilation)
build-check:
	$(GO) build ./...

# Install xcaddy
install-xcaddy:
	$(GO) install github.com/caddyserver/xcaddy/cmd/xcaddy@latest

# Clean build artifacts
clean:
	rm -f $(BINARY_NAME)
	rm -f coverage.out coverage.html
	rm -f caddy

# Format code
fmt:
	$(GO) fmt ./...

# Run linter
lint:
	golangci-lint run

# Verify module
verify:
	$(GO) mod verify

# Update dependencies
update:
	$(GO) get -u ./...
	$(GO) mod tidy

# Run example Caddy config
run: build
	./caddy run --config Caddyfile.example --adapter caddyfile

# Development: watch and rebuild
watch:
	@echo "Watching for changes..."
	@while true; do \
		inotifywait -q -e modify -e create -e delete --exclude '\.git' -r .; \
		make build-check; \
	done

# Help
help:
	@echo "Caddy Wormhole Plugin Makefile"
	@echo ""
	@echo "Targets:"
	@echo "  all           - Run deps, test, and build"
	@echo "  deps          - Install Go dependencies"
	@echo "  test          - Run tests"
	@echo "  test-coverage - Run tests with coverage report"
	@echo "  build         - Build Caddy with wormhole plugin (requires xcaddy)"
	@echo "  build-check   - Check that code compiles"
	@echo "  install-xcaddy- Install xcaddy tool"
	@echo "  clean         - Remove build artifacts"
	@echo "  fmt           - Format Go code"
	@echo "  lint          - Run linter"
	@echo "  verify        - Verify module dependencies"
	@echo "  update        - Update dependencies"
	@echo "  run           - Build and run with example config"
	@echo "  help          - Show this help message"
