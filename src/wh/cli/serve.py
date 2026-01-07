"""
wh serve - Persistent WNS server with identity-based addressing.

Unlike `wh listen` which uses ephemeral codes, `wh serve` uses a persistent
WNS identity. The address (wh://xxx.wns) stays the same across connections
and server restarts.
"""

import click
from typing import Optional

from wh.cli.main import async_command


@click.command()
@click.option(
    '--identity', '-i',
    default=None,
    help='WNS identity address to use (default: first identity)'
)
@click.option(
    '--ssh',
    is_flag=True,
    help='Run SSH server mode'
)
@click.option(
    '--http',
    is_flag=True,
    help='Run HTTP proxy mode'
)
@click.option(
    '--nc',
    is_flag=True,
    help='Run netcat mode (stdin/stdout)'
)
@click.option(
    '--port', '-p',
    type=int,
    default=None,
    help='Run port forwarding mode to this local port'
)
@click.pass_context
@async_command
async def serve(
    ctx: click.Context,
    identity: Optional[str],
    ssh: bool,
    http: bool,
    nc: bool,
    port: Optional[int],
) -> None:
    """
    Run a persistent WNS server with identity-based addressing.

    Unlike `wh listen`, this command:
    - Uses a persistent WNS identity (create with `wh identity create`)
    - Publishes codes to DHT for discovery
    - Automatically generates new codes after each connection
    - Keeps the same address (wh://xxx.wns) forever

    \b
    Examples:
        # Start SSH server with default identity
        wh serve --ssh

        # Start SSH server with specific identity
        wh serve --identity abc123def456 --ssh

        # Start HTTP proxy
        wh serve --http

        # Port forwarding to local port 8080
        wh serve --port 8080

    \b
    Clients connect using the WNS address:
        wh ssh wh://abc123def456.wns
    """
    verbose = ctx.obj.get('verbose', 0)

    def status(msg: str) -> None:
        if verbose > 0 or msg.startswith("Listening") or msg.startswith("Current code"):
            click.echo(f"[*] {msg}", err=True)

    # Determine service type
    service_type = "ssh"  # default
    if ssh:
        service_type = "ssh"
    elif http:
        service_type = "http"
    elif nc:
        service_type = "nc"
    elif port:
        service_type = "port"

    # Validate options
    mode_count = sum([ssh, http, nc, port is not None])
    if mode_count > 1:
        raise click.UsageError("Only one mode (--ssh, --http, --nc, --port) can be specified")

    if service_type == "port" and not port:
        raise click.UsageError("--port requires a port number")

    # Load identity
    from wh.wns.identity import WNSIdentityStore

    store = WNSIdentityStore()

    if identity:
        wns_identity = store.load_identity(identity)
        if not wns_identity:
            raise click.ClickException(f"Identity not found: {identity}")
    else:
        wns_identity = store.get_default_identity()
        if not wns_identity:
            raise click.ClickException(
                "No identity found. Create one with: wh identity create"
            )

    click.echo(f"Using identity: {wns_identity.full_address}", err=True)
    if wns_identity.name:
        click.echo(f"Name: {wns_identity.name}", err=True)
    click.echo(f"Service: {service_type}", err=True)
    click.echo("", err=True)

    # Run server
    from wh.wns.server import WNSServer, ServiceType

    server = WNSServer(
        identity=wns_identity,
        service_type=ServiceType(service_type),
        port=port,
        relay_url=ctx.obj.get('relay'),
        transit_relay=ctx.obj.get('transit'),
        on_status=status,
    )

    try:
        await server.run()
    except KeyboardInterrupt:
        click.echo("\nShutting down...", err=True)
    except Exception as e:
        if verbose > 0:
            raise
        raise click.ClickException(str(e))
