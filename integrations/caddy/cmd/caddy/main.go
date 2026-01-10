// Command caddy is a custom Caddy build with the wormhole module included.
//
// Build with:
//
//	go build -o caddy ./cmd/caddy
//
// Or use xcaddy:
//
//	xcaddy build --with github.com/bshuler/wormhole-tools/integrations/caddy
package main

import (
	caddycmd "github.com/caddyserver/caddy/v2/cmd"

	// Standard Caddy modules
	_ "github.com/caddyserver/caddy/v2/modules/standard"

	// Wormhole module
	_ "github.com/bshuler/wormhole-tools/integrations/caddy"
)

func main() {
	caddycmd.Main()
}
