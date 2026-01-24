# @wormhole-tools/mailbox

Magic Wormhole mailbox client - WebSocket relay for rendezvous and message exchange.

## Features

- WebSocket-based mailbox protocol
- Nameplate allocation and claiming
- Secure message exchange via encrypted phases
- Compatible with Python magic-wormhole relay servers
- Browser and Node.js compatible

## Installation

```bash
npm install @wormhole-tools/mailbox
```

## Usage

```javascript
import { MailboxClient, parseCode, generateCode } from '@wormhole-tools/mailbox';

// Create mailbox client
const mailbox = new MailboxClient('wss://relay.magic-wormhole.io/v1', 'my-app-id');

// Connect to relay
await mailbox.connect();

// Sender: allocate a nameplate
const nameplate = await mailbox.allocate();
const code = generateCode(nameplate, 2); // e.g., "7-guitar-sunset"

// Receiver: claim existing nameplate
const { nameplate, password } = parseCode(code);
await mailbox.claim(nameplate);

// Both: open mailbox
await mailbox.open();

// Send a message
await mailbox.addMessage('phase-name', 'Hello, world!');

// Receive a message
const message = await mailbox.waitForPhase('phase-name');

// Clean up
await mailbox.close();
```

## API

### `MailboxClient(relayUrl, appId)`

Create a new mailbox client.

**Parameters:**
- `relayUrl` (string): WebSocket relay URL (default: `wss://relay.magic-wormhole.io/v1`)
- `appId` (string): Application identifier (default: `wh.tools/v1`)

### Key Methods

- `connect()` - Connect to relay server
- `allocate()` - Allocate a new nameplate (sender)
- `claim(nameplate)` - Claim existing nameplate (receiver)
- `open(mailbox)` - Open mailbox for message exchange
- `addMessage(phase, body)` - Send a message
- `waitForPhase(phase)` - Wait for a specific message
- `onMessage(handler)` - Register message handler
- `close()` - Close connection

### Utility Functions

- `parseCode(code)` - Parse wormhole code into nameplate and password
- `generateCode(nameplate, numWords)` - Generate wormhole code

## License

MIT
