package wormhole

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"
)

func TestNewDaemonClient(t *testing.T) {
	client := NewDaemonClient()

	if client.BaseURL != "http://127.0.0.1:9475" {
		t.Errorf("NewDaemonClient().BaseURL = %q, want %q", client.BaseURL, "http://127.0.0.1:9475")
	}

	if client.HTTPClient == nil {
		t.Error("NewDaemonClient().HTTPClient should not be nil")
	}

	if client.Timeout != 30*time.Second {
		t.Errorf("NewDaemonClient().Timeout = %v, want %v", client.Timeout, 30*time.Second)
	}
}

func TestNewDaemonClientWithURL(t *testing.T) {
	customURL := "http://localhost:8080"
	client := NewDaemonClientWithURL(customURL)

	if client.BaseURL != customURL {
		t.Errorf("NewDaemonClientWithURL(%q).BaseURL = %q, want %q", customURL, client.BaseURL, customURL)
	}
}

func TestDaemonClient_Status(t *testing.T) {
	// Create a test server
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/status" {
			t.Errorf("Expected path /status, got %s", r.URL.Path)
		}

		status := DaemonStatus{
			Running:     true,
			Version:     "0.5.0",
			Uptime:      3600,
			Connections: 5,
			Port:        9475,
		}
		json.NewEncoder(w).Encode(status)
	}))
	defer server.Close()

	client := NewDaemonClientWithURL(server.URL)
	ctx := context.Background()

	status, err := client.Status(ctx)
	if err != nil {
		t.Fatalf("Status() unexpected error: %v", err)
	}

	if !status.Running {
		t.Error("Status().Running = false, want true")
	}
	if status.Version != "0.5.0" {
		t.Errorf("Status().Version = %q, want %q", status.Version, "0.5.0")
	}
	if status.Connections != 5 {
		t.Errorf("Status().Connections = %d, want %d", status.Connections, 5)
	}
}

func TestDaemonClient_Status_Error(t *testing.T) {
	// Create a test server that returns an error
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusInternalServerError)
	}))
	defer server.Close()

	client := NewDaemonClientWithURL(server.URL)
	ctx := context.Background()

	_, err := client.Status(ctx)
	if err == nil {
		t.Error("Status() expected error for 500 response, got nil")
	}
}

func TestDaemonClient_IsRunning(t *testing.T) {
	tests := []struct {
		name     string
		handler  http.HandlerFunc
		expected bool
	}{
		{
			name: "daemon running",
			handler: func(w http.ResponseWriter, r *http.Request) {
				json.NewEncoder(w).Encode(DaemonStatus{Running: true})
			},
			expected: true,
		},
		{
			name: "daemon not running",
			handler: func(w http.ResponseWriter, r *http.Request) {
				json.NewEncoder(w).Encode(DaemonStatus{Running: false})
			},
			expected: false,
		},
		{
			name: "daemon error",
			handler: func(w http.ResponseWriter, r *http.Request) {
				w.WriteHeader(http.StatusServiceUnavailable)
			},
			expected: false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			server := httptest.NewServer(tt.handler)
			defer server.Close()

			client := NewDaemonClientWithURL(server.URL)
			ctx := context.Background()

			if got := client.IsRunning(ctx); got != tt.expected {
				t.Errorf("IsRunning() = %v, want %v", got, tt.expected)
			}
		})
	}
}

func TestDaemonClient_Resolve(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/resolve" {
			t.Errorf("Expected path /resolve, got %s", r.URL.Path)
		}
		if r.Method != http.MethodPost {
			t.Errorf("Expected POST method, got %s", r.Method)
		}

		var req map[string]string
		json.NewDecoder(r.Body).Decode(&req)

		if req["address"] != "test.wns" {
			t.Errorf("Expected address test.wns, got %s", req["address"])
		}

		json.NewEncoder(w).Encode(ResolveResponse{
			Address: "test.wns",
			Code:    "7-guitar-sunset",
			Expires: time.Now().Add(5 * time.Minute).Unix(),
		})
	}))
	defer server.Close()

	client := NewDaemonClientWithURL(server.URL)
	ctx := context.Background()

	resp, err := client.Resolve(ctx, "test.wns")
	if err != nil {
		t.Fatalf("Resolve() unexpected error: %v", err)
	}

	if resp.Code != "7-guitar-sunset" {
		t.Errorf("Resolve().Code = %q, want %q", resp.Code, "7-guitar-sunset")
	}
}

func TestDaemonClient_Resolve_Error(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		json.NewEncoder(w).Encode(ResolveResponse{
			Error: "address not found",
		})
	}))
	defer server.Close()

	client := NewDaemonClientWithURL(server.URL)
	ctx := context.Background()

	_, err := client.Resolve(ctx, "unknown.wns")
	if err == nil {
		t.Error("Resolve() expected error for unknown address, got nil")
	}
}

func TestDaemonClient_Connect(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/connect" {
			t.Errorf("Expected path /connect, got %s", r.URL.Path)
		}

		json.NewEncoder(w).Encode(ConnectResponse{
			ConnectionID: "conn-abc123",
			Code:         "7-guitar-sunset",
			Status:       "connected",
		})
	}))
	defer server.Close()

	client := NewDaemonClientWithURL(server.URL)
	ctx := context.Background()

	resp, err := client.Connect(ctx, &ConnectRequest{
		Address: "test.wns",
	})
	if err != nil {
		t.Fatalf("Connect() unexpected error: %v", err)
	}

	if resp.ConnectionID != "conn-abc123" {
		t.Errorf("Connect().ConnectionID = %q, want %q", resp.ConnectionID, "conn-abc123")
	}
	if resp.Status != "connected" {
		t.Errorf("Connect().Status = %q, want %q", resp.Status, "connected")
	}
}

func TestDaemonClient_Browse(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// Check that the path is correctly formed
		expectedPath := "/browse/wh%3A%2F%2Ftest.wns/index.html"
		if r.URL.Path != expectedPath && r.URL.RawPath != expectedPath {
			// Also accept the unescaped version
			if r.URL.Path != "/browse/wh://test.wns/index.html" {
				t.Errorf("Expected path %s, got %s (raw: %s)", expectedPath, r.URL.Path, r.URL.RawPath)
			}
		}

		w.Header().Set("Content-Type", "text/html")
		w.Write([]byte("<html><body>Hello</body></html>"))
	}))
	defer server.Close()

	client := NewDaemonClientWithURL(server.URL)
	ctx := context.Background()

	resp, err := client.Browse(ctx, "wh://test.wns", "/index.html")
	if err != nil {
		t.Fatalf("Browse() unexpected error: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		t.Errorf("Browse() status = %d, want %d", resp.StatusCode, http.StatusOK)
	}
}

func TestDaemonClient_WaitForDaemon(t *testing.T) {
	callCount := 0
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		callCount++
		// Respond as running after 2 calls
		if callCount >= 2 {
			json.NewEncoder(w).Encode(DaemonStatus{Running: true})
		} else {
			w.WriteHeader(http.StatusServiceUnavailable)
		}
	}))
	defer server.Close()

	client := NewDaemonClientWithURL(server.URL)
	ctx := context.Background()

	err := client.WaitForDaemon(ctx, 5*time.Second)
	if err != nil {
		t.Fatalf("WaitForDaemon() unexpected error: %v", err)
	}

	if callCount < 2 {
		t.Errorf("WaitForDaemon() callCount = %d, expected at least 2", callCount)
	}
}

func TestDaemonClient_WaitForDaemon_Timeout(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusServiceUnavailable)
	}))
	defer server.Close()

	client := NewDaemonClientWithURL(server.URL)
	ctx := context.Background()

	err := client.WaitForDaemon(ctx, 1*time.Second)
	if err == nil {
		t.Error("WaitForDaemon() expected timeout error, got nil")
	}
}

func TestConnectRequest_JSON(t *testing.T) {
	req := ConnectRequest{
		Address: "test.wns",
		Code:    "7-guitar-sunset",
	}

	data, err := json.Marshal(req)
	if err != nil {
		t.Fatalf("json.Marshal() unexpected error: %v", err)
	}

	var decoded ConnectRequest
	if err := json.Unmarshal(data, &decoded); err != nil {
		t.Fatalf("json.Unmarshal() unexpected error: %v", err)
	}

	if decoded.Address != req.Address {
		t.Errorf("Address = %q, want %q", decoded.Address, req.Address)
	}
	if decoded.Code != req.Code {
		t.Errorf("Code = %q, want %q", decoded.Code, req.Code)
	}
}
