"""
wh ssh - SSH through wormhole.

Connect to an SSH server running on a wormhole code.
"""

import click
from typing import Optional

from wh.cli.main import async_command
from wh.core.wormhole_manager import WormholeManager


@click.command()
@click.argument('destination')
@click.option(
    '-l', '--login',
    help='Username for SSH login'
)
@click.option(
    '-i', '--identity',
    type=click.Path(exists=True),
    help='Path to private key file'
)
@click.option(
    '-t', '--tty',
    is_flag=True,
    help='Force TTY allocation'
)
@click.option(
    '-N', '--no-shell',
    is_flag=True,
    help="Don't execute shell (for port forwarding)"
)
@click.argument('command', nargs=-1)
@click.pass_context
@async_command
async def ssh(
    ctx: click.Context,
    destination: str,
    login: Optional[str],
    identity: Optional[str],
    tty: bool,
    no_shell: bool,
    command: tuple,
) -> None:
    """
    SSH through wormhole.

    Connect to an SSH server running on a wormhole code. The destination
    can be just a code or user@code format.

    \b
    Examples:
        # Connect to SSH server (will prompt for username/password)
        $ wh ssh 7-guitar-sunset

        # Connect with specific username
        $ wh ssh user@7-guitar-sunset
        $ wh ssh -l user 7-guitar-sunset

        # Run a command
        $ wh ssh 7-guitar-sunset ls -la

        # Use SSH key
        $ wh ssh -i ~/.ssh/id_rsa user@7-guitar-sunset

        # Connect using WNS address (persistent naming)
        $ wh ssh wh://abc123def456.wns
        $ wh ssh user@wh://abc123def456.wns
    """
    verbose = ctx.obj.get('verbose', 0)

    def status(msg: str) -> None:
        if verbose > 0:
            click.echo(f"[*] {msg}", err=True)

    # Parse destination (user@code or just code)
    if '@' in destination:
        username, code = destination.rsplit('@', 1)
    else:
        code = destination
        username = login

    if not username:
        username = click.prompt("Username")

    # Create wormhole manager
    manager = WormholeManager(
        relay_url=ctx.obj.get('relay'),
        transit_relay=ctx.obj.get('transit'),
        on_status=status if verbose > 0 else None,
    )

    try:
        status(f"Connecting to {code}...")
        await manager.create_and_set_code(code)
        await manager.dilate()

        # Import SSH client
        from wh.ssh.client import WormholeSSHClient

        # Get password if no key provided
        password = None
        client_keys = []
        if identity:
            client_keys.append(identity)
        else:
            import os
            password = os.environ.get('WH_SSH_PASSWORD')
            if not password:
                password = click.prompt("Password", hide_input=True)

        # Create SSH client
        client = WormholeSSHClient(
            wormhole_manager=manager,
            username=username,
            password=password,
            client_keys=client_keys,
        )

        await client.connect()
        status("SSH connected")

        if command:
            # Run command
            cmd_str = ' '.join(command)
            result = await client.run_command(cmd_str)
            if result.stdout:
                click.echo(result.stdout, nl=False)
            if result.stderr:
                click.echo(result.stderr, nl=False, err=True)
            return result.returncode
        elif not no_shell:
            # Interactive shell
            await client.start_shell()

    except KeyboardInterrupt:
        click.echo("\nDisconnected", err=True)
    except Exception as e:
        if verbose > 0:
            raise
        raise click.ClickException(str(e))
    finally:
        await manager.close()
