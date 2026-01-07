"""
Main CLI entry point for wh tools.

Uses Click for command-line argument parsing and subcommand routing.
"""

import click
import asyncio
from functools import wraps
from typing import Any, Callable

# Import wh first to ensure reactor is set up
import wh  # noqa: F401


def async_command(f: Callable) -> Callable:
    """
    Decorator to run async Click commands.

    Wraps an async function to run it in the asyncio event loop,
    with proper handling of the Twisted reactor.
    """
    @wraps(f)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        from twisted.internet import reactor

        async def run():
            try:
                return await f(*args, **kwargs)
            finally:
                # Stop the reactor when done
                if reactor.running:
                    reactor.callFromThread(reactor.stop)

        # Schedule the coroutine
        loop = asyncio.get_event_loop()
        future = asyncio.ensure_future(run())

        # Run the reactor (which drives both Twisted and asyncio)
        if not reactor.running:
            reactor.run()

        # Get result (will raise if there was an exception)
        if future.done():
            return future.result()
        return None

    return wrapper


@click.group()
@click.version_option(version=wh.__version__, prog_name="wh")
@click.option(
    '--relay',
    envvar='WH_RELAY',
    default=None,
    help='Custom mailbox relay URL'
)
@click.option(
    '--transit',
    envvar='WH_TRANSIT',
    default=None,
    help='Custom transit relay URL'
)
@click.option(
    '-v', '--verbose',
    count=True,
    help='Increase verbosity (-v for info, -vv for debug)'
)
@click.pass_context
def cli(ctx: click.Context, relay: str, transit: str, verbose: int) -> None:
    """
    wh - Wormhole Tools

    Network utilities using Magic Wormhole's code-based addressing.
    Connect to any machine using a simple code like "7-guitar-sunset".

    \b
    Commands:
      nc      Netcat over wormhole - bidirectional pipe
      listen  Accept connections on a wormhole code
      ssh     SSH through wormhole
      scp     Secure copy through wormhole
      sftp    Interactive file transfer through wormhole
      curl    HTTP requests through wormhole
      wget    Download files through wormhole
      ping    Measure latency through wormhole
      tunnel  SSH-style port forwarding through wormhole
      proxy   SOCKS5 proxy through wormhole
      rsync   Incremental file sync through wormhole

    \b
    Examples:
      # Simple pipe (like netcat)
      wh nc --listen          # Side A: generates code
      wh nc 7-guitar-sunset   # Side B: connects with code

      # SSH to a remote machine
      wh listen --ssh         # Remote: starts SSH server on wormhole
      wh ssh 7-guitar-sunset  # Local: SSH to remote via code
    """
    ctx.ensure_object(dict)
    ctx.obj['relay'] = relay
    ctx.obj['transit'] = transit
    ctx.obj['verbose'] = verbose


# Import and register subcommands
# These will be implemented in subsequent phases
from wh.cli.nc import nc
from wh.cli.listen import listen
from wh.cli.ssh import ssh
from wh.cli.scp import scp
from wh.cli.sftp import sftp
from wh.cli.curl import curl
from wh.cli.wget import wget
from wh.cli.ping import ping
from wh.cli.tunnel import tunnel
from wh.cli.proxy import proxy
from wh.cli.rsync import rsync
from wh.cli.serve import serve
from wh.wns.cli import identity, alias

cli.add_command(nc)
cli.add_command(listen)
cli.add_command(ssh)
cli.add_command(scp)
cli.add_command(sftp)
cli.add_command(curl)
cli.add_command(wget)
cli.add_command(ping)
cli.add_command(tunnel)
cli.add_command(proxy)
cli.add_command(rsync)
cli.add_command(serve)
cli.add_command(identity)
cli.add_command(alias)


if __name__ == "__main__":
    cli()
