# Wormhole Browser Extension - Standalone Architecture

## Overview

This browser extension implements the complete Wormhole Protocol in JavaScript, requiring no external daemon or CLI tools. It enables users to browse `wh://` addresses directly in their browser.

## Design Principles

1. **Self-contained**: All protocol logic runs in the browser
2. **Standard APIs**: Uses Web Crypto, WebSocket, WebRTC
3. **Decentralized**: DHT discovery via WebRTC peer mesh
4. **Privacy-preserving**: No data leaves the browser except encrypted traffic

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Browser Extension                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    Extension UI                           │   │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────────┐  │   │
│  │  │ Popup   │  │ Options │  │ Sidebar │  │ Omnibox     │  │   │
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────────┘  │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              │                                   │
│                              ▼                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              Background Service Worker                    │   │
│  │  ┌─────────────────────────────────────────────────────┐ │   │
│  │  │              Wormhole Protocol Engine               │ │   │
│  │  │  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │ │   │
│  │  │  │ SPAKE2   │  │ Ed25519  │  │ XSalsa20-Poly1305│  │ │   │
│  │  │  └──────────┘  └──────────┘  └──────────────────┘  │ │   │
│  │  │  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │ │   │
│  │  │  │ Mailbox  │  │ Transit  │  │ Dilation         │  │ │   │
│  │  │  │ Client   │  │ Handler  │  │ Manager          │  │ │   │
│  │  │  └──────────┘  └──────────┘  └──────────────────┘  │ │   │
│  │  └─────────────────────────────────────────────────────┘ │   │
│  │  ┌─────────────────────────────────────────────────────┐ │   │
│  │  │                   WNS Engine                        │ │   │
│  │  │  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │ │   │
│  │  │  │ Identity │  │ DHT Node │  │ Name Resolver    │  │ │   │
│  │  │  │ Manager  │  │ (WebRTC) │  │                  │  │ │   │
│  │  │  └──────────┘  └──────────┘  └──────────────────┘  │ │   │
│  │  └─────────────────────────────────────────────────────┘ │   │
│  │  ┌─────────────────────────────────────────────────────┐ │   │
│  │  │                 HTTP Proxy                          │ │   │
│  │  │  Intercepts wh:// requests → Proxies over Wormhole  │ │   │
│  │  └─────────────────────────────────────────────────────┘ │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              │                                   │
└──────────────────────────────┼───────────────────────────────────┘
                               │
           ┌───────────────────┼───────────────────┐
           │                   │                   │
           ▼                   ▼                   ▼
    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
    │  WebSocket  │    │  WebRTC     │    │  IndexedDB  │
    │  (Mailbox)  │    │  (P2P/DHT)  │    │  (Storage)  │
    └─────────────┘    └─────────────┘    └─────────────┘
```

## Core Modules

### 1. Crypto Module (`src/lib/crypto/`)

Pure JavaScript cryptographic primitives:

```
crypto/
├── spake2.js      # SPAKE2 implementation over Ed25519
├── ed25519.js     # Ed25519 signatures (wraps @noble/ed25519)
├── nacl.js        # XSalsa20-Poly1305 (wraps tweetnacl)
├── hkdf.js        # HKDF-SHA256 key derivation
└── index.js       # Unified crypto interface
```

### 2. Protocol Module (`src/lib/protocol/`)

Wormhole protocol implementation:

```
protocol/
├── mailbox.js     # WebSocket mailbox client
├── spake2.js      # SPAKE2 key exchange protocol
├── transit.js     # Transit connection (WebRTC-based)
├── dilation.js    # Dilated wormhole channels
├── wormhole.js    # High-level Wormhole class
└── index.js       # Exports
```

### 3. WNS Module (`src/lib/wns/`)

Wormhole Name Service:

```
wns/
├── identity.js    # Identity generation/management
├── address.js     # Address derivation/parsing
├── advertisement.js # Signed code advertisements
├── dht.js         # Kademlia DHT over WebRTC
├── resolver.js    # Name resolution
├── store.js       # IndexedDB storage
└── index.js       # Exports
```

### 4. Network Module (`src/lib/network/`)

Network transport abstraction:

```
network/
├── websocket.js   # WebSocket wrapper
├── webrtc.js      # WebRTC DataChannel wrapper
├── signaling.js   # WebRTC signaling over wormhole
└── index.js       # Exports
```

## Data Flow

### Connecting to wh://address.wns

```
1. User enters wh://address.wns in URL bar
   │
2. Extension intercepts request
   │
3. Resolve WNS address
   │  ├─ Check local cache (IndexedDB)
   │  ├─ Query DHT (via WebRTC peer mesh)
   │  └─ Try HTTP well-known (fallback)
   │
4. Verify advertisement signature
   │
5. Extract ephemeral wormhole code
   │
6. Connect to mailbox server (WebSocket)
   │
7. Perform SPAKE2 key exchange
   │
8. Establish transit connection
   │  ├─ Try WebRTC direct (ICE)
   │  └─ Fall back to relay
   │
9. Dilate connection (if persistent)
   │
10. Proxy HTTP request/response
    │
11. Render page in browser
```

### Hosting a wh:// site

```
1. User clicks "Host Site" in extension
   │
2. Generate/load WNS identity
   │
3. Generate ephemeral wormhole code
   │
4. Create signed advertisement
   │
5. Publish to DHT
   │
6. Listen for connections (via mailbox)
   │
7. On connection:
   │  ├─ SPAKE2 key exchange
   │  ├─ Establish transit
   │  └─ Serve HTTP requests
   │
8. On disconnect:
   │  ├─ Generate new code
   │  ├─ Update advertisement
   │  └─ Re-publish to DHT
```

## Storage (IndexedDB)

```javascript
// Database: "wormhole-extension"

// Object Stores:
{
  "identities": {
    // WNS identities (keypairs)
    keyPath: "address",
    indexes: ["name", "created"]
  },
  "known_hosts": {
    // TOFU public key cache
    keyPath: "address",
    indexes: ["lastSeen"]
  },
  "aliases": {
    // Local petnames
    keyPath: "alias",
    indexes: []
  },
  "dht_cache": {
    // DHT lookup cache
    keyPath: "key",
    indexes: ["expires"]
  },
  "settings": {
    // Extension settings
    keyPath: "key"
  }
}
```

## External Dependencies

### NPM Packages (bundled)

| Package | Purpose | Size |
|---------|---------|------|
| @noble/ed25519 | Ed25519 signatures | ~8KB |
| @noble/hashes | SHA-256, HKDF | ~12KB |
| tweetnacl | XSalsa20-Poly1305 | ~7KB |
| buffer | Buffer polyfill | ~10KB |

### External Services

| Service | Purpose | Required |
|---------|---------|----------|
| Mailbox relay | Rendezvous | Yes |
| Transit relay | NAT traversal fallback | Recommended |
| STUN/TURN | WebRTC ICE | Recommended |
| DHT bootstrap | Initial peer discovery | For WNS |

### Default Servers

```javascript
const DEFAULT_CONFIG = {
  mailbox: "wss://relay.magic-wormhole.io/v1",
  transit: "tcp://relay.magic-wormhole.io:4001",
  stun: ["stun:stun.l.google.com:19302"],
  turn: [], // Optional TURN servers
  dhtBootstrap: [
    "wss://wns-bootstrap-1.example.com",
    "wss://wns-bootstrap-2.example.com"
  ]
};
```

## Security Considerations

### Key Storage

- Private keys stored in IndexedDB (encrypted at rest by browser)
- Consider Web Crypto `extractable: false` for additional protection
- User can export keys for backup

### WebRTC Security

- All data channels encrypted with wormhole session key
- ICE candidates may leak IP addresses (use TURN for privacy)

### TOFU Risks

- First connection to new address vulnerable to MITM
- Extension shows warning for unknown hosts
- User can verify public key fingerprint out-of-band

## Browser Compatibility

| Feature | Chrome | Firefox | Safari | Edge |
|---------|--------|---------|--------|------|
| Service Workers | ✅ | ✅ | ✅ | ✅ |
| WebSocket | ✅ | ✅ | ✅ | ✅ |
| WebRTC | ✅ | ✅ | ✅ | ✅ |
| IndexedDB | ✅ | ✅ | ✅ | ✅ |
| Web Crypto | ✅ | ✅ | ✅ | ✅ |
| Proxy API | ✅ | ✅ | ❌ | ✅ |

## Build Process

```bash
# Install dependencies
npm install

# Development build (with source maps)
npm run dev

# Production build (minified)
npm run build

# Run tests
npm test

# Package for distribution
npm run package
```

## Directory Structure

```
browser-extension/
├── manifest.json          # Extension manifest
├── package.json           # NPM dependencies
├── webpack.config.js      # Build configuration
├── src/
│   ├── background.js      # Service worker entry
│   ├── popup/
│   │   ├── popup.html
│   │   ├── popup.js
│   │   └── popup.css
│   ├── options/
│   │   ├── options.html
│   │   ├── options.js
│   │   └── options.css
│   ├── lib/
│   │   ├── crypto/        # Cryptographic primitives
│   │   ├── protocol/      # Wormhole protocol
│   │   ├── wns/           # Wormhole Name Service
│   │   └── network/       # Network transports
│   └── utils/
│       ├── base32.js
│       ├── base64.js
│       └── logger.js
├── tests/
│   ├── crypto.test.js
│   ├── protocol.test.js
│   └── wns.test.js
├── icons/
│   └── *.png
└── dist/                  # Built extension
```

## Development Phases

### Phase 1: Core Crypto
- [ ] SPAKE2 implementation
- [ ] Ed25519 wrapper
- [ ] XSalsa20-Poly1305 wrapper
- [ ] HKDF implementation
- [ ] Test vectors validation

### Phase 2: Wormhole Protocol
- [x] Mailbox WebSocket client
- [x] SPAKE2 key exchange integration
- [x] WebRTC transit handler
- [x] Basic dilation support (subchannel multiplexing over WebRTC)

### Phase 3: WNS Implementation
- [ ] Identity generation/storage
- [ ] Address derivation
- [ ] Advertisement signing/verification
- [ ] DHT implementation (simplified)
- [ ] Name resolution

### Phase 4: HTTP Proxy
- [ ] Request interception
- [ ] HTTP-over-wormhole protocol
- [ ] Response rendering

### Phase 5: UI & Polish
- [ ] Popup interface
- [ ] Options page
- [ ] Omnibox integration
- [ ] Error handling & UX
