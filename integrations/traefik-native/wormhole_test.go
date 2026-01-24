// Package traefik_wormhole_plugin provides a Traefik middleware for WNS resolution
package traefik_wormhole_plugin

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
)

// TestIsWormholeRequest tests the wormhole request detection logic
func TestIsWormholeRequest(t *testing.T) {
	config := CreateConfig()
	next := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	})

	middleware, err := New(context.Background(), next, config, "test")
	if err != nil {
		t.Fatalf("Failed to create middleware: %v", err)
	}

	wm := middleware.(*WormholeMiddleware)

	tests := []struct {
		name     string
		host     string
		expected bool
	}{
		{"wh:// prefix", "wh://example", true},
		{"wh:// with domain", "wh://mysite.wns", true},
		{".wns suffix", "mysite.wns", true},
		{".wns with port", "mysite.wns:8080", true},
		{"subdomain.wns", "sub.mysite.wns", true},
		{"regular domain", "example.com", false},
		{"regular with port", "example.com:443", false},
		{"empty host", "", false},
		{"partial wns", "wns.com", false},
		{"wns in middle", "my.wns.site.com", false},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := wm.isWormholeRequest(tt.host)
			if result != tt.expected {
				t.Errorf("isWormholeRequest(%q) = %v, want %v", tt.host, result, tt.expected)
			}
		})
	}
}

// TestExtractWNSName tests WNS name extraction from various host formats
func TestExtractWNSName(t *testing.T) {
	config := CreateConfig()
	next := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	})

	middleware, err := New(context.Background(), next, config, "test")
	if err != nil {
		t.Fatalf("Failed to create middleware: %v", err)
	}

	wm := middleware.(*WormholeMiddleware)

	tests := []struct {
		name     string
		host     string
		expected string
	}{
		{"wh:// simple", "wh://example", "example"},
		{"wh:// with wns", "wh://mysite.wns", "mysite.wns"},
		{"wh:// with path", "wh://example/path", "example"},
		{"wh:// with port", "wh://example:8080", "example"},
		{".wns simple", "mysite.wns", "mysite.wns"},
		{".wns with port", "mysite.wns:8080", "mysite.wns"},
		{"subdomain.wns", "sub.mysite.wns", "sub.mysite.wns"},
		{"regular domain", "example.com", ""},
		{"empty", "", ""},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := wm.extractWNSName(tt.host)
			if result != tt.expected {
				t.Errorf("extractWNSName(%q) = %q, want %q", tt.host, result, tt.expected)
			}
		})
	}
}

// TestServeHTTPPassthrough tests that non-wormhole requests are passed through
func TestServeHTTPPassthrough(t *testing.T) {
	config := CreateConfig()
	nextCalled := false
	next := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		nextCalled = true
		w.WriteHeader(http.StatusOK)
		w.Write([]byte("next handler"))
	})

	middleware, err := New(context.Background(), next, config, "test")
	if err != nil {
		t.Fatalf("Failed to create middleware: %v", err)
	}

	req := httptest.NewRequest(http.MethodGet, "http://example.com/path", nil)
	rr := httptest.NewRecorder()

	middleware.ServeHTTP(rr, req)

	if !nextCalled {
		t.Error("Expected next handler to be called for non-wormhole request")
	}

	if rr.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", rr.Code)
	}
}

// TestServeHTTPWormholeRequest tests that wormhole requests are handled
func TestServeHTTPWormholeRequest(t *testing.T) {
	// Create a mock daemon server
	mockDaemon := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/browse/mysite.wns/" {
			w.Header().Set("Content-Type", "text/html")
			w.WriteHeader(http.StatusOK)
			w.Write([]byte("<html>Hello from wormhole</html>"))
		} else {
			w.WriteHeader(http.StatusNotFound)
		}
	}))
	defer mockDaemon.Close()

	config := CreateConfig()
	config.DaemonURL = mockDaemon.URL
	config.Debug = true

	next := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		t.Error("Next handler should not be called for wormhole request")
	})

	middleware, err := New(context.Background(), next, config, "test")
	if err != nil {
		t.Fatalf("Failed to create middleware: %v", err)
	}

	req := httptest.NewRequest(http.MethodGet, "http://mysite.wns/", nil)
	req.Host = "mysite.wns"
	rr := httptest.NewRecorder()

	middleware.ServeHTTP(rr, req)

	if rr.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", rr.Code)
	}

	body := rr.Body.String()
	if body != "<html>Hello from wormhole</html>" {
		t.Errorf("Unexpected response body: %s", body)
	}
}

// TestServeHTTPWormholeDaemonError tests error handling when daemon fails
func TestServeHTTPWormholeDaemonError(t *testing.T) {
	// Create a mock daemon that returns errors
	mockDaemon := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusInternalServerError)
		w.Write([]byte("daemon error"))
	}))
	defer mockDaemon.Close()

	config := CreateConfig()
	config.DaemonURL = mockDaemon.URL

	next := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		t.Error("Next handler should not be called for wormhole request")
	})

	middleware, err := New(context.Background(), next, config, "test")
	if err != nil {
		t.Fatalf("Failed to create middleware: %v", err)
	}

	req := httptest.NewRequest(http.MethodGet, "http://mysite.wns/", nil)
	req.Host = "mysite.wns"
	rr := httptest.NewRecorder()

	middleware.ServeHTTP(rr, req)

	// Should return the daemon's error status
	if rr.Code != http.StatusInternalServerError {
		t.Errorf("Expected status 500, got %d", rr.Code)
	}
}

// TestResolveWNS tests WNS resolution via daemon API
func TestResolveWNS(t *testing.T) {
	// Create a mock daemon server
	mockDaemon := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/resolve" && r.Method == http.MethodPost {
			var body map[string]string
			json.NewDecoder(r.Body).Decode(&body)

			response := ResolveResponse{
				Address: body["address"],
				Code:    "test-code-123",
				Expires: 1234567890,
			}
			w.Header().Set("Content-Type", "application/json")
			json.NewEncoder(w).Encode(response)
		} else {
			w.WriteHeader(http.StatusNotFound)
		}
	}))
	defer mockDaemon.Close()

	config := CreateConfig()
	config.DaemonURL = mockDaemon.URL

	next := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {})
	middleware, err := New(context.Background(), next, config, "test")
	if err != nil {
		t.Fatalf("Failed to create middleware: %v", err)
	}

	wm := middleware.(*WormholeMiddleware)

	result, err := wm.resolveWNS(context.Background(), "mysite.wns")
	if err != nil {
		t.Fatalf("resolveWNS failed: %v", err)
	}

	if result.Address != "mysite.wns" {
		t.Errorf("Expected address 'mysite.wns', got %q", result.Address)
	}
	if result.Code != "test-code-123" {
		t.Errorf("Expected code 'test-code-123', got %q", result.Code)
	}
}

// TestResolveWNSCaching tests that resolved addresses are cached
func TestResolveWNSCaching(t *testing.T) {
	callCount := 0
	mockDaemon := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		callCount++
		if r.URL.Path == "/resolve" && r.Method == http.MethodPost {
			response := ResolveResponse{
				Address: "cached.wns",
				Code:    "cached-code",
				Expires: 1234567890,
			}
			w.Header().Set("Content-Type", "application/json")
			json.NewEncoder(w).Encode(response)
		}
	}))
	defer mockDaemon.Close()

	config := CreateConfig()
	config.DaemonURL = mockDaemon.URL
	config.CacheEnabled = true

	next := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {})
	middleware, err := New(context.Background(), next, config, "test")
	if err != nil {
		t.Fatalf("Failed to create middleware: %v", err)
	}

	wm := middleware.(*WormholeMiddleware)

	// First call should hit the daemon
	_, err = wm.resolveWNS(context.Background(), "cached.wns")
	if err != nil {
		t.Fatalf("First resolveWNS failed: %v", err)
	}

	if callCount != 1 {
		t.Errorf("Expected 1 daemon call, got %d", callCount)
	}

	// Second call should use cache
	_, err = wm.resolveWNS(context.Background(), "cached.wns")
	if err != nil {
		t.Fatalf("Second resolveWNS failed: %v", err)
	}

	if callCount != 1 {
		t.Errorf("Expected still 1 daemon call after cache hit, got %d", callCount)
	}
}

// TestCreateConfig tests default configuration creation
func TestCreateConfig(t *testing.T) {
	config := CreateConfig()

	if config.DaemonURL != "http://localhost:8080" {
		t.Errorf("Expected DaemonURL 'http://localhost:8080', got %q", config.DaemonURL)
	}
	if config.Identity != "default" {
		t.Errorf("Expected Identity 'default', got %q", config.Identity)
	}
	if config.Timeout != "30s" {
		t.Errorf("Expected Timeout '30s', got %q", config.Timeout)
	}
	if config.ConnectTimeout != "10s" {
		t.Errorf("Expected ConnectTimeout '10s', got %q", config.ConnectTimeout)
	}
	if !config.CacheEnabled {
		t.Error("Expected CacheEnabled to be true")
	}
	if config.CacheTTL != "5m" {
		t.Errorf("Expected CacheTTL '5m', got %q", config.CacheTTL)
	}
	if config.MaxConnections != 100 {
		t.Errorf("Expected MaxConnections 100, got %d", config.MaxConnections)
	}
}

// TestNewMiddlewareInvalidTimeout tests error handling for invalid timeout
func TestNewMiddlewareInvalidTimeout(t *testing.T) {
	config := CreateConfig()
	config.Timeout = "invalid"

	next := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {})
	_, err := New(context.Background(), next, config, "test")

	if err == nil {
		t.Error("Expected error for invalid timeout")
	}
}

// TestNewMiddlewareInvalidConnectTimeout tests error handling for invalid connect timeout
func TestNewMiddlewareInvalidConnectTimeout(t *testing.T) {
	config := CreateConfig()
	config.ConnectTimeout = "invalid"

	next := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {})
	_, err := New(context.Background(), next, config, "test")

	if err == nil {
		t.Error("Expected error for invalid connect timeout")
	}
}

// TestNewMiddlewareInvalidCacheTTL tests error handling for invalid cache TTL
func TestNewMiddlewareInvalidCacheTTL(t *testing.T) {
	config := CreateConfig()
	config.CacheEnabled = true
	config.CacheTTL = "invalid"

	next := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {})
	_, err := New(context.Background(), next, config, "test")

	if err == nil {
		t.Error("Expected error for invalid cache TTL")
	}
}

// TestProxyHeaderForwarding tests that headers are properly forwarded
func TestProxyHeaderForwarding(t *testing.T) {
	var receivedHeaders http.Header
	mockDaemon := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		receivedHeaders = r.Header
		w.WriteHeader(http.StatusOK)
	}))
	defer mockDaemon.Close()

	config := CreateConfig()
	config.DaemonURL = mockDaemon.URL

	next := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {})
	middleware, err := New(context.Background(), next, config, "test")
	if err != nil {
		t.Fatalf("Failed to create middleware: %v", err)
	}

	req := httptest.NewRequest(http.MethodGet, "http://mysite.wns/", nil)
	req.Host = "mysite.wns"
	req.Header.Set("X-Custom-Header", "custom-value")
	req.Header.Set("Authorization", "Bearer token123")
	rr := httptest.NewRecorder()

	middleware.ServeHTTP(rr, req)

	// Check that custom headers were forwarded
	if receivedHeaders.Get("X-Custom-Header") != "custom-value" {
		t.Error("X-Custom-Header was not forwarded")
	}
	if receivedHeaders.Get("Authorization") != "Bearer token123" {
		t.Error("Authorization header was not forwarded")
	}
	// Check wormhole-specific headers were added
	if receivedHeaders.Get("X-Wormhole-Original-Host") != "mysite.wns" {
		t.Error("X-Wormhole-Original-Host was not set correctly")
	}
}
