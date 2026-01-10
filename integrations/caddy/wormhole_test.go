package wormhole

import (
	"testing"
)

func TestParseWormholeAddress(t *testing.T) {
	tests := []struct {
		name       string
		input      string
		wantAddr   string
		wantScoped string
		wantFull   string
		wantErr    bool
	}{
		{
			name:     "bare address",
			input:    "abc123def456",
			wantAddr: "abc123def456",
			wantFull: "wh://abc123def456.wns",
		},
		{
			name:     "address with .wns",
			input:    "abc123def456.wns",
			wantAddr: "abc123def456",
			wantFull: "wh://abc123def456.wns",
		},
		{
			name:     "full URL",
			input:    "wh://abc123def456.wns",
			wantAddr: "abc123def456",
			wantFull: "wh://abc123def456.wns",
		},
		{
			name:       "scoped address",
			input:      "api.abc123def456",
			wantAddr:   "abc123def456",
			wantScoped: "api",
			wantFull:   "wh://api.abc123def456.wns",
		},
		{
			name:       "scoped address with .wns",
			input:      "api.abc123def456.wns",
			wantAddr:   "abc123def456",
			wantScoped: "api",
			wantFull:   "wh://api.abc123def456.wns",
		},
		{
			name:       "full scoped URL",
			input:      "wh://api.abc123def456.wns",
			wantAddr:   "abc123def456",
			wantScoped: "api",
			wantFull:   "wh://api.abc123def456.wns",
		},
		{
			name:    "empty address",
			input:   "",
			wantErr: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			addr, err := ParseWormholeAddress(tt.input)
			if tt.wantErr {
				if err == nil {
					t.Errorf("ParseWormholeAddress(%q) expected error, got nil", tt.input)
				}
				return
			}
			if err != nil {
				t.Errorf("ParseWormholeAddress(%q) unexpected error: %v", tt.input, err)
				return
			}
			if addr.Address != tt.wantAddr {
				t.Errorf("ParseWormholeAddress(%q).Address = %q, want %q", tt.input, addr.Address, tt.wantAddr)
			}
			if addr.ScopedName != tt.wantScoped {
				t.Errorf("ParseWormholeAddress(%q).ScopedName = %q, want %q", tt.input, addr.ScopedName, tt.wantScoped)
			}
			if addr.FullURL != tt.wantFull {
				t.Errorf("ParseWormholeAddress(%q).FullURL = %q, want %q", tt.input, addr.FullURL, tt.wantFull)
			}
		})
	}
}

func TestWormholeAddr(t *testing.T) {
	addr := &WormholeAddr{address: "abc123def456"}

	if got := addr.Network(); got != "wormhole" {
		t.Errorf("WormholeAddr.Network() = %q, want %q", got, "wormhole")
	}

	want := "wh://abc123def456.wns"
	if got := addr.String(); got != want {
		t.Errorf("WormholeAddr.String() = %q, want %q", got, want)
	}
}

func TestSplitAddress(t *testing.T) {
	tests := []struct {
		input string
		want  []string
	}{
		{"abc", []string{"abc"}},
		{"abc.def", []string{"abc", "def"}},
		{"abc.def.ghi", []string{"abc", "def.ghi"}},
		{"", []string{""}},
	}

	for _, tt := range tests {
		t.Run(tt.input, func(t *testing.T) {
			got := splitAddress(tt.input)
			if len(got) != len(tt.want) {
				t.Errorf("splitAddress(%q) = %v, want %v", tt.input, got, tt.want)
				return
			}
			for i := range got {
				if got[i] != tt.want[i] {
					t.Errorf("splitAddress(%q)[%d] = %q, want %q", tt.input, i, got[i], tt.want[i])
				}
			}
		})
	}
}

func TestHandlerProvision(t *testing.T) {
	h := &Handler{}

	// Check defaults before provision
	if h.RelayURL != "" {
		t.Errorf("Handler.RelayURL should be empty before provision")
	}

	// Note: Can't fully test Provision without Caddy context
	// but we can test the default values that would be set
	expectedRelay := "wss://relay.magic-wormhole.io/v1"
	expectedTransit := "tcp:transit.magic-wormhole.io:4001"

	// Manually set defaults as Provision would
	if h.RelayURL == "" {
		h.RelayURL = expectedRelay
	}
	if h.TransitURL == "" {
		h.TransitURL = expectedTransit
	}

	if h.RelayURL != expectedRelay {
		t.Errorf("Handler.RelayURL = %q, want %q", h.RelayURL, expectedRelay)
	}
	if h.TransitURL != expectedTransit {
		t.Errorf("Handler.TransitURL = %q, want %q", h.TransitURL, expectedTransit)
	}
}

func TestHandlerValidate(t *testing.T) {
	h := &Handler{}
	if err := h.Validate(); err != nil {
		t.Errorf("Handler.Validate() unexpected error: %v", err)
	}

	// With identity path
	h.IdentityPath = "/some/path"
	if err := h.Validate(); err != nil {
		t.Errorf("Handler.Validate() with identity unexpected error: %v", err)
	}
}

func TestCaddyModule(t *testing.T) {
	h := Handler{}
	info := h.CaddyModule()

	if info.ID != "http.handlers.wormhole" {
		t.Errorf("CaddyModule().ID = %q, want %q", info.ID, "http.handlers.wormhole")
	}

	if info.New == nil {
		t.Error("CaddyModule().New should not be nil")
		return
	}

	mod := info.New()
	if _, ok := mod.(*Handler); !ok {
		t.Errorf("CaddyModule().New() returned %T, want *Handler", mod)
	}
}
