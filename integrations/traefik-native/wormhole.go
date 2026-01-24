// Package traefik_wormhole_plugin provides a Traefik middleware for WNS resolution
package traefik_wormhole_plugin

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"net/url"
	"strings"
	"time"

	"github.com/patrickmn/go-cache"
)

// Config holds the plugin configuration
type Config struct {
	DaemonURL      string `json:"daemonURL,omitempty"`
	Identity       string `json:"identity,omitempty"`
	RelayURL       string `json:"relayURL,omitempty"`
	Timeout        string `json:"timeout,omitempty"`
	ConnectTimeout string `json:"connectTimeout,omitempty"`
	CacheEnabled   bool   `json:"cacheEnabled,omitempty"`
	CacheTTL       string `json:"cacheTTL,omitempty"`
	MaxConnections int    `json:"maxConnections,omitempty"`
	Debug          bool   `json:"debug,omitempty"`
}

// CreateConfig creates the default plugin configuration
func CreateConfig() *Config {
	return &Config{
		DaemonURL:      "http://localhost:8080",
		Identity:       "default",
		Timeout:        "30s",
		ConnectTimeout: "10s",
		CacheEnabled:   true,
		CacheTTL:       "5m",
		MaxConnections: 100,
		Debug:          false,
	}
}

// ResolveResponse represents a WNS address resolution response from the daemon.
type ResolveResponse struct {
	Address string `json:"address"`
	Code    string `json:"code"`
	Expires int64  `json:"expires"`
	Error   string `json:"error,omitempty"`
}

// WormholeMiddleware is the main plugin middleware
type WormholeMiddleware struct {
	next           http.Handler
	name           string
	daemonURL      string
	identity       string
	relayURL       string
	timeout        time.Duration
	connectTimeout time.Duration
	cache          *cache.Cache
	debug          bool
	httpClient     *http.Client
}

// New creates a new WormholeMiddleware instance
func New(ctx context.Context, next http.Handler, config *Config, name string) (http.Handler, error) {
	timeout, err := time.ParseDuration(config.Timeout)
	if err != nil {
		return nil, fmt.Errorf("invalid timeout: %w", err)
	}

	connectTimeout, err := time.ParseDuration(config.ConnectTimeout)
	if err != nil {
		return nil, fmt.Errorf("invalid connectTimeout: %w", err)
	}

	var c *cache.Cache
	if config.CacheEnabled {
		cacheTTL, err := time.ParseDuration(config.CacheTTL)
		if err != nil {
			return nil, fmt.Errorf("invalid cacheTTL: %w", err)
		}
		c = cache.New(cacheTTL, cacheTTL*2)
	}

	return &WormholeMiddleware{
		next:           next,
		name:           name,
		daemonURL:      config.DaemonURL,
		identity:       config.Identity,
		relayURL:       config.RelayURL,
		timeout:        timeout,
		connectTimeout: connectTimeout,
		cache:          c,
		debug:          config.Debug,
		httpClient: &http.Client{
			Timeout: timeout,
		},
	}, nil
}

// ServeHTTP implements the http.Handler interface
func (w *WormholeMiddleware) ServeHTTP(rw http.ResponseWriter, req *http.Request) {
	// Check if request is for a wh:// URL
	host := req.Host
	if host == "" {
		host = req.Header.Get("Host")
	}

	// Parse for wh:// scheme or .wns domain
	if !w.isWormholeRequest(host) {
		w.next.ServeHTTP(rw, req)
		return
	}

	if w.debug {
		log.Printf("[wormhole] Processing request for host: %s", host)
	}

	// Extract WNS name from host
	wnsName := w.extractWNSName(host)
	if wnsName == "" {
		http.Error(rw, "Invalid wormhole address", http.StatusBadRequest)
		return
	}

	if w.debug {
		log.Printf("[wormhole] Resolved WNS name: %s", wnsName)
	}

	// Proxy the request through the wormhole daemon
	w.proxyToPeer(rw, req, wnsName)
}

// isWormholeRequest checks if the request should be handled by wormhole
func (w *WormholeMiddleware) isWormholeRequest(host string) bool {
	// Check for wh:// prefix in Host header
	if strings.HasPrefix(host, "wh://") {
		return true
	}
	// Check for .wns TLD suffix (remove port if present)
	hostOnly := host
	if idx := strings.LastIndex(host, ":"); idx != -1 {
		hostOnly = host[:idx]
	}
	if strings.HasSuffix(hostOnly, ".wns") {
		return true
	}
	return false
}

// extractWNSName extracts the WNS name from the host
func (w *WormholeMiddleware) extractWNSName(host string) string {
	// Handle wh:// prefix
	if strings.HasPrefix(host, "wh://") {
		name := strings.TrimPrefix(host, "wh://")
		// Remove any trailing path
		if idx := strings.Index(name, "/"); idx != -1 {
			name = name[:idx]
		}
		// Remove port if present
		if idx := strings.LastIndex(name, ":"); idx != -1 {
			name = name[:idx]
		}
		return name
	}

	// Handle .wns suffix
	hostOnly := host
	if idx := strings.LastIndex(host, ":"); idx != -1 {
		hostOnly = host[:idx]
	}
	if strings.HasSuffix(hostOnly, ".wns") {
		return hostOnly
	}

	return ""
}

// resolveWNS resolves a WNS name to a peer connection via the daemon API
func (w *WormholeMiddleware) resolveWNS(ctx context.Context, name string) (*ResolveResponse, error) {
	// Check cache
	if w.cache != nil {
		if cached, found := w.cache.Get(name); found {
			if w.debug {
				log.Printf("[wormhole] Cache hit for %s", name)
			}
			return cached.(*ResolveResponse), nil
		}
	}

	// Query daemon API: POST /resolve
	body := map[string]string{"address": name}
	jsonBody, err := json.Marshal(body)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal resolve request: %w", err)
	}

	resolveURL := w.daemonURL + "/resolve"
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, resolveURL, bytes.NewReader(jsonBody))
	if err != nil {
		return nil, fmt.Errorf("failed to create resolve request: %w", err)
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := w.httpClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("failed to resolve address: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		bodyBytes, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("daemon returned status %d: %s", resp.StatusCode, string(bodyBytes))
	}

	var result ResolveResponse
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, fmt.Errorf("failed to decode resolve response: %w", err)
	}

	if result.Error != "" {
		return nil, fmt.Errorf("resolve error: %s", result.Error)
	}

	// Cache the result
	if w.cache != nil {
		w.cache.SetDefault(name, &result)
		if w.debug {
			log.Printf("[wormhole] Cached resolution for %s", name)
		}
	}

	return &result, nil
}

// proxyToPeer forwards the request through the wormhole daemon to the resolved peer
func (w *WormholeMiddleware) proxyToPeer(rw http.ResponseWriter, req *http.Request, wormholeAddr string) {
	ctx, cancel := context.WithTimeout(req.Context(), w.timeout)
	defer cancel()

	// Build the proxy URL using the daemon's /browse endpoint
	proxyPath := fmt.Sprintf("/browse/%s%s", url.PathEscape(wormholeAddr), req.URL.Path)
	if req.URL.RawQuery != "" {
		proxyPath += "?" + req.URL.RawQuery
	}
	proxyURL := w.daemonURL + proxyPath

	if w.debug {
		log.Printf("[wormhole] Proxying to: %s", proxyURL)
	}

	// Read the original request body
	var body io.Reader
	if req.Body != nil {
		bodyBytes, err := io.ReadAll(req.Body)
		if err != nil {
			http.Error(rw, fmt.Sprintf("Failed to read request body: %v", err), http.StatusInternalServerError)
			return
		}
		body = bytes.NewReader(bodyBytes)
	}

	// Create the proxy request
	proxyReq, err := http.NewRequestWithContext(ctx, req.Method, proxyURL, body)
	if err != nil {
		http.Error(rw, fmt.Sprintf("Failed to create proxy request: %v", err), http.StatusInternalServerError)
		return
	}

	// Copy headers from original request
	for key, values := range req.Header {
		for _, value := range values {
			proxyReq.Header.Add(key, value)
		}
	}

	// Add wormhole-specific headers
	proxyReq.Header.Set("X-Wormhole-Original-Host", req.Host)
	proxyReq.Header.Set("X-Wormhole-Original-Path", req.URL.Path)
	proxyReq.Header.Set("X-Forwarded-For", req.RemoteAddr)

	// Execute the proxy request
	resp, err := w.httpClient.Do(proxyReq)
	if err != nil {
		if w.debug {
			log.Printf("[wormhole] Proxy request failed: %v", err)
		}
		http.Error(rw, fmt.Sprintf("Wormhole connection failed: %v", err), http.StatusBadGateway)
		return
	}
	defer resp.Body.Close()

	// Copy response headers
	for key, values := range resp.Header {
		for _, value := range values {
			rw.Header().Add(key, value)
		}
	}

	// Write status code
	rw.WriteHeader(resp.StatusCode)

	// Stream response body
	if _, err := io.Copy(rw, resp.Body); err != nil {
		if w.debug {
			log.Printf("[wormhole] Error streaming response: %v", err)
		}
		// Can't write error at this point, headers already sent
	}
}
