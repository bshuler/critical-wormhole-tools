#!/usr/bin/env python3
"""
Wormhole Native Messaging Host

Bridges communication between the browser extension and wh daemon.
Follows the Chrome Native Messaging protocol.
"""

import asyncio
import json
import struct
import sys
import httpx

DAEMON_URL = "http://localhost:9475"


def read_message():
    """Read a message from stdin using native messaging protocol."""
    # Read the message length (4 bytes, little-endian)
    raw_length = sys.stdin.buffer.read(4)
    if not raw_length:
        return None

    # Unpack the length
    message_length = struct.unpack('<I', raw_length)[0]

    # Read the message content
    message = sys.stdin.buffer.read(message_length).decode('utf-8')
    return json.loads(message)


def send_message(message):
    """Send a message to stdout using native messaging protocol."""
    encoded = json.dumps(message).encode('utf-8')

    # Write the message length
    sys.stdout.buffer.write(struct.pack('<I', len(encoded)))

    # Write the message content
    sys.stdout.buffer.write(encoded)
    sys.stdout.buffer.flush()


async def handle_message(message):
    """Handle a message from the extension."""
    message_type = message.get('type')

    async with httpx.AsyncClient() as client:
        try:
            if message_type == 'GET_STATUS':
                response = await client.get(f'{DAEMON_URL}/status')
                if response.status_code == 200:
                    return {'type': 'STATUS_UPDATE', 'running': True, **response.json()}
                else:
                    return {'type': 'STATUS_UPDATE', 'running': False}

            elif message_type == 'RESOLVE':
                address = message.get('address')
                response = await client.post(
                    f'{DAEMON_URL}/resolve',
                    json={'address': address}
                )
                if response.status_code == 200:
                    return {'type': 'RESOLVE_RESULT', 'success': True, **response.json()}
                else:
                    return {'type': 'RESOLVE_RESULT', 'success': False, 'error': response.text}

            elif message_type == 'CONNECT':
                address = message.get('address')
                response = await client.post(
                    f'{DAEMON_URL}/connect',
                    json={'address': address}
                )
                if response.status_code == 200:
                    data = response.json()
                    return {'type': 'CONNECTION_ESTABLISHED', 'address': address, 'data': data}
                else:
                    return {'type': 'CONNECTION_FAILED', 'address': address, 'error': response.text}

            else:
                return {'type': 'ERROR', 'error': f'Unknown message type: {message_type}'}

        except httpx.ConnectError:
            return {'type': 'STATUS_UPDATE', 'running': False}
        except Exception as e:
            return {'type': 'ERROR', 'error': str(e)}


def main():
    """Main loop - read messages and respond."""
    while True:
        message = read_message()
        if message is None:
            break

        # Handle the message
        response = asyncio.run(handle_message(message))
        send_message(response)


if __name__ == '__main__':
    main()
