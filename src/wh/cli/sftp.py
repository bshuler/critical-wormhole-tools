"""
wh sftp - Interactive file transfer through wormhole.

SFTP client with interactive shell for file browsing and transfer.
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
    '-b', '--batch',
    type=click.Path(exists=True),
    help='Batch file with commands to execute'
)
@click.pass_context
@async_command
async def sftp(
    ctx: click.Context,
    destination: str,
    login: Optional[str],
    identity: Optional[str],
    batch: Optional[str],
) -> None:
    """
    Interactive file transfer through wormhole.

    Opens an SFTP session for interactive file browsing and transfer.
    Supports standard SFTP commands like ls, cd, get, put, mkdir, rm.

    \b
    Examples:
        # Interactive session
        $ wh sftp 7-guitar-sunset
        sftp> ls
        sftp> get file.txt
        sftp> put local.txt
        sftp> quit

        # With username
        $ wh sftp user@7-guitar-sunset

        # Batch mode
        $ wh sftp -b commands.txt 7-guitar-sunset

        # Using WNS address (persistent naming)
        $ wh sftp wh://abc123def456.wns
        $ wh sftp user@wh://abc123def456.wns

    \b
    Available commands:
        ls [path]       List directory
        cd <path>       Change directory
        pwd             Print working directory
        get <remote> [local]   Download file
        put <local> [remote]   Upload file
        mkdir <path>    Create directory
        rm <path>       Remove file
        rmdir <path>    Remove directory
        quit/exit       Close session
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

        # Import SFTP module
        from wh.transfer.sftp import WormholeSFTP

        # Get password if no key
        password = None
        if not identity:
            import os
            password = os.environ.get('WH_SSH_PASSWORD')
            if not password:
                password = click.prompt("Password", hide_input=True)

        sftp_client = WormholeSFTP(
            wormhole_manager=manager,
            username=username,
            password=password,
        )

        await sftp_client.connect()
        status("SFTP connected")

        if batch:
            # Batch mode
            with open(batch, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        await sftp_client.execute_command(line)
        else:
            # Interactive mode
            await sftp_client.interactive_loop()

    except KeyboardInterrupt:
        click.echo("\nDisconnected", err=True)
    except Exception as e:
        if verbose > 0:
            raise
        raise click.ClickException(str(e))
    finally:
        await manager.close()
