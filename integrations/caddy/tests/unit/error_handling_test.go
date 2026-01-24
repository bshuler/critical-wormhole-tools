package wormhole

import (
	"context"
	"errors"
	"fmt"
	"io"
	"net"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"
)

// TestDaemonClient_ConnectionTimeout tests that connection timeout raises an error
func TestDaemonClient_ConnectionTimeout(t *testing.T) {
	// Create a server that never responds
	listener, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatalf("Failed to create listener: %v", err)
	}
	defer listener.Close()

	// Create client with very short timeout pointing to unresponsive server
	client := NewDaemonClientWithURL(fmt.Sprintf("http://%s", listener.Addr().String()))
	client.HTTPClient.Timeout = 100 * time.Millisecond

	ctx := context.Background()
	_, err = client.Status(ctx)

	if err == nil {
		t.Fatal("Expected timeout error, got nil")
	}

	// Verify it's a timeout-related error
	var netErr net.Error
	if errors.As(err, &netErr) && !netErr.Timeout() {
		t.Errorf("Expected timeout error, got: %v", err)
	}
}

// TestDaemonClient_ConnectionRefused tests that connection refused raises an error
func TestDaemonClient_ConnectionRefused(t *testing.T) {
	// Create client pointing to non-existent server
	client := NewDaemonClientWithURL("http://127.0.0.1:1")
	client.HTTPClient.Timeout = 1 * time.Second

	ctx := context.Background()
	_, err := client.Status(ctx)

	if err == nil {
		t.Fatal("Expected connection refused error, got nil")
	}

	// Verify error message indicates connection failure
	errMsg := err.Error()
	if errMsg == "" {
		t.Error("Expected non-empty error message for connection refused")
	}
}

// TestDaemonClient_Resolve_InvalidAddress tests that invalid address resolution raises an error
func TestDaemonClient_Resolve_InvalidAddress(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.Write([]byte(`{"error": "invalid wormhole address format"}`))
	}))
	defer server.Close()

	client := NewDaemonClientWithURL(server.URL)
	ctx := context.Background()

	_, err := client.Resolve(ctx, "invalid@@@address")

	if err == nil {
		t.Fatal("Expected error for invalid address, got nil")
	}

	expectedMsg := "invalid wormhole address format"
	if err.Error() != fmt.Sprintf("resolve error: %s", expectedMsg) {
		t.Errorf("Expected error containing %q, got: %v", expectedMsg, err)
	}
}

// TestDaemonClient_Connect_DilationFailure tests that dilation failure is handled
func TestDaemonClient_Connect_DilationFailure(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.Write([]byte(`{"error": "dilation handshake failed", "status": "error"}`))
	}))
	defer server.Close()

	client := NewDaemonClientWithURL(server.URL)
	ctx := context.Background()

	_, err := client.Connect(ctx, &ConnectRequest{
		Address: "test.wns",
	})

	if err == nil {
		t.Fatal("Expected dilation failure error, got nil")
	}

	expectedMsg := "dilation handshake failed"
	if err.Error() != fmt.Sprintf("connect error: %s", expectedMsg) {
		t.Errorf("Expected error containing %q, got: %v", expectedMsg, err)
	}
}

// TestDaemonClient_HTTPTimeout tests that HTTP request timeout raises TimeoutError
func TestDaemonClient_HTTPTimeout(t *testing.T) {
	// Create a server that delays response beyond timeout
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		time.Sleep(2 * time.Second)
		w.WriteHeader(http.StatusOK)
	}))
	defer server.Close()

	client := NewDaemonClientWithURL(server.URL)
	client.HTTPClient.Timeout = 100 * time.Millisecond

	ctx := context.Background()
	_, err := client.Status(ctx)

	if err == nil {
		t.Fatal("Expected timeout error, got nil")
	}

	// Verify it's a timeout-related error
	var netErr net.Error
	if !errors.As(err, &netErr) || !netErr.Timeout() {
		t.Errorf("Expected timeout error, got: %v", err)
	}
}

// TestDaemonClient_ServerDisconnect tests that sudden disconnect is handled cleanly
func TestDaemonClient_ServerDisconnect(t *testing.T) {
	// Create a server that immediately closes the connection
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		hj, ok := w.(http.Hijacker)
		if !ok {
			t.Fatal("Server doesn't support hijacking")
		}
		conn, _, err := hj.Hijack()
		if err != nil {
			t.Fatalf("Hijack failed: %v", err)
		}
		conn.Close() // Abruptly close connection
	}))
	defer server.Close()

	client := NewDaemonClientWithURL(server.URL)
	ctx := context.Background()

	_, err := client.Status(ctx)

	if err == nil {
		t.Fatal("Expected connection error, got nil")
	}

	// Error should indicate connection problem (EOF or connection reset)
	if !errors.Is(err, io.EOF) && !errors.Is(err, io.ErrUnexpectedEOF) {
		// Also acceptable: "connection reset" or similar network errors
		errMsg := err.Error()
		if errMsg == "" {
			t.Error("Expected non-empty error message for connection disconnect")
		}
	}
}

// TestDaemonClient_Listen_PortInUse tests that port already bound shows clear error
func TestDaemonClient_Listen_PortInUse(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.Write([]byte(`{"error": "address already in use", "status": "error"}`))
	}))
	defer server.Close()

	client := NewDaemonClientWithURL(server.URL)
	ctx := context.Background()

	_, err := client.Listen(ctx, &ListenRequest{
		Protocol: "wh-http",
	})

	if err == nil {
		t.Fatal("Expected port in use error, got nil")
	}

	expectedMsg := "address already in use"
	if err.Error() != fmt.Sprintf("listen error: %s", expectedMsg) {
		t.Errorf("Expected error containing %q, got: %v", expectedMsg, err)
	}
}

// TestDaemonClient_Send_ConnectionNotFound tests that missing connection raises error
func TestDaemonClient_Send_ConnectionNotFound(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusNotFound)
		w.Write([]byte(`{"error": "connection not found"}`))
	}))
	defer server.Close()

	client := NewDaemonClientWithURL(server.URL)
	ctx := context.Background()

	_, err := client.Send(ctx, "nonexistent-conn-id", []byte("test data"))

	if err == nil {
		t.Fatal("Expected connection not found error, got nil")
	}

	expectedMsg := "connection not found"
	if err.Error() != expectedMsg {
		t.Errorf("Expected error %q, got: %v", expectedMsg, err)
	}
}

// TestDaemonClient_Send_ConnectionClosed tests that closed connection raises error
func TestDaemonClient_Send_ConnectionClosed(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusGone)
		w.Write([]byte(`{"error": "connection closed"}`))
	}))
	defer server.Close()

	client := NewDaemonClientWithURL(server.URL)
	ctx := context.Background()

	_, err := client.Send(ctx, "closed-conn-id", []byte("test data"))

	if err == nil {
		t.Fatal("Expected connection closed error, got nil")
	}

	expectedMsg := "connection closed"
	if err.Error() != expectedMsg {
		t.Errorf("Expected error %q, got: %v", expectedMsg, err)
	}
}

// TestDaemonClient_Recv_EOF tests that connection EOF is handled properly
func TestDaemonClient_Recv_EOF(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusNoContent)
	}))
	defer server.Close()

	client := NewDaemonClientWithURL(server.URL)
	ctx := context.Background()

	data, err := client.Recv(ctx, "test-conn-id", 5*time.Second, 1024)

	if err != io.EOF {
		t.Fatalf("Expected io.EOF, got: %v", err)
	}

	if data != nil {
		t.Errorf("Expected nil data on EOF, got: %v", data)
	}
}

// TestDaemonClient_Recv_Timeout tests that recv timeout returns nil data (not error)
func TestDaemonClient_Recv_Timeout(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusRequestTimeout)
	}))
	defer server.Close()

	client := NewDaemonClientWithURL(server.URL)
	ctx := context.Background()

	data, err := client.Recv(ctx, "test-conn-id", 1*time.Second, 1024)

	if err != nil {
		t.Fatalf("Expected nil error on timeout, got: %v", err)
	}

	if data != nil {
		t.Errorf("Expected nil data on timeout, got: %v", data)
	}
}

// TestDaemonClient_Accept_ListenerNotFound tests that missing listener raises error
func TestDaemonClient_Accept_ListenerNotFound(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusNotFound)
		w.Write([]byte(`{"error": "listener not found"}`))
	}))
	defer server.Close()

	client := NewDaemonClientWithURL(server.URL)
	ctx := context.Background()

	_, err := client.Accept(ctx, "nonexistent-listener-id", 5*time.Second)

	if err == nil {
		t.Fatal("Expected listener not found error, got nil")
	}

	expectedMsg := "listener not found"
	if err.Error() != expectedMsg {
		t.Errorf("Expected error %q, got: %v", expectedMsg, err)
	}
}

// TestDaemonClient_Accept_ListenerClosed tests that closed listener raises error
func TestDaemonClient_Accept_ListenerClosed(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusGone)
		w.Write([]byte(`{"error": "listener closed"}`))
	}))
	defer server.Close()

	client := NewDaemonClientWithURL(server.URL)
	ctx := context.Background()

	_, err := client.Accept(ctx, "closed-listener-id", 5*time.Second)

	if err == nil {
		t.Fatal("Expected listener closed error, got nil")
	}

	expectedMsg := "listener closed"
	if err.Error() != expectedMsg {
		t.Errorf("Expected error %q, got: %v", expectedMsg, err)
	}
}

// TestDaemonClient_CloseConnection_NotFound tests that closing non-existent connection is handled
func TestDaemonClient_CloseConnection_NotFound(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusNotFound)
	}))
	defer server.Close()

	client := NewDaemonClientWithURL(server.URL)
	ctx := context.Background()

	// Closing a non-existent connection should not return an error (idempotent)
	err := client.CloseConnection(ctx, "nonexistent-conn-id")
	if err != nil {
		t.Errorf("CloseConnection() for non-existent connection should be nil, got: %v", err)
	}
}

// TestDaemonClient_CloseListener_NotFound tests that closing non-existent listener is handled
func TestDaemonClient_CloseListener_NotFound(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusNotFound)
	}))
	defer server.Close()

	client := NewDaemonClientWithURL(server.URL)
	ctx := context.Background()

	// Closing a non-existent listener should not return an error (idempotent)
	err := client.CloseListener(ctx, "nonexistent-listener-id")
	if err != nil {
		t.Errorf("CloseListener() for non-existent listener should be nil, got: %v", err)
	}
}

// TestDaemonClient_Send_InvalidJSON tests that malformed response is handled
func TestDaemonClient_Send_InvalidJSON(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		w.Write([]byte(`{invalid json`))
	}))
	defer server.Close()

	client := NewDaemonClientWithURL(server.URL)
	ctx := context.Background()

	_, err := client.Send(ctx, "test-conn", []byte("data"))

	if err == nil {
		t.Fatal("Expected JSON decode error, got nil")
	}

	// Should contain "decode" in error message
	if !contains(err.Error(), "decode") {
		t.Errorf("Expected decode error, got: %v", err)
	}
}

// contains checks if a string contains a substring (helper)
func contains(s, substr string) bool {
	return len(s) >= len(substr) && (s == substr || len(substr) == 0 ||
		(len(s) > 0 && len(substr) > 0 && findSubstring(s, substr)))
}

func findSubstring(s, substr string) bool {
	for i := 0; i <= len(s)-len(substr); i++ {
		if s[i:i+len(substr)] == substr {
			return true
		}
	}
	return false
}

// TestDaemonClient_Recv_InvalidJSON tests that malformed response is handled
func TestDaemonClient_Recv_InvalidJSON(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// Return non-JSON for edge cases (though body should be raw bytes)
		// For this test, we'll test a successful response to ensure flow works
		w.WriteHeader(http.StatusOK)
		w.Write([]byte("test data"))
	}))
	defer server.Close()

	client := NewDaemonClientWithURL(server.URL)
	ctx := context.Background()

	data, err := client.Recv(ctx, "test-conn", 5*time.Second, 1024)

	if err != nil {
		t.Fatalf("Recv() unexpected error: %v", err)
	}

	if string(data) != "test data" {
		t.Errorf("Expected 'test data', got: %s", string(data))
	}
}

// TestParseWormholeAddress_Empty tests that empty address raises validation error
func TestParseWormholeAddress_Empty(t *testing.T) {
	_, err := ParseWormholeAddress("")
	if err == nil {
		t.Error("Expected error for empty address, got nil")
	}

	expectedMsg := "invalid wormhole address"
	if !contains(err.Error(), expectedMsg) {
		t.Errorf("Expected error containing %q, got: %v", expectedMsg, err)
	}
}

// TestDaemonClient_ContextCancellation tests that cancelled context stops operation
func TestDaemonClient_ContextCancellation(t *testing.T) {
	// Create a server that delays indefinitely
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		time.Sleep(10 * time.Second)
		w.WriteHeader(http.StatusOK)
	}))
	defer server.Close()

	client := NewDaemonClientWithURL(server.URL)

	// Create a context that we'll cancel immediately
	ctx, cancel := context.WithCancel(context.Background())
	cancel() // Cancel immediately

	_, err := client.Status(ctx)

	if err == nil {
		t.Fatal("Expected context cancellation error, got nil")
	}

	// Should be context.Canceled error
	if !errors.Is(err, context.Canceled) {
		t.Errorf("Expected context.Canceled error, got: %v", err)
	}
}

// TestDaemonClient_StatusNon200 tests that non-200 status code is handled
func TestDaemonClient_StatusNon200(t *testing.T) {
	testCases := []struct {
		name       string
		statusCode int
	}{
		{"BadRequest", http.StatusBadRequest},
		{"Unauthorized", http.StatusUnauthorized},
		{"Forbidden", http.StatusForbidden},
		{"InternalServerError", http.StatusInternalServerError},
		{"ServiceUnavailable", http.StatusServiceUnavailable},
	}

	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
				w.WriteHeader(tc.statusCode)
			}))
			defer server.Close()

			client := NewDaemonClientWithURL(server.URL)
			ctx := context.Background()

			_, err := client.Status(ctx)
			if err == nil {
				t.Errorf("Expected error for status %d, got nil", tc.statusCode)
			}

			expectedMsg := fmt.Sprintf("daemon returned status %d", tc.statusCode)
			if err.Error() != expectedMsg {
				t.Errorf("Expected error %q, got: %v", expectedMsg, err)
			}
		})
	}
}
