"""
wh listen - Accept connections on a wormhole code.

Daemon mode that listens for incoming wormhole connections.
Can forward to local ports or run integrated services like SSH.

Enterprise features:
- Authentication: --auth-method (none, pubkey, password, ldap)
- Audit logging: --audit-log
"""

import asyncio
import click
from typing import Optional

from wh.cli.main import async_command
from wh.core.wormhole_manager import WormholeManager

# Dilation timeout - should match browser extension timeout
DILATION_TIMEOUT = 30  # seconds


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
    '--serve',
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    help='Serve files from directory (browser extension compatible)'
)
@click.option(
    '--dilate/--no-dilate',
    default=True,
    help='Enable dilation for faster streaming (default: enabled)'
)
@click.option(
    '--code',
    help='Use specific code instead of generating one'
)
# Enterprise authentication options
@click.option(
    '--auth-method',
    type=click.Choice(['none', 'pubkey', 'password', 'ldap']),
    default='none',
    help='Authentication method (default: none)'
)
@click.option(
    '--authorized-keys',
    type=click.Path(exists=True),
    help='Path to authorized_keys file (for pubkey auth)'
)
@click.option(
    '--ldap-server',
    help='LDAP server URL (for ldap auth)'
)
@click.option(
    '--ldap-base-dn',
    help='LDAP base DN for user searches'
)
# Enterprise audit logging
@click.option(
    '--audit-log',
    type=click.Path(),
    help='Path to audit log file (JSON format)'
)
@click.pass_context
@async_command
async def listen(
    ctx: click.Context,
    port: Optional[int],
    ssh: bool,
    http: bool,
    serve: Optional[str],
    dilate: bool,
    code: Optional[str],
    auth_method: str,
    authorized_keys: Optional[str],
    ldap_server: Optional[str],
    ldap_base_dn: Optional[str],
    audit_log: Optional[str],
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
    ENTERPRISE AUTHENTICATION:
        # Require SSH public key authentication
        wh listen --ssh --auth-method=pubkey --authorized-keys=/etc/wh/authorized_keys

        # Use LDAP/AD authentication
        wh listen --ssh --auth-method=ldap --ldap-server=ldap://ad.company.com --ldap-base-dn="dc=company,dc=com"

    \b
    ENTERPRISE AUDIT LOGGING:
        # Enable JSON audit logging
        wh listen --ssh --audit-log=/var/log/wh/audit.log

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
    namespace = ctx.obj.get('namespace')

    # Set up enterprise features
    audit_logger = None

    # Configure authentication
    if auth_method != 'none':
        from wh.enterprise.auth import AuthMethod, create_authenticator

        method = AuthMethod(auth_method)

        if method == AuthMethod.PUBKEY:
            if not authorized_keys:
                raise click.ClickException("--authorized-keys required for pubkey auth")
            create_authenticator(method, authorized_keys=authorized_keys)
            click.echo(f"Authentication: pubkey (authorized_keys: {authorized_keys})", err=True)

        elif method == AuthMethod.LDAP:
            if not ldap_server or not ldap_base_dn:
                raise click.ClickException("--ldap-server and --ldap-base-dn required for ldap auth")
            create_authenticator(
                method,
                ldap_server=ldap_server,
                ldap_base_dn=ldap_base_dn,
            )
            click.echo(f"Authentication: LDAP ({ldap_server})", err=True)

        elif method == AuthMethod.PASSWORD:
            raise click.ClickException("Password auth requires --password-file (not yet implemented in CLI)")

    # Configure audit logging
    if audit_log:
        from wh.enterprise.audit import AuditLogger
        audit_logger = AuditLogger(log_file=audit_log)
        click.echo(f"Audit logging: {audit_log}", err=True)

    def status(msg: str) -> None:
        if verbose > 0:
            click.echo(f"[*] {msg}", err=True)

    # Create wormhole manager
    # Always enable dilation at protocol level - browser will check for WebRTC
    # support and skip dilation if not available (Python uses TCP-based dilation)
    manager = WormholeManager(
        relay_url=ctx.obj.get('relay'),
        transit_relay=ctx.obj.get('transit'),
        code_length=ctx.obj.get('code_length', 2),
        on_status=status if verbose > 0 else None,
        enable_dilation=True,  # Browser checks for WebRTC support before dilating
    )

    try:
        if code:
            await manager.create_and_set_code(code)
        else:
            code = await manager.create_and_allocate_code()

        click.echo(f"Listening on code: {code}", err=True)
        if namespace:
            click.echo(f"Namespace: {namespace}", err=True)
        click.echo("Press Ctrl+C to stop", err=True)

        # Log connection start if audit logging enabled
        if audit_logger:
            audit_logger.connection_start(code=code, namespace=namespace)

        if serve:
            # File server mode (browser extension compatible)
            from wh.http.server import HTTPFileServer

            if dilate:
                # Dilation mode - use WebRTC for faster streaming
                try:
                    status("Waiting for dilation...")
                    await asyncio.wait_for(manager.dilate(), timeout=DILATION_TIMEOUT)
                    status("Dilation established")
                except asyncio.TimeoutError:
                    status(f"Dilation timed out after {DILATION_TIMEOUT}s, falling back to message passing")
                except Exception as e:
                    status(f"Dilation failed: {e}, falling back to message passing")
            else:
                # Even without dilation, we need to wait for peer connection
                # (PAKE and version exchange) before we can exchange messages
                click.echo("[DEBUG] Waiting for peer connection...", err=True)
                await manager.verify_connection()
                click.echo("[DEBUG] Peer connected!", err=True)

            server = HTTPFileServer(manager, serve)
            await server.run()
        elif ssh or http or port:
            # These modes use dilation
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
            await asyncio.Event().wait()

    except KeyboardInterrupt:
        click.echo("\nStopping...", err=True)
    except Exception as e:
        if verbose > 0:
            raise
        raise click.ClickException(str(e))
    finally:
        # Log connection end if audit logging enabled
        if audit_logger:
            audit_logger.connection_end(code=code or "", namespace=namespace)
            audit_logger.close()
        await manager.close()
