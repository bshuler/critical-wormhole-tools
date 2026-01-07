"""
wh wget - Download files through wormhole.

Download files through a wormhole tunnel with wget-like interface.
"""

import click
import os
from typing import Optional
from urllib.parse import urlparse

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
    '-O', '--output-document',
    'output',
    help='Output filename (use - for stdout)'
)
@click.option(
    '-P', '--directory-prefix',
    'prefix',
    default='.',
    help='Directory to save files'
)
@click.option(
    '-q', '--quiet',
    is_flag=True,
    help='Quiet mode (no output except errors)'
)
@click.option(
    '-c', '--continue',
    'continue_download',
    is_flag=True,
    help='Resume partially downloaded file (if supported)'
)
@click.option(
    '--header',
    multiple=True,
    help='Additional headers to send'
)
@click.pass_context
@async_command
async def wget(
    ctx: click.Context,
    url: str,
    code: str,
    output: Optional[str],
    prefix: str,
    quiet: bool,
    continue_download: bool,
    header: tuple,
) -> None:
    """
    Download files through wormhole (wget-like).

    Downloads files through a wormhole tunnel. Requires a peer
    running `wh listen --http` to act as an HTTP proxy.

    \b
    Examples:
        # Download file (auto-detect filename)
        $ wh wget --code 7-guitar-sunset http://example.com/file.zip

        # Download to specific filename
        $ wh wget --code 7-guitar-sunset -O myfile.zip \\
            http://example.com/file.zip

        # Download to stdout
        $ wh wget --code 7-guitar-sunset -O - \\
            http://example.com/data.json | jq .

        # Download to directory
        $ wh wget --code 7-guitar-sunset -P ~/Downloads \\
            http://example.com/file.zip
    """
    verbose = ctx.obj.get('verbose', 0)

    def status(msg: str) -> None:
        if not quiet:
            click.echo(msg, err=True)

    # Determine output filename
    if output == '-':
        output_path = None  # Will write to stdout
    elif output:
        output_path = os.path.join(prefix, output) if prefix != '.' else output
    else:
        # Extract filename from URL
        parsed = urlparse(url)
        filename = os.path.basename(parsed.path)
        if not filename:
            filename = 'index.html'
        output_path = os.path.join(prefix, filename)

    # Parse headers
    headers = {}
    for h in header:
        if ':' in h:
            key, value = h.split(':', 1)
            headers[key.strip()] = value.strip()

    # Create wormhole manager
    manager = WormholeManager(
        relay_url=ctx.obj.get('relay'),
        transit_relay=ctx.obj.get('transit'),
        on_status=(lambda m: status(f"[*] {m}")) if verbose > 0 else None,
    )

    try:
        status(f"Connecting to {code}...")
        await manager.create_and_set_code(code)
        await manager.dilate()

        # Import HTTP client
        from wh.http.client import WormholeHTTPClient

        client = WormholeHTTPClient(manager)

        status(f"Downloading {url}...")

        response = await client.request(
            method='GET',
            url=url,
            headers=headers,
        )

        if response.status_code != 200:
            raise click.ClickException(
                f"HTTP {response.status_code}: {response.reason}"
            )

        # Write output
        if output_path is None:
            # Write to stdout
            import sys
            sys.stdout.buffer.write(response.body)
        else:
            # Write to file
            os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
            with open(output_path, 'wb') as f:
                f.write(response.body)
            status(f"Saved to {output_path} ({len(response.body)} bytes)")

    except KeyboardInterrupt:
        click.echo("\nCancelled", err=True)
    except Exception as e:
        if verbose > 0:
            raise
        raise click.ClickException(str(e))
    finally:
        await manager.close()
