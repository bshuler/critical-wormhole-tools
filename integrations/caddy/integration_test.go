package wormhole

import (
	"context"
	"encoding/json"
	"io"
	"net"
	"net/http"
	"net/http/httptest"
	"sync"
	"testing"
	"time"
)

// TestIntegration_MockDaemonServer tests the daemon client with a mock HTTP server
func TestIntegration_MockDaemonServer(t *testing.T) {
	// Create mock daemon server
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch r.URL.Path {
		case "/status":
			json.NewEncoder(w).Encode(DaemonStatus{
				Running:     true,
				Version:     "0.4.0",
				Uptime:      100,
				Connections: 0,
				Port:        9475,
			})

		case "/listen":
			json.NewEncoder(w).Encode(ListenResponse{
				ListenerID: "listener-123",
				Code:       "7-guitar-sunset",
				Status:     "listening",
			})

		default:
			http.NotFound(w, r)
		}
	}))
	defer server.Close()

	// Test daemon client against mock server
	client := NewDaemonClientWithURL(server.URL)
	ctx := context.Background()

	// Test status endpoint
	status, err := client.Status(ctx)
	if err != nil {
		t.Fatalf("Status() failed: %v", err)
	}
	if !status.Running {
		t.Error("Expected daemon to be running")
	}
	if status.Version != "0.4.0" {
		t.Errorf("Version = %q, want %q", status.Version, "0.4.0")
	}

	// Test listen endpoint
	listenResp, err := client.Listen(ctx, &ListenRequest{Protocol: "wh-http"})
	if err != nil {
		t.Fatalf("Listen() failed: %v", err)
	}
	if listenResp.Code != "7-guitar-sunset" {
		t.Errorf("Code = %q, want %q", listenResp.Code, "7-guitar-sunset")
	}
}

// TestIntegration_WormholeListener tests the listener's ability to accept connections
func TestIntegration_WormholeListener(t *testing.T) {
	// Mock daemon that simulates accepting a connection
	connReady := make(chan bool, 1)
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch {
		case r.URL.Path == "/status":
			json.NewEncoder(w).Encode(DaemonStatus{
				Running: true,
				Version: "0.4.0",
			})

		case r.URL.Path == "/listen":
			json.NewEncoder(w).Encode(ListenResponse{
				ListenerID: "listener-456",
				Code:       "8-piano-morning",
				Status:     "listening",
			})

		case r.URL.Path == "/accept/listener-456":
			// Wait for signal to return connection
			select {
			case <-connReady:
				json.NewEncoder(w).Encode(AcceptResponse{
					ConnectionID: "conn-789",
					Status:       "connected",
				})
			case <-time.After(100 * time.Millisecond):
				json.NewEncoder(w).Encode(AcceptResponse{
					Status: "timeout",
				})
			}

		default:
			http.NotFound(w, r)
		}
	}))
	defer server.Close()

	// Create listener
	listener := &WormholeListener{
		Address:    "test-address",
		DaemonURL:  server.URL,
		connChan:   make(chan net.Conn, 10),
		RelayURL:   "wss://test.relay",
		TransitURL: "tcp:test.transit:4001",
	}
	listener.ctx, listener.cancel = context.WithCancel(context.Background())
	listener.daemon = NewDaemonClientWithURL(server.URL)

	// Start accept loop in background
	go listener.acceptLoop()

	// Wait for listener to be ready
	time.Sleep(200 * time.Millisecond)

	// Signal that a connection is ready
	connReady <- true

	// Wait for connection to be accepted
	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()

	select {
	case conn := <-listener.connChan:
		if conn == nil {
			t.Fatal("Received nil connection")
		}
		defer conn.Close()

		// Verify connection properties
		if conn.LocalAddr() == nil {
			t.Error("LocalAddr() returned nil")
		}
		if conn.RemoteAddr() == nil {
			t.Error("RemoteAddr() returned nil")
		}

	case <-ctx.Done():
		t.Fatal("Timeout waiting for connection")
	}

	// Clean up
	listener.Close()
}

// TestIntegration_WormholeConn_ReadWrite tests read and write operations
func TestIntegration_WormholeConn_ReadWrite(t *testing.T) {
	// Mock daemon that handles send/recv
	var mu sync.Mutex
	dataBuffer := make([]byte, 0)

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		connID := "conn-write-test"

		switch {
		case r.URL.Path == "/send/"+connID:
			// Store sent data
			data, err := io.ReadAll(r.Body)
			if err != nil {
				http.Error(w, err.Error(), http.StatusInternalServerError)
				return
			}

			mu.Lock()
			dataBuffer = append(dataBuffer, data...)
			mu.Unlock()

			json.NewEncoder(w).Encode(map[string]interface{}{
				"bytes_sent": len(data),
			})

		case r.URL.Path == "/recv/"+connID:
			// Return stored data
			mu.Lock()
			data := make([]byte, len(dataBuffer))
			copy(data, dataBuffer)
			dataBuffer = dataBuffer[:0] // Clear buffer
			mu.Unlock()

			if len(data) == 0 {
				w.WriteHeader(http.StatusRequestTimeout)
				return
			}

			w.Header().Set("Content-Type", "application/octet-stream")
			w.Write(data)

		default:
			http.NotFound(w, r)
		}
	}))
	defer server.Close()

	// Create connection
	conn := &WormholeConn{
		localAddr:    &WormholeAddr{address: "local-addr"},
		remoteAddr:   &WormholeAddr{address: "remote-addr"},
		daemon:       NewDaemonClientWithURL(server.URL),
		connectionID: "conn-write-test",
		readBuf:      make([]byte, 0),
	}
	conn.ctx, conn.cancel = context.WithCancel(context.Background())
	defer conn.Close()

	// Test Write
	testData := []byte("Hello, Wormhole!")
	n, err := conn.Write(testData)
	if err != nil {
		t.Fatalf("Write() failed: %v", err)
	}
	if n != len(testData) {
		t.Errorf("Write() = %d bytes, want %d", n, len(testData))
	}

	// Test Read
	readBuf := make([]byte, 100)
	n, err = conn.Read(readBuf)
	if err != nil {
		t.Fatalf("Read() failed: %v", err)
	}
	if n != len(testData) {
		t.Errorf("Read() = %d bytes, want %d", n, len(testData))
	}
	if string(readBuf[:n]) != string(testData) {
		t.Errorf("Read() data = %q, want %q", readBuf[:n], testData)
	}
}

// TestIntegration_WormholeConn_PartialRead tests handling of partial reads
func TestIntegration_WormholeConn_PartialRead(t *testing.T) {
	// Mock daemon that returns more data than requested buffer size
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/recv/conn-partial" {
			// Return 20 bytes of data
			w.Header().Set("Content-Type", "application/octet-stream")
			w.Write([]byte("12345678901234567890"))
		}
	}))
	defer server.Close()

	conn := &WormholeConn{
		localAddr:    &WormholeAddr{address: "local"},
		remoteAddr:   &WormholeAddr{address: "remote"},
		daemon:       NewDaemonClientWithURL(server.URL),
		connectionID: "conn-partial",
		readBuf:      make([]byte, 0),
	}
	conn.ctx, conn.cancel = context.WithCancel(context.Background())
	defer conn.Close()

	// Read with small buffer (10 bytes)
	buf1 := make([]byte, 10)
	n1, err := conn.Read(buf1)
	if err != nil {
		t.Fatalf("First Read() failed: %v", err)
	}
	if n1 != 10 {
		t.Errorf("First Read() = %d bytes, want 10", n1)
	}

	// Second read should get the buffered remainder
	buf2 := make([]byte, 20)
	n2, err := conn.Read(buf2)
	if err != nil {
		t.Fatalf("Second Read() failed: %v", err)
	}
	if n2 != 10 {
		t.Errorf("Second Read() = %d bytes, want 10", n2)
	}

	// Verify combined data
	combined := string(buf1) + string(buf2[:n2])
	expected := "12345678901234567890"
	if combined != expected {
		t.Errorf("Combined reads = %q, want %q", combined, expected)
	}
}

// TestIntegration_Deadline_Read tests read deadline handling
func TestIntegration_Deadline_Read(t *testing.T) {
	// Mock daemon that delays responses
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/recv/conn-deadline" {
			// Simulate slow response
			time.Sleep(200 * time.Millisecond)
			w.WriteHeader(http.StatusRequestTimeout) // Timeout
		}
	}))
	defer server.Close()

	conn := &WormholeConn{
		localAddr:    &WormholeAddr{address: "local"},
		remoteAddr:   &WormholeAddr{address: "remote"},
		daemon:       NewDaemonClientWithURL(server.URL),
		connectionID: "conn-deadline",
		readBuf:      make([]byte, 0),
	}
	conn.ctx, conn.cancel = context.WithCancel(context.Background())
	defer conn.Close()

	// Set read deadline in the past
	conn.SetReadDeadline(time.Now().Add(-1 * time.Second))

	// Read should fail with timeout error
	buf := make([]byte, 100)
	_, err := conn.Read(buf)
	if err == nil {
		t.Fatal("Read() expected timeout error, got nil")
	}

	// Verify it's a timeout error
	netErr, ok := err.(net.Error)
	if !ok {
		t.Fatalf("Error is not a net.Error: %T", err)
	}
	if !netErr.Timeout() {
		t.Error("Expected timeout error")
	}
}

// TestIntegration_Deadline_Write tests write deadline handling
func TestIntegration_Deadline_Write(t *testing.T) {
	// Mock daemon (doesn't matter for this test)
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {}))
	defer server.Close()

	conn := &WormholeConn{
		localAddr:    &WormholeAddr{address: "local"},
		remoteAddr:   &WormholeAddr{address: "remote"},
		daemon:       NewDaemonClientWithURL(server.URL),
		connectionID: "conn-write-deadline",
		readBuf:      make([]byte, 0),
	}
	conn.ctx, conn.cancel = context.WithCancel(context.Background())
	defer conn.Close()

	// Set write deadline in the past
	conn.SetWriteDeadline(time.Now().Add(-1 * time.Second))

	// Write should fail with timeout error
	_, err := conn.Write([]byte("test data"))
	if err == nil {
		t.Fatal("Write() expected timeout error, got nil")
	}

	// Verify it's a timeout error
	netErr, ok := err.(net.Error)
	if !ok {
		t.Fatalf("Error is not a net.Error: %T", err)
	}
	if !netErr.Timeout() {
		t.Error("Expected timeout error")
	}
}

// TestIntegration_Deadline_Both tests SetDeadline (both read and write)
func TestIntegration_Deadline_Both(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {}))
	defer server.Close()

	conn := &WormholeConn{
		localAddr:    &WormholeAddr{address: "local"},
		remoteAddr:   &WormholeAddr{address: "remote"},
		daemon:       NewDaemonClientWithURL(server.URL),
		connectionID: "conn-both-deadline",
		readBuf:      make([]byte, 0),
	}
	conn.ctx, conn.cancel = context.WithCancel(context.Background())
	defer conn.Close()

	// Set both deadlines
	deadline := time.Now().Add(-1 * time.Second)
	conn.SetDeadline(deadline)

	// Verify both deadlines are set
	conn.deadlineMu.RLock()
	if !conn.readDeadline.Equal(deadline) {
		t.Error("Read deadline not set correctly")
	}
	if !conn.writeDeadline.Equal(deadline) {
		t.Error("Write deadline not set correctly")
	}
	conn.deadlineMu.RUnlock()
}

// TestIntegration_Connection_Lifecycle tests full connection lifecycle
func TestIntegration_Connection_Lifecycle(t *testing.T) {
	var closedConnections []string
	var mu sync.Mutex

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch {
		case r.URL.Path == "/status":
			json.NewEncoder(w).Encode(DaemonStatus{Running: true})

		case r.URL.Path == "/listen":
			json.NewEncoder(w).Encode(ListenResponse{
				ListenerID: "lifecycle-listener",
				Code:       "1-test-code",
				Status:     "listening",
			})

		case r.URL.Path == "/accept/lifecycle-listener":
			json.NewEncoder(w).Encode(AcceptResponse{
				ConnectionID: "lifecycle-conn",
				Status:       "connected",
			})

		case r.Method == http.MethodDelete && r.URL.Path == "/connection/lifecycle-conn":
			mu.Lock()
			closedConnections = append(closedConnections, "lifecycle-conn")
			mu.Unlock()
			w.WriteHeader(http.StatusOK)

		case r.Method == http.MethodDelete && r.URL.Path == "/listener/lifecycle-listener":
			w.WriteHeader(http.StatusOK)

		default:
			http.NotFound(w, r)
		}
	}))
	defer server.Close()

	// Create and start listener
	listener := &WormholeListener{
		Address:    "lifecycle-test",
		DaemonURL:  server.URL,
		connChan:   make(chan net.Conn, 10),
		RelayURL:   "wss://test.relay",
		TransitURL: "tcp:test.transit:4001",
	}
	listener.ctx, listener.cancel = context.WithCancel(context.Background())
	listener.daemon = NewDaemonClientWithURL(server.URL)

	// Start accept loop
	go listener.acceptLoop()
	time.Sleep(100 * time.Millisecond)

	// Accept connection
	ctx, cancel := context.WithTimeout(context.Background(), 1*time.Second)
	defer cancel()

	var conn net.Conn
	select {
	case conn = <-listener.connChan:
		if conn == nil {
			t.Fatal("Received nil connection")
		}
	case <-ctx.Done():
		t.Fatal("Timeout waiting for connection")
	}

	// Close connection
	if err := conn.Close(); err != nil {
		t.Errorf("Close() failed: %v", err)
	}

	// Verify connection was closed on daemon
	time.Sleep(50 * time.Millisecond)
	mu.Lock()
	if len(closedConnections) != 1 || closedConnections[0] != "lifecycle-conn" {
		t.Errorf("Expected connection 'lifecycle-conn' to be closed, got: %v", closedConnections)
	}
	mu.Unlock()

	// Close listener
	if err := listener.Close(); err != nil {
		t.Errorf("Listener.Close() failed: %v", err)
	}
}

// TestIntegration_MultipleConnections tests handling multiple concurrent connections
func TestIntegration_MultipleConnections(t *testing.T) {
	connCounter := 0
	var mu sync.Mutex

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch {
		case r.URL.Path == "/status":
			json.NewEncoder(w).Encode(DaemonStatus{Running: true})

		case r.URL.Path == "/listen":
			json.NewEncoder(w).Encode(ListenResponse{
				ListenerID: "multi-listener",
				Code:       "2-multi-test",
				Status:     "listening",
			})

		case r.URL.Path == "/accept/multi-listener":
			mu.Lock()
			connCounter++
			connID := connCounter
			mu.Unlock()

			if connID <= 3 {
				json.NewEncoder(w).Encode(AcceptResponse{
					ConnectionID: "multi-conn-" + string(rune('0'+connID)),
					Status:       "connected",
				})
			} else {
				json.NewEncoder(w).Encode(AcceptResponse{
					Status: "timeout",
				})
			}

		default:
			http.NotFound(w, r)
		}
	}))
	defer server.Close()

	// Create listener
	listener := &WormholeListener{
		Address:    "multi-test",
		DaemonURL:  server.URL,
		connChan:   make(chan net.Conn, 10),
		RelayURL:   "wss://test.relay",
		TransitURL: "tcp:test.transit:4001",
	}
	listener.ctx, listener.cancel = context.WithCancel(context.Background())
	listener.daemon = NewDaemonClientWithURL(server.URL)
	defer listener.Close()

	// Start accept loop
	go listener.acceptLoop()
	time.Sleep(100 * time.Millisecond)

	// Accept multiple connections
	connections := make([]net.Conn, 0, 3)
	for i := 0; i < 3; i++ {
		ctx, cancel := context.WithTimeout(context.Background(), 1*time.Second)
		select {
		case conn := <-listener.connChan:
			if conn == nil {
				cancel()
				t.Fatalf("Connection %d: received nil", i)
			}
			connections = append(connections, conn)
		case <-ctx.Done():
			cancel()
			t.Fatalf("Connection %d: timeout", i)
		}
		cancel()
	}

	// Verify we got 3 connections
	if len(connections) != 3 {
		t.Errorf("Expected 3 connections, got %d", len(connections))
	}

	// Clean up
	for _, conn := range connections {
		conn.Close()
	}
}
