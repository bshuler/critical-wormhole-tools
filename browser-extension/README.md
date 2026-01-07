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

```
tests/
├── unit/              # Unit tests for individual modules
│   ├── crypto/        # Crypto module tests (246 tests)
│   ├── wns/           # WNS module tests
│   └── protocol/      # Protocol module tests
├── functional/        # Integration tests with mock servers
└── e2e/               # Playwright browser tests
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

## Security

- **End-to-End Encryption**: All data encrypted with NaCl (XSalsa20-Poly1305)
- **PAKE Authentication**: No passwords sent over the network
- **Forward Secrecy**: Unique session keys for each connection
- **Code Verification**: Visual verifier display for manual confirmation

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
