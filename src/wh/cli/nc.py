"""
wh nc - Netcat over wormhole.

Provides bidirectional pipe functionality like netcat, but using
wormhole's code-based addressing instead of IP addresses.
"""

import asyncio
import click
import signal
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

        # Connect using WNS address (persistent naming)
        $ wh nc wh://abc123def456.wns

    \b
    Persistent mode (-k):
        # Terminal 1: Listen for multiple connections
        $ wh nc -l -k
        Code: 7-guitar-sunset
        Waiting for peer...
        # First client connects, data flows...
        # Client disconnects
        Waiting for connection #2...
        # Second client can connect with same code!
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

    # Set up signal handling for graceful shutdown
    shutdown_event = asyncio.Event()

    def handle_signal(signum, frame):
        click.echo("\nShutting down...", err=True)
        shutdown_event.set()

    # Install signal handlers
    original_sigint = signal.signal(signal.SIGINT, handle_signal)
    original_sigterm = signal.signal(signal.SIGTERM, handle_signal)

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

        # Run connection loop
        connection_count = 0
        while not shutdown_event.is_set():
            connection_count += 1

            if listen and connection_count > 1:
                click.echo(f"\nWaiting for connection #{connection_count}...", err=True)

            # Create bidirectional pipe for this connection
            pipe = BidirectionalPipe(
                stdin=sys.stdin.buffer,
                stdout=sys.stdout.buffer,
                on_status=status if verbose > 0 else None,
            )

            # Run as initiator or listener based on mode
            try:
                if listen:
                    await pipe.run_as_listener(manager, shutdown_event=shutdown_event)
                else:
                    await pipe.run_as_initiator(manager, shutdown_event=shutdown_event)
            except asyncio.CancelledError:
                break

            # If not keep_open mode, exit after first connection
            if not keep_open:
                break

            if listen:
                click.echo("Connection closed.", err=True)

    except KeyboardInterrupt:
        click.echo("\nInterrupted", err=True)
    except Exception as e:
        if verbose > 0:
            raise
        raise click.ClickException(str(e))
    finally:
        # Restore signal handlers
        signal.signal(signal.SIGINT, original_sigint)
        signal.signal(signal.SIGTERM, original_sigterm)
        await manager.close()
