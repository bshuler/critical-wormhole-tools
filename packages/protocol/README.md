# @wormhole-tools/protocol

Complete Magic Wormhole protocol implementation with transit support for JavaScript/TypeScript.

## Features

- Full wormhole protocol implementation
- SPAKE2 key exchange
- Mailbox-based rendezvous
- WebRTC transit for peer-to-peer data transfer
- Dilation support for streaming connections
- Browser and Node.js compatible

## Installation

```bash
npm install @wormhole-tools/protocol
```

This package includes all dependencies:
- `@wormhole-tools/spake2`
- `@wormhole-tools/mailbox`
- `@wormhole-tools/dilation`

## Usage

### Simple Send/Receive

```javascript
import { Wormhole } from '@wormhole-tools/protocol';

// Sender
const sender = new Wormhole({ appId: 'my-app' });
const code = await sender.allocate();
console.log('Code:', code);

await sender.waitForPeer();
await sender.send('Hello, world!');

// Receiver
const receiver = new Wormhole({ appId: 'my-app' });
await receiver.connect(code);
const message = await receiver.receive();
console.log('Received:', new TextDecoder().decode(message));

// Both
await sender.close();
await receiver.close();
```

### File Transfer

```javascript
// Sender
const file = document.querySelector('input[type="file"]').files[0];
await sender.sendFile(file, (sent, total) => {
  console.log(`Progress: ${sent}/${total}`);
});
```

### Dilation for Streaming

```javascript
// Both sides
const endpoints = await wormhole.dilate();

// Sender: open subchannel
const conn = endpoints.connect('my-protocol');
const subchannel = await conn.connect();
await subchannel.send('streaming data');

// Receiver: listen for subchannels
const listener = endpoints.listen('my-protocol');
await listener.listen();
const subchannel = await listener.accept();
subchannel.onData = (data) => console.log('Received:', data);
```

## API

### `Wormhole(options)`

Create a new wormhole connection.

**Options:**
- `relayUrl` (string): Mailbox relay URL
- `appId` (string): Application identifier

### Sender Methods

- `allocate(numWords)` - Create new code
- `waitForPeer()` - Wait for receiver
- `send(data)` - Send message
- `sendFile(file, onProgress)` - Send file

### Receiver Methods

- `connect(code)` - Connect with code
- `receive(timeout)` - Receive message

### Both Sides

- `dilate()` - Enable streaming (returns endpoints)
- `close()` - Close connection

### Events

- `onStateChange(newState, oldState)` - Connection state changed
- `onError(error)` - Error occurred
- `onMessage(data)` - Message received (transit mode)

## States

- `DISCONNECTED` - Not connected
- `ALLOCATING` - Creating code
- `WAITING` - Waiting for peer
- `EXCHANGING` - Key exchange in progress
- `CONNECTED` - Ready to transfer
- `DILATING` - Starting dilation
- `DILATED` - Streaming enabled
- `FAILED` - Connection failed
- `CLOSED` - Connection closed

## License

MIT
