package wormhole

import (
	"context"
	"fmt"
	"net"
	"sync"

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

	// Logger for the listener
	Logger *zap.Logger

	// Internal state
	ctx        context.Context
	cancel     context.CancelFunc
	connChan   chan net.Conn
	closedOnce sync.Once
	mu         sync.Mutex
	running    bool
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
		connChan:   make(chan net.Conn, 10),
	}
	listener.ctx, listener.cancel = context.WithCancel(ctx)

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

	if l.Logger != nil {
		l.Logger.Info("starting wormhole listener",
			zap.String("address", l.Address),
			zap.String("relay", l.RelayURL),
		)
	}

	// TODO: Implement actual wormhole connection acceptance
	// This will require:
	// 1. Establishing connection to the relay
	// 2. Allocating/publishing codes
	// 3. Waiting for peer connections
	// 4. Performing PAKE key exchange
	// 5. Dilating the connection for subchannel multiplexing
	// 6. Wrapping in net.Conn interface

	// For now, we block until context is cancelled
	<-l.ctx.Done()
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

	// reader/writer for the underlying stream
	reader chan []byte
	writer chan []byte

	// Context and cancellation
	ctx    context.Context
	cancel context.CancelFunc

	// Close state
	closedOnce sync.Once
	closed     bool
	mu         sync.Mutex
}

// Read reads data from the connection.
func (c *WormholeConn) Read(b []byte) (int, error) {
	select {
	case data := <-c.reader:
		n := copy(b, data)
		return n, nil
	case <-c.ctx.Done():
		return 0, c.ctx.Err()
	}
}

// Write writes data to the connection.
func (c *WormholeConn) Write(b []byte) (int, error) {
	c.mu.Lock()
	if c.closed {
		c.mu.Unlock()
		return 0, net.ErrClosed
	}
	c.mu.Unlock()

	select {
	case c.writer <- b:
		return len(b), nil
	case <-c.ctx.Done():
		return 0, c.ctx.Err()
	}
}

// Close closes the connection.
func (c *WormholeConn) Close() error {
	c.closedOnce.Do(func() {
		c.mu.Lock()
		c.closed = true
		c.mu.Unlock()
		c.cancel()
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
func (c *WormholeConn) SetDeadline(t interface{}) error {
	// TODO: Implement deadlines
	return nil
}

// SetReadDeadline sets the deadline for future Read calls.
func (c *WormholeConn) SetReadDeadline(t interface{}) error {
	// TODO: Implement read deadline
	return nil
}

// SetWriteDeadline sets the deadline for future Write calls.
func (c *WormholeConn) SetWriteDeadline(t interface{}) error {
	// TODO: Implement write deadline
	return nil
}

// Interface guard
var _ net.Listener = (*WormholeListener)(nil)
