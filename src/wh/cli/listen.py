"""
wh listen - Accept connections on a wormhole code.

Daemon mode that listens for incoming wormhole connections.
Can forward to local ports or run integrated services like SSH.
"""

import click
from typing import Optional

from wh.cli.main import async_command
from wh.core.wormhole_manager import WormholeManager


@click.command()
@click.option(
    '-p', '--port',
    type=int,
    help='Forward connections to this local port'
)
@click.option(
    '--ssh',
    is_flag=True,
    help='Run SSH server on wormhole'
)
@click.option(
    '--http',
    is_flag=True,
    help='Run HTTP proxy on wormhole'
)
@click.option(
    '--code',
    help='Use specific code instead of generating one'
)
@click.pass_context
@async_command
async def listen(
    ctx: click.Context,
    port: Optional[int],
    ssh: bool,
    http: bool,
    code: Optional[str],
) -> None:
    """
    Listen daemon - accept connections on a wormhole code.

    \b
    BASIC MODE (forward to local port):
        wh listen -p 8080
        # Forwards incoming wormhole connections to localhost:8080

    \b
    SSH SERVER MODE:
        wh listen --ssh
        # Starts an SSH server accessible via the wormhole code

    \b
    HTTP PROXY MODE:
        wh listen --http
        # Accepts HTTP requests and proxies them

    The generated code is displayed and remains valid until the
    process is terminated with Ctrl+C.

    \b
    Examples:
        # Forward to local web server
        $ wh listen -p 3000
        Listening on code: 7-guitar-sunset
        Press Ctrl+C to stop

        # Run SSH server (allows `wh ssh 7-guitar-sunset`)
        $ wh listen --ssh
        Listening on code: 7-guitar-sunset
        SSH server ready
    """
    verbose = ctx.obj.get('verbose', 0)

    def status(msg: str) -> None:
        if verbose > 0:
            click.echo(f"[*] {msg}", err=True)

    # Create wormhole manager
    manager = WormholeManager(
        relay_url=ctx.obj.get('relay'),
        transit_relay=ctx.obj.get('transit'),
        on_status=status if verbose > 0 else None,
    )

    try:
        if code:
            await manager.create_and_set_code(code)
        else:
            code = await manager.create_and_allocate_code()

        click.echo(f"Listening on code: {code}", err=True)
        click.echo("Press Ctrl+C to stop", err=True)

        await manager.dilate()

        if ssh:
            # SSH server mode
            from wh.ssh.server import SSHServerHandler
            handler = SSHServerHandler(manager)
            await handler.run()
        elif http:
            # HTTP proxy mode
            from wh.http.client import HTTPProxyHandler
            handler = HTTPProxyHandler(manager)
            await handler.run()
        elif port:
            # Port forwarding mode
            from wh.core.forwarder import PortForwarder
            forwarder = PortForwarder(manager, local_port=port)
            await forwarder.run()
        else:
            # Generic mode - just accept connections
            click.echo("Waiting for connections...", err=True)
            # For now, just keep running
            import asyncio
            await asyncio.Event().wait()

    except KeyboardInterrupt:
        click.echo("\nStopping...", err=True)
    except Exception as e:
        if verbose > 0:
            raise
        raise click.ClickException(str(e))
    finally:
        await manager.close()
