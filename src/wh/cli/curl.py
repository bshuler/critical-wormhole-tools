"""
wh curl - HTTP requests through wormhole.

Make HTTP requests through a wormhole tunnel to a remote proxy.
"""

import click
from typing import Optional, Tuple

from wh.cli.main import async_command
from wh.core.wormhole_manager import WormholeManager


@click.command()
@click.argument('url')
@click.option(
    '--code',
    required=True,
    help='Wormhole code or WNS address (wh://xxx.wns) of the HTTP proxy'
)
@click.option(
    '-X', '--request',
    'method',
    default='GET',
    help='HTTP method (GET, POST, PUT, DELETE, etc.)'
)
@click.option(
    '-H', '--header',
    multiple=True,
    help='Request header (can be used multiple times)'
)
@click.option(
    '-d', '--data',
    help='Request body data'
)
@click.option(
    '--data-binary',
    type=click.Path(exists=True),
    help='Send file contents as request body'
)
@click.option(
    '-o', '--output',
    type=click.Path(),
    help='Write output to file'
)
@click.option(
    '-i', '--include',
    is_flag=True,
    help='Include response headers in output'
)
@click.option(
    '-s', '--silent',
    is_flag=True,
    help='Silent mode (no progress)'
)
@click.option(
    '-v', '--verbose',
    'curl_verbose',
    is_flag=True,
    help='Verbose output (show request/response details)'
)
@click.pass_context
@async_command
async def curl(
    ctx: click.Context,
    url: str,
    code: str,
    method: str,
    header: Tuple[str, ...],
    data: Optional[str],
    data_binary: Optional[str],
    output: Optional[str],
    include: bool,
    silent: bool,
    curl_verbose: bool,
) -> None:
    """
    HTTP requests through wormhole (curl-like).

    Makes HTTP requests through a wormhole tunnel. Requires a peer
    running `wh listen --http` to act as an HTTP proxy.

    \b
    Examples:
        # Simple GET request
        $ wh curl --code 7-guitar-sunset http://api.example.com/data

        # POST with JSON data
        $ wh curl --code 7-guitar-sunset -X POST \\
            -H "Content-Type: application/json" \\
            -d '{"key": "value"}' \\
            http://api.example.com/

        # Download file
        $ wh curl --code 7-guitar-sunset -o file.zip \\
            http://example.com/file.zip

        # With headers
        $ wh curl --code 7-guitar-sunset \\
            -H "Authorization: Bearer token" \\
            http://api.example.com/protected
    """
    verbose = ctx.obj.get('verbose', 0) or curl_verbose

    def status(msg: str) -> None:
        if verbose and not silent:
            click.echo(f"[*] {msg}", err=True)

    # Parse headers
    headers = {}
    for h in header:
        if ':' in h:
            key, value = h.split(':', 1)
            headers[key.strip()] = value.strip()

    # Read binary data if specified
    body = None
    if data_binary:
        with open(data_binary, 'rb') as f:
            body = f.read()
    elif data:
        body = data.encode('utf-8')

    # Create wormhole manager
    manager = WormholeManager(
        relay_url=ctx.obj.get('relay'),
        transit_relay=ctx.obj.get('transit'),
        on_status=status if verbose else None,
    )

    try:
        status(f"Connecting to {code}...")
        await manager.create_and_set_code(code)
        await manager.dilate()

        # Import HTTP client
        from wh.http.client import WormholeHTTPClient

        client = WormholeHTTPClient(manager)

        if curl_verbose:
            click.echo(f"> {method} {url}", err=True)
            for k, v in headers.items():
                click.echo(f"> {k}: {v}", err=True)
            click.echo(">", err=True)

        response = await client.request(
            method=method,
            url=url,
            headers=headers,
            body=body,
        )

        if curl_verbose:
            click.echo(f"< HTTP/1.1 {response.status_code} {response.reason}", err=True)
            for k, v in response.headers.items():
                click.echo(f"< {k}: {v}", err=True)
            click.echo("<", err=True)

        # Output
        if include:
            click.echo(f"HTTP/1.1 {response.status_code} {response.reason}")
            for k, v in response.headers.items():
                click.echo(f"{k}: {v}")
            click.echo()

        if output:
            with open(output, 'wb') as f:
                f.write(response.body)
            if not silent:
                click.echo(f"Saved to {output}", err=True)
        else:
            # Try to decode as text, fall back to binary
            try:
                click.echo(response.body.decode('utf-8'), nl=False)
            except UnicodeDecodeError:
                import sys
                sys.stdout.buffer.write(response.body)

    except KeyboardInterrupt:
        click.echo("\nCancelled", err=True)
    except Exception as e:
        if verbose:
            raise
        raise click.ClickException(str(e))
    finally:
        await manager.close()
