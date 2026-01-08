# Wormhole Browser Extension

Browse websites hosted on wormhole addresses (`wh://`) directly in your browser. This extension implements the complete Magic Wormhole protocol in JavaScript, requiring no external daemon or CLI tools.

## Features

- **Standalone Implementation**: Full wormhole protocol in JavaScript - no daemon required
- **Navigate to wh:// URLs**: Type `wh://address.wns` in the address bar
- **WNS Support**: Persistent addresses with automatic code discovery
- **WebRTC Transit**: Direct peer-to-peer connections in the browser
- **End-to-End Encryption**: SPAKE2 key exchange, NaCl encryption

## Installation

### From Source (Development)

```bash
# Clone the repository
git clone https://github.com/bshuler/critical-wormhole-tools.git
cd critical-wormhole-tools/browser-extension

# Install dependencies
npm install

# Build the extension
npm run build
```

### Chrome/Edge

1. Open `chrome://extensions/` (or `edge://extensions/`)
2. Enable "Developer mode" (toggle in top right)
3. Click "Load unpacked"
4. Select the `dist` directory

### Firefox

1. Open `about:debugging#/runtime/this-firefox`
2. Click "Load Temporary Add-on"
3. Select `dist/manifest.json`

### From Web Stores (Coming Soon)

- Chrome Web Store
- Firefox Add-ons

## Quick Start

### Hosting a Website

On your server machine, start a local HTTP server and forward it through wormhole:

```bash
# Install critical-wormhole-tools
pip install critical-wormhole-tools

# Start a local HTTP server (in your website directory)
cd ./my-website
python -m http.server 8080 &

# Forward it through wormhole
wh listen -p 8080
# Output: Listening on code: 7-guitar-sunset
```

### Viewing in Browser

1. Install the extension (see above)
2. Enter the wormhole code in the extension popup
3. Or navigate directly to `wh://7-guitar-sunset`

### Using WNS Addresses

For persistent addresses that don't change:

```bash
# On server: Create identity
wh identity create
# Output: Created identity: a7b3c9d2e1f4

# Start local HTTP server
cd ./my-website
python -m http.server 8080 &

# Serve with persistent WNS address
wh serve -p 8080
# Output: Serving as wh://a7b3c9d2e1f4.wns
```

In browser:
```
wh://a7b3c9d2e1f4.wns
```

## Example: Hello World

### 1. Create Example Files

**index.html:**
```html
<!DOCTYPE html>
<html>
<head>
  <title>Hello Wormhole!</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <h1 id="greeting">Hello from the Wormhole!</h1>
  <p id="message">Loading...</p>
  <script src="app.js"></script>
</body>
</html>
```

**style.css:**
```css
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  max-width: 800px;
  margin: 50px auto;
  padding: 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  min-height: 100vh;
}
h1 { text-align: center; }
```

**app.js:**
```javascript
// This script is loaded and executed remotely through the wormhole!
document.getElementById('message').textContent =
  'This page was served through a Magic Wormhole connection!';

// Add timestamp to prove it's dynamic
const time = new Date().toLocaleTimeString();
document.getElementById('message').textContent += ` (Loaded at ${time})`;
```

### 2. Host with Wormhole

```bash
# Navigate to your example directory
cd ~/my-example-site

# Start a local HTTP server
python -m http.server 8080 &

# Forward through wormhole
wh listen -p 8080
# Output: Listening on code: 7-guitar-sunset
```

### 3. View in Browser

1. Click the wormhole extension icon
2. Enter `7-guitar-sunset` in the code field
3. Click "Connect" or press Enter
4. The page loads through the wormhole!

Or navigate directly to: `wh://7-guitar-sunset`

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Browser Extension                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────────┐  │
│  │   Popup     │    │  Background │    │   Content Scripts       │  │
│  │   (UI)      │◄──►│  (Worker)   │◄──►│   (Page Integration)    │  │
│  └─────────────┘    └─────────────┘    └─────────────────────────┘  │
│                            │                                         │
│                            ▼                                         │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                    Protocol Library                          │    │
│  ├──────────────┬──────────────┬──────────────┬────────────────┤    │
│  │   Mailbox    │    SPAKE2    │   Transit    │     WNS        │    │
│  │  (WebSocket) │  (Key Exch)  │   (WebRTC)   │  (Discovery)   │    │
│  └──────────────┴──────────────┴──────────────┴────────────────┘    │
│                            │                                         │
│                            ▼                                         │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                    Crypto Library                            │    │
│  ├──────────────┬──────────────┬──────────────┬────────────────┤    │
│  │   Ed25519    │    HKDF      │   NaCl       │   SHA-256      │    │
│  │ (@noble/ed)  │ (Web Crypto) │ (tweetnacl)  │ (Web Crypto)   │    │
│  └──────────────┴──────────────┴──────────────┴────────────────┘    │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
                    ┌─────────────────────────┐
                    │     Relay Server        │
                    │ relay.magic-wormhole.io │
                    └─────────────────────────┘
                                  │
                                  ▼
                    ┌─────────────────────────┐
                    │    Remote wh Server     │
                    │   (wh listen --http)    │
                    └─────────────────────────┘
```

## Development

### Prerequisites

- Node.js 18+
- npm 9+

### Setup

```bash
npm install
```

### Build

```bash
# Development build (with watch)
npm run dev

# Production build
npm run build
```

### Testing

The extension has comprehensive test coverage:

```bash
# Run all unit and functional tests
npm test

# Run tests in watch mode
npm run test:watch

# Run with coverage report
npm run test:coverage

# Run E2E browser tests (requires Chrome)
npm run test:e2e

# Run E2E tests with visible browser
npm run test:e2e:headed

# Run all tests
npm run test:all
```

### Test Structure

The extension has **552 passing tests** covering all major components:

```
tests/
├── unit/                    # Unit tests for individual modules
│   ├── crypto/              # Crypto module tests
│   │   ├── hkdf.test.js     # HKDF key derivation (57 tests)
│   │   ├── nacl.test.js     # NaCl encryption (54 tests)
│   │   ├── ed25519.test.js  # Ed25519 signatures (52 tests)
│   │   ├── hash.test.js     # SHA-256 hashing (44 tests)
│   │   ├── subkey.test.js   # Subkey derivation (39 tests)
│   │   └── spake2.test.js   # SPAKE2 key exchange (27 tests)
│   ├── protocol/            # Protocol module tests
│   │   ├── mailbox.test.js  # Mailbox protocol (36 tests)
│   │   ├── wormhole.test.js # Wormhole state machine (31 tests)
│   │   └── transit.test.js  # WebRTC transit (37 tests)
│   ├── wns/                 # WNS module tests
│   │   └── *.test.js        # Name service tests
│   ├── background.test.js   # Background script (48 tests)
│   ├── viewer.test.js       # Viewer page (80+ tests)
│   └── dilation.test.js     # Dilation protocol (100+ tests)
├── functional/              # Integration tests with mock servers
│   └── wormhole-flow.test.js
└── e2e/                     # Playwright browser tests
    └── viewer-navigation.test.js
```

### Linting

```bash
npm run lint
```

### Package for Distribution

```bash
# Chrome/Edge
npm run package:chrome

# Firefox
npm run package:firefox
```

## Testing the Hello World Example

The repository includes automated tests that verify the extension can load and display pages through a wormhole connection.

### Running the E2E Test

```bash
# Build the extension first
npm run build

# Run the hello world test
npm run test:e2e -- --grep "hello world"
```

### What the Test Verifies

1. **HTML Loading**: The `index.html` file is fetched and rendered
2. **CSS Loading**: External `style.css` is loaded and applied
3. **JavaScript Execution**: External `app.js` is loaded and runs
4. **DOM Inspection**: Playwright verifies the correct text appears in the DOM

### Manual Testing

1. Start a local test server:
   ```bash
   cd tests/e2e/fixtures/hello-world
   python -m http.server 8080
   ```

2. Forward through wormhole:
   ```bash
   wh listen -p 8080
   ```

3. Load extension and navigate to the wormhole code

## Protocol Implementation

The extension implements the complete Magic Wormhole protocol:

### Mailbox Protocol
- WebSocket connection to relay server
- Nameplate allocation and claiming
- Message exchange with phases

### SPAKE2 Key Exchange
- Password-Authenticated Key Exchange
- Derives shared secrets without transmitting passwords
- Protection against offline dictionary attacks

### Transit (WebRTC)
- Browser-native peer-to-peer connections
- ICE candidate exchange via mailbox
- Falls back through relay if direct connection fails

### WNS (Wormhole Name Service)
- Ed25519 identity management
- Signed code advertisements
- DHT-based discovery (planned)

## Web API Support

The extension runs wormhole pages in a sandboxed iframe with extensive API proxying to provide a native-like browsing experience. Here's what works and what doesn't:

### Fully Working

| Feature | Notes |
|---------|-------|
| **External Resources** | CSS, JavaScript, images all load through wormhole |
| **fetch() / XHR** | All requests routed through wormhole connection |
| **localStorage** | Per-site storage persisted via extension storage |
| **sessionStorage** | Per-site session storage |
| **Cookies** | document.cookie proxy with per-site storage |
| **Forms** | Form submission with file upload support |
| **Navigation** | Internal links, hash navigation, history |
| **Nested Iframes** | Iframes load content through wormhole |
| **WebSockets** | Proxy class (requires server-side protocol support) |
| **Web Workers** | Workers load scripts through wormhole |
| **IndexedDB** | Per-site mock database synced to extension storage |
| **history.pushState/replaceState** | Full History API support |
| **window.open()** | Opens internal paths in new viewer tabs |

### Partially Working

| Feature | Notes |
|---------|-------|
| **window.location** | `window.whLocation` always works; native `window.location` override works in some contexts. Use `whLocation` for reliable access. |
| **Geolocation** | Works, but permission dialog shows extension origin |
| **Notifications** | Works, prefixes title with wormhole address |
| **Clipboard API** | Proxied, permission shows extension origin |
| **getUserMedia** | Camera/microphone proxied, permission shows extension origin |
| **WebRTC** | Full support with public STUN servers (Google, etc.); works for P2P in most networks |

### Not Supported

| Feature | Reason |
|---------|--------|
| **Service Workers** | Cannot register for external origins in sandboxed iframe |
| **Background Sync** | Requires Service Worker |
| **Push Notifications** | Requires Service Worker |
| **Payment Request API** | Requires secure origin |
| **Web Bluetooth/USB/NFC** | Requires secure origin and hardware access |

### Example: Using Location

```javascript
// Reliable way to get wormhole location
if (window.whLocation) {
  console.log(whLocation.href);     // "wh://7-guitar-sunset/page"
  console.log(whLocation.pathname); // "/page"
  console.log(whLocation.host);     // "7-guitar-sunset"
  console.log(whLocation.protocol); // "wh:"

  whLocation.assign('/other-page'); // Navigate
  whLocation.reload();               // Refresh
}
```

### Example: Fetch through Wormhole

```javascript
// All fetch requests automatically route through wormhole
const response = await fetch('/api/data.json');
const data = await response.json();

// POST requests work too
await fetch('/api/submit', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ name: 'test' })
});
```

## Security

- **End-to-End Encryption**: All data encrypted with NaCl (XSalsa20-Poly1305)
- **PAKE Authentication**: No passwords sent over the network
- **Forward Secrecy**: Unique session keys for each connection
- **Code Verification**: Visual verifier display for manual confirmation
- **Sandboxed Execution**: All page content runs in sandboxed iframe with CSP

## Browser Compatibility

| Browser | Status | Notes |
|---------|--------|-------|
| Chrome 113+ | ✅ Full | Native Ed25519 support |
| Edge 113+ | ✅ Full | Chromium-based |
| Firefox 120+ | ✅ Full | WebRTC support |
| Safari 17+ | ⚠️ Partial | Limited WebRTC |

## Troubleshooting

### Extension Not Loading

1. Ensure you're loading from the `dist` directory (after `npm run build`)
2. Check for JavaScript errors in the extension console
3. Verify manifest.json is present

### Connection Failed

1. Check that the wormhole server is running
2. Verify the code was entered correctly
3. Check browser console for WebSocket errors

### Page Not Rendering

1. Verify the server is using `--http` mode
2. Check that files exist in the served directory
3. Look for CORS errors in the console

## Running Your Own Relay

By default, `wh` uses the public Magic Wormhole relay servers. For privacy, reliability, or air-gapped networks, you can run your own.

### Why Self-Host?

- **Privacy**: Keep connection metadata on your own infrastructure
- **Reliability**: No dependency on public infrastructure
- **Air-gapped networks**: Run wormhole on isolated networks
- **Performance**: Lower latency with geographically closer relays

### Architecture

Magic Wormhole uses two relay types:

```
┌─────────────┐         ┌─────────────────────┐         ┌─────────────┐
│   Client A  │◄───────►│   Mailbox Server    │◄───────►│   Client B  │
│             │         │ (rendezvous/signaling)        │             │
└──────┬──────┘         └─────────────────────┘         └──────┬──────┘
       │                                                        │
       │                ┌─────────────────────┐                │
       └───────────────►│   Transit Relay     │◄───────────────┘
                        │   (data transfer)   │
                        └─────────────────────┘
```

- **Mailbox Server**: Handles code exchange and signaling (WebSocket)
- **Transit Relay**: Relays encrypted data if direct connection fails (TCP)

### Option 1: Docker (Recommended)

```bash
# Run mailbox server (rendezvous)
docker run -d --name wormhole-mailbox \
  -p 4000:4000 \
  ghcr.io/magic-wormhole/magic-wormhole-mailbox-server:latest

# Run transit relay
docker run -d --name wormhole-transit \
  -p 4001:4001 \
  ghcr.io/magic-wormhole/magic-wormhole-transit-relay:latest
```

### Option 2: Install from PyPI

```bash
# Install servers
pip install magic-wormhole-mailbox-server magic-wormhole-transit-relay

# Run mailbox server (default port 4000)
twist wormhole-mailbox --port 4000

# Run transit relay (default port 4001)
twist wormhole-transit --port 4001
```

### Option 3: From Source

```bash
# Mailbox server
git clone https://github.com/magic-wormhole/magic-wormhole-mailbox-server
cd magic-wormhole-mailbox-server
pip install -e .
twist wormhole-mailbox

# Transit relay
git clone https://github.com/magic-wormhole/magic-wormhole-transit-relay
cd magic-wormhole-transit-relay
pip install -e .
twist wormhole-transit
```

### Configuring wh to Use Your Relay

```bash
# Via command line flags
wh --relay ws://your-server:4000/v1 --transit tcp:your-server:4001 listen -p 8080

# Via environment variables (recommended)
export WH_RELAY=ws://your-server:4000/v1
export WH_TRANSIT=tcp:your-server:4001
wh listen -p 8080

# In ~/.bashrc or ~/.zshrc for permanent config
echo 'export WH_RELAY=ws://relay.mycompany.com:4000/v1' >> ~/.bashrc
echo 'export WH_TRANSIT=tcp:relay.mycompany.com:4001' >> ~/.bashrc
```

### Production Deployment

For production, use a reverse proxy with TLS:

```nginx
# /etc/nginx/sites-available/wormhole
server {
    listen 443 ssl;
    server_name relay.example.com;

    ssl_certificate /etc/letsencrypt/live/relay.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/relay.example.com/privkey.pem;

    # Mailbox (WebSocket)
    location /v1 {
        proxy_pass http://127.0.0.1:4000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400;
    }
}

# Transit relay (TCP passthrough)
stream {
    server {
        listen 4001;
        proxy_pass 127.0.0.1:4001;
    }
}
```

Then configure clients:
```bash
export WH_RELAY=wss://relay.example.com/v1
export WH_TRANSIT=tcp:relay.example.com:4001
```

### Browser Extension with Custom Relay

The browser extension can also use custom relays. Edit `src/config.js`:

```javascript
export const CONFIG = {
  RELAY_URL: 'wss://your-relay.example.com/v1',
  TRANSIT_RELAY: 'your-relay.example.com:4001'
};
```

Then rebuild: `npm run build`

### Future: Built-in Relay Mode

We're considering adding a built-in relay mode to `wh` itself:

```bash
# Proposed future feature
wh relay --port 4000 --transit-port 4001

# Would make wh completely self-contained!
```

This would eliminate external dependencies entirely. Track progress in [GitHub Issues](https://github.com/bshuler/critical-wormhole-tools/issues).

## Contributing

1. Fork the repository
2. Create a feature branch
3. Write tests for new functionality
4. Ensure all tests pass: `npm test`
5. Submit a pull request

## License

MIT License - see main project LICENSE file.

## Links

- [Main Project](https://github.com/bshuler/critical-wormhole-tools)
- [Magic Wormhole Protocol](https://magic-wormhole.readthedocs.io/)
- [Protocol Specification](../docs/protocol/PROTOCOL.md)
- [Mailbox Server](https://github.com/magic-wormhole/magic-wormhole-mailbox-server)
- [Transit Relay](https://github.com/magic-wormhole/magic-wormhole-transit-relay)
