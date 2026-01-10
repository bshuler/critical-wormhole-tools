"""
wh daemon - Local daemon for browser extension and Caddy integration.

Provides HTTP API for:
- Browser extension: status, resolve, browse
- Caddy plugin: listen, accept, send, recv

Endpoints:
- GET /status - Daemon status
- POST /resolve - Resolve WNS address to code
- POST /connect - Establish wormhole connection
- GET /browse/<url> - Proxy HTTP request through wormhole
- POST /listen - Start a wormhole listener (returns code)
- GET /accept/<listener_id> - Wait for incoming connection
- WebSocket /ws/<conn_id> - Bidirectional data transfer
"""

import asyncio
import click
import uuid
from typing import Dict, Any, Optional
from functools import wraps
from dataclasses import dataclass, field
from asyncio import Queue

# Import wh first to ensure reactor is set up
import wh  # noqa: F401


@dataclass
class ListenerState:
    """State for an active wormhole listener."""

    id: str
    code: str
    manager: Any  # WormholeManager
    protocol_name: str = "wh-http"
    connections: Queue = field(default_factory=Queue)
    closed: bool = False


@dataclass
class ConnectionState:
    """State for an established wormhole connection."""

    id: str
    listener_id: str
    protocol: Any  # Twisted Protocol
    read_queue: Queue = field(default_factory=Queue)
    write_queue: Queue = field(default_factory=Queue)
    closed: bool = False


def async_command(f):
    """Decorator to run async Click commands."""

    @wraps(f)
    def wrapper(*args, **kwargs):
        from twisted.internet import reactor

        async def run():
            try:
                return await f(*args, **kwargs)
            finally:
                if reactor.running:
                    reactor.callFromThread(reactor.stop)

        future = asyncio.ensure_future(run())

        if not reactor.running:
            reactor.run()

        if future.done():
            return future.result()
        return None

    return wrapper


class WormholeDaemon:
    """
    Local HTTP daemon for browser extension and Caddy plugin communication.

    Provides endpoints:
    - GET /status - Daemon status
    - POST /resolve - Resolve WNS address to code
    - POST /connect - Establish wormhole connection
    - GET /browse/<url> - Proxy HTTP request through wormhole
    - POST /listen - Start a wormhole listener (returns code)
    - GET /accept/<listener_id> - Wait for incoming connection (long-poll)
    - POST /send/<conn_id> - Send data through connection
    - POST /recv/<conn_id> - Receive data from connection
    - DELETE /listener/<listener_id> - Close a listener
    - DELETE /connection/<conn_id> - Close a connection
    """

    def __init__(self, port: int = 9475, verbose: bool = False):
        self.port = port
        self.verbose = verbose
        self.connections: Dict[str, Any] = {}  # Legacy connection tracking
        self.listeners: Dict[str, ListenerState] = {}  # Active listeners
        self.active_connections: Dict[str, ConnectionState] = {}  # Active connections
        self.server = None

    async def start(self):
        """Start the HTTP server."""
        from aiohttp import web

        app = web.Application()
        # Browser extension endpoints
        app.router.add_get('/status', self.handle_status)
        app.router.add_post('/resolve', self.handle_resolve)
        app.router.add_post('/connect', self.handle_connect)
        app.router.add_get('/browse/{url:.*}', self.handle_browse)
        app.router.add_get('/config/relays', self.handle_get_relays)

        # Caddy plugin listener endpoints
        app.router.add_post('/listen', self.handle_listen)
        app.router.add_get('/accept/{listener_id}', self.handle_accept)
        app.router.add_post('/send/{conn_id}', self.handle_send)
        app.router.add_post('/recv/{conn_id}', self.handle_recv)
        app.router.add_delete('/listener/{listener_id}', self.handle_close_listener)
        app.router.add_delete('/connection/{conn_id}', self.handle_close_connection)

        app.router.add_options('/{path:.*}', self.handle_cors)

        # Add CORS middleware
        @web.middleware
        async def cors_middleware(request, handler):
            response = await handler(request)
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
            return response

        app.middlewares.append(cors_middleware)

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, 'localhost', self.port)
        await site.start()

        click.echo(f"Wormhole daemon running on http://localhost:{self.port}")
        click.echo("Press Ctrl+C to stop")

        # Keep running
        while True:
            await asyncio.sleep(1)

    async def handle_cors(self, request):
        """Handle CORS preflight requests."""
        from aiohttp import web
        return web.Response(status=200)

    async def handle_status(self, request):
        """Return daemon status."""
        from aiohttp import web

        status = {
            'running': True,
            'version': wh.__version__,
            'connections': len(self.connections),
            'port': self.port
        }
        return web.json_response(status)

    async def handle_resolve(self, request):
        """Resolve a WNS address to ephemeral code."""
        from aiohttp import web
        from wh.wns.discovery import discover_code
        from wh.wns.identity import parse_wns_address

        try:
            data = await request.json()
            address = data.get('address', '')

            # Parse the address
            parsed = parse_wns_address(address)
            if not parsed:
                return web.json_response(
                    {'error': 'Invalid WNS address'},
                    status=400
                )

            # Try to discover the code
            result = await discover_code(parsed['address'])
            if result:
                return web.json_response({
                    'address': parsed['address'],
                    'code': result.get('code'),
                    'verified': result.get('verified', False)
                })
            else:
                return web.json_response(
                    {'error': 'Address not found'},
                    status=404
                )

        except Exception as e:
            return web.json_response(
                {'error': str(e)},
                status=500
            )

    async def handle_connect(self, request):
        """Establish a wormhole connection to an address."""
        from aiohttp import web
        from wh.wns.discovery import discover_code
        from wh.wns.identity import parse_wns_address

        try:
            data = await request.json()
            address = data.get('address', '')

            # Parse the address
            parsed = parse_wns_address(address)
            if not parsed:
                return web.json_response(
                    {'error': 'Invalid WNS address'},
                    status=400
                )

            # Discover the code
            result = await discover_code(parsed['address'])
            if not result:
                return web.json_response(
                    {'error': 'Address not found'},
                    status=404
                )

            # Store connection info
            self.connections[address] = {
                'code': result.get('code'),
                'connected_at': asyncio.get_event_loop().time()
            }

            return web.json_response({
                'address': parsed['address'],
                'code': result.get('code'),
                'status': 'connected'
            })

        except Exception as e:
            return web.json_response(
                {'error': str(e)},
                status=500
            )

    async def handle_browse(self, request):
        """Proxy an HTTP request through wormhole."""
        from aiohttp import web
        from urllib.parse import unquote

        try:
            # Get the target URL
            url = unquote(request.match_info['url'])

            if not url.startswith('wh://'):
                return web.json_response(
                    {'error': 'URL must start with wh://'},
                    status=400
                )

            # Parse the wh:// URL
            # wh://address.wns/path -> extract address and path
            url_without_scheme = url[5:]  # Remove 'wh://'
            parts = url_without_scheme.split('/', 1)
            host = parts[0]
            path = '/' + parts[1] if len(parts) > 1 else '/'

            # For now, return a placeholder response
            # Full implementation would establish wormhole and proxy HTTP
            html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Wormhole Browser</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1e1b4b 0%, #312e81 100%);
            color: #e0e7ff;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0;
        }}
        .container {{
            text-align: center;
            padding: 40px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 16px;
            max-width: 500px;
        }}
        h1 {{ margin-bottom: 16px; }}
        .address {{
            font-family: monospace;
            background: rgba(0, 0, 0, 0.3);
            padding: 12px 20px;
            border-radius: 8px;
            margin: 20px 0;
            word-break: break-all;
        }}
        .status {{
            color: #22c55e;
            margin-bottom: 20px;
        }}
        p {{ opacity: 0.8; line-height: 1.6; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Wormhole Connection</h1>
        <div class="status">Resolving address...</div>
        <div class="address">{host}</div>
        <p>Path: {path}</p>
        <p>
            The wormhole daemon is establishing a connection to this address.
            This page will automatically refresh when the connection is ready.
        </p>
    </div>
    <script>
        // Poll for connection status
        async function checkConnection() {{
            try {{
                const response = await fetch('/connect', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ address: '{host}' }})
                }});
                if (response.ok) {{
                    document.querySelector('.status').textContent = 'Connected!';
                    document.querySelector('.status').style.color = '#22c55e';
                }}
            }} catch (e) {{
                console.error('Connection check failed:', e);
            }}
        }}
        checkConnection();
    </script>
</body>
</html>
"""
            return web.Response(
                text=html,
                content_type='text/html'
            )

        except Exception as e:
            return web.json_response(
                {'error': str(e)},
                status=500
            )

    async def handle_get_relays(self, request):
        """Return CLI relay configuration for browser extension sync."""
        from aiohttp import web
        from wh.relay.config import get_relay_manager

        try:
            manager = get_relay_manager()
            config = manager.load()
            relays = manager.list_relays()

            # Format relays for browser extension
            extension_relays = []
            for r in relays:
                extension_relays.append({
                    'name': r.name,
                    'mailboxUrl': r.mailbox_url,
                    'transitUrl': r.transit_url,
                    'description': r.description or '',
                    'isDefault': r.name == config.default,
                    'hasNamespaceKey': bool(r.namespace_key),
                })

            return web.json_response({
                'relays': extension_relays,
                'default': config.default,
            })

        except Exception as e:
            return web.json_response(
                {'error': str(e)},
                status=500
            )

    # =========================================================================
    # Caddy Plugin Listener Endpoints
    # =========================================================================

    async def handle_listen(self, request):
        """
        Start a new wormhole listener.

        Creates a wormhole, allocates a code, dilates for streaming,
        and returns the listener ID and code for clients to connect.

        Request body (optional):
            {
                "protocol": "wh-http",  // Protocol name for subchannel
                "identity": "path/to/identity"  // Optional WNS identity
            }

        Response:
            {
                "listener_id": "uuid",
                "code": "7-guitar-sunset",
                "status": "listening"
            }
        """
        from aiohttp import web
        from wh.core.wormhole_manager import WormholeManager

        try:
            data = await request.json() if request.body_exists else {}
            protocol_name = data.get('protocol', 'wh-http')

            # Create wormhole manager
            manager = WormholeManager.from_relay_config()

            # Allocate a code
            code = await manager.create_and_allocate_code()

            # Generate listener ID
            listener_id = str(uuid.uuid4())

            # Create listener state
            listener = ListenerState(
                id=listener_id,
                code=code,
                manager=manager,
                protocol_name=protocol_name,
            )
            self.listeners[listener_id] = listener

            if self.verbose:
                click.echo(f"Listener {listener_id} created with code {code}")

            # Start background task to dilate and accept connections
            asyncio.create_task(self._listener_accept_loop(listener))

            return web.json_response({
                'listener_id': listener_id,
                'code': code,
                'status': 'listening',
            })

        except Exception as e:
            return web.json_response(
                {'error': str(e)},
                status=500
            )

    async def _listener_accept_loop(self, listener: ListenerState):
        """
        Background task that dilates the wormhole and accepts connections.

        This runs continuously, accepting incoming connections and adding
        them to the listener's connection queue.
        """
        from twisted.internet.protocol import Factory, Protocol

        try:
            # Wait for peer to connect and dilate
            await listener.manager.dilate()

            if self.verbose:
                click.echo(f"Listener {listener.id} dilated, ready for connections")

            # Get the listener endpoint for our protocol
            endpoint = listener.manager.listener_for(listener.protocol_name)

            # Create a protocol factory that bridges to our async queues
            daemon = self

            class BridgeProtocol(Protocol):
                """Protocol that bridges Twisted to asyncio queues."""

                def __init__(self):
                    self.conn_id = str(uuid.uuid4())
                    self.conn_state: Optional[ConnectionState] = None

                def connectionMade(self):
                    # Create connection state
                    self.conn_state = ConnectionState(
                        id=self.conn_id,
                        listener_id=listener.id,
                        protocol=self,
                    )
                    daemon.active_connections[self.conn_id] = self.conn_state

                    # Notify listener of new connection
                    asyncio.get_event_loop().call_soon_threadsafe(
                        listener.connections.put_nowait,
                        self.conn_id
                    )

                    if daemon.verbose:
                        click.echo(f"Connection {self.conn_id} established")

                def dataReceived(self, data: bytes):
                    if self.conn_state:
                        asyncio.get_event_loop().call_soon_threadsafe(
                            self.conn_state.read_queue.put_nowait,
                            data
                        )

                def connectionLost(self, reason):
                    if self.conn_state:
                        self.conn_state.closed = True
                        # Signal EOF
                        asyncio.get_event_loop().call_soon_threadsafe(
                            self.conn_state.read_queue.put_nowait,
                            None
                        )

            class BridgeFactory(Factory):
                def buildProtocol(self, addr):
                    return BridgeProtocol()

            # Start listening with Twisted
            def listen_callback(port):
                if daemon.verbose:
                    click.echo(f"Listener {listener.id} accepting on {port}")

            def listen_errback(failure):
                click.echo(f"Listener {listener.id} error: {failure}")
                listener.closed = True

            d = endpoint.listen(BridgeFactory())
            d.addCallback(listen_callback)
            d.addErrback(listen_errback)

            # Keep running until closed
            while not listener.closed:
                await asyncio.sleep(1)

        except Exception as e:
            click.echo(f"Listener {listener.id} error: {e}")
            listener.closed = True

    async def handle_accept(self, request):
        """
        Wait for an incoming connection on a listener.

        This is a long-polling endpoint that blocks until a connection
        is available or timeout is reached.

        Response:
            {
                "connection_id": "uuid",
                "status": "connected"
            }
        """
        from aiohttp import web

        listener_id = request.match_info['listener_id']
        timeout = float(request.query.get('timeout', '30'))

        listener = self.listeners.get(listener_id)
        if not listener:
            return web.json_response(
                {'error': 'Listener not found'},
                status=404
            )

        if listener.closed:
            return web.json_response(
                {'error': 'Listener closed'},
                status=410
            )

        try:
            # Wait for a connection with timeout
            conn_id = await asyncio.wait_for(
                listener.connections.get(),
                timeout=timeout
            )

            return web.json_response({
                'connection_id': conn_id,
                'status': 'connected',
            })

        except asyncio.TimeoutError:
            return web.json_response({
                'connection_id': None,
                'status': 'timeout',
            })

    async def handle_send(self, request):
        """
        Send data through an established connection.

        Request body: raw bytes to send
        Response: {"bytes_sent": N}
        """
        from aiohttp import web

        conn_id = request.match_info['conn_id']

        conn = self.active_connections.get(conn_id)
        if not conn:
            return web.json_response(
                {'error': 'Connection not found'},
                status=404
            )

        if conn.closed:
            return web.json_response(
                {'error': 'Connection closed'},
                status=410
            )

        try:
            data = await request.read()

            # Write through Twisted protocol (thread-safe)
            from twisted.internet import reactor
            reactor.callFromThread(conn.protocol.transport.write, data)

            return web.json_response({
                'bytes_sent': len(data),
            })

        except Exception as e:
            return web.json_response(
                {'error': str(e)},
                status=500
            )

    async def handle_recv(self, request):
        """
        Receive data from an established connection.

        Query params:
            timeout: Max seconds to wait (default 30)
            max_bytes: Max bytes to return (default 65536)

        Response: raw bytes received
        """
        from aiohttp import web

        conn_id = request.match_info['conn_id']
        timeout = float(request.query.get('timeout', '30'))
        max_bytes = int(request.query.get('max_bytes', '65536'))

        conn = self.active_connections.get(conn_id)
        if not conn:
            return web.json_response(
                {'error': 'Connection not found'},
                status=404
            )

        if conn.closed:
            return web.json_response(
                {'error': 'Connection closed'},
                status=410
            )

        try:
            # Wait for data with timeout
            data = await asyncio.wait_for(
                conn.read_queue.get(),
                timeout=timeout
            )

            if data is None:
                # EOF
                return web.Response(
                    body=b'',
                    status=204,  # No Content = EOF
                )

            # Truncate if needed
            if len(data) > max_bytes:
                # Put remainder back
                remainder = data[max_bytes:]
                data = data[:max_bytes]
                await conn.read_queue.put(remainder)

            return web.Response(
                body=data,
                content_type='application/octet-stream',
            )

        except asyncio.TimeoutError:
            return web.Response(
                body=b'',
                status=408,  # Request Timeout
            )

    async def handle_close_listener(self, request):
        """Close a listener and all its connections."""
        from aiohttp import web

        listener_id = request.match_info['listener_id']

        listener = self.listeners.get(listener_id)
        if not listener:
            return web.json_response(
                {'error': 'Listener not found'},
                status=404
            )

        # Mark as closed
        listener.closed = True

        # Close the wormhole
        try:
            await listener.manager.close()
        except Exception:
            pass

        # Remove from tracking
        del self.listeners[listener_id]

        # Close all associated connections
        for conn_id, conn in list(self.active_connections.items()):
            if conn.listener_id == listener_id:
                conn.closed = True
                try:
                    conn.protocol.transport.loseConnection()
                except Exception:
                    pass
                del self.active_connections[conn_id]

        return web.json_response({
            'status': 'closed',
        })

    async def handle_close_connection(self, request):
        """Close a specific connection."""
        from aiohttp import web

        conn_id = request.match_info['conn_id']

        conn = self.active_connections.get(conn_id)
        if not conn:
            return web.json_response(
                {'error': 'Connection not found'},
                status=404
            )

        # Mark as closed
        conn.closed = True

        # Close the transport
        try:
            conn.protocol.transport.loseConnection()
        except Exception:
            pass

        # Remove from tracking
        del self.active_connections[conn_id]

        return web.json_response({
            'status': 'closed',
        })


@click.group("daemon")
def daemon():
    """
    Wormhole daemon for browser integration.

    The daemon provides a local HTTP server that the browser extension
    uses to resolve WNS addresses and proxy HTTP requests through wormhole.
    """
    pass


@daemon.command("start")
@click.option(
    '-p', '--port',
    default=9475,
    help='Port to listen on (default: 9475)'
)
@click.option(
    '-v', '--verbose',
    is_flag=True,
    help='Enable verbose logging'
)
@async_command
async def start(port: int, verbose: bool):
    """
    Start the wormhole daemon.

    The daemon runs a local HTTP server that the browser extension
    communicates with to:

    \b
    - Check daemon status
    - Resolve WNS addresses to ephemeral codes
    - Proxy HTTP requests through wormhole connections

    Example:
        wh daemon start
        wh daemon start -p 8080
    """
    daemon_instance = WormholeDaemon(port=port, verbose=verbose)

    try:
        await daemon_instance.start()
    except KeyboardInterrupt:
        click.echo("\nDaemon stopped")


@daemon.command("status")
@click.option(
    '-p', '--port',
    default=9475,
    help='Daemon port (default: 9475)'
)
@async_command
async def status(port: int):
    """
    Check if the daemon is running.

    Example:
        wh daemon status
    """
    import httpx

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f'http://localhost:{port}/status')
            if response.status_code == 200:
                data = response.json()
                click.echo(f"Daemon running on port {port}")
                click.echo(f"  Version: {data.get('version', 'unknown')}")
                click.echo(f"  Connections: {data.get('connections', 0)}")
            else:
                click.echo(f"Daemon returned error: {response.status_code}")
    except Exception:
        click.echo(f"Daemon not running on port {port}")
        raise SystemExit(1)
