"""
CLI command for running a built-in wormhole relay server.

This makes wh completely self-contained - no external relay infrastructure needed.
"""

import asyncio
import click
import logging
import sys

logger = logging.getLogger(__name__)


@click.command()
@click.option(
    "--host",
    default="0.0.0.0",
    help="Host to bind to (default: 0.0.0.0)",
)
@click.option(
    "-p", "--port",
    "mailbox_port",
    default=4000,
    type=int,
    help="Mailbox (WebSocket) port (default: 4000)",
)
@click.option(
    "-t", "--transit-port",
    default=4001,
    type=int,
    help="Transit (TCP) relay port (default: 4001)",
)
@click.option(
    "--mailbox-only",
    is_flag=True,
    help="Only run mailbox server (no transit relay)",
)
@click.option(
    "--transit-only",
    is_flag=True,
    help="Only run transit relay (no mailbox server)",
)
@click.pass_context
def relay(
    ctx: click.Context,
    host: str,
    mailbox_port: int,
    transit_port: int,
    mailbox_only: bool,
    transit_only: bool,
) -> None:
    """
    Run a built-in wormhole relay server.

    This eliminates dependency on external relay infrastructure, making
    wh completely self-contained.

    USAGE:

        # Run full relay (mailbox + transit)
        wh relay

        # Custom ports
        wh relay -p 5000 -t 5001

        # Only mailbox server
        wh relay --mailbox-only

        # Only transit relay
        wh relay --transit-only

    CONFIGURING CLIENTS:

        # Use your relay with wh commands
        wh --relay ws://your-server:4000/v1 --transit tcp:your-server:4001 nc -l

        # Or set environment variables
        export WH_RELAY=ws://your-server:4000/v1
        export WH_TRANSIT=tcp:your-server:4001
        wh nc -l

    ARCHITECTURE:

        ┌─────────────────────────────────────────────────────────────┐
        │                     wh relay server                          │
        ├─────────────────────────────────────────────────────────────┤
        │  ┌─────────────────────┐    ┌─────────────────────────────┐ │
        │  │   Mailbox Server    │    │      Transit Relay          │ │
        │  │   (WebSocket)       │    │      (TCP)                  │ │
        │  │   Port: 4000        │    │      Port: 4001             │ │
        │  │                     │    │                             │ │
        │  │   - Nameplate alloc │    │   - Token matching          │ │
        │  │   - Message relay   │    │   - Bidirectional relay     │ │
        │  │   - PAKE signaling  │    │   - NAT traversal fallback  │ │
        │  └─────────────────────┘    └─────────────────────────────┘ │
        └─────────────────────────────────────────────────────────────┘
    """
    # Check for websockets dependency
    try:
        import websockets
    except ImportError:
        click.echo(
            "Error: websockets package required for relay server.\n"
            "Install with: pip install websockets",
            err=True,
        )
        sys.exit(1)

    if mailbox_only and transit_only:
        click.echo("Error: Cannot specify both --mailbox-only and --transit-only", err=True)
        sys.exit(1)

    # Configure logging
    verbose = ctx.obj.get("verbose", 0) if ctx.obj else 0
    if verbose:
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        )
    else:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s: %(message)s",
        )

    async def run():
        from wh.relay import MailboxServer, TransitRelay, RelayServer

        if mailbox_only:
            server = MailboxServer(host=host, port=mailbox_port)
            click.echo(f"Starting mailbox server on ws://{host}:{mailbox_port}/v1")
            click.echo("Press Ctrl+C to stop")
            await server.serve_forever()

        elif transit_only:
            server = TransitRelay(host=host, port=transit_port)
            click.echo(f"Starting transit relay on tcp://{host}:{transit_port}")
            click.echo("Press Ctrl+C to stop")
            await server.serve_forever()

        else:
            server = RelayServer(
                host=host,
                mailbox_port=mailbox_port,
                transit_port=transit_port,
            )
            click.echo(f"Starting wormhole relay server:")
            click.echo(f"  Mailbox: ws://{host}:{mailbox_port}/v1")
            click.echo(f"  Transit: tcp://{host}:{transit_port}")
            click.echo()
            click.echo("Configure clients with:")
            click.echo(f"  export WH_RELAY=ws://{host}:{mailbox_port}/v1")
            click.echo(f"  export WH_TRANSIT=tcp:{host}:{transit_port}")
            click.echo()
            click.echo("Press Ctrl+C to stop")
            await server.serve_forever()

    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        click.echo("\nRelay server stopped")
