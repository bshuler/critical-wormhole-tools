"""
WormholeSFTP - SFTP interactive file transfer over wormhole.

Provides SFTP functionality using AsyncSSH's SFTP implementation
tunneled through the wormhole connection.
"""

from typing import Optional, Any, List
from pathlib import Path
import os
import stat

import asyncssh

from wh.ssh.client import WormholeSSHClient


class WormholeSFTP:
    """
    SFTP interactive file transfer over wormhole.

    Example:
        manager = WormholeManager()
        await manager.create_and_set_code("7-guitar-sunset")
        await manager.dilate()

        sftp = WormholeSFTP(manager, username="user", password="pass")
        await sftp.connect()

        # List files
        files = await sftp.ls("/home/user")

        # Interactive mode
        await sftp.interactive_loop()
    """

    def __init__(
        self,
        wormhole_manager: Any,
        username: str,
        password: Optional[str] = None,
        client_keys: Optional[list] = None,
    ):
        """
        Initialize SFTP client.

        Args:
            wormhole_manager: A dilated WormholeManager instance.
            username: SSH username.
            password: SSH password.
            client_keys: List of paths to private key files.
        """
        self.manager = wormhole_manager
        self.username = username
        self.password = password
        self.client_keys = client_keys or []
        self._ssh_client: Optional[WormholeSSHClient] = None
        self._sftp: Optional[asyncssh.SFTPClient] = None
        self._cwd = "/"
        self._local_cwd = os.getcwd()

    async def connect(self) -> None:
        """Establish SFTP session over wormhole."""
        self._ssh_client = WormholeSSHClient(
            wormhole_manager=self.manager,
            username=self.username,
            password=self.password,
            client_keys=self.client_keys,
        )
        conn = await self._ssh_client.connect()
        self._sftp = await conn.start_sftp_client()

        # Get initial directory
        self._cwd = await self._sftp.getcwd() or "/"

    async def ls(self, path: str = ".") -> List[asyncssh.SFTPName]:
        """
        List directory contents.

        Args:
            path: Directory path to list.

        Returns:
            List of SFTPName objects with file information.
        """
        if not self._sftp:
            raise RuntimeError("Not connected")

        # Resolve relative paths
        if not path.startswith("/"):
            path = os.path.join(self._cwd, path)

        return await self._sftp.readdir(path)

    async def cd(self, path: str) -> str:
        """
        Change remote directory.

        Args:
            path: Directory to change to.

        Returns:
            New current directory.
        """
        if not self._sftp:
            raise RuntimeError("Not connected")

        # Resolve relative paths
        if not path.startswith("/"):
            path = os.path.join(self._cwd, path)

        # Normalize and validate
        path = os.path.normpath(path)

        # Check if directory exists
        file_stat = await self._sftp.stat(path)
        if not file_stat.permissions or not stat.S_ISDIR(file_stat.permissions):
            raise ValueError(f"Not a directory: {path}")

        self._cwd = path
        return self._cwd

    async def pwd(self) -> str:
        """Get current remote directory."""
        return self._cwd

    async def lpwd(self) -> str:
        """Get current local directory."""
        return self._local_cwd

    async def lcd(self, path: str) -> str:
        """
        Change local directory.

        Args:
            path: Local directory to change to.

        Returns:
            New local directory.
        """
        if not path.startswith("/"):
            path = os.path.join(self._local_cwd, path)

        path = os.path.normpath(path)

        if not os.path.isdir(path):
            raise ValueError(f"Not a directory: {path}")

        self._local_cwd = path
        return self._local_cwd

    async def get(
        self,
        remote_path: str,
        local_path: Optional[str] = None,
    ) -> None:
        """
        Download a file.

        Args:
            remote_path: Remote file path.
            local_path: Local destination (default: current local dir).
        """
        if not self._sftp:
            raise RuntimeError("Not connected")

        # Resolve remote path
        if not remote_path.startswith("/"):
            remote_path = os.path.join(self._cwd, remote_path)

        # Determine local path
        if local_path is None:
            local_path = os.path.join(
                self._local_cwd,
                os.path.basename(remote_path)
            )
        elif not local_path.startswith("/"):
            local_path = os.path.join(self._local_cwd, local_path)

        await self._sftp.get(remote_path, local_path)

    async def put(
        self,
        local_path: str,
        remote_path: Optional[str] = None,
    ) -> None:
        """
        Upload a file.

        Args:
            local_path: Local file path.
            remote_path: Remote destination (default: current remote dir).
        """
        if not self._sftp:
            raise RuntimeError("Not connected")

        # Resolve local path
        if not local_path.startswith("/"):
            local_path = os.path.join(self._local_cwd, local_path)

        # Determine remote path
        if remote_path is None:
            remote_path = os.path.join(
                self._cwd,
                os.path.basename(local_path)
            )
        elif not remote_path.startswith("/"):
            remote_path = os.path.join(self._cwd, remote_path)

        await self._sftp.put(local_path, remote_path)

    async def mkdir(self, path: str) -> None:
        """Create remote directory."""
        if not self._sftp:
            raise RuntimeError("Not connected")

        if not path.startswith("/"):
            path = os.path.join(self._cwd, path)

        await self._sftp.mkdir(path)

    async def rm(self, path: str) -> None:
        """Remove remote file."""
        if not self._sftp:
            raise RuntimeError("Not connected")

        if not path.startswith("/"):
            path = os.path.join(self._cwd, path)

        await self._sftp.remove(path)

    async def rmdir(self, path: str) -> None:
        """Remove remote directory."""
        if not self._sftp:
            raise RuntimeError("Not connected")

        if not path.startswith("/"):
            path = os.path.join(self._cwd, path)

        await self._sftp.rmdir(path)

    async def execute_command(self, line: str) -> bool:
        """
        Execute an SFTP command.

        Args:
            line: Command line to execute.

        Returns:
            True to continue, False to quit.
        """
        parts = line.strip().split()
        if not parts:
            return True

        cmd = parts[0].lower()
        args = parts[1:]

        try:
            if cmd in ("quit", "exit", "bye"):
                return False
            elif cmd == "ls":
                path = args[0] if args else "."
                entries = await self.ls(path)
                for entry in entries:
                    print(self._format_entry(entry))
            elif cmd == "cd":
                path = args[0] if args else "/"
                new_dir = await self.cd(path)
                print(f"Changed to: {new_dir}")
            elif cmd == "pwd":
                print(await self.pwd())
            elif cmd == "lpwd":
                print(await self.lpwd())
            elif cmd == "lcd":
                path = args[0] if args else os.path.expanduser("~")
                new_dir = await self.lcd(path)
                print(f"Local directory: {new_dir}")
            elif cmd == "get":
                if not args:
                    print("Usage: get <remote_path> [local_path]")
                else:
                    remote = args[0]
                    local = args[1] if len(args) > 1 else None
                    await self.get(remote, local)
                    print(f"Downloaded: {remote}")
            elif cmd == "put":
                if not args:
                    print("Usage: put <local_path> [remote_path]")
                else:
                    local = args[0]
                    remote = args[1] if len(args) > 1 else None
                    await self.put(local, remote)
                    print(f"Uploaded: {local}")
            elif cmd == "mkdir":
                if not args:
                    print("Usage: mkdir <path>")
                else:
                    await self.mkdir(args[0])
                    print(f"Created: {args[0]}")
            elif cmd == "rm":
                if not args:
                    print("Usage: rm <path>")
                else:
                    await self.rm(args[0])
                    print(f"Removed: {args[0]}")
            elif cmd == "rmdir":
                if not args:
                    print("Usage: rmdir <path>")
                else:
                    await self.rmdir(args[0])
                    print(f"Removed directory: {args[0]}")
            elif cmd == "help":
                self._print_help()
            else:
                print(f"Unknown command: {cmd}")
                print("Type 'help' for available commands")
        except Exception as e:
            print(f"Error: {e}")

        return True

    def _format_entry(self, entry: asyncssh.SFTPName) -> str:
        """Format a directory entry for display."""
        # Get file type indicator
        if entry.attrs.permissions:
            if stat.S_ISDIR(entry.attrs.permissions):
                type_char = "d"
            elif stat.S_ISLNK(entry.attrs.permissions):
                type_char = "l"
            else:
                type_char = "-"
        else:
            type_char = "?"

        # Format size
        size = entry.attrs.size if entry.attrs.size else 0

        return f"{type_char} {size:>10}  {entry.filename}"

    def _print_help(self) -> None:
        """Print help message."""
        print("""Available commands:
  ls [path]           List directory
  cd <path>           Change remote directory
  pwd                 Print remote working directory
  lcd <path>          Change local directory
  lpwd                Print local working directory
  get <remote> [local]  Download file
  put <local> [remote]  Upload file
  mkdir <path>        Create directory
  rm <path>           Remove file
  rmdir <path>        Remove directory
  help                Show this help
  quit/exit/bye       Close session""")

    async def interactive_loop(self) -> None:
        """Run interactive SFTP shell."""
        try:
            import readline  # Enable line editing
        except ImportError:
            pass

        print("SFTP session started. Type 'help' for commands.")

        while True:
            try:
                line = input(f"sftp {self._cwd}> ")
                if not await self.execute_command(line):
                    break
            except EOFError:
                break
            except KeyboardInterrupt:
                print()
                break

        print("Goodbye!")

    async def close(self) -> None:
        """Close the SFTP session."""
        if self._sftp:
            self._sftp.exit()
            self._sftp = None
        if self._ssh_client:
            await self._ssh_client.close()
            self._ssh_client = None

    async def __aenter__(self) -> "WormholeSFTP":
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()
