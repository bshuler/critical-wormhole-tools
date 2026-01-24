# @wormhole-tools/dilation

Magic Wormhole dilation - persistent multiplexed streaming connections over WebRTC.

## Features

- WebRTC-based dilation protocol
- Multiplexed subchannels over single connection
- Connection durability (survives network changes)
- Efficient bulk data transfer
- Browser and Node.js compatible

## Installation

```bash
npm install @wormhole-tools/dilation
```

## Usage

```javascript
import { DilationManager } from '@wormhole-tools/dilation';

// Create dilation manager (requires established wormhole)
const dilation = new DilationManager({
  mailbox,          // MailboxClient instance
  sharedKey,        // SPAKE2 shared key
  mailboxSide,      // Our mailbox side ID
  peerSide          // Peer's mailbox side ID
});

// Start dilation
await dilation.dilate();

// Open a subchannel
const subchannel = await dilation.openSubchannel('my-protocol');

// Send data
await subchannel.send(new TextEncoder().encode('Hello!'));

// Receive data
subchannel.onData = (data) => {
  console.log('Received:', new TextDecoder().decode(data));
};

// Listen for incoming subchannels
dilation.listen('my-protocol', (subchannel) => {
  subchannel.onData = (data) => {
    console.log('Received on server:', data);
  };
});

// Clean up
await subchannel.close();
await dilation.close();
```

## API

### `DilationManager(options)`

Create a new dilation manager.

**Options:**
- `mailbox` (MailboxClient): Connected mailbox client
- `sharedKey` (Uint8Array): SPAKE2 shared key
- `mailboxSide` (string): Our mailbox side identifier
- `peerSide` (string): Peer's mailbox side identifier
- `iceServers` (RTCConfiguration): ICE server config (optional)

### Key Methods

- `dilate()` - Start dilation protocol
- `openSubchannel(protocol)` - Open new subchannel to peer
- `listen(protocol, callback)` - Listen for incoming subchannels
- `close()` - Close all subchannels and connection

### Subchannel API

- `send(data)` - Send data on subchannel
- `onData` - Handler for incoming data
- `onClose` - Handler for subchannel close
- `close()` - Close subchannel

## Protocol Details

Dilation transforms a simple message-exchange wormhole into a full streaming connection:

1. Exchange PLEASE messages to agree on version and roles
2. Exchange CONNECTION-HINTS with WebRTC offers/answers
3. Establish direct WebRTC data channel
4. Multiplex subchannels with encrypted framing

## License

MIT
