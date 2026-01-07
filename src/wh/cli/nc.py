"""
wh nc - Netcat over wormhole.

Provides bidirectional pipe functionality like netcat, but using
wormhole's code-based addressing instead of IP addresses.
"""

import click
import sys
from typing import Optional

from wh.cli.main import async_command
from wh.core.wormhole_manager import WormholeManager
from wh.core.protocol import BidirectionalPipe


@click.command()
@click.argument('code', required=False)
@click.option(
    '-l', '--listen',
    is_flag=True,
    help='Listen mode - generate a code and wait for peer'
)
@click.option(
    '-k', '--keep-open',
    is_flag=True,
    help='Keep listening for multiple connections'
)
@click.pass_context
@async_command
async def nc(
    ctx: click.Context,
    code: Optional[str],
    listen: bool,
    keep_open: bool,
) -> None:
    """
    Netcat over wormhole - bidirectional pipe.

    \b
    LISTEN MODE (generate code, wait for peer):
        wh nc -l
        # Displays code like "7-guitar-sunset", waits for peer

    \b
    CONNECT MODE (connect using code):
        wh nc 7-guitar-sunset
        # Connects to the peer who shared that code

    Once connected, stdin/stdout flow bidirectionally between peers.
    Type on one side, see it on the other. Great for simple data
    transfer or testing connectivity.

    \b
    Examples:
        # Terminal 1: Listen and wait
        $ wh nc -l
        Code: 7-guitar-sunset
        Waiting for peer...

        # Terminal 2: Connect
        $ wh nc 7-guitar-sunset
        Connected!

        # Now type on either side - text flows both ways
    """
    verbose = ctx.obj.get('verbose', 0)

    def status(msg: str) -> None:
        if verbose > 0:
            click.echo(f"[*] {msg}", err=True)

    # Validate arguments
    if listen and code:
        raise click.UsageError("Cannot specify both --listen and a code")
    if not listen and not code:
        raise click.UsageError("Must specify either --listen or a code to connect to")

    # Create wormhole manager
    manager = WormholeManager(
        relay_url=ctx.obj.get('relay'),
        transit_relay=ctx.obj.get('transit'),
        on_status=status if verbose > 0 else None,
    )

    try:
        if listen:
            # Generate code and wait for peer
            code = await manager.create_and_allocate_code()
            click.echo(f"Code: {code}", err=True)
            click.echo("Waiting for peer...", err=True)
        else:
            # Connect with provided code
            await manager.create_and_set_code(code)
            status(f"Connecting with code: {code}")

        # Dilate for streaming
        await manager.dilate()

        if not listen:
            click.echo("Connected!", err=True)

        # Create bidirectional pipe
        pipe = BidirectionalPipe(
            stdin=sys.stdin.buffer,
            stdout=sys.stdout.buffer,
            on_status=status if verbose > 0 else None,
        )

        # Run as initiator or listener based on mode
        if listen:
            await pipe.run_as_listener(manager)
        else:
            await pipe.run_as_initiator(manager)

    except KeyboardInterrupt:
        click.echo("\nInterrupted", err=True)
    except Exception as e:
        if verbose > 0:
            raise
        raise click.ClickException(str(e))
    finally:
        await manager.close()
