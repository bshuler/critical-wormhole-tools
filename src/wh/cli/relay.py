"""
CLI commands for relay management and running a built-in relay server.

This makes wh completely self-contained - no external relay infrastructure needed.
"""

import asyncio
import click
import json
import logging
import sys
from typing import Optional

logger = logging.getLogger(__name__)


@click.group()
@click.pass_context
def relay(ctx: click.Context) -> None:
    """
    Manage relay servers and configurations.

    Relays are used for wormhole rendezvous (mailbox) and NAT traversal (transit).
    You can use the default public relay or configure your own.

    \b
    Commands:
      serve       Run a built-in relay server
      list        List configured relays
      add         Add a new relay configuration
      remove      Remove a relay configuration
      set-default Set the default relay
      share       Share relay config via wormhole code

    \b
    Examples:
        # List configured relays
        wh relay list

        # Add a private relay
        wh relay add myrelay ws://myserver:4000/v1 tcp:myserver:4001

        # Run your own relay
        wh relay serve

        # Share relay config with someone
        wh relay share myrelay
    """
    pass


@relay.command("serve")
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
@click.option(
    "-a", "--advertise",
    is_flag=True,
    help="Advertise relay via mDNS/Bonjour for local network discovery",
)
@click.option(
    "-n", "--name",
    "advertise_name",
    default=None,
    help="Name to advertise (default: hostname)",
)
@click.pass_context
def serve(
    ctx: click.Context,
    host: str,
    mailbox_port: int,
    transit_port: int,
    mailbox_only: bool,
    transit_only: bool,
    advertise: bool,
    advertise_name: Optional[str],
) -> None:
    """
    Run a built-in wormhole relay server.

    This eliminates dependency on external relay infrastructure, making
    wh completely self-contained.

    \b
    Examples:
        # Run full relay (mailbox + transit)
        wh relay serve

        # Custom ports
        wh relay serve -p 5000 -t 5001

        # Only mailbox server
        wh relay serve --mailbox-only

        # Only transit relay
        wh relay serve --transit-only

        # Advertise on local network via mDNS/Bonjour
        wh relay serve --advertise
        wh relay serve --advertise --name myrelay

    \b
    Configuring clients:
        wh --relay ws://your-server:4000/v1 --transit tcp:your-server:4001 nc -l

        # Or set environment variables
        export WH_RELAY=ws://your-server:4000/v1
        export WH_TRANSIT=tcp:your-server:4001

        # Or discover on local network
        wh relay discover --add
    """
    # Check for websockets dependency
    import importlib.util
    if importlib.util.find_spec("websockets") is None:
        click.echo(
            "Error: websockets package required for relay server.\n"
            "Install with: pip install 'wh[relay]'",
            err=True,
        )
        sys.exit(1)

    if mailbox_only and transit_only:
        click.echo("Error: Cannot specify both --mailbox-only and --transit-only", err=True)
        sys.exit(1)

    # Check for zeroconf if advertising
    zeroconf_available = False
    if advertise:
        if importlib.util.find_spec("zeroconf") is not None:
            zeroconf_available = True
        else:
            click.echo(
                "Warning: zeroconf package not installed. "
                "Install with: pip install zeroconf",
                err=True,
            )
            click.echo("Continuing without mDNS advertisement...", err=True)

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

    def setup_mdns_advertisement(relay_name: str, mb_port: int, tr_port: int) -> Optional[tuple]:
        """Set up mDNS service advertisement."""
        if not (advertise and zeroconf_available):
            return None

        import socket
        from zeroconf import ServiceInfo, Zeroconf

        hostname = socket.gethostname()
        service_name = relay_name or hostname

        # Get local IP address
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
        except Exception:
            local_ip = "127.0.0.1"

        service_info = ServiceInfo(
            "_wormhole-relay._tcp.local.",
            f"{service_name}._wormhole-relay._tcp.local.",
            addresses=[socket.inet_aton(local_ip)],
            port=mb_port,
            properties={
                "name": service_name.encode(),
                "transit_port": str(tr_port).encode(),
                "version": "1".encode(),
            },
        )

        zc = Zeroconf()
        zc.register_service(service_info)
        click.echo(f"  mDNS: {service_name} (discoverable via 'wh relay discover')")
        return (zc, service_info)

    def cleanup_mdns(mdns_info: Optional[tuple]) -> None:
        """Clean up mDNS registration."""
        if mdns_info:
            zc, service_info = mdns_info
            zc.unregister_service(service_info)
            zc.close()

    async def run():
        from wh.relay import MailboxServer, TransitRelay, RelayServer

        mdns_info = None

        if mailbox_only:
            server = MailboxServer(host=host, port=mailbox_port)
            click.echo(f"Starting mailbox server on ws://{host}:{mailbox_port}/v1")
            mdns_info = setup_mdns_advertisement(advertise_name, mailbox_port, 0)
            click.echo("Press Ctrl+C to stop")
            try:
                await server.serve_forever()
            finally:
                cleanup_mdns(mdns_info)

        elif transit_only:
            server = TransitRelay(host=host, port=transit_port)
            click.echo(f"Starting transit relay on tcp://{host}:{transit_port}")
            click.echo("Press Ctrl+C to stop")
            try:
                await server.serve_forever()
            finally:
                cleanup_mdns(mdns_info)

        else:
            server = RelayServer(
                host=host,
                mailbox_port=mailbox_port,
                transit_port=transit_port,
            )
            click.echo("Starting wormhole relay server:")
            click.echo(f"  Mailbox: ws://{host}:{mailbox_port}/v1")
            click.echo(f"  Transit: tcp://{host}:{transit_port}")
            mdns_info = setup_mdns_advertisement(advertise_name, mailbox_port, transit_port)
            click.echo()
            click.echo("Configure clients with:")
            click.echo(f"  export WH_RELAY=ws://{host}:{mailbox_port}/v1")
            click.echo(f"  export WH_TRANSIT=tcp:{host}:{transit_port}")
            click.echo()
            click.echo("Or add to your relay config:")
            click.echo(f"  wh relay add myrelay ws://{host}:{mailbox_port}/v1 tcp:{host}:{transit_port}")
            click.echo()
            click.echo("Press Ctrl+C to stop")
            try:
                await server.serve_forever()
            finally:
                cleanup_mdns(mdns_info)

    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        click.echo("\nRelay server stopped")


@relay.command("list")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_context
def list_relays(ctx: click.Context, as_json: bool) -> None:
    """
    List configured relay servers.

    Shows all relays stored in ~/.wh/relays.yaml.
    """
    from wh.relay.config import get_relay_manager

    manager = get_relay_manager()
    config = manager.load()
    relays = manager.list_relays()

    if as_json:
        output = {
            "default": config.default,
            "relays": [r.to_dict() for r in relays],
        }
        click.echo(json.dumps(output, indent=2))
        return

    if not relays:
        click.echo("No relays configured")
        return

    for r in relays:
        default_marker = " (default)" if r.name == config.default else ""
        click.echo(f"{r.name}{default_marker}")
        click.echo(f"  Mailbox: {r.mailbox_url}")
        click.echo(f"  Transit: {r.transit_url}")
        if r.description:
            click.echo(f"  Description: {r.description}")
        if r.namespace_key:
            click.echo("  Namespace: encrypted")
        click.echo()


@relay.command("add")
@click.argument("name")
@click.argument("mailbox_url")
@click.argument("transit_url")
@click.option("-d", "--description", help="Description of this relay")
@click.option("--default", "set_default", is_flag=True, help="Set as default relay")
@click.option("--namespace-key", help="Base64 namespace encryption key")
@click.pass_context
def add_relay(
    ctx: click.Context,
    name: str,
    mailbox_url: str,
    transit_url: str,
    description: Optional[str],
    set_default: bool,
    namespace_key: Optional[str],
) -> None:
    """
    Add a new relay configuration.

    \b
    Arguments:
      NAME         Unique name for this relay
      MAILBOX_URL  WebSocket URL (e.g., ws://server:4000/v1)
      TRANSIT_URL  Transit URL (e.g., tcp:server:4001)

    \b
    Examples:
        # Add a private relay
        wh relay add myrelay ws://myserver:4000/v1 tcp:myserver:4001

        # Add and set as default
        wh relay add work ws://work.example.com:4000/v1 tcp:work.example.com:4001 --default

        # Add with description
        wh relay add home ws://192.168.1.10:4000/v1 tcp:192.168.1.10:4001 -d "Home network relay"
    """
    from wh.relay.config import get_relay_manager

    manager = get_relay_manager()

    # Check if already exists
    existing = manager.get_relay(name)
    if existing:
        click.echo(f"Error: Relay '{name}' already exists. Remove it first with 'wh relay remove {name}'", err=True)
        sys.exit(1)

    manager.add_relay(
        name=name,
        mailbox_url=mailbox_url,
        transit_url=transit_url,
        namespace_key=namespace_key,
        description=description,
        set_default=set_default,
    )

    click.echo(f"Added relay '{name}'")
    if set_default:
        click.echo("Set as default relay")


@relay.command("remove")
@click.argument("name")
@click.option("-f", "--force", is_flag=True, help="Don't ask for confirmation")
@click.pass_context
def remove_relay(ctx: click.Context, name: str, force: bool) -> None:
    """
    Remove a relay configuration.

    Cannot remove the 'public' relay (built-in default).

    \b
    Examples:
        wh relay remove myrelay
        wh relay remove myrelay --force
    """
    from wh.relay.config import get_relay_manager

    manager = get_relay_manager()

    if not manager.get_relay(name):
        click.echo(f"Error: Relay '{name}' not found", err=True)
        sys.exit(1)

    if not force:
        if not click.confirm(f"Remove relay '{name}'?"):
            return

    try:
        manager.remove_relay(name)
        click.echo(f"Removed relay '{name}'")
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@relay.command("set-default")
@click.argument("name")
@click.pass_context
def set_default(ctx: click.Context, name: str) -> None:
    """
    Set the default relay.

    The default relay is used when no --relay option is specified.

    \b
    Examples:
        wh relay set-default myrelay
        wh relay set-default public
    """
    from wh.relay.config import get_relay_manager

    manager = get_relay_manager()

    try:
        manager.set_default(name)
        click.echo(f"Default relay set to '{name}'")
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@relay.command("share")
@click.argument("name")
@click.option("-r", "--receive", is_flag=True, help="Receive a shared relay config")
@click.option("--code", help="Wormhole code (for receiving)")
@click.option("--default", "set_default", is_flag=True, help="Set received relay as default")
@click.pass_context
def share_relay(
    ctx: click.Context,
    name: str,
    receive: bool,
    code: Optional[str],
    set_default: bool,
) -> None:
    """
    Share relay configuration via wormhole code.

    This makes it easy to distribute relay settings to team members.

    \b
    Sending:
        wh relay share myrelay
        # Displays a wormhole code for the receiver

    \b
    Receiving:
        wh relay share newname --receive --code 7-guitar-sunset
        # Imports the relay config with name 'newname'
    """
    from wh.relay.config import get_relay_manager

    manager = get_relay_manager()

    if receive:
        if not code:
            click.echo("Error: --code required when receiving", err=True)
            sys.exit(1)

        async def receive_config():
            from wh.core.wormhole_manager import WormholeManager

            wh_manager = WormholeManager(
                relay_url=ctx.obj.get("relay") if ctx.obj else None,
                transit_relay=ctx.obj.get("transit") if ctx.obj else None,
                code_length=ctx.obj.get("code_length", 2) if ctx.obj else 2,
            )

            try:
                async with wh_manager:
                    await wh_manager.create_and_set_code(code)
                    click.echo(f"Connecting to {code}...", err=True)
                    await wh_manager.establish()

                    # Receive the config
                    data = await wh_manager.receive_json()
                    click.echo("Received relay configuration", err=True)

                    # Import it
                    relay = manager.import_relay(
                        data,
                        name_override=name,
                        set_default=set_default,
                    )

                    click.echo(f"Added relay '{relay.name}'")
                    click.echo(f"  Mailbox: {relay.mailbox_url}")
                    click.echo(f"  Transit: {relay.transit_url}")
                    if set_default:
                        click.echo("Set as default relay")

            except Exception as e:
                click.echo(f"Error: {e}", err=True)
                sys.exit(1)

        asyncio.run(receive_config())

    else:
        # Sending mode
        relay = manager.get_relay(name)
        if not relay:
            click.echo(f"Error: Relay '{name}' not found", err=True)
            sys.exit(1)

        export_data = manager.export_relay(name)

        async def send_config():
            from wh.core.wormhole_manager import WormholeManager

            wh_manager = WormholeManager(
                relay_url=ctx.obj.get("relay") if ctx.obj else None,
                transit_relay=ctx.obj.get("transit") if ctx.obj else None,
                code_length=ctx.obj.get("code_length", 2) if ctx.obj else 2,
            )

            try:
                async with wh_manager:
                    await wh_manager.create_and_allocate_code()
                    click.echo("Share this relay config with:")
                    click.echo(f"  wh relay share NEWNAME --receive --code {wh_manager.code}")
                    click.echo()
                    click.echo("Waiting for receiver...", err=True)

                    await wh_manager.establish()
                    click.echo("Connected, sending config...", err=True)

                    await wh_manager.send_json(export_data)
                    click.echo(f"Relay '{name}' configuration sent successfully")

            except Exception as e:
                click.echo(f"Error: {e}", err=True)
                sys.exit(1)

        asyncio.run(send_config())


@relay.command("discover")
@click.option("--timeout", default=5, type=int, help="Discovery timeout in seconds")
@click.option("--add", "add_found", is_flag=True, help="Add discovered relays to config")
@click.pass_context
def discover_relays(ctx: click.Context, timeout: int, add_found: bool) -> None:
    """
    Discover relays on local network via mDNS/Bonjour.

    Searches for wormhole relay services advertised on the local network.
    Requires the zeroconf package.

    \b
    Examples:
        # Find relays on local network
        wh relay discover

        # Find and add to config
        wh relay discover --add
    """
    try:
        from zeroconf import ServiceBrowser, Zeroconf, ServiceListener
    except ImportError:
        click.echo(
            "Error: zeroconf package required for relay discovery.\n"
            "Install with: pip install zeroconf",
            err=True,
        )
        sys.exit(1)

    import socket
    import time
    from wh.relay.config import get_relay_manager

    found_relays = []

    class RelayListener(ServiceListener):
        def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
            info = zc.get_service_info(type_, name)
            if info:
                host = socket.inet_ntoa(info.addresses[0]) if info.addresses else None
                if host:
                    mailbox_port = info.port
                    transit_port = info.properties.get(b"transit_port", b"4001").decode()
                    relay_name = info.properties.get(b"name", name.split(".")[0].encode()).decode()

                    found_relays.append({
                        "name": relay_name,
                        "host": host,
                        "mailbox_port": mailbox_port,
                        "transit_port": int(transit_port),
                    })
                    click.echo(f"Found: {relay_name} at {host}")

        def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
            pass

        def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
            pass

    click.echo(f"Searching for wormhole relays (timeout: {timeout}s)...")

    zeroconf = Zeroconf()
    listener = RelayListener()
    ServiceBrowser(zeroconf, "_wormhole-relay._tcp.local.", listener)

    try:
        time.sleep(timeout)
    finally:
        zeroconf.close()

    if not found_relays:
        click.echo("No relays found on local network")
        return

    click.echo(f"\nFound {len(found_relays)} relay(s):")
    for r in found_relays:
        click.echo(f"  {r['name']}: ws://{r['host']}:{r['mailbox_port']}/v1")

    if add_found:
        manager = get_relay_manager()
        for r in found_relays:
            try:
                manager.add_relay(
                    name=r["name"],
                    mailbox_url=f"ws://{r['host']}:{r['mailbox_port']}/v1",
                    transit_url=f"tcp:{r['host']}:{r['transit_port']}",
                    description="Discovered via mDNS",
                )
                click.echo(f"Added relay '{r['name']}'")
            except Exception as e:
                click.echo(f"Could not add '{r['name']}': {e}", err=True)
