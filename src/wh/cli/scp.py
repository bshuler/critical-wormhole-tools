"""
wh scp - Secure copy through wormhole.

Copy files to/from a remote machine using wormhole addressing.
"""

import click
from typing import Optional

from wh.cli.main import async_command
from wh.core.wormhole_manager import WormholeManager


@click.command()
@click.argument('source')
@click.argument('destination')
@click.option(
    '-r', '--recursive',
    is_flag=True,
    help='Recursively copy directories'
)
@click.option(
    '-p', '--preserve',
    is_flag=True,
    help='Preserve file permissions and times'
)
@click.option(
    '-l', '--login',
    help='Username for SSH login'
)
@click.option(
    '-i', '--identity',
    type=click.Path(exists=True),
    help='Path to private key file'
)
@click.pass_context
@async_command
async def scp(
    ctx: click.Context,
    source: str,
    destination: str,
    recursive: bool,
    preserve: bool,
    login: Optional[str],
    identity: Optional[str],
) -> None:
    """
    Secure copy through wormhole.

    Copy files to or from a remote machine using wormhole code addressing.
    Format is similar to regular scp: [user@]code:path

    \b
    Examples:
        # Download file
        $ wh scp 7-guitar-sunset:/remote/file.txt ./local/

        # Upload file
        $ wh scp ./local/file.txt 7-guitar-sunset:/remote/

        # Copy directory recursively
        $ wh scp -r 7-guitar-sunset:/remote/dir ./local/

        # With username
        $ wh scp user@7-guitar-sunset:/file.txt .

        # Using WNS address (persistent naming)
        $ wh scp wh://abc123def456.wns:/file.txt .
        $ wh scp user@wh://abc123def456.wns:/file.txt .
    """
    verbose = ctx.obj.get('verbose', 0)

    def status(msg: str) -> None:
        if verbose > 0:
            click.echo(f"[*] {msg}", err=True)

    # Parse source and destination to determine direction
    def parse_remote(path: str) -> tuple:
        """
        Parse [user@]code:path format.

        Handles both regular codes and WNS addresses:
            - 7-guitar-sunset:/path
            - user@7-guitar-sunset:/path
            - wh://abc123.wns:/path
            - user@wh://abc123.wns:/path
        """
        if ':' not in path:
            return None, None, path  # Local path

        # Handle WNS addresses (wh://xxx.wns:path)
        # Need to skip the :// in the protocol
        if 'wh://' in path:
            # Find the colon after .wns
            wns_end = path.find('.wns')
            if wns_end != -1:
                # Find the colon after .wns
                path_sep = path.find(':', wns_end)
                if path_sep != -1:
                    remote_part = path[:path_sep]
                    remote_path = path[path_sep + 1:]
                else:
                    return None, None, path  # No path separator, treat as local
            else:
                return None, None, path  # Invalid WNS format
        else:
            remote_part, remote_path = path.split(':', 1)

        if '@' in remote_part:
            # Handle user@code or user@wh://xxx.wns
            # Use rsplit to handle @ in WNS address (there won't be any)
            user, code = remote_part.rsplit('@', 1)
            return user, code, remote_path
        return None, remote_part, remote_path

    src_user, src_code, src_path = parse_remote(source)
    dst_user, dst_code, dst_path = parse_remote(destination)

    # Determine if upload or download
    if src_code and dst_code:
        raise click.UsageError("Cannot copy between two remote hosts")
    if not src_code and not dst_code:
        raise click.UsageError("At least one path must be remote (code:path)")

    is_download = src_code is not None
    code = src_code or dst_code
    username = src_user or dst_user or login

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

        # Import SCP module
        from wh.transfer.scp import WormholeSCP

        # Get password if no key
        password = None
        if not identity:
            import os
            password = os.environ.get('WH_SSH_PASSWORD')
            if not password:
                password = click.prompt("Password", hide_input=True)

        scp_client = WormholeSCP(
            wormhole_manager=manager,
            username=username,
            password=password,
        )

        if is_download:
            status(f"Downloading {src_path} -> {dst_path}")
            await scp_client.download(
                remote_path=src_path,
                local_path=dst_path,
                recursive=recursive,
                preserve=preserve,
            )
            click.echo(f"Downloaded: {dst_path}")
        else:
            status(f"Uploading {src_path} -> {dst_path}")
            await scp_client.upload(
                local_path=src_path,
                remote_path=dst_path,
                recursive=recursive,
                preserve=preserve,
            )
            click.echo(f"Uploaded: {dst_path}")

    except KeyboardInterrupt:
        click.echo("\nCancelled", err=True)
    except Exception as e:
        if verbose > 0:
            raise
        raise click.ClickException(str(e))
    finally:
        await manager.close()
