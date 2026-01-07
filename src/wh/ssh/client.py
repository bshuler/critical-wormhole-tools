"""
WormholeSSHClient - SSH client that connects through wormhole.

Uses AsyncSSH with a custom tunnel adapter to route SSH traffic
through the wormhole dilation subchannel.
"""

from typing import Optional, List, Any
import asyncio
import sys
import tty
import termios

import asyncssh

from wh.ssh.tunnel import WormholeTunnel


class WormholeSSHClient:
    """
    SSH client that connects through a wormhole tunnel.

    Example:
        manager = WormholeManager()
        await manager.create_and_set_code("7-guitar-sunset")
        await manager.dilate()

        client = WormholeSSHClient(manager, username="user", password="pass")
        await client.connect()
        result = await client.run_command("ls -la")
        print(result.stdout)
    """

    def __init__(
        self,
        wormhole_manager: Any,
        username: str,
        password: Optional[str] = None,
        client_keys: Optional[List[str]] = None,
        known_hosts: Optional[str] = None,
    ):
        """
        Initialize SSH client.

        Args:
            wormhole_manager: A dilated WormholeManager instance.
            username: SSH username.
            password: SSH password (optional if using keys).
            client_keys: List of paths to private key files.
            known_hosts: Path to known_hosts file (or None to skip verification).
        """
        self.manager = wormhole_manager
        self.username = username
        self.password = password
        self.client_keys = client_keys or []
        self.known_hosts = known_hosts
        self._conn: Optional[asyncssh.SSHClientConnection] = None

    async def connect(self) -> asyncssh.SSHClientConnection:
        """
        Establish SSH connection over wormhole.

        Returns:
            The SSH connection object.
        """
        # Create tunnel adapter
        tunnel = WormholeTunnel(self.manager)

        # Build connection options
        connect_kwargs = {
            'host': 'wormhole',  # Placeholder, tunnel handles routing
            'port': 22,          # Placeholder
            'tunnel': tunnel,
            'username': self.username,
            'known_hosts': None,  # Skip host key verification for wormhole
        }

        if self.password:
            connect_kwargs['password'] = self.password

        if self.client_keys:
            connect_kwargs['client_keys'] = self.client_keys

        # Connect via AsyncSSH with our custom tunnel
        self._conn = await asyncssh.connect(**connect_kwargs)

        return self._conn

    async def run_command(
        self,
        command: str,
        check: bool = False,
    ) -> asyncssh.SSHCompletedProcess:
        """
        Execute a command on the remote host.

        Args:
            command: Command string to execute.
            check: If True, raise exception on non-zero exit.

        Returns:
            SSHCompletedProcess with stdout, stderr, and returncode.
        """
        if not self._conn:
            await self.connect()

        return await self._conn.run(command, check=check)

    async def start_shell(self) -> None:
        """
        Start an interactive shell session.

        Sets up terminal for raw mode and handles input/output.
        """
        if not self._conn:
            await self.connect()

        # Get terminal size
        try:
            import shutil
            cols, rows = shutil.get_terminal_size()
        except Exception:
            cols, rows = 80, 24

        # Save terminal settings
        old_settings = None
        stdin_fd = sys.stdin.fileno()

        try:
            # Set terminal to raw mode for proper key handling
            old_settings = termios.tcgetattr(stdin_fd)
            tty.setraw(stdin_fd)

            # Create process with PTY
            async with self._conn.create_process(
                term_type='xterm-256color',
                term_size=(cols, rows),
            ) as process:
                # Handle input/output concurrently
                await asyncio.gather(
                    self._pump_stdin(process.stdin),
                    self._pump_stdout(process.stdout),
                    self._pump_stderr(process.stderr),
                    return_exceptions=True
                )

        finally:
            # Restore terminal settings
            if old_settings:
                termios.tcsetattr(stdin_fd, termios.TCSADRAIN, old_settings)

    async def _pump_stdin(self, writer: Any) -> None:
        """Read from local stdin and write to remote."""
        loop = asyncio.get_event_loop()

        try:
            while True:
                # Read in executor to avoid blocking
                data = await loop.run_in_executor(
                    None,
                    lambda: sys.stdin.buffer.read(1)
                )
                if not data:
                    writer.write_eof()
                    break
                writer.write(data)
                await writer.drain()
        except Exception:
            pass

    async def _pump_stdout(self, reader: Any) -> None:
        """Read from remote stdout and write to local."""
        try:
            while True:
                data = await reader.read(4096)
                if not data:
                    break
                sys.stdout.buffer.write(data)
                sys.stdout.buffer.flush()
        except Exception:
            pass

    async def _pump_stderr(self, reader: Any) -> None:
        """Read from remote stderr and write to local."""
        try:
            while True:
                data = await reader.read(4096)
                if not data:
                    break
                sys.stderr.buffer.write(data)
                sys.stderr.buffer.flush()
        except Exception:
            pass

    async def start_sftp_client(self) -> asyncssh.SFTPClient:
        """
        Start an SFTP client session.

        Returns:
            SFTPClient for file operations.
        """
        if not self._conn:
            await self.connect()

        return await self._conn.start_sftp_client()

    async def close(self) -> None:
        """Close the SSH connection."""
        if self._conn:
            self._conn.close()
            await self._conn.wait_closed()
            self._conn = None

    async def __aenter__(self) -> "WormholeSSHClient":
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()
