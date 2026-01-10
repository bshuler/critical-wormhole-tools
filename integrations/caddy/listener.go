package wormhole

import (
	"context"
	"fmt"
	"io"
	"net"
	"sync"
	"time"

	"github.com/caddyserver/caddy/v2"
	"go.uber.org/zap"
)

func init() {
	caddy.RegisterNetwork("wormhole", getWormholeListener)
}

// WormholeListener implements net.Listener for wormhole connections.
type WormholeListener struct {
	// Address is the WNS address being listened on
	Address string

	// Identity is the WNS identity keypair
	Identity *Identity

	// RelayURL is the wormhole relay server
	RelayURL string

	// TransitURL is the wormhole transit relay
	TransitURL string

	// DaemonURL is the wh daemon HTTP API endpoint
	DaemonURL string

	// Logger for the listener
	Logger *zap.Logger

	// Internal state
	ctx        context.Context
	cancel     context.CancelFunc
	connChan   chan net.Conn
	closedOnce sync.Once
	mu         sync.Mutex
	running    bool

	// Daemon integration
	daemon     *DaemonClient
	listenerID string
	code       string
}

// Identity represents a WNS identity (Ed25519 keypair).
type Identity struct {
	// Address is the base32-encoded public key hash
	Address string

	// PublicKey is the Ed25519 public key
	PublicKey []byte

	// PrivateKey is the Ed25519 private key (seed)
	PrivateKey []byte

	// ScopedName is an optional scoped name for the address
	ScopedName string
}

// getWormholeListener returns a wormhole listener for the given address.
func getWormholeListener(ctx context.Context, network, address string, cfg net.ListenConfig) (any, error) {
	listener := &WormholeListener{
		Address:    address,
		RelayURL:   "wss://relay.magic-wormhole.io/v1",
		TransitURL: "tcp:transit.magic-wormhole.io:4001",
		DaemonURL:  "http://127.0.0.1:9475",
		connChan:   make(chan net.Conn, 10),
	}
	listener.ctx, listener.cancel = context.WithCancel(ctx)

	// Initialize daemon client
	listener.daemon = NewDaemonClientWithURL(listener.DaemonURL)

	// Start accepting connections in background
	go listener.acceptLoop()

	return listener, nil
}

// Accept waits for and returns the next connection.
func (l *WormholeListener) Accept() (net.Conn, error) {
	select {
	case conn := <-l.connChan:
		return conn, nil
	case <-l.ctx.Done():
		return nil, l.ctx.Err()
	}
}

// Close closes the listener.
func (l *WormholeListener) Close() error {
	l.closedOnce.Do(func() {
		l.cancel()
		close(l.connChan)
	})
	return nil
}

// Addr returns the listener's network address.
func (l *WormholeListener) Addr() net.Addr {
	return &WormholeAddr{
		address: l.Address,
	}
}

// acceptLoop continuously accepts new wormhole connections.
func (l *WormholeListener) acceptLoop() {
	l.mu.Lock()
	l.running = true
	l.mu.Unlock()

	defer func() {
		l.mu.Lock()
		l.running = false
		l.mu.Unlock()
	}()

	// Wait for daemon to be available
	if err := l.daemon.WaitForDaemon(l.ctx, 30*time.Second); err != nil {
		if l.Logger != nil {
			l.Logger.Error("daemon not available", zap.Error(err))
		}
		return
	}

	// Start the wormhole listener via daemon
	resp, err := l.daemon.Listen(l.ctx, &ListenRequest{
		Protocol: "wh-http",
	})
	if err != nil {
		if l.Logger != nil {
			l.Logger.Error("failed to start listener", zap.Error(err))
		}
		return
	}

	l.listenerID = resp.ListenerID
	l.code = resp.Code

	if l.Logger != nil {
		l.Logger.Info("wormhole listener started",
			zap.String("address", l.Address),
			zap.String("code", l.code),
			zap.String("listener_id", l.listenerID),
		)
	}

	// Accept connections loop
	for {
		select {
		case <-l.ctx.Done():
			// Clean up listener on shutdown
			_ = l.daemon.CloseListener(context.Background(), l.listenerID)
			return
		default:
		}

		// Wait for incoming connection (with timeout to check context)
		acceptResp, err := l.daemon.Accept(l.ctx, l.listenerID, 5*time.Second)
		if err != nil {
			if l.Logger != nil {
				l.Logger.Error("accept failed", zap.Error(err))
			}
			return
		}

		// Timeout - no connection yet, continue loop
		if acceptResp.Status == "timeout" || acceptResp.ConnectionID == "" {
			continue
		}

		// Create WormholeConn wrapping the daemon connection
		conn := &WormholeConn{
			localAddr:    l.Addr(),
			remoteAddr:   &WormholeAddr{address: acceptResp.ConnectionID},
			daemon:       l.daemon,
			connectionID: acceptResp.ConnectionID,
			readBuf:      make([]byte, 0),
		}
		conn.ctx, conn.cancel = context.WithCancel(l.ctx)

		if l.Logger != nil {
			l.Logger.Info("accepted wormhole connection",
				zap.String("connection_id", acceptResp.ConnectionID),
			)
		}

		// Send to accept channel
		select {
		case l.connChan <- conn:
		case <-l.ctx.Done():
			_ = conn.Close()
			return
		}
	}
}

// WormholeAddr implements net.Addr for wormhole addresses.
type WormholeAddr struct {
	address string
}

// Network returns "wormhole".
func (a *WormholeAddr) Network() string {
	return "wormhole"
}

// String returns the wormhole address.
func (a *WormholeAddr) String() string {
	return fmt.Sprintf("wh://%s.wns", a.address)
}

// WormholeConn wraps a wormhole connection as a net.Conn.
type WormholeConn struct {
	// LocalAddr is our WNS address
	localAddr net.Addr

	// RemoteAddr is the peer's address (ephemeral code)
	remoteAddr net.Addr

	// Daemon client for data transfer
	daemon       *DaemonClient
	connectionID string

	// Read buffer for partial reads
	readBuf []byte
	readMu  sync.Mutex

	// Context and cancellation
	ctx    context.Context
	cancel context.CancelFunc

	// Close state
	closedOnce sync.Once
	closed     bool
	mu         sync.Mutex

	// Deadlines
	readDeadline  time.Time
	writeDeadline time.Time
	deadlineMu    sync.RWMutex
}

// Read reads data from the connection.
func (c *WormholeConn) Read(b []byte) (int, error) {
	c.mu.Lock()
	if c.closed {
		c.mu.Unlock()
		return 0, net.ErrClosed
	}
	c.mu.Unlock()

	// Check for buffered data first
	c.readMu.Lock()
	if len(c.readBuf) > 0 {
		n := copy(b, c.readBuf)
		c.readBuf = c.readBuf[n:]
		c.readMu.Unlock()
		return n, nil
	}
	c.readMu.Unlock()

	// Calculate timeout from deadline
	c.deadlineMu.RLock()
	deadline := c.readDeadline
	c.deadlineMu.RUnlock()

	var timeout time.Duration = 30 * time.Second
	if !deadline.IsZero() {
		timeout = time.Until(deadline)
		if timeout <= 0 {
			return 0, &timeoutError{op: "read"}
		}
	}

	// Receive data from daemon
	data, err := c.daemon.Recv(c.ctx, c.connectionID, timeout, len(b))
	if err == io.EOF {
		return 0, io.EOF
	}
	if err != nil {
		return 0, err
	}
	if data == nil {
		// Timeout with no data - check if deadline passed
		if !deadline.IsZero() && time.Now().After(deadline) {
			return 0, &timeoutError{op: "read"}
		}
		return 0, nil
	}

	n := copy(b, data)
	// Buffer any excess
	if n < len(data) {
		c.readMu.Lock()
		c.readBuf = append(c.readBuf, data[n:]...)
		c.readMu.Unlock()
	}

	return n, nil
}

// Write writes data to the connection.
func (c *WormholeConn) Write(b []byte) (int, error) {
	c.mu.Lock()
	if c.closed {
		c.mu.Unlock()
		return 0, net.ErrClosed
	}
	c.mu.Unlock()

	// Check write deadline
	c.deadlineMu.RLock()
	deadline := c.writeDeadline
	c.deadlineMu.RUnlock()

	if !deadline.IsZero() && time.Now().After(deadline) {
		return 0, &timeoutError{op: "write"}
	}

	// Create context with deadline if set
	ctx := c.ctx
	if !deadline.IsZero() {
		var cancel context.CancelFunc
		ctx, cancel = context.WithDeadline(c.ctx, deadline)
		defer cancel()
	}

	n, err := c.daemon.Send(ctx, c.connectionID, b)
	if err != nil {
		return 0, err
	}
	return n, nil
}

// Close closes the connection.
func (c *WormholeConn) Close() error {
	c.closedOnce.Do(func() {
		c.mu.Lock()
		c.closed = true
		c.mu.Unlock()
		c.cancel()
		// Close connection on daemon
		_ = c.daemon.CloseConnection(context.Background(), c.connectionID)
	})
	return nil
}

// LocalAddr returns the local network address.
func (c *WormholeConn) LocalAddr() net.Addr {
	return c.localAddr
}

// RemoteAddr returns the remote network address.
func (c *WormholeConn) RemoteAddr() net.Addr {
	return c.remoteAddr
}

// SetDeadline sets the read and write deadlines.
func (c *WormholeConn) SetDeadline(t time.Time) error {
	c.deadlineMu.Lock()
	defer c.deadlineMu.Unlock()
	c.readDeadline = t
	c.writeDeadline = t
	return nil
}

// SetReadDeadline sets the deadline for future Read calls.
func (c *WormholeConn) SetReadDeadline(t time.Time) error {
	c.deadlineMu.Lock()
	defer c.deadlineMu.Unlock()
	c.readDeadline = t
	return nil
}

// SetWriteDeadline sets the deadline for future Write calls.
func (c *WormholeConn) SetWriteDeadline(t time.Time) error {
	c.deadlineMu.Lock()
	defer c.deadlineMu.Unlock()
	c.writeDeadline = t
	return nil
}

// timeoutError represents a timeout error for net.Conn operations.
type timeoutError struct {
	op string
}

func (e *timeoutError) Error() string {
	return fmt.Sprintf("wormhole %s timeout", e.op)
}

func (e *timeoutError) Timeout() bool {
	return true
}

func (e *timeoutError) Temporary() bool {
	return true
}

// Interface guards
var (
	_ net.Listener = (*WormholeListener)(nil)
	_ net.Conn     = (*WormholeConn)(nil)
)
