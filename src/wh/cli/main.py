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
        future = asyncio.ensure_future(run())

        # Run the reactor (which drives both Twisted and asyncio)
        if not reactor.running:
            reactor.run()

        # Get result (will raise if there was an exception)
        if future.done():
            return future.result()
        return None

    return wrapper


def resolve_relay(relay_option: str) -> tuple:
    """
    Resolve relay option to mailbox and transit URLs.

    Args:
        relay_option: Either a relay name from config, or a URL

    Returns:
        Tuple of (mailbox_url, transit_url)
    """
    from wh.relay.config import get_relay_manager

    if relay_option is None:
        # Use default relay from config
        manager = get_relay_manager()
        relay_config = manager.get_default_relay()
        return relay_config.mailbox_url, relay_config.transit_url

    # Check if it's a URL (contains ://)
    if '://' in relay_option:
        # It's a URL, use as-is (transit will use default)
        return relay_option, None

    # Check if it's a configured relay name
    manager = get_relay_manager()
    relay_config = manager.get_relay(relay_option)
    if relay_config:
        return relay_config.mailbox_url, relay_config.transit_url

    # Not a known name, treat as URL
    return relay_option, None


@click.group()
@click.version_option(version=wh.__version__, prog_name="wh")
@click.option(
    '--relay', '-r',
    envvar='WH_RELAY',
    default=None,
    help='Relay name (from config) or mailbox URL'
)
@click.option(
    '--transit',
    envvar='WH_TRANSIT',
    default=None,
    help='Custom transit relay URL'
)
@click.option(
    '-c', '--code-length',
    envvar='WH_CODE_LENGTH',
    default=2,
    type=int,
    help='Number of words in wormhole code (default: 2, e.g., 7-guitar-sunset)'
)
@click.option(
    '-v', '--verbose',
    count=True,
    help='Increase verbosity (-v for info, -vv for debug)'
)
@click.pass_context
def cli(ctx: click.Context, relay: str, transit: str, code_length: int, verbose: int) -> None:
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
      relay   Manage relays and run relay server
      daemon  Local daemon for browser extension

    \b
    Relay Configuration:
      Relays can be specified by name or URL:
        wh --relay myrelay nc -l   # Use configured relay
        wh --relay ws://server:4000/v1 nc -l  # Use URL directly

      Manage relays with:
        wh relay list              # Show configured relays
        wh relay add myrelay URL   # Add a relay
        wh relay set-default NAME  # Set default relay

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

    # Resolve relay option to URLs
    mailbox_url, transit_url = resolve_relay(relay)

    # Transit can be overridden
    if transit is not None:
        transit_url = transit

    ctx.obj['relay'] = mailbox_url
    ctx.obj['transit'] = transit_url
    ctx.obj['code_length'] = code_length
    ctx.obj['verbose'] = verbose


# Import and register subcommands
# These must be imported after cli group is defined, hence noqa: E402
from wh.cli.nc import nc  # noqa: E402
from wh.cli.listen import listen  # noqa: E402
from wh.cli.ssh import ssh  # noqa: E402
from wh.cli.scp import scp  # noqa: E402
from wh.cli.sftp import sftp  # noqa: E402
from wh.cli.curl import curl  # noqa: E402
from wh.cli.wget import wget  # noqa: E402
from wh.cli.ping import ping  # noqa: E402
from wh.cli.tunnel import tunnel  # noqa: E402
from wh.cli.proxy import proxy  # noqa: E402
from wh.cli.rsync import rsync  # noqa: E402
from wh.cli.serve import serve  # noqa: E402
from wh.cli.daemon import daemon  # noqa: E402
from wh.cli.relay import relay  # noqa: E402
from wh.wns.cli import identity, alias  # noqa: E402

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
cli.add_command(daemon)
cli.add_command(relay)
cli.add_command(identity)
cli.add_command(alias)


if __name__ == "__main__":
    cli()
