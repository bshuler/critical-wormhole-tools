// Package wormhole provides a Caddy module for serving HTTP content over
// Magic Wormhole connections.
//
// This module allows Caddy to listen on wormhole addresses (wh://mysite.wns)
// and serve content to clients connecting via the wormhole protocol.
package wormhole

import (
	"fmt"
	"net/http"

	"github.com/caddyserver/caddy/v2"
	"github.com/caddyserver/caddy/v2/caddyconfig/caddyfile"
	"github.com/caddyserver/caddy/v2/caddyconfig/httpcaddyfile"
	"github.com/caddyserver/caddy/v2/modules/caddyhttp"
	"go.uber.org/zap"
)

func init() {
	caddy.RegisterModule(Handler{})
	httpcaddyfile.RegisterHandlerDirective("wormhole", parseCaddyfile)
}

// Handler implements an HTTP handler that serves content over wormhole.
type Handler struct {
	// IdentityPath is the path to the WNS identity key file.
	// If empty, a new ephemeral identity is created.
	IdentityPath string `json:"identity,omitempty"`

	// Name is the scoped name for the WNS address.
	// Results in addresses like wh://name.address.wns
	Name string `json:"name,omitempty"`

	// RelayURL is the wormhole relay server URL.
	// Defaults to the public magic-wormhole relay.
	RelayURL string `json:"relay_url,omitempty"`

	// TransitURL is the wormhole transit relay URL.
	// Defaults to the public transit relay.
	TransitURL string `json:"transit_url,omitempty"`

	// DaemonURL is the wh daemon HTTP API endpoint.
	// Defaults to http://127.0.0.1:9475
	DaemonURL string `json:"daemon_url,omitempty"`

	logger *zap.Logger
	daemon *DaemonClient
}

// CaddyModule returns the Caddy module information.
func (Handler) CaddyModule() caddy.ModuleInfo {
	return caddy.ModuleInfo{
		ID:  "http.handlers.wormhole",
		New: func() caddy.Module { return new(Handler) },
	}
}

// Provision sets up the handler.
func (h *Handler) Provision(ctx caddy.Context) error {
	h.logger = ctx.Logger(h)

	// Set defaults
	if h.RelayURL == "" {
		h.RelayURL = "wss://relay.magic-wormhole.io/v1"
	}
	if h.TransitURL == "" {
		h.TransitURL = "tcp:transit.magic-wormhole.io:4001"
	}
	if h.DaemonURL == "" {
		h.DaemonURL = "http://127.0.0.1:9475"
	}

	// Initialize daemon client
	h.daemon = NewDaemonClientWithURL(h.DaemonURL)

	h.logger.Info("wormhole handler provisioned",
		zap.String("identity", h.IdentityPath),
		zap.String("name", h.Name),
		zap.String("relay", h.RelayURL),
		zap.String("daemon", h.DaemonURL),
	)

	return nil
}

// Validate ensures the handler is properly configured.
func (h *Handler) Validate() error {
	// Identity path is optional - we'll create an ephemeral one if not specified
	return nil
}

// ServeHTTP implements caddyhttp.MiddlewareHandler.
func (h Handler) ServeHTTP(w http.ResponseWriter, r *http.Request, next caddyhttp.Handler) error {
	// Add wormhole-specific headers
	w.Header().Set("X-Wormhole-Handler", "active")
	if h.Name != "" {
		w.Header().Set("X-Wormhole-Name", h.Name)
	}

	// Log the request
	h.logger.Debug("handling wormhole request",
		zap.String("path", r.URL.Path),
		zap.String("method", r.Method),
	)

	// Pass to the next handler (file_server, reverse_proxy, etc.)
	return next.ServeHTTP(w, r)
}

// UnmarshalCaddyfile implements caddyfile.Unmarshaler.
func (h *Handler) UnmarshalCaddyfile(d *caddyfile.Dispenser) error {
	for d.Next() {
		for d.NextBlock(0) {
			switch d.Val() {
			case "identity":
				if !d.NextArg() {
					return d.ArgErr()
				}
				h.IdentityPath = d.Val()

			case "name":
				if !d.NextArg() {
					return d.ArgErr()
				}
				h.Name = d.Val()

			case "relay":
				if !d.NextArg() {
					return d.ArgErr()
				}
				h.RelayURL = d.Val()

			case "transit":
				if !d.NextArg() {
					return d.ArgErr()
				}
				h.TransitURL = d.Val()

			case "daemon":
				if !d.NextArg() {
					return d.ArgErr()
				}
				h.DaemonURL = d.Val()

			default:
				return d.Errf("unrecognized subdirective: %s", d.Val())
			}
		}
	}
	return nil
}

// parseCaddyfile sets up the handler from Caddyfile tokens.
func parseCaddyfile(h httpcaddyfile.Helper) (caddyhttp.MiddlewareHandler, error) {
	var handler Handler
	err := handler.UnmarshalCaddyfile(h.Dispenser)
	return handler, err
}

// Interface guards
var (
	_ caddy.Module                = (*Handler)(nil)
	_ caddy.Provisioner           = (*Handler)(nil)
	_ caddy.Validator             = (*Handler)(nil)
	_ caddyhttp.MiddlewareHandler = (*Handler)(nil)
	_ caddyfile.Unmarshaler       = (*Handler)(nil)
)

// WormholeAddress represents a parsed wormhole address.
type WormholeAddress struct {
	Address    string // The base32-encoded address
	ScopedName string // Optional scoped name (e.g., "api" in api.addr.wns)
	FullURL    string // Full URL (wh://api.addr.wns)
}

// ParseWormholeAddress parses a wormhole URL into its components.
func ParseWormholeAddress(url string) (*WormholeAddress, error) {
	// Strip wh:// prefix if present
	if len(url) > 5 && url[:5] == "wh://" {
		url = url[5:]
	}

	// Strip .wns suffix if present
	if len(url) > 4 && url[len(url)-4:] == ".wns" {
		url = url[:len(url)-4]
	}

	// Check for scoped name (name.address format)
	parts := splitAddress(url)
	if len(parts) == 0 {
		return nil, fmt.Errorf("invalid wormhole address: %s", url)
	}

	addr := &WormholeAddress{}
	if len(parts) == 1 {
		addr.Address = parts[0]
	} else {
		addr.ScopedName = parts[0]
		addr.Address = parts[1]
	}

	// Reconstruct full URL
	if addr.ScopedName != "" {
		addr.FullURL = fmt.Sprintf("wh://%s.%s.wns", addr.ScopedName, addr.Address)
	} else {
		addr.FullURL = fmt.Sprintf("wh://%s.wns", addr.Address)
	}

	return addr, nil
}

// splitAddress splits an address on the first dot.
func splitAddress(s string) []string {
	for i := 0; i < len(s); i++ {
		if s[i] == '.' {
			return []string{s[:i], s[i+1:]}
		}
	}
	return []string{s}
}
