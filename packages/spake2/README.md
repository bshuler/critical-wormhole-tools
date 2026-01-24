# @wormhole-tools/spake2

SPAKE2 Password-Authenticated Key Exchange implementation for JavaScript/TypeScript, compatible with the Magic Wormhole protocol.

## Features

- SPAKE2 Symmetric mode over Ed25519
- Compatible with Python magic-wormhole library
- Browser and Node.js compatible
- Zero external crypto dependencies (uses @noble libraries)

## Installation

```bash
npm install @wormhole-tools/spake2
```

## Usage

```javascript
import { createSPAKE2 } from '@wormhole-tools/spake2';

// Create SPAKE2 instance
const spake = createSPAKE2('my-password', 'my-app-id');

// Generate PAKE message to send to peer
const pakeMessage = spake.start();

// After receiving peer's PAKE message
const sharedKey = spake.finish(peerPakeMessage);
```

## API

### `createSPAKE2(password, appId)`

Create a new SPAKE2 instance.

**Parameters:**
- `password` (string): The password/wormhole code
- `appId` (string): Application identifier (default: 'wh.tools/v1')

**Returns:** `SPAKE2_Symmetric` instance

### `spake.start()`

Generate the PAKE message to send to the peer.

**Returns:** `Uint8Array` - 33 bytes ('S' + 32-byte Ed25519 point)

### `spake.finish(peerMessage)`

Complete the key exchange with peer's PAKE message.

**Parameters:**
- `peerMessage` (Uint8Array): Peer's PAKE message

**Returns:** `Uint8Array` - 32-byte shared secret

## Protocol Details

This implementation follows the SPAKE2 Symmetric protocol as used by Python magic-wormhole:

1. Both sides use the same blinding point M (symmetric mode)
2. Message format: `'S'` (0x53) + 32-byte compressed Ed25519 point
3. Shared key derived using HKDF-SHA256 with transcript hash

## License

MIT
