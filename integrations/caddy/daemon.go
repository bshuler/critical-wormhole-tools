package wormhole

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"time"
)

// DaemonClient communicates with the wh daemon HTTP API.
type DaemonClient struct {
	// BaseURL is the daemon's HTTP endpoint (default: http://127.0.0.1:9475)
	BaseURL string

	// HTTPClient is the HTTP client to use
	HTTPClient *http.Client

	// Timeout for requests
	Timeout time.Duration
}

// DaemonStatus represents the daemon's status response.
type DaemonStatus struct {
	Running     bool   `json:"running"`
	Version     string `json:"version"`
	Uptime      int64  `json:"uptime"`
	Connections int    `json:"connections"`
	Port        int    `json:"port"`
}

// ResolveResponse represents a WNS address resolution response.
type ResolveResponse struct {
	Address string `json:"address"`
	Code    string `json:"code"`
	Expires int64  `json:"expires"`
	Error   string `json:"error,omitempty"`
}

// ConnectRequest represents a connection request to the daemon.
type ConnectRequest struct {
	Address string `json:"address"`
	Code    string `json:"code,omitempty"`
}

// ConnectResponse represents a connection response from the daemon.
type ConnectResponse struct {
	ConnectionID string `json:"connection_id"`
	Code         string `json:"code"`
	Status       string `json:"status"`
	Error        string `json:"error,omitempty"`
}

// NewDaemonClient creates a new daemon client with default settings.
func NewDaemonClient() *DaemonClient {
	return &DaemonClient{
		BaseURL: "http://127.0.0.1:9475",
		HTTPClient: &http.Client{
			Timeout: 30 * time.Second,
		},
		Timeout: 30 * time.Second,
	}
}

// NewDaemonClientWithURL creates a daemon client with a custom URL.
func NewDaemonClientWithURL(baseURL string) *DaemonClient {
	client := NewDaemonClient()
	client.BaseURL = baseURL
	return client
}

// Status checks the daemon's status.
func (c *DaemonClient) Status(ctx context.Context) (*DaemonStatus, error) {
	resp, err := c.get(ctx, "/status")
	if err != nil {
		return nil, fmt.Errorf("failed to get daemon status: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("daemon returned status %d", resp.StatusCode)
	}

	var status DaemonStatus
	if err := json.NewDecoder(resp.Body).Decode(&status); err != nil {
		return nil, fmt.Errorf("failed to decode status response: %w", err)
	}

	return &status, nil
}

// IsRunning checks if the daemon is running and responsive.
func (c *DaemonClient) IsRunning(ctx context.Context) bool {
	status, err := c.Status(ctx)
	if err != nil {
		return false
	}
	return status.Running
}

// Resolve resolves a WNS address to an ephemeral wormhole code.
func (c *DaemonClient) Resolve(ctx context.Context, address string) (*ResolveResponse, error) {
	body := map[string]string{"address": address}
	resp, err := c.post(ctx, "/resolve", body)
	if err != nil {
		return nil, fmt.Errorf("failed to resolve address: %w", err)
	}
	defer resp.Body.Close()

	var result ResolveResponse
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, fmt.Errorf("failed to decode resolve response: %w", err)
	}

	if result.Error != "" {
		return nil, fmt.Errorf("resolve error: %s", result.Error)
	}

	return &result, nil
}

// Connect establishes a wormhole connection through the daemon.
func (c *DaemonClient) Connect(ctx context.Context, req *ConnectRequest) (*ConnectResponse, error) {
	resp, err := c.post(ctx, "/connect", req)
	if err != nil {
		return nil, fmt.Errorf("failed to connect: %w", err)
	}
	defer resp.Body.Close()

	var result ConnectResponse
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, fmt.Errorf("failed to decode connect response: %w", err)
	}

	if result.Error != "" {
		return nil, fmt.Errorf("connect error: %s", result.Error)
	}

	return &result, nil
}

// Browse fetches content from a wormhole address.
func (c *DaemonClient) Browse(ctx context.Context, wormholeURL string, path string) (*http.Response, error) {
	// Construct the browse URL
	browseURL := fmt.Sprintf("%s/browse/%s%s", c.BaseURL, url.PathEscape(wormholeURL), path)

	req, err := http.NewRequestWithContext(ctx, http.MethodGet, browseURL, nil)
	if err != nil {
		return nil, fmt.Errorf("failed to create browse request: %w", err)
	}

	return c.HTTPClient.Do(req)
}

// ProxyRequest proxies an HTTP request through the wormhole to a remote address.
func (c *DaemonClient) ProxyRequest(ctx context.Context, wormholeAddr string, r *http.Request) (*http.Response, error) {
	// Build the proxy URL
	proxyPath := fmt.Sprintf("/browse/%s%s", url.PathEscape(wormholeAddr), r.URL.Path)
	if r.URL.RawQuery != "" {
		proxyPath += "?" + r.URL.RawQuery
	}

	proxyURL := c.BaseURL + proxyPath

	// Create the proxy request
	var body io.Reader
	if r.Body != nil {
		bodyBytes, err := io.ReadAll(r.Body)
		if err != nil {
			return nil, fmt.Errorf("failed to read request body: %w", err)
		}
		body = bytes.NewReader(bodyBytes)
	}

	proxyReq, err := http.NewRequestWithContext(ctx, r.Method, proxyURL, body)
	if err != nil {
		return nil, fmt.Errorf("failed to create proxy request: %w", err)
	}

	// Copy headers
	for key, values := range r.Header {
		for _, value := range values {
			proxyReq.Header.Add(key, value)
		}
	}

	// Add wormhole-specific headers
	proxyReq.Header.Set("X-Wormhole-Original-Host", r.Host)
	proxyReq.Header.Set("X-Wormhole-Original-Path", r.URL.Path)

	return c.HTTPClient.Do(proxyReq)
}

// get performs a GET request to the daemon.
func (c *DaemonClient) get(ctx context.Context, path string) (*http.Response, error) {
	url := c.BaseURL + path
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, url, nil)
	if err != nil {
		return nil, err
	}
	return c.HTTPClient.Do(req)
}

// post performs a POST request to the daemon with JSON body.
func (c *DaemonClient) post(ctx context.Context, path string, body interface{}) (*http.Response, error) {
	url := c.BaseURL + path

	jsonBody, err := json.Marshal(body)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request body: %w", err)
	}

	req, err := http.NewRequestWithContext(ctx, http.MethodPost, url, bytes.NewReader(jsonBody))
	if err != nil {
		return nil, err
	}
	req.Header.Set("Content-Type", "application/json")

	return c.HTTPClient.Do(req)
}

// WaitForDaemon waits for the daemon to become available.
func (c *DaemonClient) WaitForDaemon(ctx context.Context, timeout time.Duration) error {
	deadline := time.Now().Add(timeout)

	for time.Now().Before(deadline) {
		if c.IsRunning(ctx) {
			return nil
		}

		select {
		case <-ctx.Done():
			return ctx.Err()
		case <-time.After(500 * time.Millisecond):
			// Continue polling
		}
	}

	return fmt.Errorf("daemon did not become available within %v", timeout)
}
