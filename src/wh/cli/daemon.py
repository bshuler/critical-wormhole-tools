"""
wh daemon - Local daemon for browser extension integration.

Provides HTTP API for the browser extension to:
- Check daemon status
- Resolve WNS addresses
- Proxy HTTP requests through wormhole
"""

import asyncio
import click
from typing import Dict, Any
from functools import wraps

# Import wh first to ensure reactor is set up
import wh  # noqa: F401


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
    Local HTTP daemon for browser extension communication.

    Provides endpoints:
    - GET /status - Daemon status
    - POST /resolve - Resolve WNS address to code
    - POST /connect - Establish wormhole connection
    - GET /browse/<url> - Proxy HTTP request through wormhole
    """

    def __init__(self, port: int = 9475, verbose: bool = False):
        self.port = port
        self.verbose = verbose
        self.connections: Dict[str, Any] = {}
        self.server = None

    async def start(self):
        """Start the HTTP server."""
        from aiohttp import web

        app = web.Application()
        app.router.add_get('/status', self.handle_status)
        app.router.add_post('/resolve', self.handle_resolve)
        app.router.add_post('/connect', self.handle_connect)
        app.router.add_get('/browse/{url:.*}', self.handle_browse)
        app.router.add_get('/config/relays', self.handle_get_relays)
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
